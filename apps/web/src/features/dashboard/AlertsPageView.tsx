"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api-client";
import { AlertsList, unitsOf } from "./AlertsList";
import type { MetricValue } from "./types";

/** `/home/alerts` — the open alerts behind the "Rủi ro mở" count of SCR-40 (EP-15 + EP-11 for units). */
export function AlertsPageView({ canWrite }: { canWrite: boolean }) {
  const t = useTranslations();
  const metrics = useQuery({
    queryKey: ["metrics", "all"],
    queryFn: ({ signal }) => api.get<MetricValue[]>("/dashboard/metrics", undefined, signal),
    staleTime: 300_000,
  });
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4" data-testid="alerts-page">
      <Link href="/home" className="flex items-center gap-1 text-sm text-primary hover:underline"><ArrowLeft className="h-4 w-4" aria-hidden />{t("nav.home")}</Link>
      <h1 className="text-2xl font-semibold">{t("dashboard.alertsPageTitle")}</h1>
      <AlertsList units={unitsOf(metrics.data ?? [])} canWrite={canWrite} />
    </div>
  );
}
