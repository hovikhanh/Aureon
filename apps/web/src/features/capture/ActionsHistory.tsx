"use client";
import { useLocale, useTranslations } from "next-intl";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { captureError } from "./errors";
import { useActions } from "./use-capture";

const actLabel = (t: ReturnType<typeof useTranslations>, name: string) => (t.has(`capture.act.${name}`) ? t(`capture.act.${name}`) : name);

/** "Lịch sử ghi" (EP-DC-25): ACT-* in `seq` order with result refs and reverted status. */
export function ActionsHistory({ documentId, onClose }: { documentId: string | null; onClose: () => void }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const q = useActions(documentId);
  return (
    <Dialog open={Boolean(documentId)} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl" data-testid="actions-history">
        <DialogTitle>{t("capture.history.title")}</DialogTitle>
        {q.isPending && <div className="h-24 animate-pulse rounded bg-muted" />}
        {q.isError && <p role="alert" className="text-danger">{captureError(t, q.error)}</p>}
        {q.data?.length === 0 && <p className="text-sm text-muted-foreground">{t("capture.history.empty")}</p>}
        {q.data && q.data.length > 0 && (
          <table className="w-full text-sm">
            <thead><tr className="border-b text-left text-muted-foreground">
              <th className="py-1 pr-2">{t("capture.history.seq")}</th><th className="pr-2">{t("capture.history.action")}</th><th className="pr-2">{t("capture.history.records")}</th><th>{t("capture.history.status")}</th>
            </tr></thead>
            <tbody>
              {q.data.map((a) => (
                <tr key={a.seq} className="border-b last:border-0 align-top" data-testid="history-row">
                  <td className="py-1 pr-2 tabular-nums">{a.seq}</td>
                  <td className="pr-2">{actLabel(t, a.action_name)}</td>
                  <td className="pr-2 tabular-nums">{a.result_refs.length}{a.result_refs.some((r) => r.reused) ? ` (${a.result_refs.filter((r) => r.reused).length} ${t("capture.history.reused")})` : ""}</td>
                  <td>{a.status === "reverted" ? t("capture.history.reverted", { at: a.reverted_at ? formatDateTime(a.reverted_at, locale) : "" }) : t("capture.history.applied")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </DialogContent>
    </Dialog>
  );
}
