/**
 * Sidebar navigation per role — 06 §2.1 (IA) × 02 §3 (permission matrix), routes per 06 §2.3.
 *
 * Rules:
 * - An item a role has no right to is **hidden** (06 §2.1, last bullet); the API still enforces
 *   (02 §4.1). Context-only screens (SCR-06 Review, SCR-09 Metric Detail, SCR-10 Source Viewer)
 *   are never on the sidebar (06 §2.1).
 * - Role Switcher (SCR-12) lives in the top bar, not here (06 §2.1, §2.2).
 * - `home_route` mirrors 05 §4.2 `roles.home_route` / 10 EP-02..EP-04 (ROLE-05 → Inbox SCR-05);
 *   T-106/T-107 will read the real value from the session (`UserOut.role.home_route`).
 */
import type { RoleCode } from "@aureon/shared-types";

export const ROLE_CODES = ["ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05"] as const satisfies readonly RoleCode[];

/** `roles.key` per 05 §4.2 — also the i18n key suffix for the role name (`shell.roles.<key>`). */
export type RoleKey = "CEO" | "CFO" | "SALES_DIRECTOR" | "HR_MANAGER" | "REVIEWER";

export const ROLE_KEY: Record<RoleCode, RoleKey> = {
  "ROLE-01": "CEO",
  "ROLE-02": "CFO",
  "ROLE-03": "SALES_DIRECTOR",
  "ROLE-04": "HR_MANAGER",
  "ROLE-05": "REVIEWER",
};

/** Sidebar item ids (06 §2.1 rows 1–6); also the i18n key suffix `shell.nav.<id>`. */
export type NavItemId = "dashboard" | "inbox" | "documents" | "upload" | "schemas" | "audit";

export type ScreenId = "SCR-01..04" | "SCR-05" | "SCR-07" | "SCR-08" | "SCR-11" | "SCR-14";

export interface NavItemConfig {
  id: NavItemId;
  /** Route per 06 §2.3. */
  href: string;
  screen: ScreenId;
  /** Roles that see the item (06 §2.1 column 4, derived from 02 §3). */
  roles: readonly RoleCode[];
  /** Spec rows justifying `roles`. */
  source: string;
}

/** Ordered as in 06 §2.1. */
export const NAV_ITEMS: readonly NavItemConfig[] = [
  {
    id: "dashboard",
    href: "/dashboard",
    screen: "SCR-01..04",
    roles: ["ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04"],
    source: "06 §2.1 #1; 02 §3.2, §3.7 (ROLE-05 dashboard = none)",
  },
  {
    id: "inbox",
    href: "/inbox",
    screen: "SCR-05",
    roles: ["ROLE-01", "ROLE-02", "ROLE-04", "ROLE-05"],
    source: "06 §2.1 #2; 02 §3.4 review-queue row (ROLE-03 = none)",
  },
  {
    id: "documents",
    href: "/documents",
    screen: "SCR-07",
    roles: ["ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05"],
    source: "06 §2.1 #3; 02 §3.4 document-status row (scope-filtered)",
  },
  {
    id: "upload",
    href: "/upload",
    screen: "SCR-08",
    roles: ["ROLE-01", "ROLE-02", "ROLE-03", "ROLE-04", "ROLE-05"],
    source: "06 §2.1 #4; 02 §3.4 upload row (UC-07 mode: ROLE-01, ROLE-05 only — in-page)",
  },
  {
    id: "schemas",
    href: "/schemas",
    screen: "SCR-11",
    roles: ["ROLE-05"],
    source: "06 §2.1 #5, §3.1 SCR-11 (P1, read-only)",
  },
  {
    id: "audit",
    href: "/audit",
    screen: "SCR-14",
    roles: ["ROLE-01"],
    source: "06 §2.1 #6; 02 §3.6 audit-log row (ROLE-01 only)",
  },
];

/** Home route after login / role switch (05 §4.2 `home_route`; TC-AUTH-016: ROLE-05 → SCR-05). */
export const HOME_ROUTE: Record<RoleCode, string> = {
  "ROLE-01": "/dashboard",
  "ROLE-02": "/dashboard",
  "ROLE-03": "/dashboard",
  "ROLE-04": "/dashboard",
  "ROLE-05": "/inbox",
};

/** Dashboard screen rendered at `/dashboard` for each role (06 §3.1). */
export const DASHBOARD_SCREEN: Partial<Record<RoleCode, "SCR-01" | "SCR-02" | "SCR-03" | "SCR-04">> = {
  "ROLE-01": "SCR-01",
  "ROLE-02": "SCR-02",
  "ROLE-03": "SCR-03",
  "ROLE-04": "SCR-04",
};

export function getNavItems(role: RoleCode): NavItemConfig[] {
  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}

export function canAccessNavItem(role: RoleCode, id: NavItemId): boolean {
  return NAV_ITEMS.some((item) => item.id === id && item.roles.includes(role));
}

/** Active-link rule: exact match or a nested route (e.g. `/documents/123` → Documents). */
export function isNavItemActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function isRoleCode(value: unknown): value is RoleCode {
  return typeof value === "string" && (ROLE_CODES as readonly string[]).includes(value);
}
