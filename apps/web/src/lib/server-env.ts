/** Server-only module (imported by route handlers / NextAuth only). */
/** Server-side config (never exposed via NEXT_PUBLIC_*). API base without `/api/v1`. */
export const API_URL = (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000").replace(/\/+$/, "");
export const API_BASE = `${API_URL}/api/v1`;
export const DEMO_MODE = process.env.DEMO_MODE === "true" || process.env.NEXT_PUBLIC_DEMO_MODE === "true";

/** Demo quick-login (SCR-13, DEMO_MODE only): password resolved server-side, never sent to the browser. */
const DEMO_PASSWORD_ENV: Record<string, readonly string[]> = {
  "ceo@abc.demo": ["DEMO_CEO_PASSWORD"],
  "cfo@abc.demo": ["DEMO_CFO_PASSWORD"],
  "sales@abc.demo": ["DEMO_VP_SALES_PASSWORD", "DEMO_SALES_PASSWORD"],
  "hr@abc.demo": ["DEMO_HR_MANAGER_PASSWORD", "DEMO_HR_PASSWORD"],
  "reviewer@abc.demo": ["DEMO_REVIEWER_PASSWORD"],
};

export function demoPasswordFor(email: string): string | undefined {
  if (!DEMO_MODE) return undefined;
  for (const name of DEMO_PASSWORD_ENV[email.toLowerCase()] ?? []) {
    const v = process.env[name];
    if (v) return v;
  }
  return process.env.DEMO_PASSWORD || undefined;
}

/**
 * T-604 (R-DEC-25): `API_MODE=mock` serves `/api/backend/*` + login from `src/mocks` (fixtures =
 * `seed_snapshot.json`) so the FE runs without the backend. Server env only (never NEXT_PUBLIC);
 * refused when `NODE_ENV=production` — a production build must always talk to the real API.
 */
export type ApiMode = "real" | "mock";

export function resolveApiMode(env: Record<string, string | undefined> = process.env): ApiMode {
  const raw = (env.API_MODE ?? "real").trim().toLowerCase();
  if (raw !== "real" && raw !== "mock") throw new Error(`API_MODE must be "real" or "mock", got "${raw}"`);
  if (raw === "mock" && env.NODE_ENV === "production") {
    throw new Error("API_MODE=mock is forbidden when NODE_ENV=production");
  }
  return raw;
}

export function isMockMode(): boolean {
  return resolveApiMode() === "mock";
}
