import { Suspense } from "react";
import { GoalsShell, goalCaps, goalsUser } from "@/features/goals/GoalsShell";
import { ObjectiveDetailView } from "@/features/goals/ObjectiveDetailView";

/** SCR-59 `/goals/objectives/[id]` (T-627F, 06 §3.4) — `?kr=` opens the KR check-in history. */
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await goalsUser();
  return (
    <GoalsShell active="tree" user={user}>
      <Suspense>
        <ObjectiveDetailView id={id} caps={goalCaps(user)} />
      </Suspense>
    </GoalsShell>
  );
}
