/**
 * Mock data scope for D03 (mirror of `idp/services/scope.py` `inbox_filter` / `document_visible` /
 * `lineage_visible`, bảng scope 10 §7.2.4). Pillar of a target permission follows `DOMAIN_PILLAR`
 * (hr → O, finance → F; execution/idp cross-pillar).
 */
import type { MockClaims } from "./fixtures";
import { ACT_PERMISSION } from "./capture-schemas";
import type { MDoc } from "./capture-store";

const DOMAIN_PILLAR: Record<string, string> = { finance: "F", hr: "O", sales: "C", product: "U", risk: "S" };

/** `Principal.has` + `in_pillar` — a DIR writes a domain only inside its khối (require_pillar). */
export function canPerm(c: MockClaims, perm: string): boolean {
  if (!c.permissions.includes(perm)) return false;
  const pillar = DOMAIN_PILLAR[perm.split(":")[0] ?? ""];
  return c.role !== "DIR" || !pillar || c.scope_pillars.length === 0 || c.scope_pillars.includes(pillar);
}

/** ACT required_permission (any-of) held by the caller; EMP writes execution only for itself (scope `o`). */
export function actPermitted(c: MockClaims, action: string, ownOnly = false): boolean {
  const perms = ACT_PERMISSION[action] ?? [];
  if (c.role === "EMP" && action !== "ACT-create_task" && action !== "ACT-record_kr_checkin") return false;
  if (c.role === "EMP" && !ownOnly) return false;
  return perms.some((p) => canPerm(c, p));
}

/** Level-4 values (salary…) are readable by CEO / DIR khối O, and REV inside its assigned review. */
export function seesLevel4(c: MockClaims, doc?: MDoc): boolean {
  if (c.role === "CEO") return true;
  if (c.role === "DIR") return c.scope_pillars.length === 0 || c.scope_pillars.includes("O");
  return c.role === "REV" && doc !== undefined && doc.assigned_to === c.sub;
}

/** EP-DC-13 / GET-by-id scope. ADM is refused at the inbox (403) but sees its own submissions by id. */
export function docVisible(c: MockClaims, d: MDoc): boolean {
  if (d.submitted_by === c.sub || d.approved_by === c.sub) return true;
  switch (c.role) {
    case "CEO": return true;
    case "DIR": return c.scope_pillars.length === 0 || d.pillars.some((p) => c.scope_pillars.includes(p)) || d.department_id === c.department_id;
    case "MGR": return d.department_id === c.department_id;
    case "REV": return d.assigned_to === c.sub;
    default: return false;
  }
}

/** Review queue scope (EP-DC-04): REV = assigned; DIR = khối; MGR = department. */
export function reviewVisible(c: MockClaims, d: MDoc): boolean {
  if (!c.permissions.includes("idp:approve")) return false;
  if (c.role === "REV") return d.assigned_to === c.sub;
  return docVisible(c, d);
}
