/** Sales pipeline pure helpers (T-715F) — shared by SalesPipelineView + its unit test. */

/** Deal stages in the canonical order (05 / sales schema `DealStage`). */
export const STAGES = ["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"] as const;
export type DealStage = (typeof STAGES)[number];

/** PipelineOut / PipelineStage wire shape (sales schema, EP-75). */
export interface PipelineStage {
  stage: string;
  count: number;
  value: number;
  weighted_value: number;
  avg_days_in_stage: number | null;
}
export interface PipelineOut {
  period: { key: string; type: string; start_date: string; end_date: string } | null;
  stages: PipelineStage[];
  coverage_ratio: number | null;
  currency: string;
}

/** SalesDashboardOut.summary wire shape (sales schema, EP-70) — only the fields the strip renders. */
export interface SalesSummary {
  pipeline_value: number;
  weighted_pipeline: number;
  deals_open: number;
  deals_won: number;
  deals_lost: number;
  win_rate_pct: number | null;
  avg_deal_value: number | null;
  currency: string;
}
export interface SalesDashboardOut {
  pillar: "C";
  status: "ok" | "warning" | "critical" | "no_data";
  summary: SalesSummary;
}

/** closed_lost is shown dimmed (not excluded) so the board still reflects total deal flow. */
export const DIMMED_STAGES: readonly DealStage[] = ["closed_lost"];

/** Order a server stage list by the canonical STAGES order (server may omit empty stages). */
export function orderStages(stages: PipelineStage[]): PipelineStage[] {
  const idx = (s: string) => {
    const i = STAGES.indexOf(s as DealStage);
    return i === -1 ? STAGES.length : i;
  };
  return [...stages].sort((a, b) => idx(a.stage) - idx(b.stage));
}
