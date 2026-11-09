import { DealDetailView } from "@/features/crm/DealDetailView";
import { crmCaps } from "@/features/crm/crm-caps";
import { recordCaps } from "@/features/records/records-caps";

/** `/business/sales/deals/[id]` — opportunity detail (BRD §2.5, R-DEC-175) + activities (R-DEC-176). */
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [c, caps] = await Promise.all([crmCaps(), recordCaps("sales")]);
  return <DealDetailView id={id} canMove={c.canMove} userId={c.userId} canReadUsers={c.canReadUsers} caps={caps} />;
}
