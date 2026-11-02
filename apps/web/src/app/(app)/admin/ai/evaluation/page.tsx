import { EvaluationView } from "@/features/admin/ai/evaluation/EvaluationView";

/** SCR-64 `/admin/ai/evaluation` (M3.4) — `ai:admin`, ADM/CEO (guard `/admin/ai` prefix in middleware). */
export default function Page() {
  return <EvaluationView />;
}
