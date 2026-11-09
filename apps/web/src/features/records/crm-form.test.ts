/** TC-V4-CRM-11 (unit) — CRM additions of the record form engine (R-DEC-176): datetime, multi, duplicate warning, ref gating. */
import { describe, expect, it } from "vitest";
import { createBody, fromLocalInput, initialValues, recordSchema, similarOf, toLocalInput, updateBody } from "./record-form";
import { RESOURCES, refKindsOf } from "./specs";

const M = { required: "req", number: "num", tooLong: "long", range: "range", period: "period", lines: "lines" };
const spec = (key: string) => RESOURCES.find((r) => r.key === key)!;

describe("datetime fields", () => {
  it("round-trips local wall time ↔ ISO UTC", () => {
    const iso = fromLocalInput("2026-11-10T09:30")!;
    expect(iso).toMatch(/Z$/);
    expect(toLocalInput(iso)).toBe("2026-11-10T09:30");
    expect(fromLocalInput("")).toBeNull();
    expect(fromLocalInput("not a date")).toBeNull();
    expect(toLocalInput("garbage")).toBe("");
  });

  it("activity form: start_at required and sent as ISO", () => {
    const fields = spec("activities").fields;
    const empty = recordSchema(fields, M).safeParse(initialValues(fields));
    expect(empty.success).toBe(false);
    const v = { ...initialValues(fields), type: "call", subject: "Gọi khách", start_at: "2026-11-10T09:00" };
    expect(recordSchema(fields, M).safeParse(v).success).toBe(true);
    const body = createBody(fields, v);
    expect(body).toMatchObject({ type: "call", subject: "Gọi khách" });
    expect(String(body.start_at)).toMatch(/^2026-11-1\dT\d\d:00:00\.000Z$/);
    expect(body).not.toHaveProperty("end_at");
  });
});

describe("multi fields (contact roles)", () => {
  const fields = spec("contacts").fields;
  it("defaults to [] and sends the checked values", () => {
    const init = initialValues(fields);
    expect(init.roles).toEqual([]);
    const v = { ...init, client_id: "c1", first_name: "Lan", roles: ["decision_maker", "champion"] };
    expect(recordSchema(fields, M).safeParse(v).success).toBe(true);
    expect(createBody(fields, v).roles).toEqual(["decision_maker", "champion"]);
  });
  it("PATCH sends roles only when they changed", () => {
    const row = { id: "x", version: 3, client_id: "c1", first_name: "Lan", roles: ["user"] };
    const same = initialValues(fields, row);
    expect(updateBody(fields, same, row)).toEqual({ version: 3 });
    expect(updateBody(fields, { ...same, roles: ["user", "influencer"] }, row)).toEqual({ version: 3, roles: ["user", "influencer"] });
  });
});

describe("duplicate warning", () => {
  const similar = [{ id: "1", code: "LD-000001", name: "An", match: ["email"] }];
  it("is a warning only when the API asks for `confirm_duplicate`", () => {
    expect(similarOf({ confirm_with: "confirm_duplicate", similar })).toEqual(similar);
    expect(similarOf({ similar })).toBeNull(); // hard duplicate (e.g. client tax code)
    expect(similarOf({ confirm_with: "confirm_duplicate", similar: [] })).toBeNull();
  });
});

describe("CRM resources", () => {
  it("fetch only the reference lists they use", () => {
    expect([...refKindsOf(spec("activities"))].sort()).toEqual(["client", "contact", "deal", "lead", "user"]);
    expect(refKindsOf(spec("leads")).has("lead")).toBe(false);
    expect(refKindsOf(spec("clients")).has("deal")).toBe(false);
  });
  it("leads: converted rows are read-only and cannot be converted again", () => {
    const leads = spec("leads");
    expect(leads.editable?.({ status: "converted" })).toBe(false);
    expect(leads.editable?.({ status: "qualified" })).toBe(true);
    const convert = leads.actions!.find((a) => a.key === "convert")!;
    expect(convert.visible({ status: "qualified" })).toBe(true);
    expect(convert.visible({ status: "converted" })).toBe(false);
    expect(convert.visible({ status: "disqualified" })).toBe(false);
    // status select never offers `converted` (only the convert action sets it — EP-SAL-13)
    expect(leads.fields.find((f) => f.name === "status")!.options).not.toContain("converted");
  });
});
