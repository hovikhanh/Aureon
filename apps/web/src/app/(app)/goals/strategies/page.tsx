import { GoalsShell, goalCaps, goalsUser } from "@/features/goals/GoalsShell";
import { StrategiesView } from "@/features/goals/StrategiesView";

/** `/goals/strategies` (F12): Strategy + Strategic Objective list and create (EP-STR-02/03/07/08). */
export default async function Page() {
  const user = await goalsUser();
  return (
    <GoalsShell active={null} user={user}>
      <StrategiesView caps={goalCaps(user)} />
    </GoalsShell>
  );
}
