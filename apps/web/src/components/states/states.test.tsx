/**
 * TC-UI-009 (part) — the four standard page states (06 §3.2) render the correct ARIA role and
 * i18n text, and convey meaning with icon + text (not color alone, 06 §9).
 */
import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import viMessages from "../../../messages/vi.json";
import { renderWithIntl } from "@/test/render";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { ForbiddenState } from "./ForbiddenState";
import { LoadingState } from "./LoadingState";

const m = viMessages.states;

afterEach(cleanup);

describe("page states (06 §3.2)", () => {
  it("Loading: aria-busy status with an accessible label (no full-page spinner)", () => {
    renderWithIntl(<LoadingState />);
    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveTextContent(m.loading.label);
  });

  it("Empty: shows title + description + optional action", () => {
    renderWithIntl(<EmptyState action={<button type="button">go</button>} />);
    expect(screen.getByRole("heading", { name: m.empty.title })).toBeInTheDocument();
    expect(screen.getByText(m.empty.description)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "go" })).toBeInTheDocument();
  });

  it("Error: alert role, text, retry button fires callback", () => {
    const onRetry = vi.fn();
    renderWithIntl(<ErrorState onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toHaveTextContent(m.error.title);
    const retry = screen.getByRole("button", { name: m.error.retry });
    fireEvent.click(retry);
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("Error: no stale note by default", () => {
    renderWithIntl(<ErrorState />);
    expect(screen.queryByText(m.error.stale)).toBeNull();
  });

  it("Error: stale note appears when stale=true", () => {
    renderWithIntl(<ErrorState stale />);
    expect(screen.getByText(m.error.stale)).toBeInTheDocument();
  });

  it("Forbidden: alert role with the out-of-scope message (02 §4.1 — never silent)", () => {
    renderWithIntl(<ForbiddenState />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(m.forbidden.title);
    expect(alert).toHaveTextContent(m.forbidden.description);
  });
});
