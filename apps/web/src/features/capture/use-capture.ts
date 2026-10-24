"use client";
/** D03 Capture data hooks (T-635F..T-638F) — one query per widget; contract = 10 §7.2.4. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiRequest, buildUrl, newIdempotencyKey, toApiError } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { ACTIVE_STATUSES, type CaptureDocument, type CommitOut, type DocumentAction, type DocumentType, type FormOut, type ImportPreview, type ImportRow, type InboxItem, type LineageOut, type SourceView, type UndoOut, type UndoReason } from "./types";

type Q = Record<string, string | number | boolean | null | undefined>;

/** EP-DC-13; polls every 5 s while a visible document is still in the pipeline. */
export function useInbox(params: Q, enabled = true) {
  return useQuery({
    queryKey: qk.captureInbox(params),
    enabled,
    queryFn: ({ signal }) => apiRequest<InboxItem[]>("/data-capture/inbox", { query: params, signal }),
    refetchInterval: (q) => (q.state.data?.data.some((r) => ACTIVE_STATUSES.includes(r.document.status)) ? 5000 : false),
  });
}

export function useDocTypes(includeInactive = false) {
  return useQuery({ queryKey: [...qk.captureDocTypes(), includeInactive], queryFn: ({ signal }) => api.get<DocumentType[]>("/data-capture/document-types", { include_inactive: includeInactive || undefined }, signal), staleTime: 60_000 });
}

export function useForm(type: string, enabled = true) {
  return useQuery({ queryKey: qk.captureForm(type), enabled, queryFn: ({ signal }) => api.get<FormOut>(`/data-capture/forms/${type}`, undefined, signal), retry: false });
}

/** EP-DC-02 document (file name / status / version). */
export function useDocument(id: string | null) {
  return useQuery({ queryKey: ["capture", "document", id], enabled: Boolean(id), queryFn: ({ signal }) => api.get<CaptureDocument>(`/idp/documents/${id}`, undefined, signal) });
}

export function useSource(id: string | null, page: number) {
  return useQuery({ queryKey: qk.captureSource(id ?? "", page), enabled: Boolean(id), queryFn: ({ signal }) => api.get<SourceView>(`/data-capture/documents/${id}/source`, { page }, signal), retry: false, staleTime: 4 * 60_000 });
}

export function useActions(id: string | null) {
  return useQuery({ queryKey: qk.captureActions(id ?? ""), enabled: Boolean(id), queryFn: ({ signal }) => api.get<DocumentAction[]>(`/data-capture/documents/${id}/actions`, undefined, signal) });
}

export function useLineage(entity: string, id: string, enabled: boolean) {
  return useQuery({ queryKey: qk.lineage(entity, id), enabled, queryFn: ({ signal }) => api.get<LineageOut>(`/lineage/${entity}/${id}`, undefined, signal), retry: false });
}

export function useImport(id: string) {
  return useQuery({ queryKey: qk.captureImport(id), queryFn: ({ signal }) => api.get<ImportPreview>(`/data-capture/imports/${id}`, undefined, signal), retry: false });
}

export function useImportRows(id: string, params: Q, enabled = true) {
  return useQuery({ queryKey: qk.captureImportRows(id, params), enabled, queryFn: ({ signal }) => apiRequest<ImportRow[]>(`/data-capture/imports/${id}/rows`, { query: params, signal }) });
}

/** Multipart POST through the BFF (EP-DC-01 `files`, EP-DC-17 `file`). */
export async function postMultipart<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(buildUrl(path), { method: "POST", body: form, headers: { "idempotency-key": newIdempotencyKey() }, credentials: "same-origin" });
  if (!res.ok) throw await toApiError(res);
  return ((await res.json()) as { data: T }).data;
}

/** EP-DC-21 — streams the error workbook to a download. */
export async function downloadErrorFile(batchId: string): Promise<void> {
  const res = await fetch(buildUrl(`/data-capture/imports/${batchId}/error-file`), { credentials: "same-origin" });
  if (!res.ok) throw await toApiError(res);
  const name = /filename="?([^";]+)"?/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? "errors.xlsx";
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}

export const undoDocument = (id: string, reason: string, reason_code: UndoReason) => api.post<UndoOut>(`/data-capture/documents/${id}/undo`, { reason, reason_code });
export const commitDocument = (id: string, version: number | undefined) => api.post<CommitOut>(`/data-capture/documents/${id}/commit`, { version });

/** Undo (EP-DC-24) + refresh every capture / work / goals / org view the document wrote into. */
export function useUndo() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; reason: string; reason_code: UndoReason }) => undoDocument(v.id, v.reason, v.reason_code),
    onSuccess: () => invalidateWrites(client),
  });
}

export function invalidateWrites(client: ReturnType<typeof useQueryClient>) {
  for (const k of ["capture", "idp", "org", "work", "goals", "lineage", "hr"]) void client.invalidateQueries({ queryKey: [k] });
}
