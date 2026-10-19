"use client";

import { useCallback, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Upload, X, CheckCircle2, AlertCircle, Loader2, UploadCloud } from "lucide-react";
import { cn } from "@/lib/utils";

/* -------------------------------------------------------------------------- */
/* Types                                                                       */
/* -------------------------------------------------------------------------- */
export type FileUploadStatus =
  | "pending"
  | "uploading"
  | "processing"
  | "done"
  | "error"
  | "duplicate";

export interface FileItem {
  id: string;
  file: File;
  status: FileUploadStatus;
  error?: string;
}

export interface DropzoneC3Props {
  files: FileItem[];
  onFilesAdded: (files: File[]) => void;
  onRemoveFile: (id: string) => void;
  docTypeHint?: string;
  onDocTypeHintChange?: (value: string) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  className?: string;
}

/* -------------------------------------------------------------------------- */
/* Constants                                                                   */
/* -------------------------------------------------------------------------- */
const ACCEPTED_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "text/csv",
  "image/jpeg",
  "image/png",
  "image/heic",
];
const MAX_SIZE_BYTES = 20 * 1024 * 1024;

const DOC_TYPE_KEYS = [
  "INVOICE",
  "SALES_REPORT",
  "KPI_OKR",
  "MEETING_MINUTES",
  "FINANCIAL_REPORT",
  "CONTRACT",
  "EMPLOYEE_LIST",
] as const;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

/* -------------------------------------------------------------------------- */
/* FileStatusIcon                                                              */
/* -------------------------------------------------------------------------- */
function FileStatusIcon({ status }: { status: FileUploadStatus }) {
  switch (status) {
    case "uploading":
    case "processing":
      return <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />;
    case "done":
      return <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden="true" />;
    case "error":
      return <AlertCircle className="h-4 w-4 text-rose-500" aria-hidden="true" />;
    case "duplicate":
      return <AlertCircle className="h-4 w-4 text-amber-500" aria-hidden="true" />;
    default:
      return <Upload className="h-4 w-4 text-muted-foreground" aria-hidden="true" />;
  }
}

/* -------------------------------------------------------------------------- */
/* DropzoneC3                                                                  */
/* -------------------------------------------------------------------------- */
export function DropzoneC3({
  files,
  onFilesAdded,
  onRemoveFile,
  docTypeHint,
  onDocTypeHintChange,
  onSubmit,
  isSubmitting,
  className,
}: DropzoneC3Props) {
  const t = useTranslations("upload");
  const tIdp = useTranslations("idp");
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = useCallback(
    (rawFiles: FileList | File[]) => {
      const valid = Array.from(rawFiles).filter(
        (f) => ACCEPTED_TYPES.includes(f.type) && f.size <= MAX_SIZE_BYTES,
      );
      if (valid.length > 0) onFilesAdded(valid);
    },
    [onFilesAdded],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  const statusText = (item: FileItem): string => {
    switch (item.status) {
      case "pending":     return t("fileItem.statusPending");
      case "uploading":   return t("fileItem.statusUploading");
      case "processing":  return t("fileItem.statusProcessing");
      case "done":        return t("fileItem.statusDone");
      case "duplicate":   return t("fileItem.statusDuplicate");
      case "error":       return t("fileItem.statusError", { message: item.error ?? "error" });
    }
  };

  const hasFiles = files.length > 0;
  const hasPending = files.some((f) => f.status === "pending");

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <p className="text-sm text-muted-foreground">{t("c3.description")}</p>

      {/* Drop zone */}
      <div
        role="region"
        aria-label={t("c3.dragPrompt")}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex min-h-[160px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-border bg-muted/30 hover:border-primary/60 hover:bg-primary/5",
        )}
      >
        <UploadCloud
          className={cn("h-10 w-10", isDragging ? "text-primary" : "text-muted-foreground")}
          aria-hidden="true"
        />
        <p className="mt-2 text-sm font-medium text-foreground">{t("c3.dragPrompt")}</p>
        <p className="text-sm text-muted-foreground">{t("c3.orText")}</p>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
          className="mt-2 rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {t("c3.browseButton")}
        </button>
        <p className="mt-3 text-xs text-muted-foreground">{t("c3.formats")}</p>
        <p className="text-xs text-muted-foreground">{t("c3.maxSize")}</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_TYPES.join(",")}
          className="sr-only"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
          aria-label={t("c3.browseButton")}
        />
      </div>

      {/* Doc type hint */}
      <div>
        <label htmlFor="c3-doc-type-hint" className="mb-1 block text-sm font-medium text-foreground">
          {t("c3.docTypeHint")}
        </label>
        <select
          id="c3-doc-type-hint"
          value={docTypeHint ?? ""}
          onChange={(e) => onDocTypeHintChange?.(e.target.value)}
          className="h-9 w-full max-w-xs rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          aria-label={t("c3.docTypeHint")}
        >
          <option value="">{tIdp("docTypeFull.none")}</option>
          {DOC_TYPE_KEYS.map((dt) => (
            <option key={dt} value={dt}>
              {tIdp(`docTypeFull.${dt}` as Parameters<typeof tIdp>[0])}
            </option>
          ))}
        </select>
      </div>

      {/* File list */}
      {hasFiles && (
        <ul className="flex flex-col gap-2" role="list" aria-label="Files to upload">
          {files.map((item) => (
            <li
              key={item.id}
              className={cn(
                "flex items-center gap-3 rounded-lg border p-3 text-sm transition-colors",
                item.status === "error"
                  ? "border-rose-200 bg-rose-50 dark:border-rose-900 dark:bg-rose-950/30"
                  : item.status === "done"
                  ? "border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30"
                  : "border-border bg-card",
              )}
              data-testid={`file-item-${item.file.name}`}
            >
              <FileStatusIcon status={item.status} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-foreground">{item.file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatBytes(item.file.size)} · {statusText(item)}
                </p>
              </div>
              {(item.status === "pending" || item.status === "error") && (
                <button
                  type="button"
                  onClick={() => onRemoveFile(item.id)}
                  className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  aria-label={t("fileItem.removeFile", { name: item.file.name })}
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Submit */}
      {hasPending && (
        <button
          type="button"
          onClick={onSubmit}
          disabled={isSubmitting}
          className="self-start inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
        >
          {isSubmitting ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Upload className="h-4 w-4" aria-hidden="true" />
          )}
          {isSubmitting ? t("c3.submitting") : t("c3.submit")}
        </button>
      )}
    </div>
  );
}
