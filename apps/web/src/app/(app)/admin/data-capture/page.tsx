import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { DataCaptureAdmin } from "@/features/capture/admin/DataCaptureAdmin";

/** SCR-63 `/admin/data-capture` (T-638F) — `idp:admin` (ADM; guard in middleware). */
export default async function Page() {
  const session = await getServerSession(authOptions);
  return <DataCaptureAdmin permissions={session?.user.permissions ?? []} />;
}
