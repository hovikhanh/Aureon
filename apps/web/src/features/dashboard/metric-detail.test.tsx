import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, screen, waitFor } from "@testing-library/react";
import type { MetricDetailOut } from "@aureon/shared-types";
import { renderWithIntl } from "@/test/render";
import { MetricDetailView } from "./MetricDetailView";

vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => ({ session: { accessToken: "tok" }, role: "ROLE-01" }),
}));

const getMetricDetailApi = vi.fn();
const getMetricRecordsApi = vi.fn();
vi.mock("./dashboard-api", () => ({
  getMetricDetailApi: (...a: unknown[]) => getMetricDetailApi(...a),
  getMetricRecordsApi: (...a: unknown[]) => getMetricRecordsApi(...a),
}));

function detail(overrides: Partial<MetricDetailOut> = {}): MetricDetailOut {
  return {
    metric: {
      metric_code: "METRIC-FIN-01",
      pillar: "FIN",
      name_i18n_key: "metric.METRIC-FIN-01.name",
      unit: "VND",
      chart_type: "bar",
      access_level: "FULL",
      period_key: "2026-09",
      value: 8_500_000_000,
      value_state: "OK",
      not_computable_reason: null,
      display_hint: null,
      target_value: 9_600_000_000,
      status_color: "YELLOW",
      warning_threshold: 90,
      critical_threshold: 80,
      sparkline: [],
      computed_at: "2026-10-20T08:30:00Z",
      open_alert: null,
    },
    lineage_panel: {
      formula_display: "8.500.000.000 / 9.600.000.000 (88,5% KH)",
      formula_expr: "revenue / target",
      source_record_types: ["INVOICE"],
      computed_at: "2026-10-20T08:30:00Z",
      computation: "SEED",
      source_record_count: 0,
      source_documents: [],
    },
    computation_inputs: null,
    history: [
      { period_key: "2026-08", value: 9_000_000_000, target_value: 9_600_000_000, value_state: "OK", status_color: "YELLOW" },
      { period_key: "2026-09", value: 8_500_000_000, target_value: 9_600_000_000, value_state: "OK", status_color: "YELLOW" },
    ],
    breakdown: null,
    alert: null,
    ...overrides,
  };
}

describe("SCR-09 MetricDetailView (06 §4.6, EP-12/EP-13, T-310)", () => {
  afterEach(() => {
    cleanup();
    getMetricDetailApi.mockReset();
    getMetricRecordsApi.mockReset();
  });

  it("renders header, lineage panel (P01) and trend for a FULL metric", async () => {
    getMetricDetailApi.mockResolvedValue(detail());
    getMetricRecordsApi.mockResolvedValue({ data: [], meta: { total: 0 } });

    renderWithIntl(<MetricDetailView metricCode="METRIC-FIN-01" />);

    await waitFor(() => expect(screen.getByText("Doanh thu tháng")).toBeInTheDocument());
    // Lineage formula (P01 #1)
    expect(screen.getByText(/88,5% KH/)).toBeInTheDocument();
    // Lineage panel heading (data source)
    expect(screen.getByRole("heading", { name: /Nguồn dữ liệu/i })).toBeInTheDocument();
    // RecordPanel empty state (seed has no source_record_ids yet)
    expect(screen.getByText(/Chưa có bản ghi nguồn/i)).toBeInTheDocument();
  });

  it("shows the aggregate-only notice and skips records when access is AGG", async () => {
    const agg = detail();
    agg.metric.access_level = "AGG";
    getMetricDetailApi.mockResolvedValue(agg);

    renderWithIntl(<MetricDetailView metricCode="METRIC-FIN-01" />);

    await waitFor(() => expect(screen.getByText("Doanh thu tháng")).toBeInTheDocument());
    expect(screen.getByText(/quyền xem tổng hợp/i)).toBeInTheDocument();
    expect(getMetricRecordsApi).not.toHaveBeenCalled();
  });

  it("renders a graceful error state when the detail request fails", async () => {
    getMetricDetailApi.mockRejectedValue(new Error("boom"));

    renderWithIntl(<MetricDetailView metricCode="METRIC-FIN-01" />);

    await waitFor(() =>
      expect(screen.getByText(/Không tải được chi tiết chỉ số/i)).toBeInTheDocument(),
    );
  });
});
