"use client";

import { useMemo } from "react";
import { AlertTriangle, Bot, CheckCircle2, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/features/auth/auth-context";
import { MetricCard } from "@/components/metric/MetricCard";
import { AlertCard } from "@/components/alert/AlertCard";
import { AIStateBadge } from "@/components/ai/AIStateBadge";
import { getRoleDashboardData } from "./demo-fixtures";

export function DashboardView() {
  const t = useTranslations();
  const { user, role } = useAuth();

  const data = useMemo(() => getRoleDashboardData(role), [role]);

  const salutation = user?.salutation ?? "anh";
  const fullName = user?.full_name ?? "";

  return (
    <div className="space-y-8 pb-12">
      {/* 1. Header & Welcome Greeting */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-h1 font-bold text-foreground">
            {t("dashboard.greeting", { salutation, name: fullName })}
          </h1>
          <p className="text-body-sm text-muted-foreground">
            {t("dashboard.roleBadge", { role })}
          </p>
        </div>
      </div>

      {/* 2. AI Executive Summary (L1 read-only, DEC-072 Đề xuất A, SCR-01 CEO only) */}
      {data.hasAISummary && (
        <section
          aria-label={t("dashboard.ceoSummaryTitle")}
          className="relative overflow-hidden rounded-xl border border-ai/30 bg-ai/5 p-5 shadow-xs"
        >
          <div className="flex items-start gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-ai/15 text-ai">
              <Bot className="h-6 w-6" aria-hidden="true" />
            </div>
            <div className="space-y-1.5 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-foreground text-body">
                  {t("dashboard.ceoSummaryTitle")}
                </span>
                <AIStateBadge level="L1" />
              </div>
              <p className="text-body text-foreground/90 leading-relaxed">
                {t("dashboard.ceoSummaryContent")}
              </p>
            </div>
          </div>
        </section>
      )}

      {/* 3. Action Needed ("Cần anh/chị quyết" - 06 §4.1) */}
      <section aria-labelledby="action-needed-heading" className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" aria-hidden="true" />
            <h2 id="action-needed-heading" className="text-h2 font-bold text-foreground">
              {t("dashboard.actionNeededTitle")}
            </h2>
            <span className="ml-1 inline-flex items-center rounded-full bg-critical/10 px-2.5 py-0.5 text-caption font-bold text-critical">
              {data.alerts.length}
            </span>
          </div>
          <p className="text-caption text-muted-foreground hidden sm:block">
            {t("dashboard.actionNeededSubtitle", { count: data.alerts.length })}
          </p>
        </div>

        {data.alerts.length === 0 ? (
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card p-4 text-body-sm text-muted-foreground">
            <CheckCircle2 className="h-5 w-5 text-success" aria-hidden="true" />
            <span>{t("dashboard.allPillarsGood")}</span>
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data.alerts.map((alert) => (
              <AlertCard key={alert.alertCode} {...alert} />
            ))}
          </div>
        )}
      </section>

      {/* 4. Full Pillars Grid (06 §4.1..4.4) */}
      <div className="space-y-8">
        {data.pillars.map((group) => (
          <section
            key={group.pillar}
            aria-labelledby={`pillar-${group.pillar}-heading`}
            className="space-y-4"
          >
            <div className="border-b border-border pb-2">
              <h2
                id={`pillar-${group.pillar}-heading`}
                className="text-h2 font-bold text-foreground"
              >
                {t(group.nameKey)}
              </h2>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {group.metrics.map((metric) => (
                <MetricCard key={metric.metricCode} {...metric} />
              ))}
            </div>
          </section>
        ))}
      </div>

      {/* 5. Aggregate Pillars (Out of scope, CFO / Sales / HR) */}
      {data.aggPillars.length > 0 && (
        <section aria-labelledby="agg-pillars-heading" className="space-y-4 pt-4 border-t border-border">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            <h2 id="agg-pillars-heading" className="text-h3 font-semibold text-foreground">
              {t("dashboard.aggPillarsTitle")}
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.aggPillars.flatMap((group) =>
              group.metrics.map((metric) => (
                <MetricCard key={metric.metricCode} {...metric} />
              )),
            )}
          </div>
        </section>
      )}
    </div>
  );
}
