/**
 * IA v3 navigation + route access (06 §3.1–§3.4, R-DEC-25, T-607). Display only — the backend
 * enforces (default deny). An item/route is visible when the role is in the "Role thấy" column
 * of 06 §3.4 **and** the user holds one of `anyOf` (empty = any authenticated user).
 */
export type RoleCode = "CEO" | "DIR" | "MGR" | "EMP" | "REV" | "ADM" | "AI";
export type NavKey = "home" | "ask" | "goals" | "work" | "meetings" | "data" | "review" | "business" | "knowledge" | "admin";

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

/**
 * 8 IA items + Quản trị (06 §3.1). product/risk have no item of their own (R-DEC-16). `review` is
 * the shortcut to SCR-18a for whoever holds review duty (`idp:approve`): the queue used to be
 * reachable only from a document row, so a Reviewer had no way in.
 */
export const NAV_ITEMS: readonly NavItem[] = [
  { key: "home", href: "/home", scr: "SCR-40", group: "main", roles: HUMANS, anyOf: [] },
  { key: "ask", href: "/ask", scr: "SCR-16", group: "main", roles: HUMANS, anyOf: ["ai:query"] },
  { key: "goals", href: "/goals", scr: "SCR-41", group: "main", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { key: "work", href: "/work", scr: "SCR-42", group: "main", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { key: "meetings", href: "/meetings", scr: "SCR-44", group: "main", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { key: "data", href: "/data", scr: "SCR-45", group: "main", roles: HUMANS, anyOf: ["idp:read", "idp:admin"] },
  { key: "review", href: "/data/review", scr: "SCR-18a", group: "main", roles: ["REV", "DIR", "MGR", "CEO"], anyOf: ["idp:approve"] },
  { key: "business", href: "/business", scr: "SCR-46", group: "main", roles: ["CEO", "DIR", "MGR", "EMP"], anyOf: ["finance:read", "sales:read", "hr:read"] },
  { key: "knowledge", href: "/knowledge", scr: "SCR-49", group: "main", roles: HUMANS, anyOf: [] },
  // M1.2 (06 §3.4): DIR khối O reaches Quản trị for SCR-51/52 (org structure) only.
  { key: "admin", href: "/admin", scr: "SCR-50", group: "admin", roles: ["ADM", "CEO", "DIR"], anyOf: ["platform:read", "hr:admin"], dirPillars: ["O"] },
];

/** Protected route prefixes (06 §3.4). Longest prefix wins; sub-routes narrow their parent. */
type RouteRule = { prefix: string } & AccessRule;
const SUB_ROUTES: readonly RouteRule[] = [
  { prefix: "/home/pillar", roles: ["CEO", "DIR"], anyOf: ["dashboard:read"] },
  // EP-12 / EP-15 are `dashboard:read`: MGR / EMP / REV / ADM would open a page of permission errors.
  { prefix: "/home/alerts", roles: HUMANS, anyOf: ["dashboard:read"] },
  { prefix: "/home/metrics", roles: HUMANS, anyOf: ["dashboard:read"] },
  { prefix: "/work/approvals", roles: ["CEO", "DIR", "MGR"], anyOf: ["platform:approve"] },
  // M1.3 (06 §3.4, R-DEC-48): SCR-55/56 projects (EMP: projects with own tasks), SCR-57 workload
  { prefix: "/work/projects", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { prefix: "/work/workload", roles: ["CEO", "DIR", "MGR"], anyOf: ["execution:query"] },
  // M1.4 (06 §3.4): SCR-58 KPI detail, SCR-59 Objective detail, SCR-60 check-ins (EMP: own scope — the API filters)
  { prefix: "/goals/kpis", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  { prefix: "/goals/objectives", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  // F12: Strategy + StrategicObjective list (EP-STR-02/03/07/08); EMP stays on the own tree
  { prefix: "/goals/strategies", roles: ["CEO", "DIR", "MGR"], anyOf: ["execution:read"] },
  { prefix: "/goals/check-ins", roles: EXECUTION_ROLES, anyOf: ["execution:read"] },
  // M1.5 (06 §3.4): SCR-61 C1 form, SCR-62 C5 import wizard (ADM: R-DEC-76 `idp:write` scope s), SCR-63 capture config
  { prefix: "/data/new", roles: ["CEO", "DIR", "MGR", "EMP", "REV", "ADM"], anyOf: ["idp:write"] },
  { prefix: "/data/imports", roles: ["CEO", "DIR", "MGR", "EMP", "REV", "ADM"], anyOf: ["idp:write"] },
  { prefix: "/admin/data-capture", roles: ["ADM"], anyOf: ["idp:admin"] },
  // M6: record screens follow the API's khối isolation (`require_pillar_permission`) — a DIR of another
  // khối is sent to /403 instead of a page whose every call answers 403. Overviews built on the
  // cross-khối `:query` endpoints (/finance/dashboard, /sales/pipeline) stay open to every DIR, and
  // need that `:query` permission: `:read` alone (REV, EMP's `/business` hub) gets only 403 there.
  // D-07 (R-DEC-183): REV `◑r` reads finance / sales only inside an assigned review, and MGR `◑d` has no
  // company invoices (no `department_id`) — the API answers 403 FORBIDDEN_SCOPE, so no route leads there.
  { prefix: "/business/finance", roles: ["CEO", "DIR", "MGR", "EMP"], anyOf: ["finance:query"] },
  { prefix: "/business/sales", roles: ["CEO", "DIR", "MGR", "EMP"], anyOf: ["sales:query"] },
  // D-20: MGR lists the invoices they created (incl. through an IDP review); company invoices of others stay 403
  { prefix: "/business/finance/invoices", roles: ["CEO", "DIR", "MGR", "EMP"], anyOf: ["finance:read"], dirPillars: ["F"] },
  // REV: `hr:read ◑r` covers an assigned review only — every employee / hiring-plan list is 403 (scope.py)
  { prefix: "/business/hr", roles: ["CEO", "DIR", "MGR", "EMP"], anyOf: ["hr:read"], dirPillars: ["O"] },
  // EMP reads the own profile on `/business/hr/employees`; the records editor is for HR managers
  { prefix: "/business/hr/records", roles: ["CEO", "DIR", "MGR"], anyOf: ["hr:read"], dirPillars: ["O"] },
  // M7 record editors: the list endpoints are khối-isolated (`require_pillar_permission`)
  { prefix: "/business/finance/records", roles: ["CEO", "DIR", "MGR", "EMP"], anyOf: ["finance:read"], dirPillars: ["F"] },
  { prefix: "/business/sales/records", roles: ["CEO", "DIR", "MGR", "EMP"], anyOf: ["sales:read"], dirPillars: ["C"] },
  // D-21: record management of the frozen product / risk modules (R-DEC-16 keeps them off the sidebar)
  { prefix: "/business/product", roles: ["CEO", "DIR"], anyOf: ["product:read"], dirPillars: ["U"] },
  { prefix: "/business/risk", roles: ["CEO", "DIR"], anyOf: ["risk:read"], dirPillars: ["S"] },
  // D-21: meetings / decisions / projects editor (the API scopes DIR / MGR to their unit)
  { prefix: "/business/execution", roles: ["CEO", "DIR", "MGR"], anyOf: ["execution:write"] },
  // M8 CRM views (R-DEC-175): deal / client records in khối C; REV's sales:read is review-scoped
  { prefix: "/business/sales/pipeline", roles: ["CEO", "DIR", "MGR"], anyOf: ["sales:read"], dirPillars: ["C"] },
  { prefix: "/business/sales/deals", roles: ["CEO", "DIR", "MGR"], anyOf: ["sales:read"], dirPillars: ["C"] },
  { prefix: "/business/sales/clients", roles: ["CEO", "DIR", "MGR"], anyOf: ["sales:read"], dirPillars: ["C"] },
  { prefix: "/admin/audit", roles: ["ADM"], anyOf: ["platform:read"] },
  { prefix: "/admin/org", roles: ["ADM", "CEO", "DIR"], anyOf: ["hr:admin"], dirPillars: ["O"] },
  { prefix: "/admin/positions", roles: ["ADM", "CEO", "DIR"], anyOf: ["hr:admin"], dirPillars: ["O"] },
  { prefix: "/admin/users", roles: ["ADM", "CEO"], anyOf: ["platform:read"] },
  { prefix: "/admin/roles", roles: ["ADM", "CEO"], anyOf: ["platform:read"] },
  // M1.6 (06 §3.4, R-DEC-79): SCR-64/65 AI Control Center + logs (DIR never), SCR-66 onboarding wizard
  { prefix: "/admin/ai", roles: ["ADM", "CEO"], anyOf: ["ai:admin"] },
  { prefix: "/admin/onboarding", roles: ["ADM", "CEO"], anyOf: ["platform:admin"] },
  // M3.5 (09 §2.2, R-DEC-145): SCR-64 MVP acceptance G1–G4 (CEO toàn DN / DIR theo scope)
  { prefix: "/admin/acceptance", roles: ["ADM", "CEO", "DIR"], anyOf: ["dashboard:read"] },
];
export const ROUTE_RULES: readonly RouteRule[] = [
  ...NAV_ITEMS.map(({ href, roles, anyOf, dirPillars }): RouteRule => ({ prefix: href, roles, anyOf, dirPillars })),
  ...SUB_ROUTES,
].sort((a, b) => b.prefix.length - a.prefix.length);

export const PROTECTED_PREFIXES = ROUTE_RULES.map((r) => r.prefix);

/**
 * Domain ↔ khối F.O.C.U.S — mirror of `core/permissions.py` `DOMAIN_PILLAR` (R-DEC-12a). The API
 * isolates a DIR to the khối of `finance`/`hr`/`sales`/`product`/`risk` (`require_pillar_permission`:
 * DIR ngoài khối → `403 FORBIDDEN_ROLE`, 10 §7.2.1), so the UI must not offer — or call — another
 * khối's records: e.g. Finance-DIR has `hr:read` but `/org/tree`, `/hr/departments` answer 403.
 */
export const DOMAIN_PILLAR: Readonly<Record<string, string>> = { finance: "F", hr: "O", sales: "C", product: "U", risk: "S" };

/** `Principal.in_pillar` (display only): empty khối (CEO, non-DIR, DIR toàn khối) or cross-pillar domain → true. */
export function inPillar(domain: string, pillars: readonly string[]): boolean {
  const p = DOMAIN_PILLAR[domain];
  return pillars.length === 0 || p === undefined || pillars.includes(p);
}

/** `<domain>:<action>` held **and** inside the caller's khối — what a `require_pillar_permission` endpoint accepts. */
export function canDomain(perms: readonly string[], pillars: readonly string[], domain: string, action = "read"): boolean {
  return perms.includes(`${domain}:${action}`) && inPillar(domain, pillars);
}

/** Department / employee directory (`/hr/departments`, `/hr/employees`, `/org/tree`): `hr:read` in khối O; EMP / REV have no structure scope (10 §7.2.1). */
export function canReadHrDirectory(role: string, perms: readonly string[], pillars: readonly string[]): boolean {
  return canDomain(perms, pillars, "hr") && role !== "EMP" && role !== "REV";
}

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

/** The one nav item for `pathname`: the longest match, so `/data/review` lights "review", not "data" too. */
export function activeNavHref(pathname: string, items: readonly Pick<NavItem, "href">[]): string | undefined {
  return items
    .map((i) => i.href)
    .filter((h) => pathname === h || pathname.startsWith(`${h}/`))
    .sort((a, b) => b.length - a.length)[0];
}

/** Hub cards of `/business` (SCR-46): built screens, shown only where the role may open them. */
export const HUB_CARDS = [
  { href: "/business/finance", key: "finance" },
  { href: "/business/sales", key: "sales" },
  { href: "/business/finance/invoices", key: "invoices" },
  { href: "/business/hr/employees", key: "employees" },
  // M7: create / edit / archive records
  { href: "/business/finance/records", key: "financeRecords" },
  { href: "/business/sales/records", key: "salesRecords" },
  { href: "/business/hr/records", key: "hrRecords" },
  // D-21
  { href: "/business/product/records", key: "productRecords" },
  { href: "/business/risk/records", key: "riskRecords" },
  { href: "/business/execution/records", key: "executionRecords" },
] as const;

export function visibleHubCards(role: string, perms: readonly string[], pillars: readonly string[] = []) {
  return HUB_CARDS.filter((c) => canAccess(c.href, role, perms, pillars));
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
  // SCR-40 (R-DEC-84/85): Reviewer vào hàng chờ, Admin vào cấu hình nền tảng, còn lại Trang chủ.
  if (role === "REV" && canAccess("/data", role, perms)) return "/data";
  if (role === "ADM" && canAccess("/admin", role, perms)) return "/admin";
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
