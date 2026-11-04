import { PipelineBoard } from "@/features/crm/PipelineBoard";
import { crmCaps } from "@/features/crm/crm-caps";

/** `/business/sales/pipeline` — opportunity Kanban (BRD §2.6, R-DEC-175). */
export default async function Page() {
  const c = await crmCaps();
  return <PipelineBoard canMove={c.canMove} userId={c.userId} />;
}
