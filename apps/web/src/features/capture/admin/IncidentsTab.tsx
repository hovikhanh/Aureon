"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { apiRequest } from "@/lib/api-client";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { qk } from "@/lib/query-keys";
import { captureError } from "../errors";
import type { Incident } from "../types";

/** EP-DC-37 critical-field incidents (R-DEC-69): filter by period (YYYY-MM) / undetected only. */
export function IncidentsTab() {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const [period, setPeriod] = React.useState("");
  const [und, setUnd] = React.useState(false);
  const params = { period: /^\d{4}-\d{2}$/.test(period) ? period : undefined, undetected_only: und || undefined, limit: 100 };
  const q = useQuery({ queryKey: qk.captureIncidents(params), queryFn: ({ signal }) => apiRequest<Incident[]>("/data-capture/incidents", { query: params, signal }) });
  const rows = q.data?.data ?? [];
  return (
    <div className="flex flex-col gap-3" data-testid="incidents">
      <div className="flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col gap-1">{t("capture.admin.incident.period")}<Input value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="2026-10" className="w-32" /></label>
        <label className="flex items-center gap-2 pb-2"><Checkbox checked={und} onCheckedChange={(c) => setUnd(c === true)} />{t("capture.admin.incident.onlyUndetected")}</label>
      </div>
      {q.isError && <p role="alert" className="text-danger">{captureError(t, q.error)}</p>}
      {q.isSuccess && rows.length === 0 && <p className="text-sm text-muted-foreground">{t("capture.admin.incident.none")}</p>}
      {rows.length > 0 && (
        <table className="w-full rounded-lg border bg-card text-sm">
          <thead><tr className="border-b text-left text-muted-foreground">
            {(["field", "document", "detectedBy", "undetected", "reported", "description"] as const).map((c) => <th key={c} className="px-3 py-2 font-medium">{t(`capture.admin.incident.${c}`)}</th>)}
          </tr></thead>
          <tbody>
            {rows.map((i) => (
              <tr key={i.id} className="border-b align-top last:border-0" data-testid="incident-row">
                <td className="px-3 py-2 font-mono text-xs">{i.field_name}{i.is_critical ? " *" : ""}</td>
                <td className="px-3 py-2 font-mono text-xs">{i.source_document_id.slice(0, 8)}</td>
                <td className="px-3 py-2">{t(`capture.admin.incident.by.${i.detected_by}`)}</td>
                <td className="px-3 py-2">{i.undetected ? "✓" : "—"}</td>
                <td className="whitespace-nowrap px-3 py-2">{formatDateTime(i.reported_at, locale)}</td>
                <td className="px-3 py-2">{i.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
