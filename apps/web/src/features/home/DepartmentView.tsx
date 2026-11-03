"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/card";
import { MetricTile } from "./MetricTile";
import type { DepartmentDashboard } from "./types";

/** SCR-40 cấp Department (DIR/MGR) — EP-RPT-02: KPI khối (OPS/STR/PPL) + OKR + tải + việc. */
export function DepartmentView() {
  const t = useTranslations("home");
  const q = useQuery({
    queryKey: ["reporting", "department"],
    queryFn: ({ signal }) => api.get<DepartmentDashboard>("/reporting/dashboards/department", undefined, signal),
    staleTime: 60_000,
  });
  if (q.isLoading) return <p className="text-sm text-muted-foreground">{t("loading")}</p>;
  if (q.isError || !q.data) return <p className="text-sm text-danger">{t("error")}</p>;
  const d = q.data;
  return (
    <div className="flex flex-col gap-6" data-testid="dept-view">
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="dept-kpis">
        {d.kpis.map((m) => <MetricTile key={m.metric_code} m={m} />)}
      </section>
      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="p-4" data-testid="dept-okrs">{t("okrsAtRisk", { count: d.okrs.at_risk_count, total: d.okrs.total })}</Card>
        <Link href={d.workload.heatmap_ref} className="block">
          <Card className="p-4" data-testid="dept-workload">{t("overloaded", { count: d.workload.overloaded_count })}</Card>
        </Link>
        {/* same `project_rules.is_late` as the projects list filter → the count and the list agree */}
        <Link href="/work/projects?late=1" className="block" data-testid="dept-late-link">
          <Card className="p-4 transition-colors hover:border-primary hover:bg-muted" data-testid="dept-late">{t("lateProjects", { count: d.late_projects })}</Card>
        </Link>
      </section>
    </div>
  );
}
