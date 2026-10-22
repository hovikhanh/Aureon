import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { DashboardView } from "@/features/dashboard/DashboardView";

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  return <DashboardView role={session?.user.role ?? ""} permissions={session?.user.permissions ?? []} />;
}
