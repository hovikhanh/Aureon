import { GoalsShell, goalCaps, goalsUser } from "@/features/goals/GoalsShell";
import { KpiDetailView } from "@/features/goals/KpiDetailView";

/** SCR-58 `/goals/kpis/[id]` (T-627F, 06 §3.4) — out-of-scope KPI → 403 FORBIDDEN_SCOPE shown in place. */
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const user = await goalsUser();
  return (
    <GoalsShell active="tree" user={user}>
      <KpiDetailView id={id} caps={goalCaps(user)} />
    </GoalsShell>
  );
}
