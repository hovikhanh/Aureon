"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { FileSearch, Lock } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { SourceDrawer } from "@/features/capture/SourceDrawer";
import { linkLocation, lineageView } from "@/features/capture/lineage-view";
import { useLineage } from "@/features/capture/use-capture";
import { isMasked } from "@/features/capture/types";

/**
 * LineageChip (P01, EP-DC-26): "Nguồn" chip on a record written by Data Capture; opens the source
 * links (file, page / sheet + row, field, raw value) lazily; `restricted` shows only a lock
 * message (no ids or file names). "Xem tài liệu gốc" opens EP-DC-14 at the linked page.
 */
export function LineageChip({ entity, id, className }: { entity: string; id: string; className?: string }) {
  const t = useTranslations("capture");
  const [open, setOpen] = React.useState(false);
  const [source, setSource] = React.useState<{ id: string; filename: string | null; page: number } | null>(null);
  const q = useLineage(entity, id, open);
  const view = lineageView(q.data);
  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button type="button" data-testid="lineage-chip" className={`inline-flex h-6 items-center gap-1 rounded-full border px-2 text-xs text-muted-foreground hover:bg-muted ${className ?? ""}`}>
            <FileSearch className="h-3.5 w-3.5" aria-hidden />{t("lineage.chip")}
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-96" data-testid="lineage-popover">
          <div className="mb-2 font-semibold">{t("lineage.title")}</div>
          {q.isPending && <div className="h-16 animate-pulse rounded bg-muted" />}
          {q.isError && <p role="alert" className="text-danger">{t("errors.unknown", { code: (q.error as { code?: string }).code ?? "" })}</p>}
          {q.isSuccess && view.kind === "restricted" && <p className="flex items-center gap-2 text-muted-foreground" data-testid="lineage-restricted"><Lock className="h-4 w-4" aria-hidden />{t("lineage.restricted")}</p>}
          {q.isSuccess && view.kind === "none" && <p className="text-muted-foreground" data-testid="lineage-none">{t("lineage.none")}</p>}
          {q.isSuccess && view.kind === "links" && view.documents.map((d) => (
            <section key={d.source_document_id} className={`mb-2 rounded border p-2 ${d.revoked ? "opacity-60" : ""}`}>
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-medium" title={d.filename ?? ""}>{d.filename ?? t("lineage.manual")}</span>
                {d.revoked && <span className="text-xs text-warning">{t("lineage.revoked")}</span>}
              </div>
              <ul className="mt-1 space-y-1 text-xs">
                {d.links.map((l, i) => {
                  const loc = linkLocation(l);
                  return (
                    <li key={i} className="grid grid-cols-[auto_1fr] gap-x-2" data-testid="lineage-link">
                      <span className="text-muted-foreground">{l.field_name ?? l.target_column}</span>
                      <span className="truncate">
                        {isMasked(l.raw_text) ? t("lineage.masked") : String(l.raw_text ?? "—")}
                        {" · "}{[loc.page !== undefined ? t("lineage.page", { n: loc.page }) : null, loc.sheet ? t("lineage.sheet", { name: loc.sheet }) : null, loc.row !== undefined ? t("lineage.row", { n: loc.row }) : null].filter(Boolean).join(" · ")}
                      </span>
                    </li>
                  );
                })}
              </ul>
              {d.filename && (
                <button type="button" className="mt-1 text-xs text-primary hover:underline" data-testid="lineage-open-source"
                  onClick={() => { setOpen(false); setSource({ id: d.source_document_id, filename: d.filename, page: d.links[0]?.page_number ?? 1 }); }}>
                  {t("lineage.openSource")}
                </button>
              )}
            </section>
          ))}
        </PopoverContent>
      </Popover>
      <SourceDrawer documentId={source?.id ?? null} filename={source?.filename} page={source?.page ?? 1} onClose={() => setSource(null)} />
    </>
  );
}
