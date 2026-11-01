/**
 * "AI đã làm" feed logic (M3.2, R-DEC-130) — pure, UI-free so Vitest covers it without rendering.
 *
 * The feed shows the Autonomy-L3 actions the AI executed on the viewer's behalf (status
 * `executed`), newest first, each still undoable for 24h (06 §5.1, DEC-134). `undoable` mirrors the
 * backend window: `can_undo` true AND `undo_deadline` in the future; `remainingMs` drives the
 * countdown label.
 */
import type { Api } from "@aureon/shared-types";

export type FeedAction = Pick<
  Api.AIActionOut,
  "id" | "action_name" | "autonomy_level" | "status" | "executed_at" | "undo_deadline" | "can_undo"
> & { created_at?: string | null };

/** Executed L3 actions, newest first (by executed_at, falling back to created_at). */
export function feedActions(actions: FeedAction[]): FeedAction[] {
  return actions
    .filter((a) => a.status === "executed" && a.autonomy_level === "L3")
    .sort((a, b) => stamp(b) - stamp(a));
}

function stamp(a: FeedAction): number {
  const iso = a.executed_at ?? a.created_at ?? null;
  const t = iso ? Date.parse(iso) : NaN;
  return Number.isNaN(t) ? 0 : t;
}

/** Whether the viewer can still undo (within the 24h window). `now` injectable for tests. */
export function undoable(a: FeedAction, now: number = Date.now()): boolean {
  if (a.status !== "executed" || a.can_undo === false) return false;
  if (!a.undo_deadline) return false;
  const deadline = Date.parse(a.undo_deadline);
  return !Number.isNaN(deadline) && deadline > now;
}

/** Milliseconds left in the undo window, clamped to ≥ 0 (0 when past/missing). */
export function remainingMs(a: FeedAction, now: number = Date.now()): number {
  if (!a.undo_deadline) return 0;
  const deadline = Date.parse(a.undo_deadline);
  if (Number.isNaN(deadline)) return 0;
  return Math.max(0, deadline - now);
}

/** "23h 59m" / "9m" / "0m" — a coarse countdown for the undo hint (no seconds). */
export function remainingLabel(ms: number): string {
  const totalMin = Math.floor(ms / 60_000);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}
