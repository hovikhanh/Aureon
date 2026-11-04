import { ClientDetailView } from "@/features/crm/ClientDetailView";

/** `/business/sales/clients/[id]` — Account 360 (BRD §2.3, R-DEC-175). */
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ClientDetailView id={id} />;
}
