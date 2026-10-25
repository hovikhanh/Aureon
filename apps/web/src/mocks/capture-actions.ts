/**
 * Mock Action Registry v2 (bảng ACT 10 §7.2.4, R-DEC-60/61/63): plan → validate (dry-run every
 * row) → run in `ACT_ORDER` writing into the org / work / goals mock stores with `source` +
 * `source_document_id`, lineage per target column; undo in `seq DESC` order with the
 * "edited after commit" conflict check. All-or-nothing: validation runs before the first write.
 */
import type { MockClaims } from "./fixtures";
import { MockHttpError } from "./http";
import { ACT_ORDER, ACT_PERMISSION, ACT_REQUIRED, ACT_TABLE, SCHEMA_FIELDS } from "./capture-schemas";
import { actPermitted } from "./capture-scope";
import type { MAction, MDoc, MField } from "./capture-store";
import { captureStore, nowIso } from "./capture-store";
import { runAct, undoRef, refEdited, actDuplicate } from "./capture-targets";

export type Row = { row_index: number | null; values: Record<string, unknown>; fields: MField[] };

export const effective = (f: MField): unknown => (f.corrected_value !== null && f.corrected_value !== undefined ? f.corrected_value : f.ai_value);

/** Header values merged into every row (period_key …); a doc without rows = one header row. */
export function docRows(d: MDoc): Row[] {
  const header = d.fields.filter((f) => f.row_index === null);
  const hv = Object.fromEntries(header.map((f) => [f.field_name, effective(f)]));
  const idx = [...new Set(d.fields.filter((f) => f.row_index !== null).map((f) => f.row_index as number))].sort((a, b) => a - b);
  if (idx.length === 0) return [{ row_index: null, values: hv, fields: header }];
  return idx.map((i) => {
    const fs = d.fields.filter((f) => f.row_index === i);
    return { row_index: i, values: { ...hv, ...Object.fromEntries(fs.map((f) => [f.field_name, effective(f)])) }, fields: [...header, ...fs] };
  });
}

const filled = (v: unknown) => v !== null && v !== undefined && String(v).trim() !== "";

/** Which ACT runs for a row: an ACT with at least one target field filled (ACT_REQUIRED decides validity). */
export function rowActs(d: MDoc, r: Row): string[] {
  const defs = SCHEMA_FIELDS[d.document_type ?? ""] ?? [];
  const acts = new Set(defs.filter((f) => f.target && f.group === "row" && filled(r.values[f.name])).map((f) => f.target!.action));
  return ACT_ORDER.filter((a) => acts.has(a));
}

export interface Planned { action_name: string; count: number; required_permission: string; permitted: boolean }
export function plannedActions(c: MockClaims, d: MDoc): Planned[] {
  const counts = new Map<string, number>();
  for (const r of docRows(d)) for (const a of rowActs(d, r)) counts.set(a, (counts.get(a) ?? 0) + 1);
  return ACT_ORDER.filter((a) => counts.has(a)).map((a) => ({ action_name: a, count: counts.get(a)!, required_permission: ACT_PERMISSION[a]?.[0] ?? "execution:write", permitted: actPermitted(c, a, true) }));
}

/** Dry-run validate (EP-DC-08 / 16 / 23): required params + target duplicates → 422 ACTION_REJECTED. */
export function validateActs(d: MDoc): void {
  for (const r of docRows(d)) {
    for (const a of rowActs(d, r)) {
      const missing = (ACT_REQUIRED[a] ?? []).filter((p) => !filled(r.values[p]));
      const dup = actDuplicate(a, r.values);
      const errors = [...missing.map((p) => ({ field: p, code: "missing", message: "field required" })), ...(dup ? [{ field: dup, code: "duplicate", message: "already exists" }] : [])];
      if (errors.length) throw new MockHttpError(422, "ACTION_REJECTED", "action validation failed", { action_name: a, row_index: r.row_index, errors });
    }
  }
}

/** Run every ACT of the document (validated first) → document_actions rows + lineage. */
export function commitDoc(c: MockClaims, d: MDoc): MAction[] {
  validateActs(d);
  const at = nowIso();
  const created = new Map<string, string>(); // `<act>:<key>` → id (reuse inside one document)
  const actions: MAction[] = [];
  for (const a of ACT_ORDER) {
    const refs = docRows(d).filter((r) => rowActs(d, r).includes(a)).map((r) => runAct(c, d, a, r, created, at));
    if (refs.length) actions.push({ seq: actions.length + 1, action_name: a, result_refs: refs, status: "applied", reverted_at: null });
  }
  d.actions = actions;
  return actions;
}

export const actionRefs = (actions: readonly MAction[]) => actions.map((a) => ({ action_name: a.action_name, ids: a.result_refs.filter((r) => !r.reused).map((r) => r.id), table: ACT_TABLE[a.action_name] ?? "" }));

/** EP-DC-24 core: conflicts → 409 (nothing reverted); otherwise seq DESC + lineage `revoked_at`. */
export function undoDoc(d: MDoc): MAction[] {
  const conflicts = d.actions.filter((a) => a.status === "applied").flatMap((a) => a.result_refs.filter((r) => !r.reused && refEdited(r)).map((r) => ({ table: `${r.schema}.${r.table}`, id: r.id })));
  if (conflicts.length) throw new MockHttpError(409, "CONFLICT_STATE", "target records were edited after commit", { conflicts });
  const at = nowIso();
  const done = [...d.actions].sort((x, y) => y.seq - x.seq).filter((a) => a.status === "applied");
  for (const a of done) {
    for (const r of a.result_refs) if (!r.reused) undoRef(r);
    Object.assign(a, { status: "reverted", reverted_at: at });
  }
  for (const l of captureStore().lineage) if (l.document_id === d.id && !l.revoked_at) l.revoked_at = at;
  return done;
}
