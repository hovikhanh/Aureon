/**
 * TC-UI-004 — MaskedValue shows `••••` for a masked salary field (`{ masked: true }`) and
 * NEVER leaks a real value, with an accessible label (06 §7.4, 10 §1.8 DS3).
 */
import axe from "axe-core";
import { cleanup, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import viMessages from "../../../messages/vi.json";
import { renderWithIntl } from "@/test/render";
import { MaskedValue } from "./MaskedValue";

const m = viMessages.metric.masked;

afterEach(cleanup);

describe("TC-UI-004 MaskedValue (06 §7.4, DS3)", () => {
  it("renders the fixed dots glyph", () => {
    const { container } = renderWithIntl(<MaskedValue value={{ masked: true }} />);
    const el = container.querySelector('[data-masked="true"]') as HTMLElement;
    expect(el).not.toBeNull();
    expect(el).toHaveTextContent(m.dots);
  });

  it("exposes an accessible label (not color/dots alone)", () => {
    renderWithIntl(<MaskedValue value={{ masked: true }} />);
    expect(screen.getByRole("img", { name: m.label })).toBeInTheDocument();
  });

  it("never renders a numeric value in the DOM", () => {
    const { container } = renderWithIntl(<MaskedValue value={{ masked: true }} />);
    // The only text content is the dots glyph; no digits anywhere.
    expect(/\d/.test(container.textContent ?? "")).toBe(false);
  });

  it("has no serious/critical axe violations", async () => {
    const { container } = renderWithIntl(<MaskedValue value={{ masked: true }} />);
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
