"use client";

import { useCallback, useReducer } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { CheckCircle2, ArrowRight } from "lucide-react";
import { useAuth } from "@/features/auth/auth-context";
import { uploadFileApi, uploadManualApi, uploadNlApi } from "@/features/idp/idp-api";
import { cn } from "@/lib/utils";
// router is reserved for future navigation (e.g. redirect after UC-07 batch)
import { DropzoneC3, type FileItem } from "./DropzoneC3";
import { ManualFormC1 } from "./ManualFormC1";
import { NlFormC2 } from "./NlFormC2";
import { CameraCaptureC4, type CapturedPage } from "./CameraCaptureC4";

/* -------------------------------------------------------------------------- */
/* State                                                                       */
/* -------------------------------------------------------------------------- */
type Tab = "c1" | "c2" | "c3" | "c4";

interface UploadState {
  tab: Tab;
  files: FileItem[];
  docTypeHint: string;
  isSubmitting: boolean;
  isSuccess: boolean;
  error: string | null;
}

type UploadAction =
  | { type: "SET_TAB"; tab: Tab }
  | { type: "ADD_FILES"; files: File[] }
  | { type: "REMOVE_FILE"; id: string }
  | {
      type: "SET_FILE_STATUS";
      id: string;
      status: FileItem["status"];
      error?: string;
      documentId?: string;
    }
  | { type: "SET_DOC_TYPE_HINT"; value: string }
  | { type: "SET_SUBMITTING"; value: boolean }
  | { type: "SET_SUCCESS" }
  | { type: "SET_ERROR"; message: string }
  | { type: "RESET" };

function uploadReducer(state: UploadState, action: UploadAction): UploadState {
  switch (action.type) {
    case "SET_TAB":
      return { ...state, tab: action.tab, isSuccess: false, error: null };
    case "ADD_FILES":
      return {
        ...state,
        files: [
          ...state.files,
          ...action.files.map((f) => ({
            id: `${f.name}-${Date.now()}-${Math.random()}`,
            file: f,
            status: "pending" as FileItem["status"],
          })),
        ],
      };
    case "REMOVE_FILE":
      return { ...state, files: state.files.filter((f) => f.id !== action.id) };
    case "SET_FILE_STATUS":
      return {
        ...state,
        files: state.files.map((f) =>
          f.id === action.id
            ? {
                ...f,
                status: action.status,
                error: action.error,
                documentId: action.documentId ?? f.documentId,
              }
            : f,
        ),
      };
    case "SET_DOC_TYPE_HINT":
      return { ...state, docTypeHint: action.value };
    case "SET_SUBMITTING":
      return { ...state, isSubmitting: action.value };
    case "SET_SUCCESS":
      return { ...state, isSubmitting: false, isSuccess: true, error: null };
    case "SET_ERROR":
      return { ...state, isSubmitting: false, error: action.message };
    case "RESET":
      return { tab: "c3", files: [], docTypeHint: "", isSubmitting: false, isSuccess: false, error: null };
  }
}

/* -------------------------------------------------------------------------- */
/* UploadView                                                                  */
/* -------------------------------------------------------------------------- */
export function UploadView() {
  const t = useTranslations("upload");
  const { session } = useAuth();

  const [state, dispatch] = useReducer(uploadReducer, {
    tab: "c3",
    files: [],
    docTypeHint: "",
    isSubmitting: false,
    isSuccess: false,
    error: null,
  });

  /* ── C3 Upload ─────────────────────────────────────────────── */
  const handleC3Submit = useCallback(async () => {
    const pending = state.files.filter((f) => f.status === "pending");
    if (pending.length === 0) return;

    dispatch({ type: "SET_SUBMITTING", value: true });

    let anySucceeded = false;
    for (const item of pending) {
      dispatch({ type: "SET_FILE_STATUS", id: item.id, status: "uploading" });
      try {
        const doc = await uploadFileApi(
          item.file,
          {
            docTypeHint: state.docTypeHint || undefined,
            idempotencyKey: `upload-${item.id}`,
          },
          session?.accessToken,
        );
        // EP-20 returns status=UPLOADED (enqueued) or DUPLICATE (not enqueued).
        // Reflect the real server status instead of a fake timer.
        if (doc.status === "DUPLICATE") {
          dispatch({ type: "SET_FILE_STATUS", id: item.id, status: "duplicate", documentId: doc.id });
        } else {
          anySucceeded = true;
          dispatch({ type: "SET_FILE_STATUS", id: item.id, status: "done", documentId: doc.id });
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        dispatch({ type: "SET_FILE_STATUS", id: item.id, status: "error", error: msg });
      }
    }

    dispatch({ type: "SET_SUBMITTING", value: false });
    if (anySucceeded) {
      dispatch({ type: "SET_SUCCESS" });
    }
  }, [state.files, state.docTypeHint, session]);

  /* ── C1 Manual ─────────────────────────────────────────────── */
  const handleC1Submit = useCallback(
    async (docType: string, fields: Record<string, unknown>) => {
      dispatch({ type: "SET_SUBMITTING", value: true });
      try {
        await uploadManualApi(
          { doc_type: docType, fields },
          `manual-${Date.now()}`,
          session?.accessToken,
        );
        dispatch({ type: "SET_SUCCESS" });
      } catch (err) {
        dispatch({ type: "SET_ERROR", message: err instanceof Error ? err.message : "Error" });
      }
    },
    [session],
  );

  /* ── C2 NL ──────────────────────────────────────────────────── */
  // Note: EP-22 derives doc type from the text itself; docTypeHint is a UI aid only.
  const handleC2Submit = useCallback(
    async (content: string) => {
      dispatch({ type: "SET_SUBMITTING", value: true });
      try {
        await uploadNlApi(
          { text: content },
          `nl-${Date.now()}`,
          session?.accessToken,
        );
        dispatch({ type: "SET_SUCCESS" });
      } catch (err) {
        dispatch({ type: "SET_ERROR", message: err instanceof Error ? err.message : "Error" });
      }
    },
    [session],
  );

  /* ── C4 Camera ──────────────────────────────────────────────── */
  // Each captured photo is uploaded as a C4 page via EP-20 (channel=C4). Merging the
  // photos into a single multi-page document (plus deskew/blur scoring) needs an image
  // library on FE+BE and is gated behind a DEC; here we upload each page faithfully.
  const handleC4Submit = useCallback(
    async (pages: CapturedPage[]) => {
      if (pages.length === 0) return;
      dispatch({ type: "SET_SUBMITTING", value: true });
      const batchStamp = Date.now();
      let anySucceeded = false;
      try {
        for (let i = 0; i < pages.length; i++) {
          const page = pages[i];
          const file = new File([page.blob], `camera-${batchStamp}-p${i + 1}.jpg`, {
            type: "image/jpeg",
          });
          await uploadFileApi(
            file,
            { channel: "C4", idempotencyKey: `c4-${batchStamp}-${i}` },
            session?.accessToken,
          );
          anySucceeded = true;
        }
        if (anySucceeded) dispatch({ type: "SET_SUCCESS" });
      } catch (err) {
        dispatch({ type: "SET_ERROR", message: err instanceof Error ? err.message : "Error" });
      }
    },
    [session],
  );

  /* ── Success screen ─────────────────────────────────────────── */
  if (state.isSuccess) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 p-6 text-center" data-testid="upload-success">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/40">
          <CheckCircle2 className="h-8 w-8 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-foreground">{t("success.title")}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{t("success.description")}</p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/inbox"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {t("success.viewInbox")}
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
          <Link
            href="/documents"
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {t("success.viewDocuments")}
          </Link>
          <button
            type="button"
            onClick={() => dispatch({ type: "RESET" })}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {t("success.uploadMore")}
          </button>
        </div>
      </div>
    );
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "c1", label: t("tabs.c1") },
    { id: "c2", label: t("tabs.c2") },
    { id: "c3", label: t("tabs.c3") },
    { id: "c4", label: t("tabs.c4") },
  ];

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-6" data-testid="upload-view">
      {/* ── Header ─────────────────────────────────────────── */}
      <div>
        <h1 className="text-xl font-bold text-foreground">{t("title")}</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      {/* ── Error banner ───────────────────────────────────── */}
      {state.error && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
        >
          {state.error}
        </div>
      )}

      {/* ── Tab switcher ───────────────────────────────────── */}
      <div className="rounded-xl border border-border bg-card p-4 sm:p-6">
        <div className="flex border-b border-border" role="tablist" aria-label="Upload channels">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={state.tab === tab.id}
              aria-controls={`panel-${tab.id}`}
              id={`tab-${tab.id}`}
              type="button"
              onClick={() => dispatch({ type: "SET_TAB", tab: tab.id })}
              className={cn(
                "px-4 py-2.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-ring",
                state.tab === tab.id
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="mt-5">
          {/* C1 */}
          <div
            id="panel-c1"
            role="tabpanel"
            aria-labelledby="tab-c1"
            hidden={state.tab !== "c1"}
          >
            {state.tab === "c1" && (
              <ManualFormC1
                onSubmit={handleC1Submit}
                isSubmitting={state.isSubmitting}
              />
            )}
          </div>

          {/* C2 */}
          <div
            id="panel-c2"
            role="tabpanel"
            aria-labelledby="tab-c2"
            hidden={state.tab !== "c2"}
          >
            {state.tab === "c2" && (
              <NlFormC2
                onSubmit={handleC2Submit}
                isSubmitting={state.isSubmitting}
              />
            )}
          </div>

          {/* C3 */}
          <div
            id="panel-c3"
            role="tabpanel"
            aria-labelledby="tab-c3"
            hidden={state.tab !== "c3"}
          >
            {state.tab === "c3" && (
              <DropzoneC3
                files={state.files}
                onFilesAdded={(files) => dispatch({ type: "ADD_FILES", files })}
                onRemoveFile={(id) => dispatch({ type: "REMOVE_FILE", id })}
                docTypeHint={state.docTypeHint}
                onDocTypeHintChange={(v) => dispatch({ type: "SET_DOC_TYPE_HINT", value: v })}
                onSubmit={handleC3Submit}
                isSubmitting={state.isSubmitting}
              />
            )}
          </div>

          {/* C4 */}
          <div
            id="panel-c4"
            role="tabpanel"
            aria-labelledby="tab-c4"
            hidden={state.tab !== "c4"}
          >
            {state.tab === "c4" && (
              <CameraCaptureC4 onSubmit={handleC4Submit} isSubmitting={state.isSubmitting} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
