import type { RoleCode } from "@aureon/shared-types";

export interface DemoAccountInfo {
  roleCode: RoleCode;
  email: string;
  userNameKey: string;
  roleNameKey: string;
  homeRoute: string;
}

export const DEMO_ACCOUNTS: DemoAccountInfo[] = [
  {
    roleCode: "ROLE-01",
    email: "ceo@abc.demo",
    userNameKey: "auth.demoUserNames.accCeo",
    roleNameKey: "shell.roles.CEO",
    homeRoute: "/dashboard",
  },
  {
    roleCode: "ROLE-02",
    email: "cfo@abc.demo",
    userNameKey: "auth.demoUserNames.accCfo",
    roleNameKey: "shell.roles.CFO",
    homeRoute: "/dashboard",
  },
  {
    roleCode: "ROLE-03",
    email: "sales@abc.demo",
    userNameKey: "auth.demoUserNames.accSales",
    roleNameKey: "shell.roles.SALES_DIRECTOR",
    homeRoute: "/dashboard",
  },
  {
    roleCode: "ROLE-04",
    email: "hr@abc.demo",
    userNameKey: "auth.demoUserNames.accHr",
    roleNameKey: "shell.roles.HR_MANAGER",
    homeRoute: "/dashboard",
  },
  {
    roleCode: "ROLE-05",
    email: "reviewer@abc.demo",
    userNameKey: "auth.demoUserNames.accReviewer",
    roleNameKey: "shell.roles.REVIEWER",
    homeRoute: "/inbox",
  },
];
