import { describe, expect, it } from "vitest";
import axe from "axe-core";
import { screen } from "@testing-library/react";
import type { MetricHistoryPoint } from "@aureon/shared-types";
import { renderWithIntl } from "@/test/render";
import { TrendChart } from "./TrendChart";

async function noSeriousAxe(container: HTMLElement) {
  const results = await axe.run(container, {
    resultTypes: ["violations"],
    rules: { "color-contrast": { enabled: false } },
  });
  return results.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => v.id);
}

const sampleHistory: MetricHistoryPoint[] = [
  {
    period_key: "2026-07",
    value: 7500000000,
    target_value: 7000000000,
    value_state: "OK",
    status_color: "GREEN",
  },
  {
    period_key: "2026-08",
    value: 8000000000,
    target_value: 7500000000,
    value_state: "OK",
    status_color: "GREEN",
  },
  {
    period_key: "2026-09",
    value: 8400000000,
    target_value: 8000000000,
    value_state: "OK",
    status_color: "GREEN",
  },
];

describe("TrendChart (06 §4.1, §6.6, TC-UI-003)", () => {
  it("renders data summary and accessible table fallback with points", () => {
    const { container } = renderWithIntl(
      <TrendChart
        metricCode="METRIC-FIN-01"
        formatKind="compactCurrency"
        history={sampleHistory}
        width={400}
        height={200}
      />,
    );

    const figure = container.querySelector('[data-trend-chart="METRIC-FIN-01"]');
    expect(figure).toBeInTheDocument();
    expect(figure).not.toHaveAttribute("data-empty");

    // Table fallback has 3 rows
    const rows = screen.getAllByRole("row");
    // 1 header row + 3 data rows
    expect(rows).toHaveLength(4);
  });

  it("renders empty state when history has no plottable data", () => {
    const emptyHistory: MetricHistoryPoint[] = [
      {
        period_key: "2026-09",
        value: null,
        target_value: null,
        value_state: "NO_DATA",
        status_color: null,
      },
    ];

    const { container } = renderWithIntl(
      <TrendChart
        metricCode="METRIC-FIN-02"
        formatKind="compactCurrency"
        history={emptyHistory}
        width={400}
        height={200}
      />,
    );

    const figure = container.querySelector('[data-trend-chart="METRIC-FIN-02"]');
    expect(figure).toBeInTheDocument();
    expect(figure).toHaveAttribute("data-empty", "true");
  });

  it("passes axe accessibility checks without serious or critical violations", async () => {
    const { container } = renderWithIntl(
      <TrendChart
        metricCode="METRIC-FIN-01"
        formatKind="compactCurrency"
        history={sampleHistory}
        width={400}
        height={200}
      />,
    );

    expect(await noSeriousAxe(container)).toEqual([]);
  });
});
