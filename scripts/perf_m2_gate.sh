#!/usr/bin/env bash
# Perf smoke for the M2 gate (T-738, R-DEC-114) against the real compose stack.
#   NFR-PERF-01: dashboard load p95 < 3s.
#   NFR-PERF-02: chat first token (TTFT) < 2s (streaming).
# Measures over the live API (demo-replay gateway) — no new dependency, pure curl + bash.
# Usage: scripts/perf_m2_gate.sh  (reads .env for DEMO_CEO_PASSWORD; API at $API_BASE)
set -euo pipefail
set -a; [ -f .env ] && . ./.env; set +a
API="${API_BASE:-http://127.0.0.1:4000/api/v1}"
N="${PERF_SAMPLES:-5}"

token() {
  curl -s -X POST "$API/auth/login" -H 'content-type: application/json' \
    -d "{\"email\":\"ceo@abc.demo\",\"password\":\"${DEMO_CEO_PASSWORD}\"}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['access_token'])"
}
TOKEN="$(token)"
AUTH="authorization: Bearer ${TOKEN}"

p95() { python3 -c "import sys;v=sorted(float(x) for x in sys.stdin.read().split());print(f'{v[min(len(v)-1,int(round(0.95*(len(v)-1))))]:.3f}')"; }
mean() { python3 -c "import sys;v=[float(x) for x in sys.stdin.read().split()];print(f'{sum(v)/len(v):.3f}')"; }

echo "== Dashboard load (NFR-PERF-01, p95 < 3.0s) =="
dash=""
for _ in $(seq 1 "$N"); do
  t=$(curl -s -o /dev/null -w "%{time_total}" "$API/reporting/dashboards/executive" -H "$AUTH")
  dash="$dash $t"
done
echo "  samples:$dash"
echo "  mean=$(echo $dash | mean)s  p95=$(echo $dash | p95)s"

echo "== Chat TTFT (NFR-PERF-02, first token < 2.0s) =="
ttfts=""
for _ in $(seq 1 "$N"); do
  idem=$(python3 -c "import uuid;print(uuid.uuid4())")
  start=$(python3 -c "import time;print(time.time())")
  # read the stream until the first `event: token`, then stop
  curl -s -N -X POST "$API/ai/chat/stream" -H "$AUTH" \
    -H "content-type: application/json" -H "idempotency-key: $idem" \
    -d '{"message":"Doanh thu Q3?","locale":"vi"}' --max-time 30 \
    | grep -m1 "event: token" >/dev/null || true
  ttft=$(python3 -c "import time;print(f'{time.time()-$start:.3f}')")
  ttfts="$ttfts $ttft"
done
echo "  samples:$ttfts"
echo "  mean=$(echo $ttfts | mean)s  p95=$(echo $ttfts | p95)s"
