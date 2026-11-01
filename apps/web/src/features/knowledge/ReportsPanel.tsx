"use client";
/**
 * SCR-49 Reports panel (M3.3, 03 §3.6): the report catalog with CSV + XLSX download buttons per
 * report. Each download streams the export file straight to the browser (Content-Disposition).
 */
import { useState } from "react";
import { useTranslations } from "next-intl";
import { Download } from "lucide-react";
import type { Api } from "@aureon/shared-types";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { downloadReport, useReports } from "./use-knowledge";

const FORMAT_LABEL: Record<string, string> = { csv: "CSV", xlsx: "XLSX" };

export function ReportsPanel() {
  const t = useTranslations("reports");
  const toast = useToast();
  const q = useReports();
  const [busy, setBusy] = useState<string | null>(null);

  const run = async (code: string, format: "csv" | "xlsx") => {
    const key = `${code}:${format}`;
    setBusy(key);
    try {
      await downloadReport(code, format);
    } catch {
      toast.push(t("error"), "danger");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex flex-col gap-4" data-testid="reports-panel">
      <h2 className="text-lg font-semibold">{t("title")}</h2>
      {q.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {q.isError && <p className="text-sm text-danger">{t("loadError")}</p>}
      {q.data && q.data.length === 0 && (
        <p className="text-sm text-muted-foreground" data-testid="reports-empty">{t("empty")}</p>
      )}
      {q.data && q.data.length > 0 && (
        <ul className="flex flex-col gap-2">
          {q.data.map((r) => (
            <ReportRow key={r.code} r={r} busy={busy} onDownload={run} t={t} />
          ))}
        </ul>
      )}
    </div>
  );
}

function ReportRow({
  r,
  busy,
  onDownload,
  t,
}: {
  r: Api.ReportCatalogOut;
  busy: string | null;
  onDownload: (code: string, format: "csv" | "xlsx") => void;
  t: ReturnType<typeof useTranslations>;
}) {
  const formats = (r.formats ?? []).filter((f): f is "csv" | "xlsx" => f === "csv" || f === "xlsx");
  const title = t.has(`catalog.${r.code}`) ? t(`catalog.${r.code}`) : r.title_key;
  return (
    <li>
      <Card className="flex flex-wrap items-center justify-between gap-3 p-4" data-testid="report-row">
        <span className="font-medium">{title}</span>
        <div className="flex gap-2">
          {formats.map((f) => (
            <Button
              key={f}
              size="sm"
              variant="outline"
              disabled={busy === `${r.code}:${f}`}
              data-testid={`report-download-${f}`}
              onClick={() => onDownload(r.code, f)}
            >
              <Download className="h-3.5 w-3.5" aria-hidden />
              {FORMAT_LABEL[f] ?? f.toUpperCase()}
            </Button>
          ))}
        </div>
      </Card>
    </li>
  );
}
