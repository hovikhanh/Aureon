import { ImportWizard } from "@/features/capture/ImportWizard";

/** SCR-62 `/data/imports/[batchId]` — C5 table import wizard (T-636F). */
export default async function Page({ params }: { params: Promise<{ batchId: string }> }) {
  const { batchId } = await params;
  return <ImportWizard batchId={batchId} />;
}
