/**
 * SCR-66 wizard logic (T-648F, 06 §3.4, 10 §7.2.5 EP-ADM-13/14) — pure, unit-tested.
 * The server state is the only source of truth: the current step is derived from `steps`.
 */
import type { Api } from "@aureon/shared-types";

export type OnboardingState = Api.OnboardingStateOut;
export const STEPS = ["company", "org_import", "review", "users", "goals_import", "finish"] as const;
export type Step = (typeof STEPS)[number];
export const REQUIRED_STEPS: readonly Step[] = ["company", "org_import", "users"];
export const MAX_USER_ROWS = 30;
export const MIN_PASSWORD = 12;

const closed = (s: OnboardingState, k: Step) => ["done", "skipped"].includes(s.steps?.[k]?.status ?? "pending");

/** Resume point after reload: first step not done/skipped; `finish` once every earlier step is closed. */
export function currentStep(s: OnboardingState): Step {
  if (s.status === "completed") return "finish";
  return STEPS.find((k) => k !== "finish" && !closed(s, k)) ?? "finish";
}

/** A step can be opened when it is the current one or any step before it; the summary (`finish`) is always open — "Finish" with missing steps → 422 `missing_steps` → back. */
export function canOpen(s: OnboardingState, k: Step): boolean {
  return k === "finish" || STEPS.indexOf(k) <= STEPS.indexOf(currentStep(s));
}

/** EP-ADM-14 `finish` 422 `details.missing_steps[]` → the first missing step to go back to. */
export function firstMissing(missing: unknown): Step | null {
  if (!Array.isArray(missing)) return null;
  return STEPS.find((k) => missing.includes(k)) ?? null;
}

export type ClockTone = "ok" | "warn" | "late";
const H = 3_600_000;
/** "Trong 1 ngày" clock: green ≤ 8 h, yellow ≤ 24 h, red > 24 h (06 §3.4 SCR-66). */
export function clockTone(elapsedMs: number): ClockTone {
  return elapsedMs <= 8 * H ? "ok" : elapsedMs <= 24 * H ? "warn" : "late";
}

/** Elapsed since `started_at` up to `completed_at` (or now) — `HH:MM` hours may exceed 24. */
export function elapsedMs(s: OnboardingState, now: number): number {
  if (!s.started_at) return 0;
  const end = s.completed_at ? Date.parse(s.completed_at) : now;
  return Math.max(0, end - Date.parse(s.started_at));
}
export function formatElapsed(ms: number): string {
  const m = Math.floor(ms / 60_000);
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

export interface MemberLite { employee_id: string; employee_code: string; full_name: string; department_id: string; is_head: boolean }
/** Suggested role (06 §3.4 step 4): department head → MGR (DIR when the admin picks a khối), others EMP. */
export const suggestRole = (m: MemberLite): "MGR" | "EMP" => (m.is_head ? "MGR" : "EMP");

/** Random initial password (≥ 12 chars, shown once) — Web Crypto, no ambiguous characters. */
export function randomPassword(len = 16, rnd: (n: number) => Uint32Array = (n) => globalThis.crypto.getRandomValues(new Uint32Array(n))): string {
  const abc = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%";
  return Array.from(rnd(Math.max(len, MIN_PASSWORD)), (x) => abc[x % abc.length]).join("");
}

/** Mapping targets the viewer cannot see (level-4 columns dropped for ADM — R-DEC-76) → set to null. */
export function dropHidden(mapping: Record<string, string | null>, visible: readonly string[]): { mapping: Record<string, string | null>; dropped: string[] } {
  const dropped: string[] = [];
  const out = Object.fromEntries(Object.entries(mapping).map(([h, f]) => {
    if (f && !visible.includes(f)) { dropped.push(h); return [h, null]; }
    return [h, f];
  }));
  return { mapping: out, dropped };
}
