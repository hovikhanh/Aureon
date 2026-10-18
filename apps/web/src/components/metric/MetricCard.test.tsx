/**
 * TC-UI-002 — MetricCard renders every 06 §4.1 / 10 §1.9 state (OK normal / warning /
 * critical with icon + text, NO_DATA `—`, NOT_COMPUTABLE `N/A` + "Không tính được" with no
 * threshold color), the value is a drill-down link (P01), and numbers use P04 formatting.
 * TC-UI-004 (part) — a MetricCard fed masked salary shows `••••` and leaks no value.
 */
import axe from "axe-core";
import { cleanup, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import viMessages from "../../../messages/vi.json";
import { renderWithIntl } from "@/test/render";
import type { MetricCardProps } from "@/features/dashboard/types";
import { MetricCard } from "./MetricCard";

const m = viMessages.metric;

afterEach(cleanup);

function base(overrides: Partial<MetricCardProps> = {}): MetricCardProps {
  return {
    metricCode: "METRIC-FIN-01",
    pillar: "FIN",
    formatKind: "compactCurrency",
    valueState: "OK",
    value: 8_400_000_000,
    statusColor: "GREEN",
    periodKey: "2026-09",
    href: "/metrics/METRIC-FIN-01",
    ...overrides,
  };
}

async function noSeriousAxe(container: HTMLElement) {
  const results = await axe.run(container, {
    resultTypes: ["violations"],
    rules: { "color-contrast": { enabled: false } },
  });
  return results.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .map((v) => v.id);
}

describe("TC-UI-002 MetricCard states (06 §4.1, 10 §1.9)", () => {
  it("OK/GREEN: P04 compact VND value + a drill-down link + ok status (icon + text)", () => {
    renderWithIntl(<MetricCard {...base()} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/metrics/METRIC-FIN-01");
    // 8.4e9 → `8,4 tỷ` via the P04 formatter (dot-less, comma decimal, tỷ unit).
    expect(link).toHaveTextContent("8,4 tỷ");
    expect(screen.getByText(m.status.ok)).toBeInTheDocument();
  });

  it("OK/YELLOW: warning label (icon + text) and warn accent, not color alone", () => {
    const { container } = renderWithIntl(
      <MetricCard {...base({ statusColor: "YELLOW", formatKind: "percent", value: 0.088 })} />,
    );
    expect(screen.getByText(m.status.warning)).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveTextContent("8,8%");
    const card = container.querySelector("[data-metric-code]") as HTMLElement;
    expect(card.getAttribute("data-status-color")).toBe("YELLOW");
  });

  it("OK/RED: critical label (icon + text)", () => {
    renderWithIntl(<MetricCard {...base({ statusColor: "RED", formatKind: "days", value: 64 })} />);
    expect(screen.getByText(m.status.critical)).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveTextContent(`64 ${m.unit.days}`);
  });

  it("NO_DATA: shows the `—` placeholder + 'Chưa có dữ liệu nguồn', no threshold color, no fake 0", () => {
    const { container } = renderWithIntl(
      <MetricCard {...base({ valueState: "NO_DATA", value: null, statusColor: null })} />,
    );
    const link = screen.getByRole("link");
    expect(link).toHaveTextContent(viMessages.format.placeholder); // `—`
    expect(link).not.toHaveTextContent("0");
    expect(screen.getByText(m.state.noData)).toBeInTheDocument();
    // No status label and no threshold color attribute.
    expect(screen.queryByText(m.status.ok)).toBeNull();
    const card = container.querySelector("[data-metric-code]") as HTMLElement;
    expect(card.getAttribute("data-status-color")).toBeNull();
  });

  it("NOT_COMPUTABLE: shows `N/A` + 'Không tính được' + reason, no threshold color", () => {
    const { container } = renderWithIntl(
      <MetricCard
        {...base({
          valueState: "NOT_COMPUTABLE",
          value: null,
          statusColor: null,
          notComputableReason: "DENOMINATOR_ZERO",
          formatKind: "percent",
        })}
      />,
    );
    expect(screen.getByRole("link")).toHaveTextContent("N/A");
    expect(screen.getByText(m.state.notComputable)).toBeInTheDocument();
    expect(screen.getByText(m.notComputableReason.DENOMINATOR_ZERO)).toBeInTheDocument();
    expect(screen.queryByText(m.status.ok)).toBeNull();
    const card = container.querySelector("[data-metric-code]") as HTMLElement;
    expect(card.getAttribute("data-status-color")).toBeNull();
  });

  it("GT_24_MONTHS display hint (FIN-03): shows `> 24 tháng` instead of a number", () => {
    renderWithIntl(
      <MetricCard
        {...base({ metricCode: "METRIC-FIN-03", formatKind: "months", value: null, displayHint: "GT_24_MONTHS" })}
      />,
    );
    expect(screen.getByRole("link")).toHaveTextContent(m.displayHint.GT_24_MONTHS);
  });

  it("period, formula caption and freshness use P04 formatting", () => {
    renderWithIntl(
      <MetricCard
        {...base({ formulaDisplay: "SUM(invoice.amount)", computedAt: "2026-10-05T08:30:00+07:00", deltaRatio: 0.082 })}
      />,
    );
    // Period `2026-09` → `T9/2026`.
    expect(screen.getByText(/T9\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/SUM\(invoice\.amount\)/)).toBeInTheDocument();
    // dateTime 05/10/2026 08:30.
    expect(screen.getByText(/05\/10\/2026 08:30/)).toBeInTheDocument();
    // Signed delta +8,2%.
    expect(screen.getByText("+8,2%")).toBeInTheDocument();
  });

  it("the link has an accessible name that includes the value (P01)", () => {
    renderWithIntl(<MetricCard {...base()} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAccessibleName(/8,4 tỷ/);
  });

  it("TC-UI-004: a masked salary card renders `••••` and never a numeric value", () => {
    renderWithIntl(
      <MetricCard
        {...base({
          metricCode: "METRIC-HR-XX",
          formatKind: "compactCurrency",
          value: { masked: true },
        })}
      />,
    );
    const link = screen.getByRole("link");
    expect(within(link).getByRole("img", { name: m.masked.label })).toBeInTheDocument();
    expect(link).toHaveTextContent(m.masked.dots);
    // No digits leaked anywhere in the value link.
    expect(/\d/.test(link.textContent ?? "")).toBe(false);
  });

  it.each(["GREEN", "YELLOW", "RED"] as const)("OK/%s has no serious/critical axe violations", async (color) => {
    const { container } = renderWithIntl(<MetricCard {...base({ statusColor: color })} />);
    expect(await noSeriousAxe(container)).toEqual([]);
  });

  it.each(["NO_DATA", "NOT_COMPUTABLE"] as const)("%s has no serious/critical axe violations", async (vs) => {
    const { container } = renderWithIntl(
      <MetricCard
        {...base({ valueState: vs, value: null, statusColor: null, notComputableReason: "UNDEFINED" })}
      />,
    );
    expect(await noSeriousAxe(container)).toEqual([]);
  });
});
