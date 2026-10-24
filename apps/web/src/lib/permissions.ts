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
  /** ROLE-DIR only: allowed when the DIR's khối includes one of these (default deny). */
  dirPillars?: readonly string[];
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
  // M1.2 (06 §3.4): DIR khối O reaches Quản trị for SCR-51/52 (org structure) only.
  { key: "admin", href: "/admin", scr: "SCR-50", group: "admin", roles: ["ADM", "CEO", "DIR"], anyOf: ["platform:read", "hr:admin"], dirPillars: ["O"] },
];

/** Protected route prefixes (06 §3.4). Longest prefix wins; sub-routes narrow their parent. */
type RouteRule = { prefix: string } & AccessRule;
const SUB_ROUTES: readonly RouteRule[] = [
  { prefix: "/home/pillar", roles: ["CEO", "DIR"], anyOf: ["dashboard:read"] },
  { prefix: "/work/approvals", roles: ["CEO", "DIR", "MGR"], anyOf: ["platform:approve"] },
  // M1.3 (06 §3.4, R-DEC-48): SCR-55/56 projects (EMP: projects with own tasks), SCR-57 workload
  { prefix: "/work/projects", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { prefix: "/work/workload", roles: ["CEO", "DIR", "MGR"], anyOf: ["execution:query"] },
  // M1.4 (06 §3.4): SCR-58 KPI detail, SCR-59 Objective detail, SCR-60 check-ins (EMP: own scope — the API filters)
  { prefix: "/goals/kpis", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { prefix: "/goals/objectives", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { prefix: "/goals/check-ins", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { prefix: "/data/review", roles: ["REV", "DIR", "MGR", "CEO"], anyOf: ["idp:approve"] },
  // M1.5 (06 §3.4): SCR-61 C1 form, SCR-62 C5 import wizard (ADM: R-DEC-76 `idp:write` scope s), SCR-63 capture config
  { prefix: "/data/new", roles: ["CEO", "DIR", "MGR", "EMP", "REV", "ADM"], anyOf: ["idp:write"] },
  { prefix: "/data/imports", roles: ["CEO", "DIR", "MGR", "EMP", "REV", "ADM"], anyOf: ["idp:write"] },
  { prefix: "/admin/data-capture", roles: ["ADM"], anyOf: ["idp:admin"] },
  { prefix: "/business/finance", roles: ["CEO", "DIR", "MGR", "EMP", "REV"], anyOf: ["finance:read"] },
  { prefix: "/business/hr", roles: ["CEO", "DIR", "MGR", "EMP", "REV"], anyOf: ["hr:read"] },
  { prefix: "/admin/audit", roles: ["ADM"], anyOf: ["platform:read"] },
  { prefix: "/admin/org", roles: ["ADM", "CEO", "DIR"], anyOf: ["hr:admin"], dirPillars: ["O"] },
  { prefix: "/admin/positions", roles: ["ADM", "CEO", "DIR"], anyOf: ["hr:admin"], dirPillars: ["O"] },
  { prefix: "/admin/users", roles: ["ADM", "CEO"], anyOf: ["platform:read"] },
  { prefix: "/admin/roles", roles: ["ADM", "CEO"], anyOf: ["platform:read"] },
];
export const ROUTE_RULES: readonly RouteRule[] = [
  ...NAV_ITEMS.map(({ href, roles, anyOf, dirPillars }): RouteRule => ({ prefix: href, roles, anyOf, dirPillars })),
  ...SUB_ROUTES,
].sort((a, b) => b.prefix.length - a.prefix.length);

export const PROTECTED_PREFIXES = ROUTE_RULES.map((r) => r.prefix);

export function hasAny(perms: readonly string[], anyOf: readonly string[]): boolean {
  return anyOf.length === 0 || anyOf.some((p) => perms.includes(p));
}

function pillarOk(rule: AccessRule, role: string, pillars: readonly string[]): boolean {
  if (role !== "DIR" || !rule.dirPillars) return true;
  return rule.dirPillars.some((p) => pillars.includes(p));
}

function allowed(rule: AccessRule, role: string, perms: readonly string[], pillars: readonly string[] = []): boolean {
  return (rule.roles as readonly string[]).includes(role) && hasAny(perms, rule.anyOf) && pillarOk(rule, role, pillars);
}

export function ruleFor(pathname: string) {
  return ROUTE_RULES.find((r) => pathname === r.prefix || pathname.startsWith(`${r.prefix}/`));
}

/** Pages outside the role-gated (app) tree, open to any signed-in user. */
const PUBLIC_PAGES = new Set(["/", "/403"]);

/** Default deny (06 §3.3): a path with no rule is closed — every (app) route must declare one. */
export function canAccess(pathname: string, role: string, perms: readonly string[], pillars: readonly string[] = []): boolean {
  const rule = ruleFor(pathname);
  if (rule) return allowed(rule, role, perms, pillars);
  return PUBLIC_PAGES.has(pathname);
}

/** Same-origin relative callback only (no `//host`, no `/\host` which browsers treat as `//`). */
export function safeCallback(cb: string | null, origin: string): string {
  if (!cb || !cb.startsWith("/") || cb.includes("\\")) return "/";
  try {
    const url = new URL(cb, origin);
    return url.origin === origin ? url.pathname + url.search + url.hash : "/";
  } catch {
    return "/";
  }
}

export function visibleNav(role: string, perms: readonly string[], pillars: readonly string[] = []): NavItem[] {
  return NAV_ITEMS.filter((i) => allowed(i, role, perms, pillars));
}

/** Tab bar of `/work` (06 §3.4 Spec lock M1.3): Task của tôi · Nhóm (not EMP) · Dự án · Workload · Phê duyệt. */
export type WorkTabKey = "mine" | "board" | "projects" | "workload" | "approvals";
export interface WorkTab extends AccessRule { key: WorkTabKey; href: string; scr: string }
export const WORK_TABS: readonly WorkTab[] = [
  { key: "mine", href: "/work", scr: "SCR-42", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { key: "board", href: "/work?view=board", scr: "SCR-42", roles: ["CEO", "DIR", "MGR"], anyOf: ["execution:read"] },
  { key: "projects", href: "/work/projects", scr: "SCR-55", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { key: "workload", href: "/work/workload", scr: "SCR-57", roles: ["CEO", "DIR", "MGR"], anyOf: ["execution:query"] },
  { key: "approvals", href: "/work/approvals", scr: "SCR-43", roles: ["CEO", "DIR", "MGR"], anyOf: ["platform:approve"] },
];

export function visibleWorkTabs(role: string, perms: readonly string[]): WorkTab[] {
  return WORK_TABS.filter((tab) => allowed(tab, role, perms));
}

/** Every human role lands on Trang chủ (SCR-40); the AI actor has no UI. */
export function landingFor(role: string, perms: readonly string[]): string {
  return canAccess("/home", role, perms) ? "/home" : "/403";
}

/** Tab bar of `/goals` (06 §3.4 Spec lock M1.4): Cây mục tiêu (SCR-41) · Check-in (SCR-60). */
export type GoalsTabKey = "tree" | "checkins";
export interface GoalsTab extends AccessRule { key: GoalsTabKey; href: string; scr: string }
export const GOALS_TABS: readonly GoalsTab[] = [
  { key: "tree", href: "/goals", scr: "SCR-41", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { key: "checkins", href: "/goals/check-ins", scr: "SCR-60", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
];

export function visibleGoalsTabs(role: string, perms: readonly string[]): GoalsTab[] {
  return GOALS_TABS.filter((tab) => allowed(tab, role, perms));
}
