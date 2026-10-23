/**
 * 5 demo accounts (08 §2, DEC-136). Emails only — passwords stay server-side.
 * `role` is the v3 role_code (R-DEC-12): 5 C-level → ROLE-DIR, phân biệt bằng khối ở server.
 * `labelKey` is a distinct i18n label (`demoAccount.*`) so the login list stays readable.
 */
export const DEMO_ACCOUNTS = [
  { email: "ceo@abc.demo", role: "CEO", labelKey: "ceo" },
  { email: "cfo@abc.demo", role: "DIR", labelKey: "cfo" },
  { email: "sales@abc.demo", role: "DIR", labelKey: "vp_sales" },
  { email: "hr@abc.demo", role: "DIR", labelKey: "hr_manager" },
  { email: "reviewer@abc.demo", role: "REV", labelKey: "reviewer" },
] as const;
