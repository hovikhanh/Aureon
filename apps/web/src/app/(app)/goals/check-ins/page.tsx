import { GoalsShell, goalCaps, goalsUser } from "@/features/goals/GoalsShell";
import { CheckInsView } from "@/features/goals/CheckInsView";

/** SCR-60 `/goals/check-ins` (T-628F, 06 §3.4 F4) — EMP own cards; MGR/DIR/CEO + team feed. */
export default async function Page() {
  const user = await goalsUser();
  return (
    <GoalsShell active="checkins" user={user}>
      <CheckInsView caps={goalCaps(user)} />
    </GoalsShell>
  );
}
