/**
 * IA v3 navigation + route access (06 §3.1–§3.4, R-DEC-25, T-607). Display only — the backend
 * enforces (default deny). An item/route is visible when the role is in the "Role thấy" column
 * of 06 §3.4 **and** the user holds one of `anyOf` (empty = any authenticated user).
 */
export type RoleCode = "CEO" | "DIR" | "MGR" | "EMP" | "REV" | "ADM" | "AI";
export type NavKey = "home" | "ask" | "goals" | "work" | "meetings" | "data" | "business" | "knowledge" | "admin";

const HUMANS: readonly RoleCode[] = ["CEO", "DIR", "MGR", "EMP", "REV", "ADM"];
const EXECUTION_ROLES: readonly RoleCode[] = ["CEO", "DIR", "MGR", "EMP"];

export interface AccessRule {
  roles: readonly RoleCode[];
  /** Any of these permissions grants access; empty = authenticated is enough. */
  anyOf: readonly string[];
}

export interface NavItem extends AccessRule {
  key: NavKey;
  href: string;
  scr: string;
  /** `admin` = the separate "Quản trị" group under the 8 main items (06 §3.1). */
  group: "main" | "admin";
}

/** 8 IA items + Quản trị (06 §3.1). product/risk have no item of their own (R-DEC-16). */
export const NAV_ITEMS: readonly NavItem[] = [
  { key: "home", href: "/home", scr: "SCR-40", group: "main", roles: HUMANS, anyOf: [] },
  { key: "ask", href: "/ask", scr: "SCR-16", group: "main", roles: HUMANS, anyOf: ["ai:query"] },
  { key: "goals", href: "/goals", scr: "SCR-41", group: "main", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { key: "work", href: "/work", scr: "SCR-42", group: "main", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { key: "meetings", href: "/meetings", scr: "SCR-44", group: "main", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { key: "data", href: "/data", scr: "SCR-45", group: "main", roles: HUMANS, anyOf: ["idp:read", "idp:admin"] },
  { key: "business", href: "/business", scr: "SCR-46", group: "main", roles: ["CEO", "DIR", "MGR", "EMP", "REV"], anyOf: ["finance:read", "sales:read", "hr:read"] },
  { key: "knowledge", href: "/knowledge", scr: "SCR-49", group: "main", roles: HUMANS, anyOf: [] },
  { key: "admin", href: "/admin", scr: "SCR-50", group: "admin", roles: ["ADM", "CEO"], anyOf: ["platform:read"] },
];

/** Protected route prefixes (06 §3.4). Longest prefix wins; sub-routes narrow their parent. */
type RouteRule = { prefix: string } & AccessRule;
const SUB_ROUTES: readonly RouteRule[] = [
  { prefix: "/home/pillar", roles: ["CEO", "DIR"], anyOf: ["dashboard:read"] },
  { prefix: "/work/approvals", roles: ["CEO", "DIR", "MGR"], anyOf: ["platform:approve"] },
  { prefix: "/data/review", roles: ["REV", "DIR", "MGR", "CEO"], anyOf: ["idp:approve"] },
  { prefix: "/business/finance", roles: ["CEO", "DIR", "MGR", "EMP", "REV"], anyOf: ["finance:read"] },
  { prefix: "/business/hr", roles: ["CEO", "DIR", "MGR", "EMP", "REV"], anyOf: ["hr:read"] },
  { prefix: "/admin/audit", roles: ["ADM"], anyOf: ["platform:read"] },
];
export const ROUTE_RULES: readonly RouteRule[] = [
  ...NAV_ITEMS.map(({ href, roles, anyOf }): RouteRule => ({ prefix: href, roles, anyOf })),
  ...SUB_ROUTES,
].sort((a, b) => b.prefix.length - a.prefix.length);

export const PROTECTED_PREFIXES = ROUTE_RULES.map((r) => r.prefix);

export function hasAny(perms: readonly string[], anyOf: readonly string[]): boolean {
  return anyOf.length === 0 || anyOf.some((p) => perms.includes(p));
}

function allowed(rule: AccessRule, role: string, perms: readonly string[]): boolean {
  return (rule.roles as readonly string[]).includes(role) && hasAny(perms, rule.anyOf);
}

export function ruleFor(pathname: string) {
  return ROUTE_RULES.find((r) => pathname === r.prefix || pathname.startsWith(`${r.prefix}/`));
}

export function canAccess(pathname: string, role: string, perms: readonly string[]): boolean {
  const rule = ruleFor(pathname);
  return rule ? allowed(rule, role, perms) : true;
}

export function visibleNav(role: string, perms: readonly string[]): NavItem[] {
  return NAV_ITEMS.filter((i) => allowed(i, role, perms));
}

/** Every human role lands on Trang chủ (SCR-40); the AI actor has no UI. */
export function landingFor(role: string, perms: readonly string[]): string {
  return canAccess("/home", role, perms) ? "/home" : "/403";
}
