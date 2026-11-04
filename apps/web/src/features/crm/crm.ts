/**
 * CRM on the existing sales model (M8, R-DEC-175 — BRD_Newfeature Phase 1 on Client/Deal; R-DEC-90
 * aliases: Account/Lead = Client, Opportunity = Deal). Pure helpers, unit-tested. Every figure
 * comes from the API (BRD CORE-06: the dashboard creates no numbers of its own); these only
 * arrange and compare them.
 */
import { STAGES, type DealStage } from "@/features/sales/pipeline";

export { STAGES, type DealStage };
export const OPEN_STAGES: readonly DealStage[] = ["lead", "qualified", "proposal", "negotiation"];
export const isClosed = (s: string) => s === "closed_won" || s === "closed_lost";

/**
 * Mirror of `sales/services/calculations.py` (the API decides, this only hides impossible
 * moves on the board — CRM-PIPE-05/07): closed deals are final; an open deal moves forward to a
 * later open stage, or straight to won / lost; never backward or to the same stage.
 */
export function canMoveTo(from: string, to: string): boolean {
  if (isClosed(from) || from === to) return false;
  if (isClosed(to)) return true;
  return OPEN_STAGES.indexOf(to as DealStage) > OPEN_STAGES.indexOf(from as DealStage);
}

export interface StageCount { stage: string; count: number; value: number; weighted_value: number }
export interface FunnelStep { stage: string; count: number; value: number; conversionPct: number | null; dropOffPct: number | null }

/**
 * BRD §2.8 Method A (current counts): open stages + Closed Won in pipeline order;
 * `ConversionRate = N_current / N_previous × 100%`, drop-off = 100 − conversion (L910–923).
 * Closed Lost is not a funnel step (it is the loss) — returned apart by the caller.
 */
export function funnel(stages: readonly StageCount[]): FunnelStep[] {
  const by = new Map(stages.map((s) => [s.stage, s]));
  const order: DealStage[] = [...OPEN_STAGES, "closed_won"];
  return order.map((stage, i) => {
    const cur = by.get(stage);
    const prev = i > 0 ? by.get(order[i - 1]!) : undefined;
    const count = cur?.count ?? 0;
    const conversionPct = i > 0 && prev && prev.count > 0 ? Math.round((count / prev.count) * 1000) / 10 : null;
    return { stage, count, value: cur?.value ?? 0, conversionPct, dropOffPct: conversionPct === null ? null : Math.round((100 - conversionPct) * 10) / 10 };
  });
}

/**
 * Weighted forecast of a period (BRD §2.9, `WP = Σ(DealValue_i × Probability_i)`, L1029) from
 * `/sales/pipeline?period=` — the API already filters open deals by expected close date in the
 * period and closed ones by close date; Closed Lost is excluded (AC L1056).
 */
export function forecast(stages: readonly StageCount[]) {
  const open = stages.filter((s) => OPEN_STAGES.includes(s.stage as DealStage));
  const won = stages.find((s) => s.stage === "closed_won");
  const pipeline = open.reduce((a, s) => a + s.value, 0);
  const weighted = open.reduce((a, s) => a + s.weighted_value, 0);
  return { pipeline, weighted, closedWon: won?.value ?? 0, expected: weighted + (won?.value ?? 0) };
}

export type DealRisk = "overdue" | "dueSoon" | null;
/** Deal risk (BRD DASH-07 "Deal sắp đến hạn"): open and past / within 7 days of its expected close. */
export function dealRisk(deal: { stage: string; expected_close_date: string }, today: string, soonDays = 7): DealRisk {
  if (isClosed(deal.stage)) return null;
  const days = (Date.parse(deal.expected_close_date) - Date.parse(today)) / 86_400_000;
  if (days < 0) return "overdue";
  return days <= soonDays ? "dueSoon" : null;
}

/** Quarter keys around today for the forecast period picker (`YYYY-Qn`, API `resolve_period`). */
export function quarterOptions(today: string, before = 1, after = 2): string[] {
  const y = Number(today.slice(0, 4));
  const q = Math.floor((Number(today.slice(5, 7)) - 1) / 3);
  const out: string[] = [];
  for (let i = -before; i <= after; i++) {
    const n = y * 4 + q + i;
    out.push(`${Math.floor(n / 4)}-Q${(n % 4) + 1}`);
  }
  return out;
}
