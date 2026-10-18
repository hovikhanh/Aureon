/**
 * TC-UI-003 (part) — AIStateBadge renders L0–L3 with the `--ai` token family (never
 * `--primary`), and always with text + icon, not color alone (06 §6.3, P02, US-DC-017).
 */
import axe from "axe-core";
import { cleanup, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { AIStateLevel } from "@aureon/shared-types";
import viMessages from "../../../messages/vi.json";
import { renderWithIntl } from "@/test/render";
import { AIStateBadge } from "./AIStateBadge";

const state = viMessages.ai.state;

const CASES: { level: AIStateLevel; label: string }[] = [
  { level: "L0", label: state.off },
  { level: "L1", label: state.suggest },
  { level: "L2", label: state.draft },
  { level: "L3", label: state.done },
];

afterEach(cleanup);

describe("TC-UI-003 AIStateBadge (06 §6.3)", () => {
  it.each(CASES)("L$level shows the i18n label text", ({ level, label }) => {
    const { container } = renderWithIntl(<AIStateBadge level={level} />);
    const badge = container.querySelector(`[data-ai-level="${level}"]`) as HTMLElement;
    expect(badge).not.toBeNull();
    expect(badge).toHaveTextContent(label);
  });

  it.each(CASES)("L$level carries an icon (not color alone)", ({ level }) => {
    const { container } = renderWithIntl(<AIStateBadge level={level} />);
    const badge = container.querySelector(`[data-ai-level="${level}"]`) as HTMLElement;
    // lucide renders an <svg aria-hidden> alongside the text span.
    expect(within(badge).getByText(CASES.find((c) => c.level === level)!.label)).toBeInTheDocument();
    expect(badge.querySelector("svg")).not.toBeNull();
  });

  it.each(CASES)("L$level uses the --ai family and never --primary", ({ level }) => {
    const { container } = renderWithIntl(<AIStateBadge level={level} />);
    const badge = container.querySelector(`[data-ai-level="${level}"]`) as HTMLElement;
    const cls = badge.className;
    // No primary token anywhere (bg-primary / text-primary / border-primary / ring-primary).
    expect(/\b(?:bg|text|border|ring)-primary\b/.test(cls)).toBe(false);
    // No metric status color leaking onto AI content (06 §6.2).
    expect(/\b(?:bg|text|border)-status-/.test(cls)).toBe(false);
    // L1..L3 must reference the --ai family; L0 is a neutral outline by design.
    if (level !== "L0") {
      expect(/\bai\b/.test(cls)).toBe(true);
    }
  });

  it("the four levels render distinct labels", () => {
    renderWithIntl(
      <div>
        <AIStateBadge level="L0" />
        <AIStateBadge level="L1" />
        <AIStateBadge level="L2" />
        <AIStateBadge level="L3" />
      </div>,
    );
    for (const { label } of CASES) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it.each(CASES)("L$level has no serious/critical axe violations", async ({ level }) => {
    const { container } = renderWithIntl(<AIStateBadge level={level} />);
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
