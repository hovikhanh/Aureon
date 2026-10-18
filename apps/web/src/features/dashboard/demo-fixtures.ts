import type { Pillar, RoleCode } from "@aureon/shared-types";
import type { AlertCardProps, MetricCardProps } from "./types";

/**
 * Demo fixtures for 18 metrics and 12 alerts at DEMO_REFERENCE_DATE = 2026-10-20 (08 §5.1, 03 §2).
 * All UI titles and AI actions use i18n translation keys to strictly comply with TC-UI-005.
 */

export interface PillarData {
  pillar: Pillar;
  nameKey: string;
  metrics: MetricCardProps[];
}

export const ALL_METRICS: MetricCardProps[] = [
  // Pillar FIN (6 metrics)
  {
    metricCode: "METRIC-FIN-01",
    nameI18nKey: "metricNames.METRIC-FIN-01",
    pillar: "FIN",
    formatKind: "compactCurrency",
    valueState: "OK",
    value: 8_500_000_000,
    statusColor: "YELLOW",
    periodKey: "2026-09",
    deltaRatio: -0.115,
    formulaDisplay: "8.500.000.000 / 9.600.000.000 (88,5% KH)",
    href: "/dashboard/metric/METRIC-FIN-01",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-FIN-02",
    nameI18nKey: "metricNames.METRIC-FIN-02",
    pillar: "FIN",
    formatKind: "percent",
    valueState: "OK",
    value: 0.184,
    statusColor: "GREEN",
    periodKey: "2026-09",
    deltaRatio: 0.012,
    formulaDisplay: "4.500.000.000 / 24.500.000.000",
    href: "/dashboard/metric/METRIC-FIN-02",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-FIN-03",
    nameI18nKey: "metricNames.METRIC-FIN-03",
    pillar: "FIN",
    formatKind: "months",
    valueState: "OK",
    value: 8.0,
    statusColor: "YELLOW",
    periodKey: "2026-09",
    deltaRatio: -0.05,
    formulaDisplay: "6.800.000.000 / 850.000.000",
    href: "/dashboard/metric/METRIC-FIN-03",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-FIN-04",
    nameI18nKey: "metricNames.METRIC-FIN-04",
    pillar: "FIN",
    formatKind: "days",
    valueState: "OK",
    value: 47.8,
    statusColor: "YELLOW",
    periodKey: "2026-09",
    deltaRatio: 0.045,
    formulaDisplay: "13.000.000.000 / 24.500.000.000 × 90",
    href: "/dashboard/metric/METRIC-FIN-04",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-FIN-05",
    nameI18nKey: "metricNames.METRIC-FIN-05",
    pillar: "FIN",
    formatKind: "percent",
    valueState: "OK",
    value: 0.239,
    statusColor: "RED",
    periodKey: "2026-09",
    deltaRatio: 0.062,
    formulaDisplay: "1.306.000.000 / 5.459.100.000",
    href: "/dashboard/metric/METRIC-FIN-05",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-FIN-06",
    nameI18nKey: "metricNames.METRIC-FIN-06",
    pillar: "FIN",
    formatKind: "percent",
    valueState: "OK",
    value: 0.079,
    statusColor: "YELLOW",
    periodKey: "2026-09",
    deltaRatio: 0.021,
    formulaDisplay: "(3.400.000.000 − 3.150.000.000) / 3.150.000.000",
    href: "/dashboard/metric/METRIC-FIN-06",
    computedAt: "2026-10-20T08:00:00Z",
  },

  // Pillar CUS (5 metrics)
  {
    metricCode: "METRIC-CUS-01",
    nameI18nKey: "metricNames.METRIC-CUS-01",
    pillar: "CUS",
    formatKind: "multiple",
    valueState: "OK",
    value: 0.77,
    statusColor: "RED",
    periodKey: "2026-09",
    deltaRatio: -0.15,
    formulaDisplay: "16.600.000.000 / (27.000.000.000 − 5.500.000.000)",
    href: "/dashboard/metric/METRIC-CUS-01",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-CUS-02",
    nameI18nKey: "metricNames.METRIC-CUS-02",
    pillar: "CUS",
    formatKind: "percent",
    valueState: "OK",
    value: 0.24,
    statusColor: "YELLOW",
    periodKey: "2026-09",
    deltaRatio: -0.03,
    formulaDisplay: "12 / (12 + 38)",
    href: "/dashboard/metric/METRIC-CUS-02",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-CUS-03",
    nameI18nKey: "metricNames.METRIC-CUS-03",
    pillar: "CUS",
    formatKind: "percent",
    valueState: "OK",
    value: 1.045,
    statusColor: "GREEN",
    periodKey: "2026-09",
    deltaRatio: 0.045,
    formulaDisplay: "23.300.000.000 / 22.300.000.000",
    href: "/dashboard/metric/METRIC-CUS-03",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-CUS-04",
    nameI18nKey: "metricNames.METRIC-CUS-04",
    pillar: "CUS",
    formatKind: "percent",
    valueState: "OK",
    value: 0.51,
    statusColor: "RED",
    periodKey: "2026-09",
    deltaRatio: 0.03,
    formulaDisplay: "49.980.000.000 / 98.000.000.000",
    href: "/dashboard/metric/METRIC-CUS-04",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-CUS-05",
    nameI18nKey: "metricNames.METRIC-CUS-05",
    pillar: "CUS",
    formatKind: "score",
    valueState: "OK",
    value: 32,
    statusColor: "GREEN",
    periodKey: "2026-09",
    deltaRatio: 0.02,
    formulaDisplay: "DOC-03 nps_score",
    href: "/dashboard/metric/METRIC-CUS-05",
    computedAt: "2026-10-20T08:00:00Z",
  },

  // Pillar OPS (4 metrics)
  {
    metricCode: "METRIC-OPS-01",
    nameI18nKey: "metricNames.METRIC-OPS-01",
    pillar: "OPS",
    formatKind: "percent",
    valueState: "OK",
    value: 0.6,
    statusColor: "RED",
    periodKey: "2026-09",
    deltaRatio: -0.12,
    formulaDisplay: "9 / 15 (DOC-05)",
    href: "/dashboard/metric/METRIC-OPS-01",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-OPS-02",
    nameI18nKey: "metricNames.METRIC-OPS-02",
    pillar: "OPS",
    formatKind: "count",
    valueState: "OK",
    value: 2,
    statusColor: "YELLOW",
    periodKey: "2026-09",
    deltaRatio: 1,
    formulaDisplay: "2 projects overdue <= 30d",
    href: "/dashboard/metric/METRIC-OPS-02",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-OPS-03",
    nameI18nKey: "metricNames.METRIC-OPS-03",
    pillar: "OPS",
    formatKind: "percent",
    valueState: "OK",
    value: 0.667,
    statusColor: "YELLOW",
    periodKey: "2026-09",
    deltaRatio: -0.08,
    formulaDisplay: "2 / 3 decisions due",
    href: "/dashboard/metric/METRIC-OPS-03",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-OPS-04",
    nameI18nKey: "metricNames.METRIC-OPS-04",
    pillar: "OPS",
    formatKind: "tasksPerPerson",
    valueState: "OK",
    value: 5.4,
    statusColor: "YELLOW",
    periodKey: "2026-09",
    deltaRatio: 0.05,
    formulaDisplay: "81 task / 15 assignee",
    href: "/dashboard/metric/METRIC-OPS-04",
    computedAt: "2026-10-20T08:00:00Z",
  },

  // Pillar HR (3 metrics)
  {
    metricCode: "METRIC-HR-01",
    nameI18nKey: "metricNames.METRIC-HR-01",
    pillar: "HR",
    formatKind: "vndPerPerson",
    valueState: "OK",
    value: 2_180_000_000,
    statusColor: "GREEN",
    periodKey: "2026-09",
    deltaRatio: 0.03,
    formulaDisplay: "98.000.000.000 / 45",
    href: "/dashboard/metric/METRIC-HR-01",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-HR-02",
    nameI18nKey: "metricNames.METRIC-HR-02",
    pillar: "HR",
    formatKind: "percent",
    valueState: "OK",
    value: 0.133,
    statusColor: "GREEN",
    periodKey: "2026-09",
    deltaRatio: -0.01,
    formulaDisplay: "6 / 45 headcount",
    href: "/dashboard/metric/METRIC-HR-02",
    computedAt: "2026-10-20T08:00:00Z",
  },
  {
    metricCode: "METRIC-HR-03",
    nameI18nKey: "metricNames.METRIC-HR-03",
    pillar: "HR",
    formatKind: "percent",
    valueState: "OK",
    value: 0.089,
    statusColor: "GREEN",
    periodKey: "2026-09",
    deltaRatio: -0.02,
    formulaDisplay: "(2 overloaded + 2 delayed) / 45",
    href: "/dashboard/metric/METRIC-HR-03",
    computedAt: "2026-10-20T08:00:00Z",
  },
];

/**
 * 12 alerts defined in 08 §5.1 (4 Critical + 8 Warning).
 * Sorted by severity: CRITICAL first, then WARNING (06 §4.1).
 */
export const ALL_ALERTS: AlertCardProps[] = [
  // 4 Critical Alerts
  {
    alertCode: "ALERT-FIN-05",
    metricCode: "METRIC-FIN-05",
    pillar: "FIN",
    severity: "CRITICAL",
    titleI18nKey: "alertTitles.ALERT-FIN-05",
    suggestedActionI18nKey: "alertActions.ALERT-FIN-05",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:15:00Z",
    href: "/dashboard/metric/METRIC-FIN-05",
  },
  {
    alertCode: "ALERT-CUS-01",
    metricCode: "METRIC-CUS-01",
    pillar: "CUS",
    severity: "CRITICAL",
    titleI18nKey: "alertTitles.ALERT-CUS-01",
    suggestedActionI18nKey: "alertActions.ALERT-CUS-01",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:20:00Z",
    href: "/dashboard/metric/METRIC-CUS-01",
  },
  {
    alertCode: "ALERT-CUS-04",
    metricCode: "METRIC-CUS-04",
    pillar: "CUS",
    severity: "CRITICAL",
    titleI18nKey: "alertTitles.ALERT-CUS-04",
    suggestedActionI18nKey: "alertActions.ALERT-CUS-04",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:22:00Z",
    href: "/dashboard/metric/METRIC-CUS-04",
  },
  {
    alertCode: "ALERT-OPS-01",
    metricCode: "METRIC-OPS-01",
    pillar: "OPS",
    severity: "CRITICAL",
    titleI18nKey: "alertTitles.ALERT-OPS-01",
    suggestedActionI18nKey: "alertActions.ALERT-OPS-01",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:25:00Z",
    href: "/dashboard/metric/METRIC-OPS-01",
  },

  // 8 Warning Alerts
  {
    alertCode: "ALERT-FIN-01",
    metricCode: "METRIC-FIN-01",
    pillar: "FIN",
    severity: "WARNING",
    titleI18nKey: "alertTitles.ALERT-FIN-01",
    suggestedActionI18nKey: "alertActions.ALERT-FIN-01",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:30:00Z",
    href: "/dashboard/metric/METRIC-FIN-01",
  },
  {
    alertCode: "ALERT-FIN-03",
    metricCode: "METRIC-FIN-03",
    pillar: "FIN",
    severity: "WARNING",
    titleI18nKey: "alertTitles.ALERT-FIN-03",
    suggestedActionI18nKey: "alertActions.ALERT-FIN-03",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:32:00Z",
    href: "/dashboard/metric/METRIC-FIN-03",
  },
  {
    alertCode: "ALERT-FIN-04",
    metricCode: "METRIC-FIN-04",
    pillar: "FIN",
    severity: "WARNING",
    titleI18nKey: "alertTitles.ALERT-FIN-04",
    suggestedActionI18nKey: "alertActions.ALERT-FIN-04",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:35:00Z",
    href: "/dashboard/metric/METRIC-FIN-04",
  },
  {
    alertCode: "ALERT-FIN-06",
    metricCode: "METRIC-FIN-06",
    pillar: "FIN",
    severity: "WARNING",
    titleI18nKey: "alertTitles.ALERT-FIN-06",
    suggestedActionI18nKey: "alertActions.ALERT-FIN-06",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:38:00Z",
    href: "/dashboard/metric/METRIC-FIN-06",
  },
  {
    alertCode: "ALERT-CUS-02",
    metricCode: "METRIC-CUS-02",
    pillar: "CUS",
    severity: "WARNING",
    titleI18nKey: "alertTitles.ALERT-CUS-02",
    suggestedActionI18nKey: "alertActions.ALERT-CUS-02",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:40:00Z",
    href: "/dashboard/metric/METRIC-CUS-02",
  },
  {
    alertCode: "ALERT-OPS-02",
    metricCode: "METRIC-OPS-02",
    pillar: "OPS",
    severity: "WARNING",
    titleI18nKey: "alertTitles.ALERT-OPS-02",
    suggestedActionI18nKey: "alertActions.ALERT-OPS-02",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:42:00Z",
    href: "/dashboard/metric/METRIC-OPS-02",
  },
  {
    alertCode: "ALERT-OPS-03",
    metricCode: "METRIC-OPS-03",
    pillar: "OPS",
    severity: "WARNING",
    titleI18nKey: "alertTitles.ALERT-OPS-03",
    suggestedActionI18nKey: "alertActions.ALERT-OPS-03",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:45:00Z",
    href: "/dashboard/metric/METRIC-OPS-03",
  },
  {
    alertCode: "ALERT-OPS-04",
    metricCode: "METRIC-OPS-04",
    pillar: "OPS",
    severity: "WARNING",
    titleI18nKey: "alertTitles.ALERT-OPS-04",
    suggestedActionI18nKey: "alertActions.ALERT-OPS-04",
    periodKey: "2026-09",
    triggeredAt: "2026-10-20T07:48:00Z",
    href: "/dashboard/metric/METRIC-OPS-04",
  },
];

/**
 * Filter metrics and alerts for a given role per 02 §3.1 & 06 §4.1..4.4.
 */
export function getRoleDashboardData(role: RoleCode) {
  switch (role) {
    case "ROLE-01": // CEO: 4 pillars FULL, 18 metrics, all 12 alerts
      return {
        pillars: (["FIN", "CUS", "OPS", "HR"] as Pillar[]).map((p) => ({
          pillar: p,
          nameKey: `dashboard.pillars.${p}`,
          metrics: ALL_METRICS.filter((m) => m.pillar === p),
        })),
        aggPillars: [] as PillarData[],
        alerts: ALL_ALERTS,
        hasAISummary: true,
      };

    case "ROLE-02": // CFO: FIN + OPS FULL, CUS + HR AGG
      return {
        pillars: (["FIN", "OPS"] as Pillar[]).map((p) => ({
          pillar: p,
          nameKey: `dashboard.pillars.${p}`,
          metrics: ALL_METRICS.filter((m) => m.pillar === p),
        })),
        aggPillars: (["CUS", "HR"] as Pillar[]).map((p) => ({
          pillar: p,
          nameKey: `dashboard.pillars.${p}`,
          metrics: ALL_METRICS.filter((m) =>
            p === "CUS" ? m.metricCode === "METRIC-CUS-01" : m.metricCode === "METRIC-HR-01",
          ),
        })),
        alerts: ALL_ALERTS.filter((a) => a.pillar === "FIN" || a.pillar === "OPS"),
        hasAISummary: false,
      };

    case "ROLE-03": // Sales Director: CUS FULL + METRIC-FIN-01, OPS AGG
      return {
        pillars: [
          {
            pillar: "CUS" as Pillar,
            nameKey: "dashboard.pillars.CUS",
            metrics: ALL_METRICS.filter((m) => m.pillar === "CUS"),
          },
          {
            pillar: "FIN" as Pillar,
            nameKey: "dashboard.pillars.FIN",
            metrics: ALL_METRICS.filter((m) => m.metricCode === "METRIC-FIN-01"),
          },
        ],
        aggPillars: [
          {
            pillar: "OPS" as Pillar,
            nameKey: "dashboard.pillars.OPS",
            metrics: ALL_METRICS.filter((m) => m.metricCode === "METRIC-OPS-01"),
          },
        ],
        alerts: ALL_ALERTS.filter((a) => a.pillar === "CUS"),
        hasAISummary: false,
      };

    case "ROLE-04": // HR Manager: HR + OPS FULL, FIN AGG
      return {
        pillars: (["HR", "OPS"] as Pillar[]).map((p) => ({
          pillar: p,
          nameKey: `dashboard.pillars.${p}`,
          metrics: ALL_METRICS.filter((m) => m.pillar === p),
        })),
        aggPillars: [
          {
            pillar: "FIN" as Pillar,
            nameKey: "dashboard.pillars.FIN",
            metrics: ALL_METRICS.filter((m) => m.metricCode === "METRIC-FIN-01"),
          },
        ],
        alerts: ALL_ALERTS.filter((a) => a.pillar === "HR"),
        hasAISummary: false,
      };

    default: // ROLE-05 Reviewer or others: no dashboard access (redirected to /inbox)
      return {
        pillars: [] as PillarData[],
        aggPillars: [] as PillarData[],
        alerts: [] as AlertCardProps[],
        hasAISummary: false,
      };
  }
}
