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
