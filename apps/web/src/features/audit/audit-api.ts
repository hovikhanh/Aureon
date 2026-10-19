import type { AuditLogOut, PageMeta } from "@aureon/shared-types";
import { apiFetch } from "@/lib/api-client";

/* -------------------------------------------------------------------------- */
/* EP-52 GET /api/v1/audit-logs — audit log list (ROLE-01; SCR-14).           */
/* -------------------------------------------------------------------------- */

export interface AuditLogFilters {
  page?: number;
  pageSize?: number;
  actorType?: string;
  actorUserId?: string;
  action?: string;
  targetType?: string;
  sourceDocumentId?: string;
  from?: string;
  to?: string;
}

export async function getAuditLogsApi(
  filters: AuditLogFilters = {},
  token?: string,
): Promise<{ data: AuditLogOut[]; meta: PageMeta }> {
  const sp = new URLSearchParams();
  if (filters.page !== undefined) sp.set("page", filters.page.toString());
  if (filters.pageSize !== undefined) sp.set("page_size", filters.pageSize.toString());
  if (filters.actorType && filters.actorType !== "ALL") sp.set("actor_type", filters.actorType);
  if (filters.actorUserId) sp.set("actor_user_id", filters.actorUserId);
  if (filters.action?.trim()) sp.set("action", filters.action.trim());
  if (filters.targetType) sp.set("target_type", filters.targetType);
  if (filters.sourceDocumentId) sp.set("source_document_id", filters.sourceDocumentId);
  if (filters.from) sp.set("from", filters.from);
  if (filters.to) sp.set("to", filters.to);

  const qs = sp.toString();
  const path = qs ? `audit-logs?${qs}` : "audit-logs";
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const envelope = await apiFetch<AuditLogOut[], PageMeta>(path, {
    method: "GET",
    headers,
  });
  return { data: envelope.data, meta: envelope.meta! };
}
