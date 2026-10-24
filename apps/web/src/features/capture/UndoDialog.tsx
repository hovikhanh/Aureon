"use client";
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { UNDO_REASONS, type UndoReason } from "./types";
import { useUndo } from "./use-capture";
import { captureError } from "./errors";

/** UndoDialog (SCR-45): reason + reason_code → EP-DC-24; 409 lists the edited records, 410 = expired. */
export function UndoDialog({ documentId, deadline, open, onClose }: { documentId: string; deadline: string | null; open: boolean; onClose: () => void }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const toast = useToast();
  const undo = useUndo();
  const [reason, setReason] = React.useState("");
  const [code, setCode] = React.useState<UndoReason>("mistake");
  const [error, setError] = React.useState<string | null>(null);
  const [conflicts, setConflicts] = React.useState<{ table: string; id: string }[]>([]);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) return setError(t("capture.undo.reasonRequired"));
    setError(null);
    try {
      const out = await undo.mutateAsync({ id: documentId, reason: reason.trim(), reason_code: code });
      toast.push(t("capture.undo.done", { count: out.reverted_actions.length }));
      onClose();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409 && Array.isArray(err.details.conflicts)) setConflicts(err.details.conflicts as { table: string; id: string }[]);
      else setError(captureError(t, err));
    }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="undo-dialog">
        <DialogTitle>{t("capture.undo.title")}</DialogTitle>
        <DialogDescription>{t("capture.undo.body", { deadline: deadline ? formatDateTime(deadline, locale) : "—" })}</DialogDescription>
        {conflicts.length > 0 ? (
          <div role="alert" className="rounded border border-warning bg-warning-subtle p-3 text-sm" data-testid="undo-conflicts">
            <p className="font-medium">{t("capture.undo.conflictTitle")}</p>
            <p className="mt-1">{t("capture.undo.conflictBody")}</p>
            <ul className="mt-2 list-disc pl-5 font-mono text-xs">{conflicts.map((c) => <li key={`${c.table}:${c.id}`}>{c.table} · {c.id}</li>)}</ul>
          </div>
        ) : (
          <form className="flex flex-col gap-3" onSubmit={(e) => void submit(e)}>
            <Label className="flex flex-col gap-1">{t("capture.undo.reasonCode")}
              <NativeSelect value={code} onChange={(e) => setCode(e.target.value as UndoReason)} data-testid="undo-reason-code">
                {UNDO_REASONS.map((r) => <option key={r} value={r}>{t(`capture.undo.code.${r}`)}</option>)}
              </NativeSelect>
            </Label>
            <Label className="flex flex-col gap-1">{t("capture.undo.reason")}
              <textarea className="min-h-20 rounded-md border bg-card px-3 py-2 text-sm" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500}
                aria-invalid={Boolean(error)} aria-describedby={error ? "undo-err" : undefined} data-testid="undo-reason" />
            </Label>
            {error && <p id="undo-err" role="alert" className="text-sm text-danger">{error}</p>}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={onClose}>{t("buttons.cancel")}</Button>
              <Button type="submit" variant="danger" disabled={undo.isPending} data-testid="undo-confirm">{t("capture.undo.confirm")}</Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
