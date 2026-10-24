import { Suspense } from "react";
import { WorkShell, detailCaps, workUser } from "@/features/work/WorkShell";
import { ApprovalsView } from "@/features/work/ApprovalsView";

/** SCR-43 `/work/approvals` (T-625F, EP-WF-01..03; `platform:approve` — guard in middleware, EMP → /403). */
export default async function ApprovalsPage() {
  const user = await workUser();
  return (
    <WorkShell active="approvals" user={user}>
      <Suspense>
        <ApprovalsView canReadOrg={detailCaps(user).canReadOrg} />
      </Suspense>
    </WorkShell>
  );
}
