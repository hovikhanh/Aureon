"use client";
/**
 * SCR-57 `/work/workload` (EP-TASK-18): heatmap person × ISO week, shade ≤ 80 / 80–threshold /
 * > threshold (threshold from the response — not hard-coded); "Quá tải" badge when `overloaded`;
 * summary `overloaded_count/people` (= METRIC-HR-03, links to lineage); overloaded people first;
 * cell → open tasks of that person due that week (F5). Names joined from EP-ORG-24 (R-DEC-44).
 */
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { formatNumber, formatPct, type AppLocale } from "@/lib/format";
import { businessToday, isoWeek, isIsoWeek } from "@/lib/work-dates";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { LoadError } from "./common";
import { loadShade, shortId } from "./logic";
import { WorkloadCellTasks } from "./WorkloadCellTasks";
import { useMembers, useWorkload } from "./use-work";

const SHADE = { low: "bg-primary/10", mid: "bg-warning/40", high: "bg-danger/70 text-white" } as const;
const WEEK_COUNTS = [1, 2, 3, 4, 5, 6, 7, 8];

/** `metricHref`: METRIC-HR-03 lineage entry (SCR-03 pillar O) when the role can open it, else plain text. */
export function WorkloadView({ canReadOrg, pickDepartment, metricHref }: { canReadOrg: boolean; pickDepartment: boolean; metricHref: string | null }) {
  const t = useTranslations("work.workload");
  const locale = useLocale() as AppLocale;
  const [week, setWeek] = React.useState(() => isoWeek(businessToday()));
  const [weeks, setWeeks] = React.useState(4);
  const [dept, setDept] = React.useState("");
  const [cell, setCell] = React.useState<{ employeeId: string; week: string } | null>(null);
  const members = useMembers(canReadOrg);
  const q = useWorkload({ week: isIsoWeek(week) ? week : null, weeks, department_id: dept || null });
  const byId = new Map((members.data ?? []).map((m) => [m.employee_id, m]));
  const departments = [...new Map((members.data ?? []).map((m) => [m.department_id, m.department_name])).entries()];
  const nameOf = (id: string) => byId.get(id)?.full_name ?? shortId(id);
  const data = q.data;
  return (
    <div className="flex flex-col gap-4" data-testid="workload">
      <div>
        <h2 className="text-xl font-semibold">{t("title")}</h2>
        <p className="text-sm text-muted-foreground">{t("hint")}</p>
      </div>
      <Card className="flex flex-wrap items-end gap-3 p-3">
        <div className="flex flex-col gap-1">
          <Label htmlFor="wl-week" className="text-xs">{t("week")}</Label>
          <Input id="wl-week" type="week" value={week} onChange={(e) => setWeek(e.target.value)} className="w-44" data-testid="wl-week" />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="wl-weeks" className="text-xs">{t("weeks")}</Label>
          <NativeSelect id="wl-weeks" value={weeks} onChange={(e) => setWeeks(Number(e.target.value))} data-testid="wl-weeks">
            {WEEK_COUNTS.map((n) => <option key={n} value={n}>{n}</option>)}
          </NativeSelect>
        </div>
        {pickDepartment && departments.length > 1 && (
          <div className="flex flex-col gap-1">
            <Label htmlFor="wl-dept" className="text-xs">{t("department")}</Label>
            <NativeSelect id="wl-dept" value={dept} onChange={(e) => setDept(e.target.value)} data-testid="wl-dept">
              <option value="">{t("allDepartments")}</option>
              {departments.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
            </NativeSelect>
          </div>
        )}
      </Card>
      {(!canReadOrg || members.isError) && <p className="text-xs text-muted-foreground" data-testid="wl-names-unavailable">{t("namesUnavailable")}</p>}
      {q.isError && <LoadError onRetry={() => void q.refetch()} testId="wl-error" />}
      {data && (
        <>
          <div className="flex flex-wrap items-center gap-3 text-sm" data-testid="wl-summary">
            {(() => {
              const text = t("summary", { count: data.summary.overloaded_count, people: data.summary.people, pct: formatPct(data.summary.overloaded_pct, locale) });
              return metricHref
                ? <Link href={metricHref} className="font-medium text-primary hover:underline" title={t("summaryLink")} data-testid="wl-summary-text">{text}</Link>
                : <span className="font-medium" data-testid="wl-summary-text">{text}</span>;
            })()}
            <span className="text-xs text-muted-foreground">{t("threshold", { pct: formatPct(data.threshold_pct, locale), weeks: data.overload_weeks })}</span>
            <span className="flex items-center gap-1 text-xs" aria-hidden>
              <span className={cn("h-3 w-5 rounded", SHADE.low)} />{t("legendLow")}
              <span className={cn("ml-2 h-3 w-5 rounded", SHADE.mid)} />{t("legendMid", { pct: formatPct(data.threshold_pct, locale) })}
              <span className={cn("ml-2 h-3 w-5 rounded", SHADE.high)} />{t("legendHigh", { pct: formatPct(data.threshold_pct, locale) })}
            </span>
          </div>
          {!data.rows.length && <p className="text-sm text-muted-foreground" data-testid="wl-empty">{t("empty")}</p>}
          {data.rows.length > 0 && (
            <Card className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="wl-table">
                <thead className="text-xs text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">{t("person")}</th>
                    {data.weeks.map((w) => <th key={w} className="px-2 py-2 font-medium">{w}</th>)}
                    <th className="px-3 py-2 font-medium">{t("overloadedHeader")}</th>
                  </tr>
                </thead>
                <tbody>
                  {[...data.rows].sort((a, b) => Number(b.overloaded) - Number(a.overloaded)).map((r) => (
                    <tr key={r.employee_id} className="border-t" data-testid={`wl-row-${r.employee_id}`} data-overloaded={r.overloaded ? "true" : "false"}>
                      <th scope="row" className="px-3 py-1.5 text-left font-normal">
                        <span className="font-medium">{nameOf(r.employee_id)}</span>
                        {byId.get(r.employee_id) && <span className="ml-1 text-xs text-muted-foreground">{byId.get(r.employee_id)?.employee_code}</span>}
                      </th>
                      {r.cells.map((c) => (
                        <td key={c.week} className="px-1 py-1">
                          <button type="button" onClick={() => setCell({ employeeId: r.employee_id, week: c.week })} data-testid={`wl-cell-${r.employee_id}-${c.week}`}
                            aria-label={t("cell", { name: nameOf(r.employee_id), week: c.week, pct: formatPct(c.load_pct, locale), hours: formatNumber(c.hours, locale), tasks: c.open_tasks })}
                            className={cn("w-full rounded px-2 py-1.5 text-center tabular-nums", SHADE[loadShade(c.load_pct, data.threshold_pct)])} data-shade={loadShade(c.load_pct, data.threshold_pct)}>
                            {formatPct(c.load_pct, locale)}
                          </button>
                        </td>
                      ))}
                      <td className="px-3 py-1.5 text-center">{r.overloaded && <Badge variant="danger" data-testid="wl-overloaded">{t("overloaded")}</Badge>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
      {cell && <WorkloadCellTasks employeeId={cell.employeeId} week={cell.week} name={nameOf(cell.employeeId)} onClose={() => setCell(null)} />}
    </div>
  );
}
