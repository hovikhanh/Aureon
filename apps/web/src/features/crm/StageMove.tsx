"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { errorText } from "@/lib/error-text";
import { STAGES, canMoveTo } from "./crm";
import { useMoveStage } from "./use-crm";

/**
 * Move a deal's stage (CRM-PIPE-05): the keyboard / screen-reader path of the board's drag and
 * drop, and the detail page's action. Only moves the API allows are offered; Closed Lost asks for
 * the loss reason (BR-011, FR-SAL-02) before the request.
 */
export function useStageMove(onDone?: () => void) {
  const [pending, setPending] = React.useState<{ id: string; stage: string } | null>(null);
  const move = useMoveStage();
  const toast = useToast();
  const t = useTranslations();
  const run = async (deal: { id: string }, to: string, reason?: string) => {
    try {
      await move.mutateAsync({ id: deal.id, to_stage: to, lost_reason: reason });
      toast.push(t("crm.moved", { stage: t(`sales.stage.${to}` as "sales.stage.lead") }));
      onDone?.();
    } catch (e) {
      toast.push(errorText(t, e), "danger");
    }
  };
  /** Closed Lost first asks for the reason (`pending` → LostReasonDialog → `confirmLost`). */
  const request = (deal: { id: string; stage: string }, to: string) => (to === "closed_lost" ? setPending(deal) : void run(deal, to));
  const confirmLost = (reason: string) => {
    const deal = pending;
    setPending(null);
    if (deal) void run(deal, "closed_lost", reason);
  };
  return { request, pending, cancel: () => setPending(null), confirmLost, busy: move.isPending };
}

export function StageSelect({ deal, onMove, disabled, testId = "stage-select" }: { deal: { id: string; stage: string }; onMove: (to: string) => void; disabled?: boolean; testId?: string }) {
  const t = useTranslations();
  const options = STAGES.filter((s) => canMoveTo(deal.stage, s));
  if (!options.length) return null;
  return (
    <NativeSelect value="" disabled={disabled} aria-label={t("crm.moveTo")} onChange={(e) => e.target.value && onMove(e.target.value)} data-testid={testId} className="h-8 text-xs">
      <option value="">{t("crm.moveTo")}</option>
      {options.map((s) => <option key={s} value={s}>{t(`sales.stage.${s}` as "sales.stage.lead")}</option>)}
    </NativeSelect>
  );
}

export function LostReasonDialog({ open, onCancel, onConfirm }: { open: boolean; onCancel: () => void; onConfirm: (reason: string) => void }) {
  const t = useTranslations("crm");
  const [reason, setReason] = React.useState("");
  React.useEffect(() => { if (open) setReason(""); }, [open]);
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent data-testid="lost-reason-dialog">
        <DialogTitle>{t("lostTitle")}</DialogTitle>
        <DialogDescription>{t("lostHint")}</DialogDescription>
        <Input value={reason} onChange={(e) => setReason(e.target.value)} aria-label={t("lostReason")} placeholder={t("lostReason")} data-testid="lost-reason-input" />
        <div className="mt-4 flex justify-end gap-2">
          <DialogClose asChild><Button type="button" variant="ghost">{t("cancel")}</Button></DialogClose>
          <Button type="button" variant="danger" disabled={!reason.trim()} onClick={() => onConfirm(reason.trim())} data-testid="lost-reason-confirm">{t("markLost")}</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
