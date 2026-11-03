"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/card";
import type { EmployeeDashboard } from "./types";

/** SCR-40 cấp Employee — EP-RPT-03: việc của tôi + mục tiêu + check-in chờ + tải tuần. */
export function EmployeeView() {
  const t = useTranslations("home");
  const q = useQuery({
    queryKey: ["reporting", "employee"],
    queryFn: ({ signal }) => api.get<EmployeeDashboard>("/reporting/dashboards/employee", undefined, signal),
    staleTime: 60_000,
  });
  if (q.isLoading) return <p className="text-sm text-muted-foreground">{t("loading")}</p>;
  if (q.isError || !q.data) return <p className="text-sm text-danger">{t("error")}</p>;
  const d = q.data;
  return (
    <div className="flex flex-col gap-6" data-testid="emp-view">
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Link href="/work" className="block">
          <Card className="p-4" data-testid="emp-tasks">{t("myTasks", { overdue: d.my_tasks.overdue, today: d.my_tasks.today, week: d.my_tasks.this_week })}</Card>
        </Link>
        <Card className="p-4" data-testid="emp-goals">{t("myGoals", { kpis: d.my_goals.kpis, krs: d.my_goals.krs })}</Card>
        <Card className="p-4" data-testid="emp-workload">{t("workloadWeek", { pct: d.workload_week_pct ?? 0 })}</Card>
      </section>
      {d.pending_checkins.length > 0 && (
        <Card className="p-4" data-testid="emp-checkins">
          <h2 className="text-sm font-medium">{t("pendingCheckins", { count: d.pending_checkins.length })}</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {d.pending_checkins.map((c) => <li key={`${c.target_type}:${c.target_id}`}>{c.label}</li>)}
          </ul>
        </Card>
      )}
    </div>
  );
}
