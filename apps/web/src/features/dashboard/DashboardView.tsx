"use client";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api-client";
import { AlertsList, unitsOf } from "./AlertsList";
import { PillarCard } from "./PillarCard";
import { PeriodPicker } from "./PeriodPicker";
import { usePeriod } from "./period";
import { visiblePillars } from "./pillars";
import type { MetricValue } from "./types";

export function DashboardView({ role, permissions, scopePillars = [] }: { role: string; permissions: string[]; scopePillars?: string[] }) {
  const t = useTranslations("dashboard");
  const { period } = usePeriod();
  const pillars = visiblePillars(role, permissions, scopePillars);
  // EP-11 only for the metric unit map used to format alert values.
  const metrics = useQuery({
    queryKey: ["metrics", "all"],
    queryFn: ({ signal }) => api.get<MetricValue[]>("/dashboard/metrics", undefined, signal),
    staleTime: 300_000,
  });
  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <PeriodPicker />
      </div>
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5" data-testid="pillar-grid">
        {pillars.map((p) => (
          <PillarCard key={p.code} def={p} period={period} permissions={permissions} />
        ))}
      </section>
      <AlertsList units={unitsOf(metrics.data ?? [])} canWrite={permissions.includes("dashboard:write")} />
    </div>
  );
}
