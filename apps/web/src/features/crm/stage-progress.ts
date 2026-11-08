import { OPEN_STAGES, isClosed } from "./crm";

export type StepState = "reached" | "current" | "upcoming";

/**
 * Deal stage steps (CRM-OPP-04): the open stages + the outcome. The outcome step is `closed_won`
 * until the deal closes — it sits outside OPEN_STAGES, so comparing its `indexOf` (-1) always read
 * as "reached" and "Thắng" stayed highlighted on every open deal.
 */
export function stageProgress(stage: string): { stage: string; state: StepState }[] {
  const closed = isClosed(stage);
  const at = OPEN_STAGES.indexOf(stage as never);
  const state = (s: string, i: number): StepState => (s === stage ? "current" : closed || i < at ? "reached" : "upcoming");
  return [...OPEN_STAGES, closed ? stage : "closed_won"].map((s, i) => ({ stage: s, state: state(s, i) }));
}
