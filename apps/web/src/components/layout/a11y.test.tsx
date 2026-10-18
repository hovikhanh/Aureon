/**
 * TC-UI-006 — axe-core accessibility scan on the shell and each page state: 0 violations at
 * `serious` or `critical` impact (06 §9, WCAG 2.1 AA). jsdom-based scan complements the
 * Playwright+axe e2e sweep listed in 14 TC-UI-006.
 */
import axe from "axe-core";
import { cleanup, render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactElement } from "react";
import viMessages from "../../../messages/vi.json";
import { AppShell } from "./AppShell";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { ForbiddenState } from "@/components/states/ForbiddenState";
import { LoadingState } from "@/components/states/LoadingState";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

afterEach(cleanup);

function withIntl(ui: ReactElement) {
  return (
    <NextIntlClientProvider locale="vi" messages={viMessages} timeZone="Asia/Ho_Chi_Minh">
      {ui}
    </NextIntlClientProvider>
  );
}

async function expectNoSeriousViolations(container: HTMLElement) {
  const results = await axe.run(container, {
    resultTypes: ["violations"],
    // Color-contrast cannot be computed reliably in jsdom (no layout/paint); the token
    // contrast is covered by design-tokens.test.ts and the Playwright axe sweep (TC-UI-006).
    rules: { "color-contrast": { enabled: false } },
  });
  const serious = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  expect(serious.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
}

describe("TC-UI-006 axe scan — shell + states", () => {
  it("AppShell has no serious/critical violations", async () => {
    const { container } = render(
      withIntl(
        <AppShell role="ROLE-01">
          <h1>Dashboard</h1>
        </AppShell>,
      ),
    );
    await expectNoSeriousViolations(container);
  });

  it("LoadingState has no serious/critical violations", async () => {
    const { container } = render(withIntl(<LoadingState />));
    await expectNoSeriousViolations(container);
  });

  it("EmptyState has no serious/critical violations", async () => {
    const { container } = render(withIntl(<EmptyState />));
    await expectNoSeriousViolations(container);
  });

  it("ErrorState has no serious/critical violations", async () => {
    const { container } = render(withIntl(<ErrorState onRetry={() => {}} />));
    await expectNoSeriousViolations(container);
  });

  it("ForbiddenState has no serious/critical violations", async () => {
    const { container } = render(withIntl(<ForbiddenState />));
    await expectNoSeriousViolations(container);
  });
});
