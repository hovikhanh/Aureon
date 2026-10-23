import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { UsersView } from "@/features/admin/UsersView";

/** SCR-53 `/admin/users` (T-617F) — ADM edits; CEO reads only (06 §3.4). */
export default async function Page() {
  const session = await getServerSession(authOptions);
  const user = session?.user;
  return <UsersView canEdit={user?.role === "ADM" && user.permissions.includes("platform:admin")} selfId={user?.id ?? ""} actorRole={user?.role ?? ""} />;
}
