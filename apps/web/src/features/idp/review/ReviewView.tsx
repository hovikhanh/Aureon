"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  LogOut,
  Keyboard,
  AlertTriangle,
} from "lucide-react";
import type {
  DocType,
  ExtractedFieldOut,
} from "@aureon/shared-types";
import { AIStateBadge } from "@/components/ai/AIStateBadge";
import { cn } from "@/lib/utils";
import { ExtractionForm } from "./ExtractionForm";
import { RejectDialog } from "./RejectDialog";
import { ShortcutsModal } from "./ShortcutsModal";
import type { FieldEditState, ReviewViewProps } from "./types";

/* -------------------------------------------------------------------------- */
/* State management via useReducer                                             */
/* -------------------------------------------------------------------------- */
type ReviewAction =
  | { type: "SELECT_FIELD"; fieldId: string }
  | { type: "CHANGE_VALUE"; fieldId: string; value: unknown }
  | { type: "CONFIRM_FIELD"; fieldId: string }
  | { type: "REVERT_FIELD"; fieldId: string; originalValue: unknown }
  | { type: "TOGGLE_CONFLICT"; rule: string; note: string }
  | { type: "CHANGE_DOC_TYPE"; docType: DocType };

interface ReviewLocalState {
  selectedFieldId: string | null;
  docType: DocType;
  fieldEdits: Record<string, FieldEditState>;
  acceptedConflicts: { rule: string; note: string }[];
}

function buildInitialEdits(fields: ExtractedFieldOut[]): Record<string, FieldEditState> {
  const edits: Record<string, FieldEditState> = {};
  for (const f of fields) {
    edits[f.id] = {
      fieldId: f.id,
      originalValue: f.final_value ?? f.value,
      currentValue: f.final_value ?? f.value,
      isCorrected: f.corrected,
      isConfirmed: f.confidence_band === "HIGH",
    };
  }
  return edits;
}

function reviewReducer(state: ReviewLocalState, action: ReviewAction): ReviewLocalState {
  switch (action.type) {
    case "SELECT_FIELD":
      return { ...state, selectedFieldId: action.fieldId };

    case "CHANGE_VALUE": {
      const prev = state.fieldEdits[action.fieldId];
      if (!prev) return state;
      const isCorrected = action.value !== prev.originalValue;
      return {
        ...state,
        fieldEdits: {
          ...state.fieldEdits,
          [action.fieldId]: { ...prev, currentValue: action.value, isCorrected, isConfirmed: true },
        },
      };
    }

    case "CONFIRM_FIELD": {
      const prev = state.fieldEdits[action.fieldId];
      if (!prev) return state;
      return {
        ...state,
        fieldEdits: {
          ...state.fieldEdits,
          [action.fieldId]: { ...prev, isConfirmed: true },
        },
      };
    }

    case "REVERT_FIELD": {
      const prev = state.fieldEdits[action.fieldId];
      if (!prev) return state;
      return {
        ...state,
        fieldEdits: {
          ...state.fieldEdits,
          [action.fieldId]: {
            ...prev,
            currentValue: action.originalValue,
            isCorrected: false,
            isConfirmed: prev.originalValue !== null && prev.originalValue !== undefined,
          },
        },
      };
    }

    case "TOGGLE_CONFLICT": {
      const existing = state.acceptedConflicts.find((c) => c.rule === action.rule);
      if (existing) {
        if (action.note === "") {
          return {
            ...state,
            acceptedConflicts: state.acceptedConflicts.filter((c) => c.rule !== action.rule),
          };
        }
        return {
          ...state,
          acceptedConflicts: state.acceptedConflicts.map((c) =>
            c.rule === action.rule ? { rule: action.rule, note: action.note } : c,
          ),
        };
      }
      return {
        ...state,
        acceptedConflicts: [...state.acceptedConflicts, { rule: action.rule, note: action.note }],
      };
    }

    case "CHANGE_DOC_TYPE":
      return { ...state, docType: action.docType };

    default:
      return state;
  }
}

/* -------------------------------------------------------------------------- */
/* Lock Timer sub-component                                                    */
/* -------------------------------------------------------------------------- */
function LockTimer({ expiresAt }: { expiresAt: Date }) {
  const t = useTranslations("review");
  const [remaining, setRemaining] = useState(() =>
    Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000)),
  );

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining(Math.max(0, Math.floor((expiresAt.getTime() - Date.now()) / 1000)));
    }, 1000);
    return () => clearInterval(interval);
  }, [expiresAt]);

  const minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
  const seconds = String(remaining % 60).padStart(2, "0");
  const isExpiringSoon = remaining < 120;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium tabular-nums",
        isExpiringSoon
          ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
          : "bg-muted text-muted-foreground",
      )}
      title={isExpiringSoon ? t("lockExpiresSoon") : undefined}
    >
      {t("lockTimer", { minutes, seconds })}
    </span>
  );
}

/* -------------------------------------------------------------------------- */
/* Source Viewer placeholder (T-220 will replace with real PDF viewer)        */
/* -------------------------------------------------------------------------- */
function SourceViewerPlaceholder({
  filename,
  channel,
}: {
  filename: string | null;
  channel: string;
}) {
  const t = useTranslations("review");

  return (
    <div className="flex h-full min-h-[400px] flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/30 p-8 text-center">
      {channel === "C1" ? (
        <p className="text-sm text-muted-foreground">{t("noSourceFile")}</p>
      ) : (
        <div className="space-y-2">
          <div className="text-4xl select-none">📄</div>
          <p className="text-sm font-medium text-foreground">{filename}</p>
          <p className="text-xs text-muted-foreground">{t("sourceViewerSubtitle", { page: 1, totalPages: 1 })}</p>
          <p className="mt-4 text-xs text-muted-foreground/70">
            {/* T-220: SourceViewer with PDF/Image/Excel highlight replaces this area */}
            Source Viewer (PDF/Image) — T-220
          </p>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* ReviewView — main component                                                  */
/* -------------------------------------------------------------------------- */
export function ReviewView({
  document,
  reviewId,
  extraction,
  role,
  onApprove,
  onReject,
  onRelease,
  onChangeDocType,
  onFieldCorrect,
  onFieldConfirm,
}: ReviewViewProps) {
  const t = useTranslations("review");
  const router = useRouter();

  const [isRejectOpen, setIsRejectOpen] = useState(false);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant: "success" | "error" } | null>(
    null,
  );

  const lockExpiresAt = useRef(new Date(Date.now() + 15 * 60 * 1000));

  const [state, dispatch] = useReducer(reviewReducer, {
    selectedFieldId: null,
    docType: (document.doc_type ?? "INVOICE") as DocType,
    fieldEdits: buildInitialEdits(extraction.fields),
    acceptedConflicts: [],
  });

  // reviewId is used via the parent's onApprove/onReject closures; suppress unused warning
  void reviewId;

  // Parse cross-doc conflicts from extraction result
  const crossDocConflicts: { rule: string; message: string }[] = Object.entries(
    extraction.cross_doc_results ?? [],
  )
    .filter((entry): entry is [string, { match: boolean; message: string }] =>
      typeof (entry[1] as { match: boolean }).match === "boolean" &&
      !(entry[1] as { match: boolean }).match,
    )
    .map(([rule, val]) => ({ rule, message: (val as { message: string }).message ?? rule }));

  // Auto-focus first field needing attention
  useEffect(() => {
    const firstNeedingAttention = extraction.fields.find(
      (f) => f.confidence_band === "LOW" || f.confidence_band === "MEDIUM",
    );
    if (firstNeedingAttention) {
      dispatch({ type: "SELECT_FIELD", fieldId: firstNeedingAttention.id });
    } else if (extraction.fields[0]) {
      dispatch({ type: "SELECT_FIELD", fieldId: extraction.fields[0].id });
    }
  }, [extraction.fields]);

  // Keyboard shortcuts (06 §4.3)
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Ctrl+Enter → Approve
      if (e.ctrlKey && e.key === "Enter" && !isRejectOpen && !isSubmitting) {
        e.preventDefault();
        handleApprove();
        return;
      }
      // Ctrl+Backspace → Reject
      if (e.ctrlKey && e.key === "Backspace" && !isSubmitting) {
        e.preventDefault();
        setIsRejectOpen(true);
        return;
      }
      // Escape → release/close
      if (e.key === "Escape" && !isRejectOpen && !isShortcutsOpen) {
        onRelease?.();
        router.push("/inbox");
        return;
      }
      // ? → toggle shortcuts
      if (e.key === "?" && !isRejectOpen) {
        e.preventDefault();
        setIsShortcutsOpen((v) => !v);
        return;
      }
      // J → next field, K → prev field
      if (!isRejectOpen && (e.key === "j" || e.key === "k")) {
        const idx = extraction.fields.findIndex((f) => f.id === state.selectedFieldId);
        if (idx === -1) return;
        const next =
          e.key === "j"
            ? extraction.fields[idx + 1]?.id
            : extraction.fields[idx - 1]?.id;
        if (next) dispatch({ type: "SELECT_FIELD", fieldId: next });
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isRejectOpen, isShortcutsOpen, isSubmitting, state.selectedFieldId, extraction.fields],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const showToast = (message: string, variant: "success" | "error") => {
    setToast({ message, variant });
    setTimeout(() => setToast(null), 4000);
  };

  const handleApprove = async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    showToast(t("toast.approving"), "success");
    try {
      await onApprove(state.acceptedConflicts);
      showToast(t("toast.approved", { metrics: "" }), "success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      showToast(t("toast.error", { message: msg }), "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmReject = async (reasonCode: string, note?: string) => {
    setIsSubmitting(true);
    showToast(t("toast.rejecting"), "error");
    try {
      await onReject(reasonCode, note);
      showToast(t("toast.rejected"), "success");
      setIsRejectOpen(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      showToast(t("toast.error", { message: msg }), "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRelease = async () => {
    await onRelease?.();
    router.push("/inbox");
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col overflow-hidden">
      {/* ── Top Bar ─────────────────────────────────────────────────── */}
      <div className="flex shrink-0 items-center gap-3 border-b border-border bg-card px-4 py-2.5">
        <Link
          href="/inbox"
          className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          onClick={() => onRelease?.()}
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          <span>{t("backToInbox")}</span>
        </Link>

        <div className="mx-1 h-4 w-px bg-border" aria-hidden="true" />

        <div className="flex min-w-0 flex-1 items-center gap-2">
          <h1 className="truncate text-sm font-semibold text-foreground">
            {document.original_filename}
          </h1>
          <AIStateBadge level={document.ai_state ?? "L2"} aria-label={t("aiBadgeLabel")} />
          {crossDocConflicts.length > 0 && (
            <span
              className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
              title={t("conflictBanner")}
            >
              <AlertTriangle className="h-3 w-3" aria-hidden="true" />
              XD
            </span>
          )}
        </div>

        <LockTimer expiresAt={lockExpiresAt.current} />

        {/* Shortcuts help */}
        <button
          type="button"
          onClick={() => setIsShortcutsOpen(true)}
          className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border text-muted-foreground hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
          title={t("actions.shortcuts")}
          aria-label={t("actions.shortcuts")}
        >
          <Keyboard className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      {/* ── 2-column Content ─────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left ≈55%: Source Viewer */}
        <div className="flex w-[55%] shrink-0 flex-col overflow-hidden border-r border-border p-3">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {t("sourceViewerTitle")}
          </h2>
          <div className="flex-1 overflow-auto">
            <SourceViewerPlaceholder
              filename={document.original_filename}
              channel={document.channel}
            />
          </div>
        </div>

        {/* Right ≈45%: Extraction Form */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-3">
            <ExtractionForm
              fields={extraction.fields}
              fieldEdits={state.fieldEdits}
              selectedFieldId={state.selectedFieldId}
              docType={state.docType}
              crossDocConflicts={crossDocConflicts}
              acceptedConflicts={state.acceptedConflicts}
              onSelectField={(id) => dispatch({ type: "SELECT_FIELD", fieldId: id })}
              onChangeFieldValue={(id, val) => {
                dispatch({ type: "CHANGE_VALUE", fieldId: id, value: val });
                onFieldCorrect?.(id, val);
              }}
              onConfirmField={(id) => {
                dispatch({ type: "CONFIRM_FIELD", fieldId: id });
                onFieldConfirm?.(id);
              }}
              onRevertField={(id) =>
                dispatch({
                  type: "REVERT_FIELD",
                  fieldId: id,
                  originalValue: state.fieldEdits[id]?.originalValue,
                })
              }
              onChangeDocType={(dt) => {
                dispatch({ type: "CHANGE_DOC_TYPE", docType: dt });
                onChangeDocType?.(dt);
              }}
              onToggleAcceptConflict={(rule, note) =>
                dispatch({ type: "TOGGLE_CONFLICT", rule, note })
              }
            />
          </div>

          {/* Bottom Actions */}
          <div className="shrink-0 border-t border-border bg-card px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              {/* Release */}
              <button
                type="button"
                onClick={handleRelease}
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              >
                <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
                <span>{t("actions.release")}</span>
              </button>

              <div className="flex items-center gap-2">
                {/* Reject */}
                {role !== "ROLE-01" && (
                  <button
                    type="button"
                    onClick={() => setIsRejectOpen(true)}
                    disabled={isSubmitting}
                    className="inline-flex items-center gap-1.5 rounded-md bg-rose-50 border border-rose-200 px-4 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100 dark:bg-rose-950/30 dark:border-rose-900/60 dark:text-rose-400 focus:outline-none focus:ring-2 focus:ring-rose-400 disabled:opacity-50"
                    aria-label={t("actions.reject")}
                  >
                    <XCircle className="h-4 w-4" aria-hidden="true" />
                    <span>{t("actions.reject")}</span>
                  </button>
                )}

                {/* Approve */}
                {role !== "ROLE-01" && (
                  <button
                    type="button"
                    onClick={handleApprove}
                    disabled={isSubmitting}
                    className="inline-flex items-center gap-1.5 rounded-md bg-primary px-5 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                    aria-label={t("actions.approve")}
                  >
                    {isSubmitting ? (
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                    )}
                    <span>{t("actions.approve")}</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Toast ─────────────────────────────────────────────────────── */}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          className={cn(
            "fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-lg border px-4 py-3 text-sm font-medium shadow-lg animate-in slide-in-from-bottom-2",
            toast.variant === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/80 dark:text-emerald-300"
              : "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950/80 dark:text-rose-300",
          )}
        >
          {toast.message}
        </div>
      )}

      {/* ── Dialogs ───────────────────────────────────────────────────── */}
      <RejectDialog
        isOpen={isRejectOpen}
        onClose={() => setIsRejectOpen(false)}
        onConfirm={handleConfirmReject}
        isSubmitting={isSubmitting}
      />
      <ShortcutsModal isOpen={isShortcutsOpen} onClose={() => setIsShortcutsOpen(false)} />
    </div>
  );
}
