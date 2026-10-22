/** 5 demo accounts (08 §2, DEC-136). Emails only — passwords stay server-side. */
export const DEMO_ACCOUNTS = [
  { email: "ceo@abc.demo", role: "CEO" },
  { email: "cfo@abc.demo", role: "CFO" },
  { email: "sales@abc.demo", role: "VP_SALES" },
  { email: "hr@abc.demo", role: "HR_MANAGER" },
  { email: "reviewer@abc.demo", role: "REVIEWER" },
] as const;
