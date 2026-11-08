"use client";
/**
 * `/business/sales/pipeline` — Kanban of opportunities (BRD §2.6 CRM-PIPE-03/05/08/09, UX-007) on
 * the existing deals API. Column totals come from `/sales/pipeline` (CORE-06), cards from
 * `/sales/deals`. Drag a card (or use its "Chuyển sang…" menu) to change stage — forward only,
 * Closed Lost asks for the reason; the API enforces both and audits the move.
 */
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { QueryError } from "@/components/QueryError";
import { formatDate, formatMoneyShort, type AppLocale } from "@/lib/format";
import { business_today } from "./today";
import { STAGES, canMoveTo, dealRisk } from "./crm";
import { LostReasonDialog, StageSelect, useStageMove } from "./StageMove";
import { useClients, useDeals, useOwnerLabel, usePipeline, type DealOut } from "./use-crm";

export function PipelineBoard({ canMove, userId, canReadUsers }: { canMove: boolean; userId: string; canReadUsers: boolean }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const deals = useDeals({ sort_by: "expected_close_date", order: "asc" });
  const totals = usePipeline();
  const clients = useClients();
  const clientName = new Map((clients.data ?? []).map((c) => [c.id, c.name]));
  const [dragged, setDragged] = React.useState<DealOut | null>(null);
  const mover = useStageMove();
  const ownerLabel = useOwnerLabel(userId, canReadUsers);
  const today = business_today();

  const drop = (stage: string) => {
    if (dragged && canMoveTo(dragged.stage, stage)) mover.request(dragged, stage);
    setDragged(null);
  };

  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-4" data-testid="crm-pipeline">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">{t("crm.pipelineTitle")}</h1>
        <Link href="/business/sales/records?tab=deals" className="text-sm text-primary hover:underline">{t("crm.manageDeals")}</Link>
      </div>
      {deals.isError && <QueryError error={deals.error} onRetry={() => void deals.refetch()} />}
      {(deals.data?.length ?? 0) >= 100 && <p className="text-xs text-muted-foreground">{t("crm.first100")}</p>}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6" data-testid="crm-board">
        {STAGES.map((stage) => {
          const total = totals.data?.stages.find((s) => s.stage === stage);
          const cards = (deals.data ?? []).filter((d) => d.stage === stage);
          const droppable = canMove && dragged !== null && canMoveTo(dragged.stage, stage);
          return (
            <section key={stage} data-testid={`crm-col-${stage}`} aria-label={t(`sales.stage.${stage}` as "sales.stage.lead")}
              className={`flex min-h-40 flex-col gap-2 rounded-lg border p-2 ${droppable ? "border-primary bg-primary/5" : "bg-muted/30"}`}
              onDragOver={(e) => droppable && e.preventDefault()} onDrop={() => drop(stage)}>
              <header className="px-1">
                <div className="text-sm font-semibold">{t(`sales.stage.${stage}` as "sales.stage.lead")}</div>
                <div className="text-xs text-muted-foreground tabular-nums" data-testid={`crm-col-total-${stage}`}>
                  {total ? `${total.count} · ${formatMoneyShort(total.value, locale)}` : "—"}
                </div>
              </header>
              {cards.map((d) => {
                const risk = dealRisk(d, today);
                return (
                  <Card key={d.id} draggable={canMove && STAGES.some((s) => canMoveTo(d.stage, s))} onDragStart={() => setDragged(d)} onDragEnd={() => setDragged(null)}
                    className="flex flex-col gap-1 p-2 text-sm" data-testid="crm-card" data-id={d.id} data-stage={d.stage}>
                    <Link href={`/business/sales/deals/${d.id}`} className="font-medium hover:text-primary hover:underline">{d.name}</Link>
                    <span className="text-xs text-muted-foreground">{clientName.get(d.client_id) ?? "—"}</span>
                    <span className="tabular-nums">{formatMoneyShort(d.deal_value, locale)} · {d.probability_pct}%</span>
                    <span className="text-xs text-muted-foreground tabular-nums">{t("crm.weighted")}: {formatMoneyShort(d.weighted_value, locale)}</span>
                    <span className="text-xs tabular-nums">{t("crm.closeDate")}: {formatDate(d.expected_close_date, locale)}</span>
                    <span className="text-xs text-muted-foreground">{t("crm.owner")}: {ownerLabel(d.owner_id)}</span>
                    {risk && <Badge variant={risk === "overdue" ? "danger" : "warning"} data-testid="crm-risk">{t(`crm.risk.${risk}`)}</Badge>}
                    {canMove && <StageSelect deal={d} disabled={mover.busy} onMove={(to) => mover.request(d, to)} testId="crm-card-move" />}
                  </Card>
                );
              })}
            </section>
          );
        })}
      </div>
      <LostReasonDialog open={mover.pending !== null} onCancel={mover.cancel} onConfirm={mover.confirmLost} />
    </div>
  );
}
