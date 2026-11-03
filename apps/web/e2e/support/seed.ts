import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");

export function rootEnv(): Record<string, string> {
  // E2E_ENV_FILE: a separate real stack (own DB/Redis) points the support scripts at its env file.
  const file = process.env.E2E_ENV_FILE ? path.resolve(ROOT, process.env.E2E_ENV_FILE) : path.join(ROOT, ".env");
  if (!existsSync(file)) return {};
  const out: Record<string, string> = {};
  for (const line of readFileSync(file, "utf8").split(/\r?\n/)) {
    const m = /^([A-Z0-9_]+)=(.*)$/.exec(line.trim());
    if (m?.[1]) out[m[1]] = unquote(m[2] ?? "");
  }
  return out;
}

/**
 * dotenv value → the string the API sees (like python-dotenv / docker compose): strip ONE pair of
 * matching single or double quotes. Only `"…"` was stripped before, so `MODEL_PRICING_JSON='{…}'`
 * reached `ConfigService` with literal quotes → `json.loads` failed at char 0 → settings
 * validation error (R-DEC-167, M6).
 */
export function unquote(v: string): string {
  const t = v.trim();
  return t.length >= 2 && (t[0] === '"' || t[0] === "'") && t.at(-1) === t[0] ? t.slice(1, -1) : t;
}

const SECRET_NAME = /(key|secret|password|passwd|token|dsn)/i;

/**
 * Mask secret-looking text before a support script's output can reach a Playwright error, report
 * or trace (R-DEC-167: a settings validation error once printed a demo password into E2E logs):
 * pydantic `input_value={…}` dumps, `NAME=value` / `'name': 'value'` pairs whose name looks secret,
 * and credentials inside URLs.
 */
export function redactSecrets(text: string): string {
  return text
    .replace(/input_value=\{[^\n]*/g, "input_value=<redacted>")
    .replace(/(['"]?)([A-Za-z0-9_]+)\1\s*([:=])\s*(['"])(.*?)\4/g, (m, q: string, name: string, sep: string, vq: string) =>
      SECRET_NAME.test(name) ? `${q}${name}${q}${sep} ${vq}<redacted>${vq}` : m)
    .replace(/\b([A-Za-z0-9_]*(?:key|secret|password|passwd|token|dsn)[A-Za-z0-9_]*)=\S+/gi, "$1=<redacted>")
    .replace(/(\w+:\/\/)[^/\s:@]+:[^@\s]+@/g, "$1<redacted>@");
}

/**
 * Run an `e2e/support/*.py` helper against the env of the stack under test. A failure is rethrown
 * with stdout/stderr redacted (never the raw `execFileSync` error, which embeds stderr verbatim).
 */
export function runSupport(script: string, args: string[], { timeout = 120_000, env }: { timeout?: number; env?: NodeJS.ProcessEnv } = {}): string {
  try {
    return execFileSync(path.join(ROOT, ".venv/bin/python"), [path.join(ROOT, "apps/web/e2e/support", script), ...args], {
      cwd: ROOT,
      // the shell wins over the env file (like onboarding-real): a run against another stack
      // exports its DATABASE_URL/REDIS_URL instead of silently writing to the dev DB of `.env`
      env: env ?? { ...rootEnv(), ...process.env, PYTHONPATH: "apps/api/src:apps/api" },
      encoding: "utf8",
      timeout,
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (e) {
    const err = e as { status?: number; stdout?: string; stderr?: string };
    const tail = redactSecrets(`${err.stderr ?? ""}`).trim().split(/\r?\n/).slice(-8).join("\n");
    throw new Error(`support script ${script} ${args.join(" ")} failed (exit ${err.status ?? "?"}):\n${tail}`);
  }
}

function runPy(args: string[]): string {
  return runSupport("seed_review_doc.py", args);
}

/** Soft-delete E2E docs left in the review queue (keeps backend queue tests deterministic). */
export function cleanupReviewDocs(): void {
  runPy(["--cleanup"]);
}

/** Seed one INVOICE in NEEDS_REVIEW on the dev DB (fixture extraction — no live LLM). */
export function seedReviewDoc(): { document_id: string; invoice_number: string } {
  const out = runPy([]);
  const last = out.trim().split(/\r?\n/).at(-1) ?? "{}";
  return JSON.parse(last) as { document_id: string; invoice_number: string };
}

/** Seed + approve one INVOICE (ACT-create_invoice) so an IN invoice links to an IDP document. */
export function seedCommittedInvoice(): { document_id: string; invoice_number: string } {
  const last = runPy(["--commit"]).trim().split(/\r?\n/).at(-1) ?? "{}";
  return JSON.parse(last) as { document_id: string; invoice_number: string };
}
