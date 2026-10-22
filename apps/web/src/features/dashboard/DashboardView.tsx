"use client";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { api } from "@/lib/api-client";
import { formatPeriod, type AppLocale } from "@/lib/format";
import { AlertsList, unitsOf } from "./AlertsList";
import { PillarCard } from "./PillarCard";
import { DEFAULT_PERIOD, visiblePillars } from "./pillars";
import type { MetricValue } from "./types";

export function DashboardView({ role, permissions }: { role: string; permissions: string[] }) {
  const t = useTranslations("dashboard");
  const locale = useLocale() as AppLocale;
  const pillars = visiblePillars(role, permissions);
  // EP-11 only for the metric unit map used to format alert values.
  const metrics = useQuery({
    queryKey: ["metrics", "all"],
    queryFn: ({ signal }) => api.get<MetricValue[]>("/dashboard/metrics", undefined, signal),
    staleTime: 300_000,
  });
  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-sm text-muted-foreground">{t("subtitle", { period: formatPeriod(DEFAULT_PERIOD, locale) })}</p>
      </div>
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5" data-testid="pillar-grid">
        {pillars.map((p) => (
          <PillarCard key={p.code} def={p} period={DEFAULT_PERIOD} permissions={permissions} />
        ))}
      </section>
      <AlertsList units={unitsOf(metrics.data ?? [])} canWrite={permissions.includes("dashboard:write")} />
    </div>
  );
}
