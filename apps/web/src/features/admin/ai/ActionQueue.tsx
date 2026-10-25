"use client";
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { ActionCard } from "@/components/ai/ActionCard";
import { NativeSelect } from "@/components/ui/select";
import { useActionFlow } from "@/features/ai/use-action-flow";
import { agentName } from "./logic";
import { useActions, useAgents } from "./use-ai-admin";
import type { Viewer } from "./types";

/**
 * SCR-64 "Hàng chờ AI soạn" (06 §3.4, T-645F): proposed L2 cards of the tenant (EP-AI-07 `ai:admin`).
 * Confirm/Reject only on the viewer's own cards (`on_behalf_of`); others are read-only here.
 */
export function ActionQueue({ viewer }: { viewer: Viewer }) {
  const t = useTranslations("aiAdmin.queue");
  const locale = useLocale();
  const [agent, setAgent] = React.useState("");
  const q = useActions({ status: "proposed", ...(agent ? { agent_profile_code: agent } : {}) });
  const agents = useAgents();
  const flow = useActionFlow();
  return (
    <section id="ai-queue" className="flex flex-col gap-3" data-testid="ai-queue">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">{t("title")}</h2>
        <NativeSelect aria-label={t("filterAgent")} value={agent} onChange={(e) => setAgent(e.target.value)} data-testid="queue-agent">
          <option value="">{t("allAgents")}</option>
          {(agents.data ?? []).map((a) => <option key={a.code} value={a.code}>{agentName(a, a.code, locale)}</option>)}
        </NativeSelect>
      </div>
      {q.isError && <p role="alert" className="text-sm text-danger">{t("error")}</p>}
      {q.data?.length === 0 && <p className="text-sm text-muted-foreground" data-testid="queue-empty">{t("empty")}</p>}
      <div className="grid gap-3 md:grid-cols-2">
        {(q.data ?? []).map((a) => (
          <ActionCard key={a.id} action={a} viewerId={viewer.id} permissions={viewer.permissions} errorText={flow.errorText}
            onConfirm={(edited) => flow.confirm(a.id, edited)} onReject={(reason) => flow.reject(a.id, reason)}
            meta={<p className="text-xs text-muted-foreground">{a.on_behalf_of === viewer.id ? t("mine") : t("forOther")} · {agentName(agents.data?.find((x) => x.code === a.agent_profile_code), a.agent_profile_code ?? "", locale, t("legacyAgent"))}</p>} />
        ))}
      </div>
      {flow.toastEl}
    </section>
  );
}
