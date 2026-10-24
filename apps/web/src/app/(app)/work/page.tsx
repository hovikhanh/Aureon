import { Suspense } from "react";
import { WorkShell, detailCaps, workUser } from "@/features/work/WorkShell";
import { WorkView } from "@/features/work/WorkView";
import { visibleWorkTabs } from "@/lib/permissions";

/** SCR-42 `/work` (T-625F, 06 §3.4): "Task của tôi" · kanban `?view=board` (R-DEC-48, hidden for EMP). */
export default async function Page({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const sp = await searchParams;
  const user = await workUser();
  const canBoard = visibleWorkTabs(user.role, user.permissions).some((t) => t.key === "board");
  const board = canBoard && sp.view === "board";
  const caps = detailCaps(user);
  return (
    <WorkShell active={board ? "board" : "mine"} user={user}>
      <Suspense>
        <WorkView board={board} pinned={user.role === "MGR"} caps={caps} />
      </Suspense>
    </WorkShell>
  );
}
