import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { ComingSoon } from "@/components/shell/ComingSoon";
import { HomeView } from "@/features/home/HomeView";

/**
 * SCR-40 `/home` — Trang chủ 3 cấp theo role (06 §3.4, R-DEC-84/85). CEO/DIR/MGR/EMP thấy
 * dashboard Reporting v3 (EP-RPT-01..03); Reviewer → hàng chờ `/data`; Admin → `/admin`.
 */
export default async function HomePage() {
  const session = await getServerSession(authOptions);
  const role = session?.user.role ?? "";
  const perms = session?.user.permissions ?? [];
  if (role === "REV") redirect("/data");
  if (role === "ADM") redirect("/admin");
  // Executive (dashboard:read) hoặc Department/Employee (execution:read) — R-DEC-84/85.
  if (perms.includes("dashboard:read") || perms.includes("execution:read")) {
    return <HomeView role={role} />;
  }
  return <ComingSoon item="home" scr="SCR-40" phase="M2.1" />;
}
