import { describe, expect, it } from "vitest";
import {
  keyResultSchema, kpiSchema, objectiveSchema, ownerOptions, toKeyResultCreate, toKpiCreate, toKpiUpdate,
  toObjectiveCreate, toObjectiveUpdate,
} from "./goal-forms";

/** TC-M5-08 — KPI / OKR editor schemas + body mappers (EP-KPI-02/04, EP-OKR-02/04/07). */
const M = { required: "req", number: "num", tooLong: "long", periodInvalid: "period", codeInvalid: "code" };
const OWNER = "11111111-1111-1111-1111-111111111111";

describe("kpiSchema", () => {
  const kpi = { code: "KPI-SAL-09", name: "Doanh số mới", unit: "VND", target: "1.250,5".replace(".", ""), period_type: "MONTH",
    direction: "HIGHER_IS_BETTER", value_type: "currency", status: "active", owner_id: OWNER } as const;

  it("accepts a valid KPI and maps it to KpiCreate (comma decimal → number)", () => {
    const v = kpiSchema(M, { creating: true }).parse(kpi);
    expect(toKpiCreate(v)).toEqual({ ...kpi, target: 1250.5 });
  });

  it("rejects empty fields, a bad code and a non-numeric target", () => {
    const r = kpiSchema(M, { creating: true }).safeParse({ ...kpi, code: "có dấu cách", name: " ", target: "abc", owner_id: "" });
    expect(r.success).toBe(false);
    const msgs = new Set(r.error?.issues.map((i) => `${String(i.path[0])}:${i.message}`));
    expect(msgs).toEqual(new Set(["code:code", "name:req", "target:num", "owner_id:req"]));
  });

  it("does not validate the (read-only) code when editing and sends the version", () => {
    const v = kpiSchema(M, { creating: false }).parse({ ...kpi, code: "" });
    const body = toKpiUpdate(v, 7);
    expect(body).toMatchObject({ version: 7, name: "Doanh số mới", target: 1250.5, owner_id: OWNER });
    expect(body).not.toHaveProperty("code");
    expect(body).not.toHaveProperty("period_type"); // KpiUpdate has no period_type (extra="forbid")
  });
});

describe("objectiveSchema / keyResultSchema", () => {
  it("objective: period must be YYYY, YYYY-MM or YYYY-Qn", () => {
    const base = { title: "Tăng trưởng Q4", level: "company", okr_type: "committed", status: "draft", owner_id: OWNER } as const;
    for (const p of ["2026-Q4", "2026-10", "2026"]) expect(objectiveSchema(M).safeParse({ ...base, period_key: p }).success, p).toBe(true);
    for (const p of ["2026-Q5", "Q4-2026", "2026-13", ""]) expect(objectiveSchema(M).safeParse({ ...base, period_key: p }).success, p).toBe(false);
    const v = objectiveSchema(M).parse({ ...base, period_key: " 2026-Q4 " });
    expect(toObjectiveCreate(v)).toEqual({ ...base, period_key: "2026-Q4" });
    expect(toObjectiveUpdate(v, 3)).toMatchObject({ version: 3, title: "Tăng trưởng Q4" });
  });

  it("key result: baseline/target numeric, never sends current_value", () => {
    const v = keyResultSchema(M).parse({ title: "NPS", baseline: "30", target: "45,5", unit: "điểm", status: "active", owner_id: OWNER });
    const body = toKeyResultCreate(v);
    expect(body).toEqual({ title: "NPS", baseline: 30, target: 45.5, unit: "điểm", status: "active", owner_id: OWNER });
    expect(body).not.toHaveProperty("current_value");
    expect(keyResultSchema(M).safeParse({ ...v, baseline: "" }).success).toBe(false);
  });
});

describe("ownerOptions", () => {
  const self = { id: OWNER, label: "Tôi" };
  const users = [
    { id: OWNER, full_name: "CEO", email: "ceo@abc.demo", is_active: true },
    { id: "u-2", full_name: "Trần B", email: "b@abc.demo", is_active: true },
    { id: "u-3", full_name: "Cũ", email: "old@abc.demo", is_active: false },
  ];

  it("a role without platform:read owns what it creates", () => {
    expect(ownerOptions(self, users, false)).toEqual([self]);
  });
  it("CEO/ADM pick among active users (self first, inactive left out)", () => {
    expect(ownerOptions(self, users, true).map((o) => o.id)).toEqual([OWNER, "u-2"]);
  });
  it("editing keeps the current owner selectable even if not listed", () => {
    expect(ownerOptions(self, users, false, "u-9").map((o) => o.id)).toEqual([OWNER, "u-9"]);
  });
});
