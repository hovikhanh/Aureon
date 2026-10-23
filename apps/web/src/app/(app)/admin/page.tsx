import { ComingSoon } from "@/components/shell/ComingSoon";

/** SCR-50 `/admin` — frame only; full screen in M1.2 (06 §3.4). */
export default function Page() {
  return <ComingSoon item="admin" scr="SCR-50" phase="M1.2" links={[{ href: "/admin/audit", labelKey: "audit" }]} />;
}
