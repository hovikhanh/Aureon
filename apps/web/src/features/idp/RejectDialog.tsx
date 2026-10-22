"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

/** EP-32 reject — reason required. */
export function RejectDialog({ disabled, onReject }: { disabled: boolean; onReject: (reason: string) => Promise<void> }) {
  const t = useTranslations();
  const [open, setOpen] = React.useState(false);
  const [reason, setReason] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const submit = async () => {
    if (!reason.trim()) return setError(t("idp.rejectReasonRequired"));
    setBusy(true);
    try {
      await onReject(reason.trim());
      setOpen(false);
    } catch {
      setError(t("errors.generic"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => { setOpen(o); setError(null); }}>
      <DialogTrigger asChild>
        <Button variant="outline" disabled={disabled} data-testid="reject"><X className="h-4 w-4" aria-hidden />{t("buttons.reject")}</Button>
      </DialogTrigger>
      <DialogContent data-testid="reject-dialog">
        <DialogTitle>{t("idp.rejectTitle")}</DialogTitle>
        <DialogDescription className="sr-only">{t("idp.rejectReason")}</DialogDescription>
        <div className="mt-4 flex flex-col gap-1.5">
          <Label htmlFor="reject-reason">{t("idp.rejectReason")}</Label>
          <textarea id="reject-reason" value={reason} onChange={(e) => { setReason(e.target.value); setError(null); }} rows={3} maxLength={2000} aria-invalid={Boolean(error)}
            className="rounded border bg-card px-3 py-2 text-sm aria-[invalid=true]:border-danger" data-testid="reject-reason" />
          {error && <p className="text-xs text-danger">{error}</p>}
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <DialogClose asChild><Button variant="ghost">{t("buttons.cancel")}</Button></DialogClose>
          <Button variant="danger" onClick={() => void submit()} disabled={busy} data-testid="reject-confirm">{t("buttons.reject")}</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
