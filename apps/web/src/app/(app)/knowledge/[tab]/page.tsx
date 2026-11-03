import { notFound } from "next/navigation";
import { KnowledgeView } from "@/features/knowledge/KnowledgeView";
import { isKnowledgeTab } from "@/features/knowledge/tabs";

/**
 * SCR-49 sub-routes `/knowledge/decisions` · `/knowledge/documents` · `/knowledge/reports`
 * (R-DEC-137): deep-linkable tabs — e.g. the Decision Log 30/60/90 review reminder links to
 * `/knowledge/decisions`. Any other segment is a real 404.
 */
export default async function Page({ params }: { params: Promise<{ tab: string }> }) {
  const { tab } = await params;
  if (!isKnowledgeTab(tab)) notFound();
  return <KnowledgeView initialTab={tab} />;
}
