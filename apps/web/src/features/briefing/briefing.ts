/**
 * CEO Daily Briefing logic (M3.3, 03 §3.1) — pure, UI-free so Vitest covers it without rendering.
 *
 * A briefing (`Api.BriefingOut`) is the single-page morning read for CEO/DIR: a one-line summary,
 * the Executive dashboard snapshot (metrics + SEI + counts + "AI đã làm"), AI recommendations,
 * today's calendar, and the stale-metric warning. The banner opens it (status `generated` →
 * `opened`) to track the G1 "read within the day" metric.
 */
import type { Api } from "@aureon/shared-types";

/**
 * Fixed one-page block order (03 §3.1): the most decision-relevant content first, so the CEO can
 * stop reading at any point and still have seen what matters most.
 */
export const BRIEFING_BLOCK_ORDER = [
  "summary",
  "stale",
  "metrics",
  "sei",
  "decisions",
  "risks",
  "recommendations",
  "aiDone",
  "calendar",
] as const;

export type BriefingBlockKey = (typeof BRIEFING_BLOCK_ORDER)[number];

export interface BriefingBlock {
  key: BriefingBlockKey;
  present: boolean;
}

/** The ExecutiveDashboardOut embedded in `dashboard` (typed loosely on the wire as a record). */
type Dashboard = Api.ExecutiveDashboardOut;

function dashboard(b: Api.BriefingOut): Dashboard | null {
  return (b.dashboard as Dashboard | undefined) ?? null;
}

/** Whether each block has content to render, in the fixed one-page order. */
export function briefingBlocks(b: Api.BriefingOut): BriefingBlock[] {
  const d = dashboard(b);
  const present: Record<BriefingBlockKey, boolean> = {
    summary: Boolean(b.summary_line),
    stale: staleCount(b) > 0,
    metrics: Boolean(d?.tiles && d.tiles.length > 0),
    sei: Boolean(d?.sei),
    decisions: Boolean(d?.decisions_waiting),
    risks: Boolean(d?.open_risks),
    recommendations: Boolean(b.recommendations && b.recommendations.length > 0),
    aiDone: Boolean(d?.ai_done),
    calendar: Boolean(b.calendar_today && b.calendar_today.length > 0),
  };
  return BRIEFING_BLOCK_ORDER.map((key) => ({ key, present: present[key] }));
}

/** Number of stale metric codes flagged on the briefing (BRD-P01 freshness). */
export function staleCount(b: Api.BriefingOut): number {
  return b.stale_metric_codes?.length ?? 0;
}

/** Whether the briefing has already been opened (status flip or an `opened_at` stamp). */
export function isOpened(b: Api.BriefingOut): boolean {
  return b.status === "opened" || Boolean(b.opened_at);
}

/** The ISO instant to show as "opened at" — `opened_at` when present, else null. */
export function openedAt(b: Api.BriefingOut): string | null {
  return b.opened_at ?? null;
}
