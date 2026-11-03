"use client";
/**
 * SCR-49 `/knowledge` (M3.3, 03 §3.5–§3.6) — two tabs: Decision Log + Reports. Tab state is local
 * (like HomeView's level tabs); the page stays a server component that renders this client view.
 */
import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { DecisionsPanel } from "./DecisionsPanel";
import { DocumentsPanel } from "./DocumentsPanel";
import { ReportsPanel } from "./ReportsPanel";
import type { KnowledgeTab } from "./tabs";

type Tab = KnowledgeTab;

/**
 * `initialTab` comes from the sub-route (`/knowledge/decisions|documents|reports`, R-DEC-137); `tabs`
 * = the tabs the role may open (`visibleKnowledgeTabs`, computed on the server page).
 */
export function KnowledgeView({ tabs, initialTab }: { tabs: readonly Tab[]; initialTab?: Tab }) {
  const t = useTranslations("knowledge");
  const [tab, setTab] = useState<Tab | undefined>(initialTab ?? tabs[0]);
  if (!tab) {
    return (
      <div className="mx-auto max-w-3xl rounded-lg border bg-card p-6" data-testid="knowledge-view">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="mt-2 text-sm text-muted-foreground" data-testid="knowledge-no-tabs">{t("noTabs")}</p>
      </div>
    );
  }
  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-6" data-testid="knowledge-view">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <div className="flex gap-1 rounded-md border p-1" role="tablist" data-testid="knowledge-tabs">
          {tabs.map((k) => (
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
      {tab === "documents" && <DocumentsPanel />}
      {tab === "reports" && <ReportsPanel />}
    </div>
  );
}
