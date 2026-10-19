/**
 * Map API DTOs (10 §3: DashboardOut / MetricValueOut / AlertOut) into the view-model
 * shapes the dashboard presentation components consume (MetricCardProps / AlertCardProps /
 * PillarData). Keeping this translation in one place lets DashboardView stay declarative and
 * lets the same components render either live API data or the demo fixtures.
 *
 * i18n keys are derived from the stable `metric_code` / `alert_code` (06 §7.2) so the UI never
 * depends on server-provided display strings (TC-UI-005, no hard-coded Vietnamese).
 */
import type { AlertOut, DashboardOut, MetricValueOut, Pillar } from "@aureon/shared-types";
import type { AlertCardProps, MetricCardProps } from "./types";
import { UNIT_FORMAT_KIND } from "./types";

export interface PillarData {
  pillar: Pillar;
  nameKey: string;
  metrics: MetricCardProps[];
}

export interface DashboardViewModel {
  pillars: PillarData[];
  aggPillars: PillarData[];
  alerts: AlertCardProps[];
  hasAISummary: boolean;
  summary?: DashboardOut["summary"];
  greeting?: DashboardOut["greeting"];
}

/** Map one MetricValueOut (10 §3) → MetricCardProps (href = SCR-09 drill-down, P01). */
export function metricToCard(m: MetricValueOut): MetricCardProps {
  return {
    metricCode: m.metric_code,
    nameI18nKey: `metricNames.${m.metric_code}`,
    pillar: m.pillar,
    formatKind: UNIT_FORMAT_KIND[m.unit],
    valueState: m.value_state,
    value: m.value,
    statusColor: m.status_color,
    notComputableReason: m.not_computable_reason as MetricCardProps["notComputableReason"],
    displayHint: m.display_hint as MetricCardProps["displayHint"],
    periodKey: m.period_key,
    href: `/dashboard/metrics/${m.metric_code}`,
    computedAt: m.computed_at,
  };
}

/** Map one AlertOut (10 §3) → AlertCardProps (href = SCR-09 filtered drill-down). */
export function alertToCard(a: AlertOut): AlertCardProps {
  return {
    alertCode: a.alert_code,
    metricCode: a.metric_code,
    pillar: a.pillar,
    severity: a.severity,
    titleI18nKey: `alertTitles.${a.alert_code}`,
    suggestedActionI18nKey: `alertActions.${a.alert_code}`,
    periodKey: a.period_key,
    triggeredAt: a.triggered_at,
    href: `/dashboard/metrics/${a.metric_code}`,
    canAcknowledge: a.can_acknowledge,
  };
}

/**
 * Split a DashboardOut into FULL-access pillars (rendered as primary cards) and AGG-access
 * pillars (rendered in the "aggregate" section). CEO (4 FULL pillars) gets the AI summary.
 */
export function toDashboardViewModel(d: DashboardOut): DashboardViewModel {
  const pillars: PillarData[] = [];
  const aggPillars: PillarData[] = [];
  for (const p of d.pillars) {
    const block: PillarData = {
      pillar: p.pillar,
      nameKey: `dashboard.pillars.${p.pillar}`,
      metrics: p.metrics.map(metricToCard),
    };
    if (p.access_level === "FULL") {
      pillars.push(block);
    } else {
      aggPillars.push(block);
    }
  }
  const allFull = d.pillars.length > 0 && d.pillars.every((p) => p.access_level === "FULL");
  return {
    pillars,
    aggPillars,
    alerts: d.alerts_top.map(alertToCard),
    // AI executive summary is shown when the role sees every pillar at FULL (CEO, SCR-01).
    hasAISummary: allFull && d.pillars.length >= 4,
    summary: d.summary,
    greeting: d.greeting,
  };
}
