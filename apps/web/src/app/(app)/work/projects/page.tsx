import { WorkShell, detailCaps, workUser } from "@/features/work/WorkShell";
import { ProjectsView } from "@/features/work/ProjectsView";

/** SCR-55 `/work/projects` (T-625F, 06 §3.4) — create for MGR+ (`execution:write`, not EMP). */
export default async function Page() {
  const user = await workUser();
  const canCreate = user.role !== "EMP" && user.permissions.includes("execution:write");
  return (
    <WorkShell active="projects" user={user}>
      <ProjectsView canCreate={canCreate} canReadOrg={detailCaps(user).canReadOrg} userId={user.id} />
    </WorkShell>
  );
}
