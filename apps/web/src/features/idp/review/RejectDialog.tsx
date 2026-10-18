"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AlertCircle, X } from "lucide-react";

export interface RejectDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reasonCode: string, note?: string) => Promise<void>;
  isSubmitting?: boolean;
}

export function RejectDialog({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting = false,
}: RejectDialogProps) {
  const t = useTranslations("review.rejectDialog");
  const [reasonCode, setReasonCode] = useState<string>("WRONG_DATA");
  const [note, setNote] = useState<string>("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (reasonCode === "OTHER" && !note.trim()) {
      return;
    }
    await onConfirm(reasonCode, note.trim() || undefined);
  };

  const isNoteRequired = reasonCode === "OTHER";
  const canSubmit = !isNoteRequired || note.trim().length > 0;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reject-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-xs p-4"
    >
      <div className="relative w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg animate-in fade-in-0 zoom-in-95">
        <button
          type="button"
          onClick={onClose}
          disabled={isSubmitting}
          className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          aria-label="close-dialog"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>

        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-rose-100 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400">
            <AlertCircle className="h-5 w-5" aria-hidden="true" />
          </div>
          <div>
            <h2 id="reject-dialog-title" className="text-lg font-semibold text-foreground">
              {t("title")}
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {t("description")}
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label
              htmlFor="reject-reason-select"
              className="block text-xs font-medium text-foreground mb-1"
            >
              {t("reasonLabel")}
            </label>
            <select
              id="reject-reason-select"
              value={reasonCode}
              onChange={(e) => setReasonCode(e.target.value)}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="WRONG_DATA">{t("reasons.WRONG_DATA")}</option>
              <option value="WRONG_DOC_TYPE">{t("reasons.WRONG_DOC_TYPE")}</option>
              <option value="UNREADABLE">{t("reasons.UNREADABLE")}</option>
              <option value="DUPLICATE_BUSINESS">{t("reasons.DUPLICATE_BUSINESS")}</option>
              <option value="SUSPICIOUS_CONTENT">{t("reasons.SUSPICIOUS_CONTENT")}</option>
              <option value="OTHER">{t("reasons.OTHER")}</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="reject-note-input"
              className="block text-xs font-medium text-foreground mb-1"
            >
              {t("noteLabel")} {isNoteRequired && <span className="text-rose-500">*</span>}
            </label>
            <textarea
              id="reject-note-input"
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder={t("notePlaceholder")}
              required={isNoteRequired}
              className="w-full rounded-md border border-input bg-background p-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-md border border-border bg-background px-4 py-2 text-xs font-medium text-foreground hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {t("cancel")}
            </button>
            <button
              type="submit"
              disabled={!canSubmit || isSubmitting}
              className="inline-flex items-center justify-center rounded-md bg-rose-600 px-4 py-2 text-xs font-medium text-white hover:bg-rose-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-rose-500"
            >
              {isSubmitting ? "..." : t("confirm")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
