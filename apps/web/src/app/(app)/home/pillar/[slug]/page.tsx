import { notFound } from "next/navigation";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { PillarDetailView } from "@/features/dashboard/PillarDetailView";
import { FinanceDrillView } from "@/features/finance/FinanceDrillView";
import { pillarBySlug, visiblePillars } from "@/features/dashboard/pillars";
import ForbiddenPage from "@/app/403/page";

export default async function PillarPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const def = pillarBySlug(slug);
  if (!def) notFound();
  const session = await getServerSession(authOptions);
  const perms = session?.user.permissions ?? [];
  if (!visiblePillars(session?.user.role ?? "", perms, session?.user.scopePillars ?? []).some((p) => p.code === def.code)) return <ForbiddenPage />;
  if (def.code === "F") return <FinanceDrillView />;
  return <PillarDetailView def={def} permissions={perms} />;
}
