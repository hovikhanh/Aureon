import { ComingSoon } from "@/components/shell/ComingSoon";

/** SCR-46 `/business` — frame only; full screen in M2.2 (06 §3.4). */
export default function Page() {
  return <ComingSoon item="business" scr="SCR-46" phase="M2.2" links={[{ href: "/business/finance/invoices", labelKey: "invoices" }, { href: "/business/hr/employees", labelKey: "employees" }]} />;
}
