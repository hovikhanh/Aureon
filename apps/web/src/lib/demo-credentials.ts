/**
 * Server-only (T-610c, R-DEC-28): resolves the demo password that SCR-13 autofills into the login
 * form. Enabled only when `DEMO_MODE=true` AND the server-only flag `DEMO_LOGIN_AUTOFILL=true`
 * (`NODE_ENV` cannot be the guard: `next start` and the Docker image always run as production).
 * Only e-mails in `DEMO_ACCOUNTS` are answered; anything else → 404 `NOT_FOUND` (no oracle).
 * Never logs the password; never read from `NEXT_PUBLIC_*` (CLAUDE §5.8, §6.4).
 */
import { DEMO_ACCOUNTS } from "./demo-accounts";
import { demoPasswordFor, isDemoMode } from "./server-env";

type Env = Record<string, string | undefined>;

export type DemoCredentialsResult =
  | { status: 200; body: { data: { email: string; password: string } } }
  | { status: 404; body: { error: { code: "NOT_FOUND"; message: string; details: Record<string, never> } } };

const NOT_FOUND: DemoCredentialsResult = {
  status: 404,
  body: { error: { code: "NOT_FOUND", message: "Not found", details: {} } },
};

export function isDemoAutofillEnabled(env: Env = process.env): boolean {
  return isDemoMode(env) && env.DEMO_LOGIN_AUTOFILL === "true";
}

export function resolveDemoCredentials(rawEmail: unknown, env: Env = process.env): DemoCredentialsResult {
  if (!isDemoAutofillEnabled(env) || typeof rawEmail !== "string") return NOT_FOUND;
  const email = rawEmail.trim().toLowerCase();
  if (!DEMO_ACCOUNTS.some((a) => a.email === email)) return NOT_FOUND;
  // API_MODE=mock (refused in production): the mock accepts only MOCK_LOGIN_PASSWORD.
  const password = (env.API_MODE ?? "").trim().toLowerCase() === "mock" ? env.MOCK_LOGIN_PASSWORD : demoPasswordFor(email, env);
  if (!password) return NOT_FOUND;
  return { status: 200, body: { data: { email, password } } };
}
