/**
 * EP-27 GET /api/v1/documents/{id}/source — source document presigned URL + page metadata
 * for the SourceViewer (SCR-10). Salary / scope / PII rules are enforced server-side; the
 * client only reacts to 403 FORBIDDEN_SALARY / FORBIDDEN_SCOPE (10 §4).
 */
import { apiFetch } from "@/lib/api-client";
import type { DocumentSourceOut } from "@aureon/shared-types";

export async function getDocumentSourceApi(
  documentId: string,
  params: { page?: number; disposition?: "inline" | "attachment" } = {},
  token?: string,
): Promise<DocumentSourceOut> {
  const sp = new URLSearchParams();
  if (params.page !== undefined) sp.set("page", params.page.toString());
  if (params.disposition) sp.set("disposition", params.disposition);
  const qs = sp.toString();
  const base = `documents/${documentId}/source`;
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const envelope = await apiFetch<DocumentSourceOut>(qs ? `${base}?${qs}` : base, {
    method: "GET",
    headers,
  });
  return envelope.data;
}
