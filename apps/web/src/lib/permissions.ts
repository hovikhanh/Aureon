/** Route/nav access by permission (06 §2.3–2.4). Display only — backend enforces (default deny). */
export type NavKey = "dashboard" | "idp" | "ai" | "approvals";

export interface NavItem {
  key: NavKey;
  href: string;
  /** Any of these permissions grants the item. */
  anyOf: readonly string[];
}

export const NAV_ITEMS: readonly NavItem[] = [
  { key: "dashboard", href: "/dashboard", anyOf: ["dashboard:read"] },
  { key: "idp", href: "/idp/review", anyOf: ["idp:approve"] },
  { key: "ai", href: "/ai", anyOf: ["ai:query"] },
  { key: "approvals", href: "/approvals", anyOf: ["platform:approve"] },
];

/** Protected route prefixes → required permission (any of). Longest prefix wins. */
export const ROUTE_RULES: readonly { prefix: string; anyOf: readonly string[] }[] = [
  { prefix: "/dashboard", anyOf: ["dashboard:read"] },
  { prefix: "/idp", anyOf: ["idp:approve"] },
  { prefix: "/ai", anyOf: ["ai:query"] },
  { prefix: "/finance", anyOf: ["finance:read"] },
  { prefix: "/approvals", anyOf: ["platform:approve"] },
];

export const PROTECTED_PREFIXES = ROUTE_RULES.map((r) => r.prefix);

export function hasAny(perms: readonly string[], anyOf: readonly string[]): boolean {
  return anyOf.some((p) => perms.includes(p));
}

export function ruleFor(pathname: string) {
  return ROUTE_RULES.find((r) => pathname === r.prefix || pathname.startsWith(`${r.prefix}/`));
}

export function canAccess(pathname: string, perms: readonly string[]): boolean {
  const rule = ruleFor(pathname);
  return rule ? hasAny(perms, rule.anyOf) : true;
}

export function visibleNav(perms: readonly string[]): NavItem[] {
  return NAV_ITEMS.filter((i) => hasAny(perms, i.anyOf));
}

/** Role-based landing after login (06 §2.3 "Trang chủ" row). */
export function landingFor(role: string, perms: readonly string[]): string {
  if (role === "REVIEWER" && perms.includes("idp:approve")) return "/idp/review";
  if (perms.includes("dashboard:read")) return "/dashboard";
  if (perms.includes("idp:approve")) return "/idp/review";
  if (perms.includes("ai:query")) return "/ai";
  return "/403";
}
