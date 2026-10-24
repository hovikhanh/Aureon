/** TC-M16-19 (unit) — ActionCard gating + edits (T-645F, R-DEC-78). */
import { describe, expect, it } from "vitest";
import { canDecide, diffEdits, isEditable, isMoneyField, selfServiceHref } from "./action-card-logic";

const card = { id: "a1", action_name: "ACT-create_task", autonomy_level: "L2", status: "proposed", on_behalf_of: "u1" };

describe("ActionCard rules", () => {
  it("confirm/reject only for the served user with ai:write on a proposed L2 card", () => {
    expect(canDecide(card, "u1", ["ai:write"])).toBe(true);
    expect(canDecide(card, "u2", ["ai:write", "ai:admin"])).toBe(false);
    expect(canDecide(card, "u1", ["ai:query"])).toBe(false);
    expect(canDecide({ ...card, status: "executed" }, "u1", ["ai:write"])).toBe(false);
    expect(canDecide({ ...card, autonomy_level: "L1", id: undefined }, "u1", ["ai:write"])).toBe(false);
  });
  it("money fields + editable fields", () => {
    expect(isMoneyField("total_amount")).toBe(true);
    expect(isMoneyField("title")).toBe(false);
    expect(isEditable("title", "x")).toBe(true);
    expect(isEditable("assignee_id", "x")).toBe(false);
    expect(isEditable("currency", "VND")).toBe(false);
  });
  it("L1 deep link", () => {
    expect(selfServiceHref("ACT-create_task")).toBe("/work?new=1");
    expect(selfServiceHref("ACT-create_invoice")).toBe("/data");
  });
  it("only changed fields are sent, numbers stay numbers", () => {
    expect(diffEdits({ title: "a", total_amount: 1000 }, { title: "a", total_amount: "1.250.000" })).toEqual({ total_amount: 1_250_000 });
    expect(diffEdits({ title: "a" }, { title: "a" })).toBeUndefined();
  });
});
