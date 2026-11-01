"use client";
/**
 * SCR-49 `/knowledge` (M3.3, 03 §3.5–§3.6) — two tabs: Decision Log + Reports. Tab state is local
 * (like HomeView's level tabs); the page stays a server component that renders this client view.
 */
import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { DecisionsPanel } from "./DecisionsPanel";
import { ReportsPanel } from "./ReportsPanel";

type Tab = "decisions" | "reports";
const TABS: Tab[] = ["decisions", "reports"];

export function KnowledgeView() {
  const t = useTranslations("knowledge");
  const [tab, setTab] = useState<Tab>("decisions");
  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-6" data-testid="knowledge-view">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <div className="flex gap-1 rounded-md border p-1" role="tablist" data-testid="knowledge-tabs">
          {TABS.map((k) => (
            <Button
              key={k}
              size="sm"
              variant={k === tab ? "default" : "ghost"}
              role="tab"
              aria-selected={k === tab}
              data-testid={`knowledge-tab-${k}`}
              onClick={() => setTab(k)}
            >
              {t(`tab.${k}`)}
            </Button>
          ))}
        </div>
      </div>
      {tab === "decisions" && <DecisionsPanel />}
      {tab === "reports" && <ReportsPanel />}
    </div>
  );
}
