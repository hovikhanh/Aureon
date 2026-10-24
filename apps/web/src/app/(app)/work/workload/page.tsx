import { WorkShell, workUser } from "@/features/work/WorkShell";
import { WorkloadView } from "@/features/work/WorkloadView";
import { canAccess } from "@/lib/permissions";

/** SCR-57 `/work/workload` (T-625F, EP-TASK-18; `execution:query` — guard in middleware). MGR is pinned to the own department by the API. */
export default async function Page() {
  const user = await workUser();
  const canReadOrg = user.permissions.includes("hr:read");
  const metricHref = canAccess("/home/pillar/operations", user.role, user.permissions) ? "/home/pillar/operations" : null;
  return (
    <WorkShell active="workload" user={user}>
      <WorkloadView canReadOrg={canReadOrg} pickDepartment={user.role !== "MGR"} metricHref={metricHref} />
    </WorkShell>
  );
}
