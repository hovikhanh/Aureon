/** F12: Strategy / Strategic Objective forms (EP-STR-03/08). */
import { describe, expect, it } from "vitest";
import { goalCaps } from "./GoalsShell";
import { strategicObjectiveSchema, strategySchema, toStrategicObjectiveCreate, toStrategyCreate } from "./goal-forms";

const m = { required: "req", number: "num", tooLong: "long", periodInvalid: "period", codeInvalid: "code", dateInvalid: "date", endBeforeStart: "order" };
const good = { code: "ST-2027", name: " Tăng trưởng ", period_start: "2027-01-01", period_end: "2027-12-31", status: "draft" as const, owner_id: "u1" };

describe("strategySchema", () => {
  it("accepts a valid strategy and maps the body", () => {
    expect(toStrategyCreate(strategySchema(m).parse(good))).toEqual({ ...good, name: "Tăng trưởng" });
  });

  it.each([
    [{ ...good, code: "" }, "req"],
    [{ ...good, code: "có dấu" }, "code"],
    [{ ...good, period_start: "" }, "date"],
    [{ ...good, period_end: "2026-12-31" }, "order"],
    [{ ...good, period_end: "2027-01-01" }, "order"], // the API needs end > start, not ≥
  ])("rejects %j", (v, msg) => {
    const r = strategySchema(m).safeParse(v);
    expect(r.success).toBe(false);
    expect(r.error?.issues[0]?.message).toBe(msg);
  });
});

describe("strategicObjectiveSchema", () => {
  const so = { code: "SO-1", title: "Biên lợi nhuận", pillar: "" as const, owner_id: "u1", department_id: "" };

  it("empty pillar / department are company level (null), not an empty string", () => {
    expect(toStrategicObjectiveCreate("s1", strategicObjectiveSchema(m).parse(so))).toEqual({ strategy_id: "s1", code: "SO-1", title: "Biên lợi nhuận", pillar: null, owner_id: "u1", department_id: null });
  });

  it("rejects a pillar outside the catalog", () => {
    expect(strategicObjectiveSchema(m).safeParse({ ...so, pillar: "X" }).success).toBe(false);
  });
});

describe("who writes strategy (10 EP-STR-03/08)", () => {
  const caps = (role: string, permissions: string[]) => goalCaps({ id: "u", role, permissions, scopePillars: [] });

  it("CEO both, DIR objectives only, MGR neither", () => {
    expect(caps("CEO", ["execution:write"])).toMatchObject({ canWriteStrategy: true, canWriteSo: true });
    expect(caps("DIR", ["execution:write"])).toMatchObject({ canWriteStrategy: false, canWriteSo: true });
    expect(caps("MGR", ["execution:write"])).toMatchObject({ canWriteStrategy: false, canWriteSo: false });
    expect(caps("CEO", [])).toMatchObject({ canWriteStrategy: false, canWriteSo: false });
  });
});
