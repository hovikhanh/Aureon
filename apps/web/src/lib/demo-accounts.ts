/**
 * 10 demo accounts (08 §2.1, DEC-136, seed `auth_seed.DEMO_USERS`). Emails only — the password
 * is resolved server-side from `DEMO_*_PASSWORD` (`server-env.demoPasswordFor`) and never
 * reaches the browser (CLAUDE §5.8, §6.4).
 * `role` is the v3 role_code (R-DEC-12); `pillar` is the DIR khối (R-DEC-12a) shown on the
 * quick-login button so two DIR accounts stay distinguishable.
 */
export interface DemoAccount {
  email: string;
  role: "CEO" | "DIR" | "MGR" | "EMP" | "REV" | "ADM";
  /** i18n key under `demoAccount.*`. */
  labelKey: string;
  /** F.O.C.U.S khối for DIR accounts (empty = full scope). */
  pillar?: "F" | "O" | "C" | "U";
}

export const DEMO_ACCOUNTS: readonly DemoAccount[] = [
  { email: "ceo@abc.demo", role: "CEO", labelKey: "ceo" },
  { email: "cfo@abc.demo", role: "DIR", labelKey: "cfo", pillar: "F" },
  { email: "sales@abc.demo", role: "DIR", labelKey: "vp_sales", pillar: "C" },
  { email: "hr@abc.demo", role: "DIR", labelKey: "hr_manager", pillar: "O" },
  { email: "cpo@abc.demo", role: "DIR", labelKey: "cpo", pillar: "U" },
  { email: "manager@abc.demo", role: "MGR", labelKey: "manager" },
  { email: "office@abc.demo", role: "MGR", labelKey: "office_manager" },
  { email: "employee@abc.demo", role: "EMP", labelKey: "employee" },
  { email: "reviewer@abc.demo", role: "REV", labelKey: "reviewer" },
  { email: "admin@abc.demo", role: "ADM", labelKey: "admin" },
] as const;

/** `data-testid` of a quick-login button (E2E + manual testing). */
export function demoTestId(email: string): string {
  return `demo-login-${email.split("@")[0]}`;
}
