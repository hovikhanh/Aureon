"use client";
/** SCR-58 tabs "Liên kết" (parent / children / SO / KR from the tree payload) and "Lịch sử" (measurements + check-ins). */
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatPeriod, type AppLocale } from "@/lib/format";
import { businessToday } from "@/lib/work-dates";
import { BandChip, KrConfidence, LoadError } from "./common";
import { formatValue, periodKeyOf, type KpiNode } from "./logic";
import { useGoalTree, useKpiCheckIns, useKpiMeasurements, type KpiOut } from "./use-goals";

/** Find the KPI in the tree to read its parent / SO (no extra endpoint — EP-STR-01 is the link source). */
function locate(tree: ReturnType<typeof useGoalTree>["data"], id: string) {
  if (!tree) return null;
  const walk = (rows: KpiNode[], parent: KpiNode | null, so: { code?: string | null; title?: string | null } | null): { parent: KpiNode | null; so: typeof so; node: KpiNode } | null => {
    for (const k of rows) {
      if (k.id === id) return { parent, so, node: k };
      const hit = walk(k.children ?? [], k, so);
      if (hit) return hit;
    }
    return null;
  };
  for (const so of (tree.strategies ?? []).flatMap((s) => s.strategic_objectives ?? [])) {
    const hit = walk(so.kpis ?? [], null, so);
    if (hit) return hit;
  }
  return walk(tree.unaligned?.kpis ?? [], null, null);
}

export function KpiLinks({ k }: { k: KpiOut }) {
  const t = useTranslations("goals.kpi");
  const tree = useGoalTree({ period_key: periodKeyOf("QUARTER", businessToday()) });
  if (tree.isError) return <LoadError onRetry={() => void tree.refetch()} />;
  const hit = locate(tree.data, k.id);
  const link = (n: KpiNode) => n.restricted ? <span className="text-muted-foreground">{n.code} {n.name}</span> : <Link href={`/goals/kpis/${n.id}`} className="text-primary hover:underline">{n.code} {n.name}</Link>;
  return (
    <dl className="grid grid-cols-[12rem_1fr] gap-2 text-sm" data-testid="kpi-links">
      <dt className="text-muted-foreground">{t("strategicObjective")}</dt>
      <dd>{hit?.so ? `${hit.so.code ?? ""} ${hit.so.title ?? ""}` : t("none")}</dd>
      <dt className="text-muted-foreground">{t("parent")}</dt>
      <dd>{hit?.parent ? link(hit.parent) : t("none")}</dd>
      <dt className="text-muted-foreground">{t("children")}</dt>
      <dd className="flex flex-col gap-1">{(hit?.node.children ?? []).length ? hit!.node.children!.map((c) => <span key={c.id} className="flex items-center gap-2">{link(c)} <BandChip band={c.latest_evaluation?.band} /></span>) : t("none")}</dd>
      <dt className="text-muted-foreground">{t("keyResult")}</dt>
      <dd>{k.key_result_id ? <Badge variant="outline">{k.key_result_id.slice(0, 8)}</Badge> : t("none")}</dd>
    </dl>
  );
}

export function KpiHistory({ id, unit }: { id: string; unit: string }) {
  const t = useTranslations("goals");
  const locale = useLocale() as AppLocale;
  const ms = useKpiMeasurements(id);
  const cis = useKpiCheckIns(id);
  return (
    <div className="flex flex-col gap-4">
      <div data-testid="kpi-measurements">
        <h2 className="mb-2 text-sm font-semibold">{t("kpi.measurements")}</h2>
        {ms.isError ? <LoadError onRetry={() => void ms.refetch()} /> : (
          <table className="w-full text-sm">
            <thead><tr className="text-left text-muted-foreground"><th className="py-1">{t("kpi.measuredAt")}</th><th>{t("kpi.period")}</th><th>{t("kpi.actual")}</th><th>{t("kpi.source")}</th><th>{t("kpi.note")}</th></tr></thead>
            <tbody>
              {(ms.data ?? []).map((m) => (
                <tr key={m.id} data-testid="measurement-row">
                  <td className="py-1">{formatDateTime(m.measured_at, locale)}</td>
                  <td>{formatPeriod(m.period_key, locale)}</td>
                  <td className="tabular-nums">{formatValue(m.actual_value, unit, locale)} <BandChip band={m.evaluation_band as "MEETS"} /></td>
                  <td>{m.data_source ?? "—"}</td>
                  <td>{m.note ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div data-testid="kpi-checkins">
        <h2 className="mb-2 text-sm font-semibold">{t("kpi.checkIns")}</h2>
        {cis.isError ? <LoadError onRetry={() => void cis.refetch()} /> : (cis.data ?? []).length === 0 ? <p className="text-sm text-muted-foreground">{t("objective.noHistory")}</p> : (
          <ul className="flex flex-col gap-2 text-sm">
            {cis.data!.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center gap-2">
                <span>{formatDateTime(c.checked_in_at, locale)}</span>
                <span className="tabular-nums">{formatValue(Number(c.value), unit, locale)}</span>
                <KrConfidence value={c.confidence} />
                {c.note && <span className="text-muted-foreground">{c.note}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
