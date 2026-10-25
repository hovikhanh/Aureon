"use client";
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { formatMoney, type AppLocale } from "@/lib/format";
import { ConfirmDialog } from "@/features/admin/common";
import { PolicyDialog } from "./PolicyDialog";
import { cappedDefault, levelKey, matrixTools } from "./logic";
import { deletePolicy, useInvalidateAi, usePolicies, useTools } from "./use-ai-admin";
import type { Policy } from "./types";

/** SCR-64 Autonomy tab (06 §3.4): WRITE/EXECUTION tools × {Mặc định, overrides} (EP-AI-18..21). Root default > L2 struck-through. */
export function AutonomyTab() {
  const t = useTranslations("aiAdmin");
  const locale = useLocale() as AppLocale;
  const tools = useTools();
  const pol = usePolicies();
  const toast = useToast();
  const invalidate = useInvalidateAi();
  const [editing, setEditing] = React.useState<Policy | { tool_name: string } | null>(null);
  const [removing, setRemoving] = React.useState<Policy | null>(null);
  if (tools.isLoading || pol.isLoading) return <p className="text-sm text-muted-foreground">{t("tools.loading")}</p>;
  if (tools.isError || pol.isError) return <p role="alert" className="text-sm text-danger">{t("autonomy.error")}</p>;
  const rows = matrixTools(tools.data ?? []);
  const scopeLabel = (p: Policy) => [p.role_code && t("autonomy.forRole", { role: p.role_code }), p.agent_profile_code && t("autonomy.forAgent", { agent: p.agent_profile_code }),
    p.max_amount != null && t("autonomy.upTo", { amount: formatMoney(p.max_amount, locale) })].filter(Boolean).join(" · ") || t("autonomy.everyone");
  return (
    <section className="flex flex-col gap-3" data-testid="autonomy-tab">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">{t("autonomy.hint")}</p>
        <Button size="sm" onClick={() => setEditing({ tool_name: rows[0]?.name ?? "" })} data-testid="policy-new"><Plus className="h-4 w-4" aria-hidden />{t("autonomy.new")}</Button>
      </div>
      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
            <tr><th className="px-3 py-2">{t("autonomy.col.tool")}</th><th className="px-3 py-2">{t("autonomy.col.default")}</th><th className="px-3 py-2">{t("autonomy.col.overrides")}</th></tr>
          </thead>
          <tbody>
            {rows.map((tool) => {
              const d = pol.data!.defaults.find((x) => x.tool_name === tool.name);
              const capped = cappedDefault(tool.autonomy_default);
              const overrides = pol.data!.rows.filter((p) => p.tool_name === tool.name);
              return (
                <tr key={tool.name} className="border-t align-top" data-testid="matrix-row" data-tool={tool.name}>
                  <td className="px-3 py-2"><div className="font-mono text-xs font-medium">{tool.name}</div><div className="text-xs text-muted-foreground">{tool.action_name} · {tool.kind}</div></td>
                  <td className="px-3 py-2" data-testid="matrix-default">
                    {capped.struck && <s className="mr-1 text-muted-foreground" data-testid="matrix-struck">{capped.struck}</s>}
                    <span>{d?.default_level ?? capped.shown} · {t(levelKey(d?.default_level ?? capped.shown))}</span>
                    {capped.struck && <div className="text-xs text-muted-foreground">{t("autonomy.capped")}</div>}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-col gap-1">
                      {overrides.map((p) => (
                        <div key={p.id} className="flex flex-wrap items-center gap-2" data-testid="policy-chip">
                          <button type="button" className="text-left hover:underline" onClick={() => setEditing(p)} data-testid="policy-edit">
                            <Badge variant={p.is_active ? "primary" : "outline"}>{p.level}</Badge> <span className="text-xs">{scopeLabel(p)}</span>
                          </button>
                          <button type="button" aria-label={t("autonomy.delete")} onClick={() => setRemoving(p)} className="text-muted-foreground hover:text-danger" data-testid="policy-delete"><Trash2 className="h-3.5 w-3.5" /></button>
                        </div>
                      ))}
                      <button type="button" className="w-fit text-xs text-primary hover:underline" onClick={() => setEditing({ tool_name: tool.name })} data-testid="policy-add">+ {t("autonomy.add")}</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <PolicyDialog value={editing} tools={rows} onClose={() => setEditing(null)} />
      <ConfirmDialog open={removing !== null} onOpenChange={(o) => { if (!o) setRemoving(null); }} title={t("autonomy.deleteTitle")} body={t("autonomy.deleteBody")}
        confirmLabel={t("autonomy.delete")} danger reasonRequired testId="policy-delete-dialog"
        onConfirm={async (reason) => { await deletePolicy(removing!.id, reason); await invalidate(); toast.push(t("autonomy.deleted"), "success"); }} />
    </section>
  );
}
