import { Suspense } from "react";
import { WorkShell, detailCaps, workUser } from "@/features/work/WorkShell";
import { ProjectDetailView } from "@/features/work/ProjectDetailView";

/** SCR-56 `/work/projects/[id]` (T-625F, 06 §3.4) — milestones editable for MGR+ (scope enforced by the API). */
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await workUser();
  const canEdit = user.role !== "EMP" && user.permissions.includes("execution:write");
  return (
    <WorkShell active="projects" user={user}>
      <Suspense>
        <ProjectDetailView id={id} canEdit={canEdit} caps={detailCaps(user)} />
      </Suspense>
    </WorkShell>
  );
}
