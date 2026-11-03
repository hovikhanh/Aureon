import { getServerSession } from "next-auth";
import { AlertsPageView } from "@/features/dashboard/AlertsPageView";
import { authOptions } from "@/lib/auth";

/**
 * `/home/alerts` — open alerts list (EP-15, scope by the API), reached from the "Rủi ro mở" card of
 * SCR-40; each alert opens `/home/metrics/<code>`. v2.1 `/dashboard/alerts` bookmarks 308 here.
 */
export default async function Page() {
  const session = await getServerSession(authOptions);
  return <AlertsPageView canWrite={(session?.user.permissions ?? []).includes("dashboard:write")} />;
}
