import type { RoleCode } from "@aureon/shared-types";

export interface DemoAccountInfo {
  roleCode: RoleCode;
  email: string;
  userNameKey: string;
  roleNameKey: string;
  homeRoute: string;
  /** i18n key: short description of what this role can do (02-PERSONAS-PERMISSIONS). */
  permissionsKey: string;
}

export const DEMO_ACCOUNTS: DemoAccountInfo[] = [
  {
    roleCode: "ROLE-01",
    email: "ceo@abc.demo",
    userNameKey: "auth.demoUserNames.accCeo",
    roleNameKey: "shell.roles.CEO",
    homeRoute: "/dashboard",
    permissionsKey: "auth.rolePermissions.ceo",
  },
  {
    roleCode: "ROLE-02",
    email: "cfo@abc.demo",
    userNameKey: "auth.demoUserNames.accCfo",
    roleNameKey: "shell.roles.CFO",
    homeRoute: "/dashboard",
    permissionsKey: "auth.rolePermissions.cfo",
  },
  {
    roleCode: "ROLE-03",
    email: "sales@abc.demo",
    userNameKey: "auth.demoUserNames.accSales",
    roleNameKey: "shell.roles.SALES_DIRECTOR",
    homeRoute: "/dashboard",
    permissionsKey: "auth.rolePermissions.sales",
  },
  {
    roleCode: "ROLE-04",
    email: "hr@abc.demo",
    userNameKey: "auth.demoUserNames.accHr",
    roleNameKey: "shell.roles.HR_MANAGER",
    homeRoute: "/dashboard",
    permissionsKey: "auth.rolePermissions.hr",
  },
  {
    roleCode: "ROLE-05",
    email: "reviewer@abc.demo",
    userNameKey: "auth.demoUserNames.accReviewer",
    roleNameKey: "shell.roles.REVIEWER",
    homeRoute: "/inbox",
    permissionsKey: "auth.rolePermissions.reviewer",
  },
];

/**
 * Demo password for a role's quick-login button, read from NEXT_PUBLIC_DEMO_PASSWORD_* env
 * (inlined by Next only when configured, i.e. demo mode). Returns undefined when not set, so
 * the UI falls back to pre-filling the email and letting the user type the password. No demo
 * password is ever hard-coded in source (CLAUDE.md § Cấm lộ credentials).
 */
export function demoPasswordFor(roleCode: RoleCode): string | undefined {
  switch (roleCode) {
    case "ROLE-01":
      return process.env.NEXT_PUBLIC_DEMO_PASSWORD_CEO || undefined;
    case "ROLE-02":
      return process.env.NEXT_PUBLIC_DEMO_PASSWORD_CFO || undefined;
    case "ROLE-03":
      return process.env.NEXT_PUBLIC_DEMO_PASSWORD_SALES || undefined;
    case "ROLE-04":
      return process.env.NEXT_PUBLIC_DEMO_PASSWORD_HR || undefined;
    case "ROLE-05":
      return process.env.NEXT_PUBLIC_DEMO_PASSWORD_REVIEWER || undefined;
    default:
      return undefined;
  }
}
