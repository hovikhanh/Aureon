import { ComingSoon } from "@/components/shell/ComingSoon";

/** SCR-45 `/data` — frame only; full screen in M1.5 (06 §3.4). */
export default function Page() {
  return <ComingSoon item="data" scr="SCR-45" phase="M1.5" links={[{ href: "/data/review", labelKey: "review" }]} />;
}
