"use client";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { ChevronRight, Database, FileText, Gauge } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api-client";
import { formatMetric, formatMoneyShort, formatPct, formatPeriod, type AppLocale } from "@/lib/format";
import { idpDocumentId, type CardDef } from "./drilldown";

interface MetricDetail {
  metric_code: string; name: string; value: number | null; unit: string; status: "ok" | "warning" | "critical" | "no_data";
  period_key: string; formula_display: string; data_source: { module: string; entities: string[] };
}
interface Row { id: string; label: string; amount: number | null; doc: string | null }
interface DocOut { id: string; original_filename: string; page_count: number | null; status: string }

type Raw = Record<string, unknown>;
const toRow = (r: Raw, locale: AppLocale): Row => ({
  id: String(r.id ?? r.budget_id),
  label:
    r.budget_utilization_pct !== undefined
      ? `${formatPeriod(String(r.period), locale)} · ${formatPct(Number(r.budget_utilization_pct), locale)}`
      : String(r.title ?? r.description ?? r.number ?? (r.period ? formatPeriod(String(r.period), locale) : r.id) ?? ""),
  amount: (r.amount ?? r.total_amount ?? r.closing_balance ?? r.spent_amount ?? null) as number | null,
  doc: idpDocumentId(r.notes as string | null),
});

/** 3-level lineage (06 P01): metric (EP-12) → component records (finance lists) → source document (EP-25). */
export function LineageDialog({ card, month, onClose }: { card: CardDef | null; month: string | null; onClose: () => void }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const open = !!card;
  const metric = useQuery({
    queryKey: ["metric-detail", card?.metric],
    queryFn: ({ signal }) => api.get<MetricDetail>(`/dashboard/metrics/${card?.metric}`, undefined, signal),
    enabled: open,
  });
  const records = useQuery({
    queryKey: ["finance-records", card?.records, month],
    queryFn: ({ signal }) =>
      card?.records === "cash-positions"
        ? api.get<Raw[]>("/finance/cash-positions", { limit: 6, sort_by: "period", order: "desc" }, signal)
        : api.get<Raw[]>(`/finance/${card?.records}`, card?.records === "budgets/status" ? { period: month } : { period: month, limit: 5, sort_by: "amount", order: "desc" }, signal),
    enabled: open && !!month,
  });
  const invoices = useQuery({
    queryKey: ["finance-records", "invoices-idp", month],
    queryFn: ({ signal }) => api.get<Raw[]>("/finance/invoices", { direction: "IN", limit: 20, sort_by: "issued_on", order: "desc" }, signal),
    enabled: open && card?.key === "expense",
  });
  const rows = (records.data ?? [])
    .filter((r) => card?.records !== "cash-positions" || !month || String(r.period) <= month)
    .slice(0, 5)
    .map((r) => toRow(r, locale));
  const docRow = (invoices.data ?? []).map((r) => toRow(r, locale)).find((r) => r.doc);
  const docId = rows.find((r) => r.doc)?.doc ?? docRow?.doc ?? null;
  const doc = useQuery({
    queryKey: ["idp-doc", docId],
    queryFn: ({ signal }) => api.get<DocOut>(`/idp/documents/${docId}`, undefined, signal),
    enabled: open && !!docId,
  });
  const m = metric.data;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl" data-testid="lineage-dialog">
        <DialogTitle>{card ? t(`financeDrill.card.${card.key}`) : ""} — {t("financeDrill.lineage.title")}</DialogTitle>
        <DialogDescription>{t("financeDrill.lineage.subtitle")}</DialogDescription>
        <ol className="mt-4 space-y-3 text-sm">
          <li className="rounded-lg border p-3" data-testid="lineage-metric">
            <div className="mb-1 flex items-center gap-2 font-medium"><Gauge className="h-4 w-4 text-primary" aria-hidden />1 · {t("financeDrill.lineage.metric")}</div>
            {m ? (
              <div className="flex flex-wrap items-center gap-2">
                <span>{t(`metric.${m.metric_code}` as "metric.METRIC-FIN-01")}</span>
                <span className="text-muted-foreground">{m.metric_code} · {formatPeriod(m.period_key, locale)}</span>
                <span className="font-semibold tabular-nums">{formatMetric(m.value, m.unit, locale, t(`unit.${m.unit}` as "unit.DAYS"))}</span>
                <StatusBadge status={m.status} />
                <span className="w-full text-xs text-muted-foreground">{t("financeDrill.lineage.sourceEntities", { list: m.data_source.entities.join(", ") })}</span>
              </div>
            ) : <span className="text-muted-foreground">{t("common.loading")}</span>}
          </li>
          <li className="rounded-lg border p-3" data-testid="lineage-records">
            <div className="mb-1 flex items-center gap-2 font-medium"><Database className="h-4 w-4 text-primary" aria-hidden />2 · {t("financeDrill.lineage.records", { month: month ? formatPeriod(month, locale) : "" })}</div>
            {rows.length === 0 && <span className="text-muted-foreground">{records.isLoading ? t("common.loading") : t("financeDrill.lineage.noRecords")}</span>}
            <ul className="divide-y">
              {rows.map((r) => (
                <li key={r.id} className="flex items-center justify-between gap-3 py-1.5" data-testid="lineage-record">
                  <span className="truncate">{r.label}</span>
                  {r.amount !== null && <span className="tabular-nums">{formatMoneyShort(r.amount, locale)}</span>}
                </li>
              ))}
            </ul>
          </li>
          <li className="rounded-lg border p-3" data-testid="lineage-document">
            <div className="mb-1 flex items-center gap-2 font-medium"><FileText className="h-4 w-4 text-primary" aria-hidden />3 · {t("financeDrill.lineage.document")}</div>
            {doc.data ? (
              <a href={`/finance/invoices`} className="flex items-center gap-1 text-primary hover:underline" data-testid="lineage-doc-link">
                {doc.data.original_filename}<ChevronRight className="h-4 w-4" aria-hidden />
              </a>
            ) : (
              <span className="text-muted-foreground">{t("financeDrill.lineage.noDocument")}</span>
            )}
          </li>
        </ol>
      </DialogContent>
    </Dialog>
  );
}
