import { execFileSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");

function rootEnv(): Record<string, string> {
  const file = path.join(ROOT, ".env");
  if (!existsSync(file)) return {};
  const out: Record<string, string> = {};
  for (const line of readFileSync(file, "utf8").split(/\r?\n/)) {
    const m = /^([A-Z0-9_]+)=(.*)$/.exec(line.trim());
    if (m?.[1]) out[m[1]] = (m[2] ?? "").replace(/^"(.*)"$/, "$1");
  }
  return out;
}

function runPy(args: string[]): string {
  return execFileSync(path.join(ROOT, ".venv/bin/python"), [path.join(ROOT, "apps/web/e2e/support/seed_review_doc.py"), ...args], {
    cwd: ROOT,
    env: { ...process.env, ...rootEnv(), PYTHONPATH: "apps/api/src:apps/api" },
    encoding: "utf8",
    timeout: 120_000,
  });
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
