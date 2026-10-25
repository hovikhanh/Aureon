"use client";
import * as React from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { AdminHeader } from "@/features/admin/common";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CostTab } from "./CostTab";
import { ModelCallsTab } from "./ModelCallsTab";
import { ToolCallsTab } from "./ToolCallsTab";
import { defaultRange, rangeQuery, type LogFilter } from "./log-logic";

const TABS = ["tool", "model", "cost"] as const;
type Tab = (typeof TABS)[number];

/**
 * SCR-65 `/admin/ai/logs` (06 §3.4, T-647F): Tool call (EP-AI-22) · Model call (EP-AI-23) · Chi phí (EP-AI-15).
 * Period filter (default 7 days) + `request_id` shared by the two log tabs; deep link `?request_id=` / `?tab=`.
 */
export function AiLogsView() {
  const t = useTranslations("aiLogs");
  const [tab, setTab] = React.useState<Tab>("tool");
  const [filter, setFilter] = React.useState<LogFilter>(() => ({ ...defaultRange(new Date()), requestId: "" }));
  React.useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    const tq = q.get("tab");
    if (tq && (TABS as readonly string[]).includes(tq)) setTab(tq as Tab);
    const rid = q.get("request_id");
    if (rid) setFilter((f) => ({ ...f, requestId: rid }));
  }, []);
  const query = rangeQuery(filter);
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4" data-testid="ai-logs" data-scr="SCR-65">
      <AdminHeader title={t("title")} hint={t("subtitle")}>
        <Link href="/admin/ai" className="text-sm text-primary hover:underline">{t("back")}</Link>
      </AdminHeader>
      <div role="tablist" aria-label={t("title")} className="flex gap-1 border-b">
        {TABS.map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} aria-controls={`logs-panel-${k}`} onClick={() => setTab(k)} data-testid={`logs-tab-${k}`}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === k ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {t(`tabs.${k}`)}
          </button>
        ))}
      </div>
      {tab !== "cost" && (
        <div className="flex flex-wrap items-end gap-3" data-testid="logs-filters">
          <div className="flex flex-col gap-1"><Label htmlFor="lg-from">{t("from")}</Label>
            <Input id="lg-from" type="date" value={filter.from} max={filter.to} onChange={(e) => setFilter({ ...filter, from: e.target.value })} data-testid="logs-from" /></div>
          <div className="flex flex-col gap-1"><Label htmlFor="lg-to">{t("to")}</Label>
            <Input id="lg-to" type="date" value={filter.to} min={filter.from} onChange={(e) => setFilter({ ...filter, to: e.target.value })} data-testid="logs-to" /></div>
          <div className="flex min-w-72 flex-col gap-1"><Label htmlFor="lg-rid">{t("requestId")}</Label>
            <Input id="lg-rid" value={filter.requestId} placeholder="req-…" onChange={(e) => setFilter({ ...filter, requestId: e.target.value.trim() })} data-testid="logs-request-id" /></div>
          {filter.requestId && (
            <Link href={`/admin/audit?request_id=${encodeURIComponent(filter.requestId)}`} className="pb-2 text-sm text-primary hover:underline" data-testid="logs-audit-link">{t("auditLink")}</Link>
          )}
        </div>
      )}
      <div role="tabpanel" id={`logs-panel-${tab}`}>
        {tab === "tool" && <ToolCallsTab query={query} onRequestId={(rid) => setFilter({ ...filter, requestId: rid })} />}
        {tab === "model" && <ModelCallsTab query={query} onRequestId={(rid) => setFilter({ ...filter, requestId: rid })} />}
        {tab === "cost" && <CostTab />}
      </div>
    </div>
  );
}
