"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { ReviewDetail } from "@/features/idp/types";
import { captureError } from "./errors";
import { useSource } from "./use-capture";

/**
 * EP-DC-14 returns `/files/<key>?expires&signature` from the local store; that path has no serving
 * route yet (debt, pending DEC — STATE M1.5). Only absolute http(s) / data: URLs are framed; otherwise
 * the drawer falls back to the page text layer (EP-DC-05 `pages[]`, readable by reviewers).
 */
export const servable = (url: string) => /^(https?:|data:)/i.test(url);

function TextLayer({ documentId, page }: { documentId: string; page: number }) {
  const t = useTranslations();
  const q = useQuery({ queryKey: qk.reviewDetail(documentId), queryFn: ({ signal }) => api.get<ReviewDetail>(`/idp/documents/${documentId}/review`, undefined, signal), retry: false, staleTime: 60_000 });
  const p = q.data?.pages.find((x) => x.page_number === page);
  if (q.isPending) return <div className="h-96 animate-pulse rounded bg-muted" />;
  if (!p?.text_content) return <p className="rounded border bg-muted p-3 text-sm text-muted-foreground" data-testid="source-unavailable">{t("capture.source.unavailable")}</p>;
  return <pre className="h-[70vh] overflow-auto whitespace-pre-wrap rounded border bg-muted p-3 text-xs" data-testid="source-text">{p.text_content}</pre>;
}

/**
 * "Xem tài liệu gốc" (EP-DC-14): presigned URL (5 min) shown inline (PDF / image in an iframe) with page
 * navigation, or the text-layer fallback above; MANUAL documents → 422 `no_file` shown as a message.
 */
export function SourceDrawer({ documentId, filename, page: initial = 1, onClose }: { documentId: string | null; filename?: string | null; page?: number; onClose: () => void }) {
  const t = useTranslations();
  const [page, setPage] = React.useState(initial);
  React.useEffect(() => setPage(initial), [documentId, initial]);
  const src = useSource(documentId, page);
  const total = src.data?.page_count ?? 1;
  return (
    <Dialog open={Boolean(documentId)} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-4xl" data-testid="source-drawer">
        <DialogTitle>{t("capture.source.title")}{filename ? ` · ${filename}` : ""}</DialogTitle>
        <DialogDescription>{t("capture.source.expires")}</DialogDescription>
        {src.isPending && <div className="h-96 animate-pulse rounded bg-muted" aria-label={t("capture.source.loading")} />}
        {src.isError && <p role="alert" className="rounded border border-warning bg-warning-subtle p-3 text-sm" data-testid="source-error">{captureError(t, src.error)}</p>}
        {src.data && (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2 text-sm">
              <div className="flex items-center gap-1">
                <Button size="icon" variant="ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} aria-label={t("buttons.previous")}><ChevronLeft className="h-4 w-4" /></Button>
                <span data-testid="source-page">{t("capture.source.page", { page, total })}</span>
                <Button size="icon" variant="ghost" disabled={page >= total} onClick={() => setPage((p) => p + 1)} aria-label={t("buttons.next")}><ChevronRight className="h-4 w-4" /></Button>
              </div>
              {servable(src.data.url) && <a href={src.data.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-primary"><ExternalLink className="h-4 w-4" aria-hidden />{t("capture.source.open")}</a>}
            </div>
            {servable(src.data.url)
              ? <iframe src={src.data.url} title={filename ?? t("capture.source.title")} className="h-[70vh] w-full rounded border bg-muted" data-testid="source-frame" />
              : documentId && <TextLayer documentId={documentId} page={page} />}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
