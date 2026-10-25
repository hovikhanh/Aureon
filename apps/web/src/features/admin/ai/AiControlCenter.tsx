"use client";
import * as React from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { AdminHeader } from "@/features/admin/common";
import { Button } from "@/components/ui/button";
import { OverviewTab } from "./OverviewTab";
import { AgentsTab } from "./AgentsTab";
import { AutonomyTab } from "./AutonomyTab";
import { ToolRegistryTab } from "./ToolRegistryTab";
import type { Viewer } from "./types";

const TABS = ["overview", "agents", "autonomy", "tools"] as const;
type Tab = (typeof TABS)[number];

/**
 * SCR-64 `/admin/ai` AI Control Center (06 §3.4, R-DEC-79): Tổng quan (kill switch, chi phí, hàng chờ),
 * Agent (EP-AI-16/17), Autonomy L0–L2 (EP-AI-18..21), Tool Registry 13 metadata (EP-AI-14). Tab in `?tab=`.
 */
export function AiControlCenter({ viewer }: { viewer: Viewer }) {
  const t = useTranslations("aiAdmin");
  const [tab, setTab] = React.useState<Tab>("overview");
  React.useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("tab");
    if (q && (TABS as readonly string[]).includes(q)) setTab(q as Tab);
  }, []);
  const select = (k: Tab) => {
    setTab(k);
    window.history.replaceState(null, "", `?tab=${k}`);
  };
  const onKey = (e: React.KeyboardEvent, i: number) => {
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!d) return;
    const next = TABS[(i + d + TABS.length) % TABS.length]!;
    select(next);
    document.getElementById(`ai-tab-${next}`)?.focus();
  };
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4" data-testid="ai-admin" data-scr="SCR-64">
      <AdminHeader title={t("title")} hint={t("subtitle")}>
        <Button asChild variant="outline" size="sm"><Link href="/admin/ai/logs" data-testid="ai-open-logs">{t("openLogs")}</Link></Button>
      </AdminHeader>
      <div role="tablist" aria-label={t("title")} className="flex gap-1 border-b">
        {TABS.map((k, i) => (
          <button key={k} id={`ai-tab-${k}`} type="button" role="tab" aria-selected={tab === k} aria-controls={`ai-panel-${k}`} tabIndex={tab === k ? 0 : -1}
            onClick={() => select(k)} onKeyDown={(e) => onKey(e, i)} data-testid={`ai-tab-${k}`}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === k ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {t(`tabs.${k}`)}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`ai-panel-${tab}`} aria-labelledby={`ai-tab-${tab}`}>
        {tab === "overview" && <OverviewTab viewer={viewer} onOpen={select} />}
        {tab === "agents" && <AgentsTab />}
        {tab === "autonomy" && <AutonomyTab />}
        {tab === "tools" && <ToolRegistryTab />}
      </div>
    </div>
  );
}
