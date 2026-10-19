"use client";

import { useMemo } from "react";
import { AlertCircle, Download, FileText, Lock, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import type { ExtractedFieldOut, SourceBoundingBox } from "@aureon/shared-types";
import { ApiClientError } from "@/lib/api-client";
import { useP04Formatter } from "@/lib/use-p04-formatter";
import { getDocumentSourceApi } from "./source-api";

export interface SourceViewerProps {
  documentId: string;
  /** C1 MANUAL / C2 TRANSCRIPT have no file → manual-entry panel (SCR-10 Empty). */
  channel: string;
  /** Whether the active role may download (attachment). CEO/CFO/Sales usually read-only. */
  canDownload?: boolean;
  /** Fields (to resolve the highlighted bounding box of the selected field). */
  fields?: ExtractedFieldOut[];
  /** Currently selected field id in the review form → drives the highlight overlay. */
  selectedFieldId?: string | null;
  token?: string;
}

function asBox(loc: Record<string, unknown> | null | undefined): SourceBoundingBox | null {
  if (!loc || typeof loc !== "object") return null;
  const b = loc as Record<string, unknown>;
  if (
    typeof b.page === "number" &&
    typeof b.x === "number" &&
    typeof b.y === "number" &&
    typeof b.w === "number" &&
    typeof b.h === "number"
  ) {
    return {
      kind: typeof b.kind === "string" ? b.kind : "BOUNDING_BOX",
      page: b.page,
      x: b.x,
      y: b.y,
      w: b.w,
      h: b.h,
    };
  }
  return null;
}

/**
 * SCR-10 — Source Viewer (06 §4.7, EP-27, T-220). Renders preprocessed page images with a
 * HighlightOverlay positioned from the selected field's `source_location` (P01 click 3). Used
 * both inside SCR-06 Review (synced to the form) and the SCR-09 drill-down. Salary / scope
 * denials and the C1/C2 manual-entry case are shown as local, non-fatal states.
 */
export function SourceViewer({
  documentId,
  channel,
  canDownload = false,
  fields,
  selectedFieldId,
  token,
}: SourceViewerProps) {
  const t = useTranslations("sourceViewer");
  const fmt = useP04Formatter();

  const query = useQuery({
    queryKey: ["document-source", documentId],
    queryFn: () => getDocumentSourceApi(documentId, {}, token),
    enabled: Boolean(token && documentId),
    retry: false,
  });

  const selectedBox = useMemo<SourceBoundingBox | null>(() => {
    const field = fields?.find((f) => f.id === selectedFieldId);
    return field ? asBox(field.source_location) : null;
  }, [fields, selectedFieldId]);

  // When a field is selected, jump to its page so the highlight is visible.
  const highlightPage = selectedBox?.page ?? 1;

  // Pending (fetching) OR disabled-without-data (e.g. no token yet) → show the loading shell
  // rather than dereferencing an undefined payload.
  if (query.isPending || (!query.data && !query.isError)) {
    return <ViewerShell>{t("loading")}</ViewerShell>;
  }

  if (query.isError) {
    const code = query.error instanceof ApiClientError ? query.error.code : undefined;
    const msg =
      code === "FORBIDDEN_SALARY"
        ? t("forbiddenSalary")
        : code === "FORBIDDEN_SCOPE"
          ? t("forbiddenScope")
          : t("loadError");
    const isDenied = code === "FORBIDDEN_SALARY" || code === "FORBIDDEN_SCOPE";
    return (
      <ViewerShell>
        <div className="flex flex-col items-center gap-3 text-center">
          {isDenied ? (
            <Lock className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
          ) : (
            <AlertCircle className="h-8 w-8 text-critical" aria-hidden="true" />
          )}
          <p className="text-body-sm text-muted-foreground">{msg}</p>
          {!isDenied && (
            <button
              type="button"
              onClick={() => query.refetch()}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-body-sm hover:bg-muted"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {t("retry")}
            </button>
          )}
        </div>
      </ViewerShell>
    );
  }

  const data = query.data!;

  // C1 MANUAL / C2 TRANSCRIPT: no file, show who entered it and when.
  if (data.manual_info || channel === "C1" || channel === "C2") {
    const info = data.manual_info;
    return (
      <ViewerShell>
        <div className="flex flex-col items-center gap-2 text-center">
          <FileText className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
          <p className="text-body-sm text-muted-foreground">
            {info
              ? t("manualEntry", {
                  name: info.created_by_full_name,
                  time: fmt.dateTime(info.created_at),
                })
              : t("loadError")}
          </p>
        </div>
      </ViewerShell>
    );
  }

  const pages = data.pages.length > 0 ? data.pages : [];
  const current = pages.find((p) => p.page_number === highlightPage) ?? pages[0] ?? null;
  const totalPages = data.page_count ?? pages.length ?? 1;

  return (
    <div className="flex h-full flex-col gap-2">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-caption text-muted-foreground">
          {t("page", { page: current?.page_number ?? 1, total: totalPages })}
        </span>
        <div className="flex items-center gap-2">
          {canDownload && data.url && (
            <a
              href={data.url}
              download
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-caption hover:bg-muted"
            >
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
              {t("download")}
            </a>
          )}
        </div>
      </div>

      {/* Page canvas + highlight overlay */}
      <div className="relative flex-1 overflow-auto rounded-lg border border-border bg-muted/30">
        {current?.image_url ? (
          <div className="relative inline-block">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={current.image_url}
              alt={t("page", { page: current.page_number, total: totalPages })}
              className="block max-w-full"
            />
            {selectedBox && selectedBox.page === current.page_number && current.width_px && current.height_px && (
              <span
                aria-label={t("highlightLabel")}
                className="pointer-events-none absolute rounded-sm border-2 border-ai bg-ai/20"
                style={{
                  left: `${(selectedBox.x / current.width_px) * 100}%`,
                  top: `${(selectedBox.y / current.height_px) * 100}%`,
                  width: `${(selectedBox.w / current.width_px) * 100}%`,
                  height: `${(selectedBox.h / current.height_px) * 100}%`,
                }}
              />
            )}
          </div>
        ) : data.url ? (
          // No rendered page images (e.g. native PDF) → embed the presigned file.
          <iframe src={data.url} title={documentId} className="h-full min-h-[480px] w-full" />
        ) : (
          <div className="flex h-full min-h-[300px] items-center justify-center">
            <p className="text-body-sm text-muted-foreground">{t("loadError")}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ViewerShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full min-h-[400px] items-center justify-center rounded-lg border border-dashed border-border bg-muted/30 p-8 text-body-sm text-muted-foreground">
      {children}
    </div>
  );
}
