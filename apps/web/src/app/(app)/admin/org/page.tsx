import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { OrgView } from "@/features/admin/org/OrgView";

/** SCR-51 `/admin/org` (T-617F) — edit needs `hr:admin` (ADM, CEO, DIR khối O; guard in middleware). */
export default async function Page() {
  const session = await getServerSession(authOptions);
  return <OrgView canEdit={session?.user.permissions.includes("hr:admin") ?? false} />;
}
