import { ClientDetailView } from "@/features/crm/ClientDetailView";
import { recordCaps } from "@/features/records/records-caps";

/** `/business/sales/clients/[id]` — Account 360 (BRD §2.3, R-DEC-175) + contacts / activities (R-DEC-176). */
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ClientDetailView id={id} caps={await recordCaps("sales")} />;
}
