import { getServerSession } from "next-auth";
import { notFound, redirect } from "next/navigation";
import { KnowledgeView } from "@/features/knowledge/KnowledgeView";
import { isKnowledgeTab, visibleKnowledgeTabs } from "@/features/knowledge/tabs";
import { authOptions } from "@/lib/auth";

/**
 * SCR-49 sub-routes `/knowledge/decisions` · `/knowledge/documents` · `/knowledge/reports`
 * (R-DEC-137): deep-linkable tabs — e.g. the Decision Log 30/60/90 review reminder links to
 * `/knowledge/decisions`. Any other segment is a real 404; a tab the role may not open (REV →
 * decisions/reports) goes to the 403 page instead of a tab full of 403 errors (M6).
 */
export default async function Page({ params }: { params: Promise<{ tab: string }> }) {
  const { tab } = await params;
  if (!isKnowledgeTab(tab)) notFound();
  const session = await getServerSession(authOptions);
  const tabs = visibleKnowledgeTabs(session?.user.permissions ?? []);
  if (!tabs.includes(tab)) redirect("/403");
  return <KnowledgeView tabs={tabs} initialTab={tab} />;
}
