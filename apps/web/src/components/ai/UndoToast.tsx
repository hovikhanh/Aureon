"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Undo2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { createUndoTimer, UNDO_TOAST_MS } from "./undo-timer";

/**
 * UndoToast (06 §5.1): shown right after a write; 10 s, paused on hover/focus. "Hoàn tác" calls
 * `onUndo` (EP-DC-24 for capture documents); after the toast closes, undo stays available from
 * the inbox until `undo_deadline` (7 days, DEC-134).
 */
export function UndoToast({ message, onUndo, onClose, ms = UNDO_TOAST_MS }: { message: string; onUndo: () => Promise<void>; onClose: () => void; ms?: number }) {
  const t = useTranslations("capture.undo");
  const [busy, setBusy] = React.useState(false);
  const close = React.useRef(onClose);
  close.current = onClose;
  const timer = React.useMemo(() => createUndoTimer(() => close.current(), ms), [ms]);
  React.useEffect(() => {
    timer.start();
    return () => timer.cancel();
  }, [timer]);
  const undo = async () => {
    timer.cancel();
    setBusy(true);
    try {
      await onUndo();
    } finally {
      setBusy(false);
      close.current();
    }
  };
  return (
    <div role="status" aria-live="polite" data-testid="undo-toast"
      className="fixed bottom-4 left-1/2 z-[60] flex -translate-x-1/2 items-center gap-3 rounded-lg border bg-card px-4 py-3 text-sm shadow-lg"
      onMouseEnter={() => timer.pause("hover")} onMouseLeave={() => timer.resume("hover")}
      onFocus={() => timer.pause("focus")} onBlur={() => timer.resume("focus")}>
      <span>{message}</span>
      <Button size="sm" variant="outline" onClick={() => void undo()} disabled={busy} data-testid="undo-toast-action">
        <Undo2 className="h-4 w-4" aria-hidden />{t("toastAction")}
      </Button>
      <button type="button" className="rounded p-1 text-muted-foreground hover:bg-muted" aria-label={t("toastClose")} onClick={() => { timer.cancel(); close.current(); }}>
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  );
}
