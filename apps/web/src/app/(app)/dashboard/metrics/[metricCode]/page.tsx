import { MetricDetailView } from "@/features/dashboard/MetricDetailView";

/**
 * SCR-09 — Metric Detail (drill-down click 1 of the ≤3-click lineage chain, 03 §4.1, 06 §4.6).
 * Reached contextually from a MetricCard / AlertCard number; not on the sidebar.
 */
export default async function MetricDetailPage({
  params,
}: {
  params: Promise<{ metricCode: string }>;
}) {
  const { metricCode } = await params;
  return <MetricDetailView metricCode={decodeURIComponent(metricCode)} />;
}
