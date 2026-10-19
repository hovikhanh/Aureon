import { describe, expect, it } from "vitest";
import type { AlertOut, DashboardOut, MetricValueOut } from "@aureon/shared-types";
import { alertToCard, metricToCard, toDashboardViewModel } from "./api-to-view";

function metric(partial: Partial<MetricValueOut> & Pick<MetricValueOut, "metric_code">): MetricValueOut {
  return {
    pillar: "FIN",
    name_i18n_key: `metric.${partial.metric_code}.name`,
    unit: "VND",
    chart_type: "bar",
    access_level: "FULL",
    period_key: "2026-09",
    value: 100,
    value_state: "OK",
    not_computable_reason: null,
    display_hint: null,
    target_value: 120,
    status_color: "YELLOW",
    warning_threshold: 90,
    critical_threshold: 80,
    sparkline: [],
    computed_at: "2026-10-20T08:30:00Z",
    open_alert: null,
    ...partial,
  };
}

function alert(partial: Partial<AlertOut> & Pick<AlertOut, "alert_code" | "metric_code">): AlertOut {
  return {
    id: "a1",
    pillar: "FIN",
    severity: "CRITICAL",
    status: "OPEN",
    period_key: "2026-09",
    title_i18n_key: `alert.${partial.alert_code}.title`,
    message_params: {},
    suggestion_level: "L1",
    suggested_action_i18n_key: `alert.${partial.alert_code}.suggestion`,
    triggered_at: "2026-10-20T08:00:00Z",
    acknowledged_at: null,
    resolved_at: null,
    dismissed_at: null,
    can_acknowledge: true,
    ...partial,
  };
}

describe("dashboard api-to-view mapper (T-309)", () => {
  it("maps MetricValueOut → MetricCardProps with FE i18n key + drill-down href (P01)", () => {
    const card = metricToCard(metric({ metric_code: "METRIC-FIN-01", unit: "PERCENT" }));
    expect(card.metricCode).toBe("METRIC-FIN-01");
    expect(card.nameI18nKey).toBe("metricNames.METRIC-FIN-01");
    expect(card.formatKind).toBe("percent");
    expect(card.href).toBe("/dashboard/metrics/METRIC-FIN-01");
    expect(card.statusColor).toBe("YELLOW");
    expect(card.valueState).toBe("OK");
  });

  it("maps AlertOut → AlertCardProps carrying can_acknowledge and FE action key", () => {
    const card = alertToCard(alert({ alert_code: "ALERT-FIN-05", metric_code: "METRIC-FIN-05" }));
    expect(card.titleI18nKey).toBe("alertTitles.ALERT-FIN-05");
    expect(card.suggestedActionI18nKey).toBe("alertActions.ALERT-FIN-05");
    expect(card.canAcknowledge).toBe(true);
    expect(card.href).toBe("/dashboard/metrics/METRIC-FIN-05");
  });

  it("splits FULL vs AGG pillars and flags CEO AI summary only when all 4 pillars are FULL", () => {
    const ceo: DashboardOut = {
      role_code: "ROLE-01",
      greeting: { full_name: "A", salutation: "anh" },
      summary: { i18n_key: "dashboard.summary.has_critical", params: {}, suggestion_level: "L1" },
      pillars: (["FIN", "CUS", "OPS", "HR"] as const).map((p) => ({
        pillar: p,
        access_level: "FULL",
        health_color: "RED",
        open_alert_count: 1,
        headline_metric: metric({ metric_code: `METRIC-${p}-01`, pillar: p }),
        metrics: [metric({ metric_code: `METRIC-${p}-01`, pillar: p })],
      })),
      alerts_top: [alert({ alert_code: "ALERT-FIN-05", metric_code: "METRIC-FIN-05" })],
    };
    const vm = toDashboardViewModel(ceo);
    expect(vm.pillars).toHaveLength(4);
    expect(vm.aggPillars).toHaveLength(0);
    expect(vm.hasAISummary).toBe(true);
    expect(vm.alerts).toHaveLength(1);
  });

  it("puts AGG pillars in aggPillars and disables AI summary (non-CEO)", () => {
    const cfo: DashboardOut = {
      role_code: "ROLE-02",
      greeting: { full_name: "B", salutation: "chị" },
      summary: { i18n_key: "dashboard.summary.has_warning", params: {}, suggestion_level: "L1" },
      pillars: [
        {
          pillar: "FIN",
          access_level: "FULL",
          health_color: "RED",
          open_alert_count: 0,
          headline_metric: metric({ metric_code: "METRIC-FIN-01" }),
          metrics: [metric({ metric_code: "METRIC-FIN-01" })],
        },
        {
          pillar: "CUS",
          access_level: "AGG",
          health_color: "GREEN",
          open_alert_count: 0,
          headline_metric: metric({ metric_code: "METRIC-CUS-01", pillar: "CUS" }),
          metrics: [metric({ metric_code: "METRIC-CUS-01", pillar: "CUS" })],
        },
      ],
      alerts_top: [],
    };
    const vm = toDashboardViewModel(cfo);
    expect(vm.pillars.map((p) => p.pillar)).toEqual(["FIN"]);
    expect(vm.aggPillars.map((p) => p.pillar)).toEqual(["CUS"]);
    expect(vm.hasAISummary).toBe(false);
  });
});
