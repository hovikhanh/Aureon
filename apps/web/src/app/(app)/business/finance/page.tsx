import { getServerSession } from "next-auth";
import { FinanceLiteView } from "@/features/finance/FinanceLiteView";
import { authOptions } from "@/lib/auth";
import { canReadHrDirectory } from "@/lib/permissions";

export default async function FinanceLitePage() {
  const u = (await getServerSession(authOptions))?.user;
  const canRead = canReadHrDirectory(u?.role ?? "", u?.permissions ?? [], u?.scopePillars ?? []);
  return <FinanceLiteView canReadDepartments={canRead} departmentId={u?.departmentId ?? null} />;
}
