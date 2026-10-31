"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { AlertTriangle, Bot, ClipboardCheck } from "lucide-react";
import { api } from "@/lib/api-client";
import { Card } from "@/components/ui/card";
import { MetricTile } from "./MetricTile";
import type { ExecutiveDashboard } from "./types";

/** SCR-40 cấp Executive (CEO/DIR) — EP-RPT-01: 4 ô + SEI + quyết chờ + rủi ro + "AI đã làm". */
export function ExecutiveView() {
  const t = useTranslations("home");
  const q = useQuery({
    queryKey: ["reporting", "executive"],
    queryFn: ({ signal }) => api.get<ExecutiveDashboard>("/reporting/dashboards/executive", undefined, signal),
    staleTime: 60_000,
  });
  if (q.isLoading) return <p className="text-sm text-muted-foreground">{t("loading")}</p>;
  if (q.isError || !q.data) return <p className="text-sm text-danger">{t("error")}</p>;
  const d = q.data;
  return (
    <div className="flex flex-col gap-6" data-testid="exec-view">
      <p className="text-base text-muted-foreground" data-testid="summary-line">{d.summary_line}</p>
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4" data-testid="exec-tiles">
        {d.tiles.map((m) => <MetricTile key={m.metric_code} m={m} />)}
      </section>
      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {d.sei && (
          <Card className="p-4" data-testid="exec-sei">
            <h2 className="text-sm font-medium text-muted-foreground">{t("sei")}</h2>
            <MetricTile m={d.sei} />
          </Card>
        )}
        <Link href="/work/approvals" className="block">
          <Card className="flex items-center gap-3 p-4" data-testid="exec-decisions">
            <ClipboardCheck className="h-5 w-5 text-primary" aria-hidden />
            <span>{t("decisionsWaiting", { count: d.decisions_waiting.count })}</span>
          </Card>
        </Link>
        <Card className="flex items-center gap-3 p-4" data-testid="exec-risks">
          <AlertTriangle className="h-5 w-5 text-danger" aria-hidden />
          <span>{t("openRisks", { count: d.open_risks.count })}</span>
        </Card>
      </section>
      <Card className="p-4" data-testid="exec-ai-done">
        <h2 className="flex items-center gap-2 text-sm font-medium text-ai">
          <Bot className="h-4 w-4" aria-hidden />{t("aiDone", { count: d.ai_done.count })}
        </h2>
        <ul className="mt-2 space-y-1 text-sm">
          {d.ai_done.items.map((a) => <li key={a.id}>{a.action_name}</li>)}
        </ul>
      </Card>
    </div>
  );
}
