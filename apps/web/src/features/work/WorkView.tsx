"use client";
/** SCR-42 `/work` client part: "Task của tôi" or kanban (`?view=board`, not EMP) + detail panel `?task=<id>`. */
import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BoardView } from "./BoardView";
import { MyTasksView } from "./MyTasksView";
import { TaskDetail, type DetailCaps } from "./TaskDetail";

export function useTaskPanel() {
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const go = React.useCallback((id: string | null) => {
    const next = new URLSearchParams(sp.toString());
    if (id) next.set("task", id);
    else next.delete("task");
    const qs = next.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [sp, router, pathname]);
  return { id: sp.get("task"), open: go, close: React.useCallback(() => go(null), [go]) };
}

export function WorkView({ board, pinned, caps }: { board: boolean; pinned: boolean; caps: DetailCaps }) {
  const panel = useTaskPanel();
  return (
    <>
      {board ? <BoardView pinned={pinned} canReadOrg={caps.canReadOrg} onOpen={panel.open} /> : <MyTasksView onOpen={panel.open} />}
      {panel.id && <TaskDetail id={panel.id} caps={caps} onClose={panel.close} onOpen={panel.open} />}
    </>
  );
}
