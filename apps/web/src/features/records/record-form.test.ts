/** TC-M7-01 (unit) — form engine of the business-record editors. */
import { describe, expect, it } from "vitest";
import { createBody, initialValues, recordSchema, updateBody, type FieldSpec } from "./record-form";
import { RESOURCES } from "./specs";

const M = { required: "req", number: "num", tooLong: "long", range: "range", period: "period", lines: "lines" };
const spec = (key: string) => RESOURCES.find((r) => r.key === key)!;
const issues = (fields: readonly FieldSpec[], v: Record<string, unknown>) => {
  const r = recordSchema(fields, M).safeParse(v);
  return r.success ? [] : r.error.issues.map((i) => `${i.path.join(".")}:${i.message}`).sort();
};

describe("recordSchema", () => {
  const expense = spec("expenses").fields;
  const ok = { ...initialValues(expense), title: "Thuê văn phòng T11", amount: "45.000.000".replace(/\./g, ""), category: "office", spent_on: "2026-11-01" };

  it("accepts a valid expense (optional refs / selects empty)", () => expect(issues(expense, ok)).toEqual([]));

  it("required, money integer ≥ 0, select required", () => {
    expect(issues(expense, { ...ok, title: " ", amount: "-5", category: "" })).toEqual(["amount:range", "category:req", "title:req"]);
    expect(issues(expense, { ...ok, amount: "12,5" })).toEqual(["amount:range"]); // VND has no decimals
    expect(issues(expense, { ...ok, amount: "abc" })).toEqual(["amount:num"]);
  });

  it("percent 0–100, month period, invoice lines", () => {
    const deal = spec("deals").fields;
    const d = { ...initialValues(deal), name: "Trang bị VP", client_id: "c1", deal_value: "100000000", probability_pct: "120", expected_close_date: "2026-12-01", owner_id: "u1" };
    expect(issues(deal, d)).toEqual(["probability_pct:range"]);
    const cash = spec("cashPositions").fields;
    expect(issues(cash, { ...initialValues(cash), period: "2026-13", closing_balance: "1" })).toEqual(["period:period"]);
    const inv = spec("invoices").fields;
    const base = { ...initialValues(inv), direction: "IN", number: "0000123", issued_on: "2026-11-01", due_date: "2026-11-30" };
    expect(issues(inv, { ...base, lines: [] })).toEqual(["lines:lines"]);
    expect(issues(inv, { ...base, lines: [{ description: "Máy in", quantity: "0", unit_price: "5000000", vat_pct: "10" }] })).toEqual(["lines.0.quantity:num"]);
  });
});

describe("bodies", () => {
  const inv = spec("invoices").fields;
  const v = { ...initialValues(inv), direction: "OUT", number: "0000123", issued_on: "2026-11-01", due_date: "2026-11-30",
    lines: [{ description: "Máy in", quantity: "2", unit_price: "5000000", vat_pct: "10" }] };

  it("create sends typed values and leaves empty optionals out", () => {
    expect(createBody(inv, v)).toEqual({
      direction: "OUT", number: "0000123", issued_on: "2026-11-01", due_date: "2026-11-30",
      lines: [{ description: "Máy in", quantity: 2, unit_price: 5000000, vat_pct: 10 }],
    });
  });

  it("update sends only changed, non-create-only fields plus the version", () => {
    const row = { id: "i1", version: 4, direction: "OUT", number: "0000123", issued_on: "2026-11-01", due_date: "2026-11-30", status: "draft",
      notes: null, lines: [{ description: "Máy in", quantity: 2, unit_price: 5000000, vat_pct: 10 }] };
    const edited = { ...initialValues(inv, row), due_date: "2026-12-15", number: "CHANGED" };
    expect(updateBody(inv, edited, row)).toEqual({ version: 4, due_date: "2026-12-15" }); // `number` is create-only
    expect(updateBody(inv, initialValues(inv, row), row)).toEqual({ version: 4 }); // nothing changed
    const cleared = { ...initialValues(spec("clients").fields, { id: "c", version: 1, name: "ABC", industry: "IT" }), industry: "" };
    expect(updateBody(spec("clients").fields, cleared, { id: "c", version: 1, name: "ABC", industry: "IT" })).toEqual({ version: 1, industry: null });
  });
});

describe("specs", () => {
  it("never edits level-4 HR data (02 §6.2)", () => {
    const names = spec("employees").fields.map((f) => f.name);
    for (const f of ["date_of_birth", "national_id", "bank_account", "address", "salary"]) expect(names).not.toContain(f);
    expect(spec("hiringPlans").fields.map((f) => f.name)).not.toContain("salary_min");
  });
});
