"use client";
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatNumber, type AppLocale } from "@/lib/format";
import { AgentEditDialog } from "./AgentEditDialog";
import { agentName, levelKey } from "./logic";
import { useAgents, useTools } from "./use-ai-admin";
import type { Agent } from "./types";

/** SCR-64 Agent tab (06 §3.4): 6 P0 agents (EP-AI-16) + edit panel (EP-AI-17). */
export function AgentsTab() {
  const t = useTranslations("aiAdmin");
  const locale = useLocale() as AppLocale;
  const agents = useAgents();
  const tools = useTools();
  const [editing, setEditing] = React.useState<Agent | null>(null);
  if (agents.isLoading) return <p className="text-sm text-muted-foreground">{t("tools.loading")}</p>;
  if (agents.isError) return <p role="alert" className="text-sm text-danger">{t("agents.error")}</p>;
  return (
    <section className="overflow-x-auto rounded-lg border bg-card" data-testid="agents-tab">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
          <tr>
            {["name", "tools", "max", "effective", "budget", "spend", "status", ""].map((c) => <th key={c} className="px-3 py-2">{c ? t(`agents.col.${c}`) : ""}</th>)}
          </tr>
        </thead>
        <tbody>
          {(agents.data ?? []).map((a) => (
            <tr key={a.code} className="border-t align-top" data-testid="agent-row" data-agent={a.code}>
              <td className="px-3 py-2">
                <div className="font-medium">{agentName(a, a.code, locale)}</div>
                <div className="text-xs text-muted-foreground">{a.agent_ref} · {locale === "en" ? a.description_en : a.description_vi}</div>
              </td>
              <td className="px-3 py-2">{a.allowed_tools?.length ?? 0}</td>
              <td className="px-3 py-2">{a.max_autonomy_level} · {t(levelKey(a.max_autonomy_level))}</td>
              <td className="px-3 py-2" data-testid="agent-effective">{a.effective_max_level}</td>
              <td className="px-3 py-2">{a.monthly_budget_usd ? `$${formatNumber(Number(a.monthly_budget_usd), locale, 2)}` : t("agents.noBudget")}</td>
              <td className="px-3 py-2">{a.month_spend_usd != null ? `$${formatNumber(a.month_spend_usd, locale, 4)}` : "—"}</td>
              <td className="px-3 py-2">
                <div className="flex flex-wrap gap-1">
                  <Badge variant={a.is_enabled ? "success" : "outline"} data-testid="agent-enabled">{t(a.is_enabled ? "agents.enabled" : "agents.disabled")}</Badge>
                  {a.kill_switched && <Badge variant="warning" data-testid="agent-killed">{t("agents.killed")}</Badge>}
                </div>
              </td>
              <td className="px-3 py-2 text-right">
                <Button size="sm" variant="outline" onClick={() => setEditing(a)} data-testid="agent-edit">{t("agents.edit")}</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <AgentEditDialog agent={editing} tools={tools.data ?? []} onClose={() => setEditing(null)} />
    </section>
  );
}
