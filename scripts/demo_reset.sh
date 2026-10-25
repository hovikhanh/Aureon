#!/usr/bin/env bash
# Demo reset (T-517): clean, reproducible demo state WITHOUT dropping schema or volumes.
#   1. TRUNCATE every table in the 10 module schemas (keeps platform.alembic_version)
#   2. re-seed (`python -m app.seed`, idempotent, DEC-062)
#   3. clear object storage (local IDP store var/idp-storage + MinIO buckets)
#   4. purge Celery queues + restart worker/beat
#   5. put 1 INVOICE in NEEDS_REVIEW (fixture extraction, no live LLM)
#   6. verify (seed v3, T-603b/T-649): 7 departments · 154 employees · 10 demo users + AI actor ·
#      34 metrics · 14 OPEN alerts · 1 NEEDS_REVIEW · 6 AI agents · 0 autonomy policies ·
#      onboarding completed; then export seed_snapshot.json (mock FE)
# Usage: ./scripts/demo_reset.sh [-y] [--host]
#   -y      skips the confirmation prompt
#   --host  runs Python on the host venv even when the api container is up (the image does not
#           mount the source — use it until the image is rebuilt with the current code)
# DEV/DEMO ONLY — refuses APP_ENV=production. Never use `docker compose down -v` instead.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE=(docker compose -f docker-compose.full.yml)
[[ -f .env ]] || { echo "✗ .env missing (cp .env.example .env)" >&2; exit 1; }
envval() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | sed 's/^"\(.*\)"$/\1/'; }
PG_USER="$(envval POSTGRES_USER)"; PG_DB="$(envval POSTGRES_DB)"
[[ "$(envval APP_ENV)" == "production" ]] && { echo "✗ APP_ENV=production — refusing to reset" >&2; exit 1; }

YES=0; HOST=0
for a in "$@"; do case "$a" in -y) YES=1 ;; --host) HOST=1 ;; *) echo "✗ unknown arg $a" >&2; exit 2 ;; esac; done
if [[ $YES == 0 && -t 0 ]]; then
  read -r -p "Reset ALL demo data in database '$PG_DB'? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || { echo "aborted"; exit 1; }
fi

psql_q() { "${COMPOSE[@]}" exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 -Atc "$1"; }
api_running() { [[ $HOST == 0 && -n "$("${COMPOSE[@]}" ps -q --status running api 2>/dev/null)" ]]; }
# Run Python in the api container when the full stack is up, else on the host venv.
py() {
  if api_running; then "${COMPOSE[@]}" exec -T api python "$@";
  else PYTHONPATH="$ROOT/apps/api/src:$ROOT/apps/api" "$ROOT/.venv/bin/python" "$@"; fi
}

echo "▸ 1/6 truncate module schemas"
psql_q "DO \$\$ DECLARE t text; BEGIN
  SELECT string_agg(format('%I.%I', schemaname, tablename), ', ') INTO t FROM pg_tables
   WHERE schemaname IN ('auth','platform','finance','sales','hr','product','risk','execution','ai','idp')
     AND NOT (schemaname = 'platform' AND tablename = 'alembic_version');
  EXECUTE 'TRUNCATE ' || t || ' RESTART IDENTITY CASCADE';
END \$\$;"

echo "▸ 2/6 seed"
py -m app.seed 2>&1 | grep -E "seed (created|updated|unchanged|skipped):" || true

echo "▸ 3/6 clear object storage"
find "$ROOT/var/idp-storage" -mindepth 1 -delete 2>/dev/null || true
"${COMPOSE[@]}" exec -T minio sh -c \
  'mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null &&
   for b in $(mc ls local | awk "{print \$NF}"); do mc rm --recursive --force "local/$b" >/dev/null || true; done' \
  2>/dev/null && echo "  minio buckets emptied" || echo "  minio: skipped (not running / no shell)"

echo "▸ 4/6 purge Celery queues + restart worker/beat"
if [[ -n "$("${COMPOSE[@]}" ps -q --status running celery-worker 2>/dev/null)" ]]; then
  "${COMPOSE[@]}" exec -T celery-worker celery -A app.worker purge -f -Q default,idp,events >/dev/null || true
  "${COMPOSE[@]}" exec -T redis redis-cli -n 0 FLUSHDB >/dev/null  # rate-limit / cache keys
  "${COMPOSE[@]}" restart celery-worker celery-beat >/dev/null
  echo "  worker + beat restarted"
else
  echo "  celery not running in compose — skipped"
fi

echo "▸ 5/6 seed 1 invoice NEEDS_REVIEW"
if api_running; then
  docker cp apps/web/e2e/support/seed_review_doc.py "$("${COMPOSE[@]}" ps -q api)":/tmp/seed_review_doc.py
  "${COMPOSE[@]}" exec -T -e PYTHONPATH=/app/apps/api/src:/app/apps/api -w /app api \
    python /tmp/seed_review_doc.py | tail -1
else
  py apps/web/e2e/support/seed_review_doc.py | tail -1
fi

echo "▸ 6/6 verify"
users=$(psql_q "SELECT count(*) FROM auth.users WHERE email LIKE '%@abc.demo' AND NOT is_service_account AND is_active")
ai=$(psql_q "SELECT count(*) FROM auth.users WHERE is_service_account AND email = 'ai-agent@abc.demo'")
depts=$(psql_q "SELECT count(*) FROM hr.departments WHERE deleted_at IS NULL")
emps=$(psql_q "SELECT count(*) FROM hr.employees WHERE deleted_at IS NULL")
metrics=$(psql_q "SELECT count(*) FROM platform.metrics")
alerts=$(psql_q "SELECT count(*) FROM platform.alerts WHERE status = 'OPEN'")
review=$(psql_q "SELECT count(*) FROM idp.source_documents WHERE status = 'NEEDS_REVIEW' AND deleted_at IS NULL")
agents=$(psql_q "SELECT count(*) FROM ai.agent_profiles")
policies=$(psql_q "SELECT count(*) FROM ai.autonomy_policies")
onboarding=$(psql_q "SELECT value->>'status' FROM platform.system_settings WHERE key = 'onboarding.state'")
ok=1
check() { if [[ "$2" == "$3" ]]; then echo "  ✔ $1: $2"; else echo "  ✗ $1: $2 (expected $3)"; ok=0; fi; }
check "departments" "$depts" 7
check "employees" "$emps" 154
check "demo users" "$users" 10
check "AI actor" "$ai" 1
check "metrics" "$metrics" 34
check "open alerts" "$alerts" 14
check "invoices NEEDS_REVIEW" "$review" 1
check "AI agents" "$agents" 6
check "autonomy policies" "$policies" 0
check "onboarding" "$onboarding" completed
echo "  (all users: $(psql_q 'SELECT count(*) FROM auth.users') — existing sessions must log in again)"
[[ $ok == 1 ]] || { echo "✗ demo reset verification failed" >&2; exit 1; }
PYTHONPATH="$ROOT/apps/api/src:$ROOT/apps/api" "$ROOT/.venv/bin/python" -m app.seed.snapshot
echo "✅ demo reset complete"
