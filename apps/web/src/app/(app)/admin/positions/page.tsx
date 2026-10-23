import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { PositionsView } from "@/features/admin/PositionsView";

/** SCR-52 `/admin/positions` (T-617F). */
export default async function Page() {
  const session = await getServerSession(authOptions);
  return <PositionsView canEdit={session?.user.permissions.includes("hr:admin") ?? false} />;
}
