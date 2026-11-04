"use client";
/**
 * `/business/sales/deals/[id]` — Opportunity detail (BRD §2.5 CRM-OPP-04 / OPP-13 history, UX-005)
 * on EP-SAL-02/03: deal info, stage progress, stage history with days spent per stage, and the
 * stage move (forward only, lost needs a reason — the API enforces and audits).
 */
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { QueryError } from "@/components/QueryError";
import { formatDate, formatDateTime, formatMoney, type AppLocale } from "@/lib/format";
import { OPEN_STAGES, dealRisk, isClosed } from "./crm";
import { LostReasonDialog, StageSelect, useStageMove } from "./StageMove";
import { business_today } from "./today";
import { useClient, useDeal, useStageHistory } from "./use-crm";

export function DealDetailView({ id, canMove, userId }: { id: string; canMove: boolean; userId: string }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const deal = useDeal(id);
  const history = useStageHistory(id);
  const d = deal.data;
  const client = useClient(d?.client_id ?? "");
  const mover = useStageMove();
  if (deal.isPending) return <div className="h-40 animate-pulse rounded-lg bg-muted" />;
  if (deal.isError || !d) return <QueryError error={deal.error} onRetry={() => void deal.refetch()} testId="deal-error" />;
  const risk = dealRisk(d, business_today());
  const rows = history.data ?? [];
  const info: [string, string][] = [
    [t("crm.value"), formatMoney(d.deal_value, locale)],
    [t("crm.probability"), `${d.probability_pct}%`],
    [t("crm.weighted"), formatMoney(d.weighted_value, locale)],
    [t("crm.closeDate"), formatDate(d.expected_close_date, locale)],
    [t("crm.owner"), d.owner_id === userId ? t("crm.me") : d.owner_id.slice(0, 8)],
  ];
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4" data-testid="deal-detail">
      <Link href="/business/sales/pipeline" className="flex items-center gap-1 text-sm text-primary hover:underline"><ArrowLeft className="h-4 w-4" aria-hidden />{t("crm.pipelineTitle")}</Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">{d.name}</h1>
        <Badge data-testid="deal-stage">{t(`sales.stage.${d.stage}` as "sales.stage.lead")}</Badge>
        {risk && <Badge variant={risk === "overdue" ? "danger" : "warning"}>{t(`crm.risk.${risk}`)}</Badge>}
        {canMove && <StageSelect deal={d} disabled={mover.busy} onMove={(to) => mover.request(d, to)} testId="deal-move" />}
      </div>
      {/* stage progress (CRM-OPP-04 "Stage Progress") */}
      <ol className="flex flex-wrap gap-1" aria-label={t("crm.progress")} data-testid="deal-progress">
        {[...OPEN_STAGES, isClosed(d.stage) ? d.stage : "closed_won"].map((s) => {
          const reached = isClosed(d.stage) || OPEN_STAGES.indexOf(s as never) <= OPEN_STAGES.indexOf(d.stage as never);
          return <li key={s} className={`rounded px-2 py-1 text-xs ${s === d.stage ? "bg-primary text-primary-foreground" : reached ? "bg-primary/15" : "bg-muted text-muted-foreground"}`}>{t(`sales.stage.${s}` as "sales.stage.lead")}</li>;
        })}
      </ol>
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-4 md:col-span-2">
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {info.map(([k, v]) => <div key={k}><dt className="text-muted-foreground">{k}</dt><dd className="font-medium tabular-nums">{v}</dd></div>)}
            <div><dt className="text-muted-foreground">{t("crm.client")}</dt>
              <dd><Link href={`/business/sales/clients/${d.client_id}`} className="font-medium text-primary hover:underline" data-testid="deal-client">{client.data?.name ?? "…"}</Link></dd></div>
          </dl>
          {d.description && <p className="mt-3 whitespace-pre-line text-sm">{d.description}</p>}
          {d.lost_reason && <p className="mt-3 text-sm text-danger">{t("crm.lostReason")}: {d.lost_reason}</p>}
        </Card>
        <Card className="p-4">
          <h2 className="text-sm font-semibold">{t("crm.history")}</h2>
          {history.isError && <QueryError error={history.error} />}
          {history.isSuccess && rows.length === 0 && <p className="mt-2 text-sm text-muted-foreground">{t("crm.noHistory")}</p>}
          <ol className="mt-2 flex flex-col gap-2 text-sm" data-testid="deal-history">
            {rows.map((h, i) => {
              const next = rows[i + 1]?.changed_at;
              const days = next ? Math.max(0, Math.round((Date.parse(next) - Date.parse(h.changed_at)) / 86_400_000)) : null;
              return (
                <li key={`${h.changed_at}-${h.to_stage}`} className="border-l-2 border-primary/40 pl-2">
                  <div className="font-medium">{t(`sales.stage.${h.to_stage}` as "sales.stage.lead")}</div>
                  <div className="text-xs text-muted-foreground tabular-nums">{formatDateTime(h.changed_at, locale)}{days !== null && ` · ${t("crm.daysInStage", { days })}`}</div>
                </li>
              );
            })}
          </ol>
        </Card>
      </div>
      <LostReasonDialog open={mover.pending !== null} onCancel={mover.cancel} onConfirm={mover.confirmLost} />
    </div>
  );
}
