import { SchemaForm } from "@/features/capture/SchemaForm";

/** SCR-61 `/data/new/[documentType]` — C1 manual entry (T-634F). */
export default async function Page({ params }: { params: Promise<{ documentType: string }> }) {
  const { documentType } = await params;
  return <SchemaForm documentType={documentType} />;
}
