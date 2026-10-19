/**
 * Dashboard API client — EP-10..EP-17 (10 §4). Typed by @aureon/shared-types
 * (single source of truth for the wire shapes). Every call attaches the bearer
 * token; real-time reads use `apiFetch` (cache: no-store).
 */
import { apiFetch } from "@/lib/api-client";
import type {
  AlertOut,
  DashboardOut,
  MetricDetailOut,
  MetricValueOut,
} from "@aureon/shared-types";

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** EP-10 GET /api/v1/dashboard — role-scoped pillars + summary + top alerts. */
export async function getDashboardApi(
  token?: string,
  periodKey?: string,
): Promise<DashboardOut> {
  const sp = new URLSearchParams();
  if (periodKey) sp.set("period_key", periodKey);
  const qs = sp.toString();
  const envelope = await apiFetch<DashboardOut>(qs ? `dashboard?${qs}` : "dashboard", {
    method: "GET",
    headers: authHeaders(token),
  });
  return envelope.data;
}

/** EP-11 GET /api/v1/metrics — flat list of in-scope metric values. */
export async function getMetricsApi(
  params: { pillar?: string; periodKey?: string } = {},
  token?: string,
): Promise<MetricValueOut[]> {
  const sp = new URLSearchParams();
  if (params.pillar) sp.set("pillar", params.pillar);
  if (params.periodKey) sp.set("period_key", params.periodKey);
  const qs = sp.toString();
  const envelope = await apiFetch<MetricValueOut[]>(qs ? `metrics?${qs}` : "metrics", {
    method: "GET",
    headers: authHeaders(token),
  });
  return envelope.data;
}

/** EP-12 GET /api/v1/metrics/{metric_code} — detail + P01 lineage panel. */
export async function getMetricDetailApi(
  metricCode: string,
  params: { periodKey?: string; history?: number } = {},
  token?: string,
): Promise<MetricDetailOut> {
  const sp = new URLSearchParams();
  if (params.periodKey) sp.set("period_key", params.periodKey);
  if (params.history !== undefined) sp.set("history", params.history.toString());
  const qs = sp.toString();
  const path = qs
    ? `metrics/${encodeURIComponent(metricCode)}?${qs}`
    : `metrics/${encodeURIComponent(metricCode)}`;
  const envelope = await apiFetch<MetricDetailOut>(path, {
    method: "GET",
    headers: authHeaders(token),
  });
  return envelope.data;
}

/** Minimal BusinessRecordOut subset the RecordPanel needs (10 §3 EP-13, 05 §4.8). */
export interface BusinessRecordBrief {
  id: string;
  record_type: string;
  code: string | null;
  name: string | null;
  period_key: string | null;
  total_amount: number | null;
  status: string | null;
  source_document_id: string | null;
  source_document_restricted: "OUT_OF_SCOPE" | "SALARY" | null;
}

/**
 * EP-13 GET /api/v1/metrics/{metric_code}/records — source records of a metric (click 2).
 * FULL access only; AGG → 403 FORBIDDEN_SCOPE. `meta.sum_check` validates the total.
 */
export async function getMetricRecordsApi(
  metricCode: string,
  params: { periodKey?: string; recordFilter?: string; page?: number; pageSize?: number } = {},
  token?: string,
): Promise<{
  data: BusinessRecordBrief[];
  meta: { total: number; sum_check?: { expected: number | null; actual: number | null } };
}> {
  const sp = new URLSearchParams();
  if (params.periodKey) sp.set("period_key", params.periodKey);
  if (params.recordFilter) sp.set("record_filter", params.recordFilter);
  if (params.page !== undefined) sp.set("page", params.page.toString());
  if (params.pageSize !== undefined) sp.set("page_size", params.pageSize.toString());
  const qs = sp.toString();
  const base = `metrics/${encodeURIComponent(metricCode)}/records`;
  const envelope = await apiFetch<
    BusinessRecordBrief[],
    { total: number; sum_check?: { expected: number | null; actual: number | null } }
  >(qs ? `${base}?${qs}` : base, { method: "GET", headers: authHeaders(token) });
  return { data: envelope.data, meta: envelope.meta ?? { total: envelope.data.length } };
}

/** EP-15 GET /api/v1/alerts — alerts in the role's receiving pillars. */
export async function getAlertsApi(
  params: { status?: string; severity?: string; page?: number; pageSize?: number } = {},
  token?: string,
): Promise<{ data: AlertOut[]; meta: { total: number; page: number; page_size: number; total_pages: number } }> {
  const sp = new URLSearchParams();
  if (params.status) sp.set("status", params.status);
  if (params.severity) sp.set("severity", params.severity);
  if (params.page !== undefined) sp.set("page", params.page.toString());
  if (params.pageSize !== undefined) sp.set("page_size", params.pageSize.toString());
  const qs = sp.toString();
  const envelope = await apiFetch<
    AlertOut[],
    { total: number; page: number; page_size: number; total_pages: number }
  >(qs ? `alerts?${qs}` : "alerts", { method: "GET", headers: authHeaders(token) });
  return { data: envelope.data, meta: envelope.meta! };
}

/** EP-16 POST /api/v1/alerts/{id}/acknowledge. */
export async function acknowledgeAlertApi(
  alertId: string,
  note: string | undefined,
  token?: string,
): Promise<AlertOut> {
  const envelope = await apiFetch<AlertOut>(`alerts/${alertId}/acknowledge`, {
    method: "POST",
    headers: authHeaders(token),
    json: note ? { note } : {},
  });
  return envelope.data;
}

/** EP-17 POST /api/v1/alerts/{id}/dismiss — `reason` required. */
export async function dismissAlertApi(
  alertId: string,
  reason: string,
  token?: string,
): Promise<AlertOut> {
  const envelope = await apiFetch<AlertOut>(`alerts/${alertId}/dismiss`, {
    method: "POST",
    headers: authHeaders(token),
    json: { reason },
  });
  return envelope.data;
}
