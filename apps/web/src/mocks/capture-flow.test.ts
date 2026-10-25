/** T-643 (mock part) — C5 import → review → commit → lineage → undo (TC-M15-17 mock path) + SCR-63 admin guards. */
import { beforeEach, describe, expect, it } from "vitest";
import { MOCK_USERS, claimsFor } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";
import { SEED_DOC } from "./capture-seed";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const CEO = user("ceo@abc.demo");
const EMP = user("employee@abc.demo");
const MGR = user("manager@abc.demo");
const HRD = user("hr@abc.demo");
const REV = user("reviewer@abc.demo");
const ADM = user("admin@abc.demo");
type C = ReturnType<typeof user>;
/** Parsed response JSON, as untyped as `res.json()` itself (assertions check the shape). */
type Loose = ReturnType<typeof JSON.parse>;
type Json = { data: Loose; meta?: Record<string, Loose>; error?: { code: string; details: Record<string, Loose> } };

async function call(path: string, claims: C, method = "GET", body?: unknown) {
  const [p, q = ""] = path.split("?");
  const res = await handleMock({ method, path: p!, query: new URLSearchParams(q), headers: new Headers({ "idempotency-key": "k" }), body, claims });
  const json = (res.headers.get("content-type") ?? "").includes("json") ? ((await res.json()) as Json) : null;
  return { status: res.status, json: json!, res };
}
const upload = (name: string, claims: C, size = 31_000) => call("/data-capture/imports", claims, "POST", { file: { name, size, type: "" }, files: [], document_type: null });

beforeEach(() => resetMockStore());

describe("C5 import DOC-06 (EP-DC-17..22)", () => {
  it("previews with suggested type + mapping, rows/errors, error file, submit", async () => {
    const up = await upload("DOC-06-danh-sach-nhan-su.xlsx", HRD);
    expect(up.status).toBe(201);
    const pv = up.json.data;
    expect(pv.suggested_document_type.code).toBe("HR_ROSTER");
    expect(pv.column_mapping["Mã NV"].field).toBe("employee_code");
    // DOC-06 sheet "Nhân sự" = real API: 48 rows, 45 valid, NV-052 / NV-053 / NV-054 invalid.
    expect(pv.summary).toEqual({ rows_total: 48, rows_valid: 45, rows_invalid: 3 });
    expect(pv.sheets.map((s: { name: string; row_count: number }) => `${s.name}:${s.row_count}`)).toEqual(["Nhân sự:48", "Đã nghỉ việc:8"]);
    const bad = await call(`/data-capture/imports/${pv.batch_id}/rows?status=invalid`, HRD);
    expect(bad.json.data.map((r: { row_number: number }) => r.row_number)).toEqual([47, 48, 49]);
    expect(bad.json.data.flatMap((r: { errors: { field: string; rule_code: string }[] }) => r.errors.map((e) => `${e.field}:${e.rule_code}`)))
      .toEqual(["manager_code:MASTER_NOT_FOUND", "hire_date:DATE_FORMAT", "department_code:REQUIRED"]);
    const file = await call(`/data-capture/imports/${pv.batch_id}/error-file`, HRD);
    expect(file.res.headers.get("content-type")).toContain("spreadsheetml");
    expect(new Uint8Array(await file.res.arrayBuffer()).slice(0, 2)).toEqual(new Uint8Array([0x50, 0x4b]));
    const unmapped = await call(`/data-capture/imports/${pv.batch_id}/mapping`, HRD, "PATCH", { document_type: "HR_ROSTER", sheet: "Nhân sự", header_row: 1, mapping: { "Mã NV": null }, version: 1 });
    expect(unmapped.json.error!.details.unmapped_required).toContain("employee_code");
    expect((await call(`/data-capture/imports/${pv.batch_id}/mapping`, HRD, "PATCH", { document_type: "HR_ROSTER", sheet: "Nhân sự", header_row: 1, mapping: {}, version: 9 })).status).toBe(409);
    const sub = await call(`/data-capture/imports/${pv.batch_id}/submit`, HRD, "POST", { version: 1 });
    expect([sub.json.data.rows_submitted, sub.json.data.rows_excluded, sub.json.data.document.status]).toEqual([45, 3, "NEEDS_REVIEW"]);
    expect((await call(`/data-capture/imports/${pv.batch_id}/submit`, HRD, "POST", { version: 2 })).status).toBe(409);
    expect((await upload("DOC-06-danh-sach-nhan-su.xlsx", HRD)).json.error!.code).toBe("DUPLICATE_RESOURCE");
  });

  it("rejects .xls (415), oversize CSV (413 details.limit), non-UTF-8 CSV (422)", async () => {
    expect((await upload("old.xls", HRD)).status).toBe(415);
    const big = "a,b\n" + "1,2\n".repeat(5001);
    const r = await call("/data-capture/imports", HRD, "POST", { file: { name: "big.csv", size: big.length, type: "text/csv", text: big } });
    expect([r.status, r.json.error!.code, r.json.error!.details.limit]).toEqual([413, "FILE_TOO_LARGE", "rows"]);
    const wide = Array.from({ length: 61 }, (_, i) => `c${i}`).join(",");
    expect((await call("/data-capture/imports", HRD, "POST", { file: { name: "w.csv", size: 9, text: wide } })).json.error!.details.limit).toBe("columns");
    expect((await call("/data-capture/imports", HRD, "POST", { file: { name: "x.csv", size: 9, text: "M\uFFFD NV" } })).status).toBe(422);
  });
});

async function rosterThroughReview(approver: C) {
  const pv = (await upload("DOC-06-danh-sach-nhan-su.xlsx", HRD)).json.data;
  await call(`/data-capture/imports/${pv.batch_id}/submit`, HRD, "POST", { version: 1 });
  const detail = (await call(`/idp/documents/${pv.document_id}/review`, approver)).json.data;
  return { id: pv.document_id as string, detail };
}

describe("review → commit → lineage → undo", () => {
  it("REV approves → APPROVED + pending_permissions; HR DIR commits; lineage; undo reverts", async () => {
    const { id, detail } = await rosterThroughReview(REV);
    expect(detail.rows).toHaveLength(45);
    expect(detail.routing_reasons).toEqual(["C5_REVIEW"]);
    expect(detail.planned_actions.map((p: { action_name: string; permitted: boolean }) => `${p.action_name}:${p.permitted}`)).toEqual(["ACT-create_department:false", "ACT-create_position:false", "ACT-create_employee:false"]);
    const critical = await call(`/idp/documents/${id}/review/approve`, REV, "POST", {});
    expect([critical.json.error!.details.reason, critical.json.error!.details.fields]).toEqual(["critical_unconfirmed", ["salary"]]);
    await call(`/idp/documents/${id}/fields`, REV, "PATCH", { fields: detail.fields.filter((f: { is_critical: boolean }) => f.is_critical).map((f: { id: string }) => ({ field_id: f.id, action: "confirm" })) });
    const ap = await call(`/idp/documents/${id}/review/approve`, REV, "POST", {});
    expect([ap.json.data.document.status, ap.json.meta!.pending_permissions]).toEqual(["APPROVED", ["hr:admin", "hr:write"]]);
    expect((await call(`/data-capture/documents/${id}/commit`, MGR, "POST", { version: 2 })).status).toBe(404);
    const version = ap.json.data.document.version;
    const cm = await call(`/data-capture/documents/${id}/commit`, HRD, "POST", { version });
    expect(cm.json.data.document.status).toBe("COMMITTED");
    const emp = cm.json.data.actions.find((a: { action_name: string }) => a.action_name === "ACT-create_employee");
    expect(emp.ids).toHaveLength(45);
    const ln = await call(`/lineage/hr.employees/${emp.ids[0]}`, HRD);
    expect(ln.json.data.links[0]).toMatchObject({ sheet_name: "Nhân sự", row_index: 2, field_name: "employee_code" });
    expect((await call(`/lineage/hr.employees/${emp.ids[0]}`, EMP)).json.data).toEqual({ restricted: true, reason: "target_out_of_scope" });
    expect((await call(`/lineage/hr.nope/${emp.ids[0]}`, HRD)).status).toBe(422);
    const acts = await call(`/data-capture/documents/${id}/actions`, HRD);
    expect(acts.json.data.map((a: { seq: number }) => a.seq)).toEqual([1, 2, 3]);
    const un = await call(`/data-capture/documents/${id}/undo`, HRD, "POST", { reason: "Nhập nhầm", reason_code: "mistake" });
    expect(un.json.data.document.status).toBe("ROLLED_BACK");
    expect((await call(`/data-capture/documents/${id}/undo`, HRD, "POST", { reason: "x", reason_code: "mistake" })).status).toBe(409);
  });

  it("undo: 410 past deadline, 409 when a target was edited after commit", async () => {
    const t = await call("/data-capture/manual", CEO, "POST", { document_type: "PLAN_KPI_OKR", schema_version: 1, values: {}, rows: [{ period_key: "2026-Q4", owner_code: "NV-0001", task_title: "Việc B" }] });
    const id = t.json.data.document.id;
    const taskId = t.json.data.actions[0].ids[0];
    const task = (await call(`/work/tasks/${taskId}`, CEO)).json.data;
    await call(`/work/tasks/${taskId}`, CEO, "PATCH", { title: "Việc B (sửa)", version: task.version });
    const c = await call(`/data-capture/documents/${id}/undo`, CEO, "POST", { reason: "x", reason_code: "mistake" });
    expect([c.status, c.json.error!.details.conflicts]).toEqual([409, [{ table: "execution.tasks", id: taskId }]]);
    const { captureStore } = await import("./capture-store");
    captureStore().docs.find((d) => d.id === SEED_DOC.kpi)!.undo_deadline = "2026-01-01T00:00:00Z";
    expect((await call(`/data-capture/documents/${SEED_DOC.kpi}/undo`, CEO, "POST", { reason: "x", reason_code: "other" })).json.error!.code).toBe("UNDO_EXPIRED");
  });
});

describe("SCR-63 admin (EP-DC-27..37)", () => {
  it("schema draft → publish; guards; rules; incidents need idp:approve", async () => {
    const types = (await call("/data-capture/document-types", ADM)).json.data;
    expect(types.map((t: { code: string }) => t.code)).toContain("HR_ROSTER");
    const hr = types.find((t: { code: string }) => t.code === "HR_ROSTER");
    expect((await call(`/data-capture/document-types/${hr.id}`, ADM, "PATCH", { is_active: true, version: 5 })).status).toBe(409);
    expect((await call(`/data-capture/document-types/${hr.id}`, CEO, "PATCH", { version: 1 })).json.error!.code).toBe("FORBIDDEN_ROLE");
    const pub = (await call("/data-capture/extraction-schemas?document_type=HR_ROSTER&status=published", ADM)).json.data[0];
    const draft = (await call("/data-capture/extraction-schemas", ADM, "POST", { document_type: "HR_ROSTER", clone_from_id: pub.id })).json.data;
    expect([draft.schema_version, draft.status]).toEqual([2, "draft"]);
    expect((await call(`/data-capture/extraction-schemas/${draft.id}`, ADM, "PATCH", { thresholds: { classification_confidence_min: 0.9, required_field_min: 0.9 }, version: 1 })).status).toBe(422);
    const fields = draft.fields.map((f: { name: string }) => (f.name === "salary" ? { ...f, is_critical: false } : f));
    expect((await call(`/data-capture/extraction-schemas/${draft.id}`, ADM, "PATCH", { fields, version: 1 })).json.error!.details.fields).toEqual(["salary"]);
    expect((await call("/data-capture/validation-rules", ADM, "POST", { extraction_schema_id: draft.id, code: "R1", kind: "field", expression: { op: "regex" }, severity: "fail" })).status).toBe(422);
    expect((await call("/data-capture/validation-rules", ADM, "POST", { extraction_schema_id: draft.id, code: "R1", kind: "field", expression: { op: "required", field: "title" }, severity: "fail" })).status).toBe(201);
    expect((await call("/data-capture/validation-rules", ADM, "POST", { extraction_schema_id: draft.id, code: "R1", kind: "field", expression: { op: "required" }, severity: "fail" })).json.error!.code).toBe("DUPLICATE_RESOURCE");
    expect((await call("/data-capture/validation-rules", ADM, "POST", { extraction_schema_id: pub.id, code: "R2", kind: "field", expression: { op: "required" }, severity: "fail" })).status).toBe(409);
    const p = await call(`/data-capture/extraction-schemas/${draft.id}/publish`, ADM, "POST", { version: 1 });
    expect(p.json.data.status).toBe("published");
    expect((await call("/data-capture/extraction-schemas?document_type=HR_ROSTER&status=retired", ADM)).json.data.map((s: { id: string }) => s.id)).toEqual([pub.id]);
    expect((await call("/data-capture/incidents", ADM)).status).toBe(403);
    const inc = await call("/data-capture/incidents", REV, "POST", { source_document_id: SEED_DOC.roster, field_name: "salary", description: "Sai lương" });
    expect(inc.status).toBe(201);
    expect((await call("/data-capture/incidents?undetected_only=true", REV)).json.data).toHaveLength(0);
  });
});
