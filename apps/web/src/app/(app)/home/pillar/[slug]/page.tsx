import { notFound } from "next/navigation";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { PillarDetailView } from "@/features/dashboard/PillarDetailView";
import { FinanceDrillView } from "@/features/finance/FinanceDrillView";
import { pillarBySlug, visiblePillars } from "@/features/dashboard/pillars";
import { PillarTabs } from "@/features/dashboard/PillarTabs";
import ForbiddenPage from "@/app/403/page";

export default async function PillarPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const def = pillarBySlug(slug);
  if (!def) notFound();
  const session = await getServerSession(authOptions);
  const perms = session?.user.permissions ?? [];
  const visible = visiblePillars(session?.user.role ?? "", perms, session?.user.scopePillars ?? []);
  if (!visible.some((p) => p.code === def.code)) return <ForbiddenPage />;
  // SCR-03 is the only place the full five-pillar layout lives (R-DEC-16).
  const tabs = visible.map(({ code, slug: s }) => ({ code, slug: s }));
  return (
    <>
      <PillarTabs pillars={tabs} active={def.code} />
      {def.code === "F" ? <FinanceDrillView /> : <PillarDetailView def={def} permissions={perms} />}
    </>
  );
}
