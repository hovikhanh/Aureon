import { AiLogsView } from "@/features/admin/ai/logs/AiLogsView";

/** SCR-65 `/admin/ai/logs` (T-647F) — `ai:admin`, ADM/CEO (guard `/admin/ai` prefix in middleware). */
export default function Page() {
  return <AiLogsView />;
}
