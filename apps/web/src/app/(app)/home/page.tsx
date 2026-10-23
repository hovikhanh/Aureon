import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { ComingSoon } from "@/components/shell/ComingSoon";
import { DashboardView } from "@/features/dashboard/DashboardView";

/**
 * SCR-40 `/home` — Trang chủ theo role (06 §3.4). M1.1: CEO/DIR get the v2.1 executive
 * dashboard as the interim view; the role-specific home of every role arrives in M2.1.
 */
export default async function HomePage() {
  const session = await getServerSession(authOptions);
  const role = session?.user.role ?? "";
  const perms = session?.user.permissions ?? [];
  if ((role === "CEO" || role === "DIR") && perms.includes("dashboard:read")) {
    return <DashboardView role={role} permissions={perms} scopePillars={session?.user.scopePillars ?? []} />;
  }
  return <ComingSoon item="home" scr="SCR-40" phase="M2.1" />;
}
