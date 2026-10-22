"use client";
import { useTranslations } from "next-intl";
import { FileText } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ReviewField, ReviewPage } from "./types";

/**
 * Source viewer placeholder (S5a): renders the page text layer; the active field's
 * `source_location` is highlighted (bbox overlay when present, else matching text line).
 */
export function SourceViewer({ pages, active, fieldLabel }: { pages: ReviewPage[]; active: ReviewField | null; fieldLabel: (f: ReviewField) => string }) {
  const t = useTranslations("idp");
  const needle = active ? String(active.ai_value ?? "") : "";
  const bbox = active?.source_location?.bbox;
  return (
    <Card className="flex h-full flex-col overflow-hidden" data-testid="source-viewer">
      <div className="flex items-center gap-2 border-b px-4 py-2 text-sm font-medium">
        <FileText className="h-4 w-4" aria-hidden />{t("source")}
        {active && <span className="ml-auto rounded bg-warning-subtle px-2 py-0.5 text-xs">{fieldLabel(active)}</span>}
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto bg-muted/40 p-4">
        {pages.length === 0 && <p className="text-sm text-muted-foreground">{t("noPreview")}</p>}
        {pages.map((p) => {
          const onPage = active?.source_location?.page === p.page_number;
          return (
            <div key={p.id} className={cn("relative rounded border bg-card p-4 shadow-sm", onPage && "ring-2 ring-warning")} data-testid="source-page" data-page={p.page_number}>
              <div className="mb-2 text-xs text-muted-foreground">{t("page", { n: p.page_number })}</div>
              {onPage && bbox && bbox.length === 4 && (
                <div
                  aria-hidden
                  data-testid="bbox"
                  className="pointer-events-none absolute rounded border-2 border-warning bg-warning/20"
                  style={{ left: `${(bbox[0] ?? 0) * 100}%`, top: `${(bbox[1] ?? 0) * 100}%`, width: `${((bbox[2] ?? 0) - (bbox[0] ?? 0)) * 100}%`, height: `${((bbox[3] ?? 0) - (bbox[1] ?? 0)) * 100}%` }}
                />
              )}
              <pre className="whitespace-pre-wrap font-mono text-xs leading-6">
                {(p.text_content ?? "").split("\n").map((line, i) => (
                  <span key={i} className={cn("block", onPage && needle && line.includes(needle) && "bg-warning/30")} data-highlight={onPage && !!needle && line.includes(needle)}>
                    {line || " "}
                  </span>
                ))}
              </pre>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
