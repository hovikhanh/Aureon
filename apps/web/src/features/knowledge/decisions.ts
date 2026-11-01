/**
 * Decision Log logic (M3.3, EP-43, 03 §3.5) — pure, UI-free so Vitest covers it without rendering.
 *
 * A decision (`Api.DecisionOut`) carries a set of 30/60/90-day review dates (`review_at`). A
 * decision is "review-due" when one of those dates has arrived and its outcome has not yet been
 * verified (`outcome_verified_at` empty) — that is the CEO's follow-up queue.
 */
import type { Api } from "@aureon/shared-types";

/** Parse an ISO date/instant to epoch ms; NaN-safe (missing/garbage → null). */
function ms(iso: string | null | undefined): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  return Number.isNaN(t) ? null : t;
}

/**
 * True when any scheduled review date is on/before `today` and the outcome is not yet verified.
 * `today` is injectable (ISO date or instant) so tests are deterministic.
 */
export function reviewDue(d: Api.DecisionOut, today: string | number = Date.now()): boolean {
  if (d.outcome_verified_at) return false;
  const now = typeof today === "number" ? today : ms(today);
  if (now === null) return false;
  return (d.review_at ?? []).some((r) => {
    const t = ms(r);
    return t !== null && t <= now;
  });
}

/**
 * The review date to surface: the soonest upcoming review (> today); if none are upcoming, the
 * most recent past-due one. Returns null when there are no review dates.
 */
export function nextReview(d: Api.DecisionOut, today: string | number = Date.now()): string | null {
  const now = typeof today === "number" ? today : (ms(today) ?? Date.now());
  const dated = (d.review_at ?? [])
    .map((r) => ({ iso: r, t: ms(r) }))
    .filter((x): x is { iso: string; t: number } => x.t !== null);
  if (dated.length === 0) return null;
  const upcoming = dated.filter((x) => x.t > now).sort((a, b) => a.t - b.t);
  if (upcoming.length > 0) return upcoming[0]!.iso;
  const past = dated.filter((x) => x.t <= now).sort((a, b) => b.t - a.t);
  return past[0]!.iso;
}

/** Filter to only review-due decisions (the CEO follow-up queue). */
export function onlyReviewDue(rows: Api.DecisionOut[], today: string | number = Date.now()): Api.DecisionOut[] {
  return rows.filter((d) => reviewDue(d, today));
}

/** Sort newest-decided first (stable fallback by id). */
export function byDecidedDesc(rows: Api.DecisionOut[]): Api.DecisionOut[] {
  return [...rows].sort((a, b) => {
    const ta = ms(a.decided_at) ?? 0;
    const tb = ms(b.decided_at) ?? 0;
    return tb - ta || a.id.localeCompare(b.id);
  });
}
