import { getServerSession } from "next-auth";
import { KnowledgeView } from "@/features/knowledge/KnowledgeView";
import { visibleKnowledgeTabs } from "@/features/knowledge/tabs";
import { authOptions } from "@/lib/auth";

/** SCR-49 `/knowledge` (M3.3, 03 §3.5–§3.6) — Decision Log · Documents · Reports, the tabs the role may open. */
export default async function Page() {
  const session = await getServerSession(authOptions);
  return <KnowledgeView tabs={visibleKnowledgeTabs(session?.user.permissions ?? [])} />;
}
