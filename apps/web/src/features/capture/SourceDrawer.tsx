"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { captureError } from "./errors";
import { sourceViewState } from "./source-view";
import { useSource } from "./use-capture";

// Re-export so existing imports (wiring.test.ts) keep working; logic lives in source-view.ts.
export { servable } from "./source-view";

/**
 * "Xem tài liệu gốc" (EP-DC-14 → EP-DC-14b, R-DEC-80): shows the original PDF/image inline in a
 * sandboxed iframe with page navigation; on an iframe load failure or an unservable URL it falls
 * back to the extracted text layer. Error states are distinguished by `sourceViewState`: 403
 * (signature/scope/expired link), a genuine load error, "no text layer at all", and "no text on
 * this page" each surface their own message instead of a blanket "no text" (the original bug).
 */
export function SourceDrawer({ documentId, filename, page: initial = 1, onClose }: { documentId: string | null; filename?: string | null; page?: number; onClose: () => void }) {
  const t = useTranslations();
  const [page, setPage] = React.useState(initial);
  const [frameFailed, setFrameFailed] = React.useState(false);
  React.useEffect(() => {
    setPage(initial);
    setFrameFailed(false);
  }, [documentId, initial]);
  const src = useSource(documentId, page);
  const data = src.data;
  const total = data?.page_count ?? 1;
  const title = filename ?? data?.filename ?? t("capture.source.title");
  const state = sourceViewState(data, page, { error: src.isError ? src.error : undefined, frameFailed });
  const canFrame = state.kind === "frame";
  return (
    <Dialog open={Boolean(documentId)} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-4xl" data-testid="source-drawer">
        <DialogTitle>{t("capture.source.title")}{title ? ` · ${title}` : ""}</DialogTitle>
        <DialogDescription>{t("capture.source.expires")}</DialogDescription>
        {src.isPending && <div className="h-96 animate-pulse rounded bg-muted" aria-label={t("capture.source.loading")} />}
        {(state.kind === "forbidden" || state.kind === "error") && (
          <p role="alert" className="rounded border border-warning bg-warning-subtle p-3 text-sm" data-testid="source-error" data-forbidden={state.kind === "forbidden" || undefined}>
            {captureError(t, src.error)}
          </p>
        )}
        {data && state.kind !== "error" && state.kind !== "forbidden" && (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2 text-sm">
              <div className="flex items-center gap-1">
                <Button size="icon" variant="ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} aria-label={t("buttons.previous")}><ChevronLeft className="h-4 w-4" /></Button>
                <span data-testid="source-page">{t("capture.source.page", { page, total })}</span>
                <Button size="icon" variant="ghost" disabled={page >= total} onClick={() => setPage((p) => p + 1)} aria-label={t("buttons.next")}><ChevronRight className="h-4 w-4" /></Button>
              </div>
              {canFrame && <a href={state.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-primary" data-testid="source-open"><ExternalLink className="h-4 w-4" aria-hidden />{t("capture.source.open")}</a>}
            </div>
            {state.kind === "frame" && (
              // No `sandbox` attribute on purpose: Chromium's built-in PDF viewer refuses to render
              // inside ANY sandboxed <iframe> (verified across every flag combination — images still
              // render, PDFs stay blank), which forced users to open PDFs in a new tab. Isolation is
              // instead enforced on the served file itself: files.py returns
              // `Content-Security-Policy: default-src 'none'; frame-ancestors 'self'` + `nosniff`, so
              // the framed document cannot run scripts, load sub-resources, or be framed cross-origin
              // even without an iframe sandbox. A raw PDF/image byte stream has no active content.
              <iframe src={state.url} title={title} className="h-[70vh] w-full rounded border bg-muted" data-testid="source-frame" onError={() => setFrameFailed(true)} />
            )}
            {state.kind === "text" && (
              <pre className="h-[70vh] overflow-auto whitespace-pre-wrap rounded border bg-muted p-3 text-xs" data-testid="source-text">{state.text}</pre>
            )}
            {state.kind === "no-text-layer" && (
              <p className="rounded border bg-muted p-3 text-sm text-muted-foreground" data-testid="source-no-text">{t("capture.source.noTextLayer")}</p>
            )}
            {state.kind === "page-no-text" && (
              <p className="rounded border bg-muted p-3 text-sm text-muted-foreground" data-testid="source-page-empty">{t("capture.source.pageNoText")}</p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
