/** TC-M15-16 (FE unit) — DropZone limits, SchemaForm zod + VN formats, ColumnMapper required check, 422 mapping. */
import { describe, expect, it } from "vitest";
import type { Api } from "@aureon/shared-types";
import { MAX_FILE_BYTES, checkFiles, duplicateTargets, errorPaths, formSchema, isTable, isoToVn, parseVnDate, parseVnNumber, toManualBody, unmappedRequired } from "./logic";

const F = (name: string, value_type: string, o: Partial<Api.FormFieldOut> = {}): Api.FormFieldOut => ({ name, label_key: `capture.field.${name}`, value_type, required: false, is_critical: false, sensitivity_level: 2, ...o });
const FORM: Api.FormOut = { document_type: "PERIOD_REPORT", schema_version: 1, required_permissions: [], permitted: true,
  fields: [F("period_key", "text", { required: true }), F("kpi_code", "text", { required: true, repeatable_group: "rows" }), F("actual_value", "number", { required: true, repeatable_group: "rows" }), F("due", "date", { repeatable_group: "rows" })] };

describe("DropZone checks (FR-DC-01)", () => {
  it("≤ 100 files, ≤ 50 MB, whitelisted extensions", () => {
    const many = Array.from({ length: 101 }, (_, i) => ({ name: `f${i}.pdf`, size: 10 }));
    const r = checkFiles(many);
    expect(r.filter((x) => x.ok)).toHaveLength(100);
    expect(r[100]!.issue).toBe("too_many");
    expect(checkFiles([{ name: "a.pdf", size: MAX_FILE_BYTES + 1 }])[0]!.issue).toBe("too_large");
    expect(checkFiles([{ name: "a.pdf", size: MAX_FILE_BYTES }])[0]!.ok).toBe(true);
    expect(checkFiles([{ name: "a.xls", size: 1 }, { name: "b.zip", size: 1 }]).map((x) => x.issue)).toEqual(["type", "type"]);
    expect(checkFiles([{ name: "B.XLSX", size: 1 }])[0]!.ok).toBe(true);
    expect([isTable("x.csv"), isTable("x.XLSX"), isTable("x.pdf")]).toEqual([true, true, false]);
  });
});

describe("SchemaForm (SCR-61)", () => {
  it("VN number/date formats", () => {
    expect(parseVnNumber("1.250.000")).toBe(1250000);
    expect(parseVnNumber("18,5")).toBe(18.5);
    expect(parseVnNumber("1.25")).toBeNull();
    expect(parseVnNumber("abc")).toBeNull();
    expect(parseVnDate("05/10/2026")).toBe("2026-10-05");
    expect(parseVnDate("31/02/2026")).toBeNull();
    expect(parseVnDate("2026-10-05")).toBeNull();
    expect(isoToVn("2026-10-05")).toBe("05/10/2026");
  });

  it("zod schema from fields[]: required, number, date per row", () => {
    const s = formSchema(FORM.fields);
    const bad = s.safeParse({ values: { period_key: "" }, rows: [{ kpi_code: "K1", actual_value: "1,2,3", due: "32/01/2026" }] });
    expect(bad.success).toBe(false);
    const issues = bad.error!.issues.map((i) => `${i.path.join(".")}:${i.message}`).sort();
    expect(issues).toEqual(["rows.0.actual_value:number_format", "rows.0.due:date_format", "values.period_key:required"]);
    expect(s.safeParse({ values: { period_key: "2026-Q4" }, rows: [{ kpi_code: "K1", actual_value: "1.250.000", due: "" }] }).success).toBe(true);
  });

  it("builds the EP-DC-16 body and maps 422 details to form paths", () => {
    const body = toManualBody(FORM, { values: { period_key: "2026-Q4" }, rows: [{ kpi_code: "K1", actual_value: "1.250.000", due: "05/10/2026" }, { kpi_code: "", actual_value: "", due: "" }] });
    expect(body).toEqual({ document_type: "PERIOD_REPORT", schema_version: 1, values: { period_key: "2026-Q4" }, rows: [{ kpi_code: "K1", actual_value: 1250000, due: "2026-10-05" }] });
    expect(errorPaths({ fields: [{ field: "period_key", rule_code: "required", row_index: null }, { field: "kpi_code", rule_code: "master_not_found", row_index: 1 }] }))
      .toEqual([{ path: "values.period_key", rule_code: "required" }, { path: "rows.1.kpi_code", rule_code: "master_not_found" }]);
  });
});

describe("ColumnMapper (SCR-62)", () => {
  it("flags required fields without a column and double-mapped fields", () => {
    expect(unmappedRequired(FORM.fields, { "Mã KPI": "kpi_code", "Ghi chú": null })).toEqual(["actual_value"]);
    expect(unmappedRequired(FORM.fields, { a: "kpi_code", b: "actual_value" })).toEqual([]);
    expect(duplicateTargets({ a: "kpi_code", b: "kpi_code", c: null })).toEqual(["kpi_code"]);
  });
});
