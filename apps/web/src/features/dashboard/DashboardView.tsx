"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { LayoutGrid } from "lucide-react";
import { api } from "@/lib/api-client";
import { AlertsList, unitsOf } from "./AlertsList";
import { PillarCard } from "./PillarCard";
import { PeriodPicker } from "./PeriodPicker";
import { usePeriod } from "./period";
import { executivePillars, visiblePillars } from "./pillars";
import type { MetricValue } from "./types";

export function DashboardView({ role, permissions, scopePillars = [] }: { role: string; permissions: string[]; scopePillars?: string[] }) {
  const t = useTranslations("dashboard");
  const { period, withPeriod } = usePeriod();
  const pillars = executivePillars(role, permissions, scopePillars);
  // U/S are off the default view (R-DEC-16); the optional 5-pillar layout is on SCR-03.
  const hasFrozen = visiblePillars(role, permissions, scopePillars).length > pillars.length;
  const first = pillars[0];
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
        <div className="flex flex-wrap items-end gap-3">
          {hasFrozen && first && (
            <Link href={withPeriod(`/home/pillar/${first.slug}`)} className="flex items-center gap-1 text-sm text-primary hover:underline" data-testid="five-pillar-link">
              <LayoutGrid className="h-4 w-4" aria-hidden />{t("fivePillarLink")}
            </Link>
          )}
          <PeriodPicker />
        </div>
      </div>
      <section className="grid grid-cols-1 gap-4 md:grid-cols-3" data-testid="pillar-grid">
        {pillars.map((p) => (
          <PillarCard key={p.code} def={p} period={period} permissions={permissions} />
        ))}
      </section>
      <AlertsList units={unitsOf(metrics.data ?? [])} canWrite={permissions.includes("dashboard:write")} />
    </div>
  );
}
