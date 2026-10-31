import { describe, expect, it } from "vitest";
import en from "../../../messages/en.json";
import vi from "../../../messages/vi.json";
import { STAGES, orderStages } from "./pipeline";

describe("sales pipeline (T-715F)", () => {
  it("defines the 6 deal stages in the canonical order", () => {
    expect([...STAGES]).toEqual(["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]);
  });

  // SalesPipelineView renders `sales.stage.<stage>` for every column; a missing key throws
  // MISSING_MESSAGE on the client. Every stage label must resolve in both locales.
  it.each(["vi", "en"] as const)("%s has a stage label for every deal stage", (loc) => {
    const stage = (loc === "vi" ? vi : en).sales.stage as Record<string, string>;
    for (const s of STAGES) expect(stage[s], `sales.stage.${s} (${loc})`).toBeTruthy();
  });

  it("orderStages sorts a shuffled server list back into canonical order", () => {
    const shuffled = ["proposal", "lead", "closed_won", "qualified"].map((stage) => ({ stage, count: 0, value: 0, weighted_value: 0, avg_days_in_stage: null }));
    expect(orderStages(shuffled).map((s) => s.stage)).toEqual(["lead", "qualified", "proposal", "closed_won"]);
  });
});
