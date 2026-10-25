import { Suspense } from "react";
import { GoalsShell, goalCaps, goalsUser } from "@/features/goals/GoalsShell";
import { GoalTreeView } from "@/features/goals/GoalTreeView";

/** SCR-41 `/goals` (T-626F, 06 §3.4) — strategy → SO → KPI / OKR / Initiative tree in the caller's scope (R-DEC-57). */
export default async function Page() {
  const user = await goalsUser();
  return (
    <GoalsShell active="tree" user={user}>
      <Suspense>
        <GoalTreeView caps={goalCaps(user)} />
      </Suspense>
    </GoalsShell>
  );
}
