/**
 * AlertCard (06 §4.1, §6.6) — severity with icon + text (not color alone), a metric
 * drill-down link (P01), period + triggered time via P04, an AI-suggested action in the
 * `--ai` family (not `--primary`, 06 §6.3), and an acknowledge affordance gated by role.
 */
import axe from "axe-core";
import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import viMessages from "../../../messages/vi.json";
import { renderWithIntl } from "@/test/render";
import type { AlertCardProps } from "@/features/dashboard/types";
import { AlertCard } from "./AlertCard";

const m = viMessages.alert;

afterEach(cleanup);

function base(overrides: Partial<AlertCardProps> = {}): AlertCardProps {
  return {
    alertCode: "ALERT-FIN-01",
    metricCode: "METRIC-FIN-01",
    pillar: "FIN",
    severity: "CRITICAL",
    periodKey: "2026-09",
    triggeredAt: "2026-10-05T08:30:00+07:00",
    href: "/metrics/METRIC-FIN-01?alert=ALERT-FIN-01",
    ...overrides,
  };
}

describe("AlertCard (06 §4.1)", () => {
  it("CRITICAL: severity label (icon + text) + metric id + period + triggered time", () => {
    renderWithIntl(<AlertCard {...base()} />);
    expect(screen.getByText(m.severity.CRITICAL)).toBeInTheDocument();
    expect(screen.getByText(/METRIC-FIN-01 · T9\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/05\/10\/2026 08:30/)).toBeInTheDocument();
  });

  it("WARNING: severity label present and card carries the severity data attr", () => {
    const { container } = renderWithIntl(<AlertCard {...base({ severity: "WARNING" })} />);
    expect(screen.getByText(m.severity.WARNING)).toBeInTheDocument();
    expect(container.querySelector('[data-severity="WARNING"]')).not.toBeNull();
  });

  it("title is a drill-down link to SCR-09 (P01)", () => {
    renderWithIntl(<AlertCard {...base()} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/metrics/METRIC-FIN-01?alert=ALERT-FIN-01");
    // Falls back to the alert code when no title key is supplied.
    expect(link).toHaveTextContent("ALERT-FIN-01");
  });

  it("AI-suggested action uses the --ai family, never --primary (06 §6.3)", () => {
    const { container } = renderWithIntl(
      <AlertCard {...base({ suggestedActionI18nKey: "alert.suggestedAction" })} />,
    );
    const aiBlock = container.querySelector(".bg-ai-muted") as HTMLElement;
    expect(aiBlock).not.toBeNull();
    expect(aiBlock.className).not.toMatch(/\b(?:bg|text|border)-primary\b/);
    // The AI block carries the "Suggested action" label prefix.
    expect(aiBlock.textContent).toContain(m.suggestedAction);
  });

  it("acknowledge button shown only when canAcknowledge + handler, uses primary, fires", () => {
    const onAcknowledge = vi.fn();
    renderWithIntl(<AlertCard {...base({ canAcknowledge: true, onAcknowledge })} />);
    const btn = screen.getByRole("button", { name: m.acknowledge });
    expect(btn.className).toMatch(/\bbg-primary\b/);
    fireEvent.click(btn);
    expect(onAcknowledge).toHaveBeenCalledOnce();
  });

  it("no acknowledge button when the role cannot acknowledge", () => {
    renderWithIntl(<AlertCard {...base({ canAcknowledge: false, onAcknowledge: () => {} })} />);
    expect(screen.queryByRole("button", { name: m.acknowledge })).toBeNull();
  });

  it.each(["CRITICAL", "WARNING"] as const)("%s has no serious/critical axe violations", async (sev) => {
    const { container } = renderWithIntl(
      <AlertCard
        {...base({ severity: sev, suggestedActionI18nKey: "alert.suggestedAction", canAcknowledge: true, onAcknowledge: () => {} })}
      />,
    );
    const results = await axe.run(container, {
      resultTypes: ["violations"],
      rules: { "color-contrast": { enabled: false } },
    });
    const serious = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(serious.map((v) => v.id)).toEqual([]);
  });
});
