/** Pure helpers for the SCR-51 tree (T-617F): nest the flat EP-ORG-24 list by `parent_id`. */
export interface FlatDept {
  id: string;
  parent_id: string | null;
  code: string;
  name: string;
  headcount: number;
}

export interface DeptNode<T extends FlatDept> {
  dept: T;
  children: DeptNode<T>[];
  /** Headcount of this department + all descendants. */
  total: number;
}

/** Roots = no parent or a parent not visible (MGR subtree / archived parent). Sorted by code. */
export function nestDepartments<T extends FlatDept>(rows: readonly T[]): DeptNode<T>[] {
  const byId = new Map(rows.map((d) => [d.id, d]));
  const kids = new Map<string | null, T[]>();
  for (const d of rows) {
    const key = d.parent_id && byId.has(d.parent_id) ? d.parent_id : null;
    kids.set(key, [...(kids.get(key) ?? []), d]);
  }
  const seen = new Set<string>();
  const build = (d: T): DeptNode<T> => {
    seen.add(d.id);
    const children = (kids.get(d.id) ?? []).filter((c) => !seen.has(c.id)).sort(byCode).map(build);
    return { dept: d, children, total: d.headcount + children.reduce((s, c) => s + c.total, 0) };
  };
  return (kids.get(null) ?? []).sort(byCode).map(build);
}

const byCode = (a: FlatDept, b: FlatDept) => a.code.localeCompare(b.code);

/** Departments that may become the parent of `id` (not itself, not a descendant). */
export function parentCandidates<T extends FlatDept>(rows: readonly T[], id: string | null): T[] {
  if (!id) return [...rows];
  const banned = new Set([id]);
  let grew = true;
  while (grew) {
    grew = false;
    for (const d of rows) if (d.parent_id && banned.has(d.parent_id) && !banned.has(d.id)) { banned.add(d.id); grew = true; }
  }
  return rows.filter((d) => !banned.has(d.id));
}
