import { DealDetailView } from "@/features/crm/DealDetailView";
import { crmCaps } from "@/features/crm/crm-caps";

/** `/business/sales/deals/[id]` — opportunity detail (BRD §2.5, R-DEC-175). */
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const c = await crmCaps();
  return <DealDetailView id={id} canMove={c.canMove} userId={c.userId} />;
}
