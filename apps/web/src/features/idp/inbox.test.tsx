/**
 * TC-UI-006 & TC-UI-009 — SCR-05 IDP Review Queue (Inbox) tests:
 * - Table rendering with filenames, pillars, doc types, AIStateBadge, confidence, and conflict indicator.
 * - Role-scoping: ROLE-05 full review, ROLE-01 view-only (salary masked), ROLE-03 forbidden.
 * - Filter functionality: pillar, docType, status, conflict.
 * - Loading, Empty, and Error states per 06 §3.2.
 * - Accessibility: axe-core scan with 0 serious or critical violations (WCAG 2.1 AA).
 */
import type { ReactElement } from "react";
import axe from "axe-core";
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";
import viMessages from "../../../messages/vi.json";
import { InboxView } from "./InboxView";
import { DEMO_REVIEW_QUEUE_ITEMS } from "./demo-fixtures";

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
    rules: { "color-contrast": { enabled: false } },
  });
  const serious = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  expect(serious.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
}

const mockCounts = {
  total: 6,
  needs_review: 4,
  in_review: 1,
  failed: 1,
};

describe("SCR-05 InboxView (06 §4.2, FR-DC-16, US-DC-011)", () => {
  it("renders header, stats cards, and queue table for ROLE-05", () => {
    const { container } = render(
      withIntl(
        <InboxView
          items={DEMO_REVIEW_QUEUE_ITEMS}
          counts={mockCounts}
          role="ROLE-05"
        />,
      ),
    );

    // Header & stats
    expect(screen.getByText("Hàng chờ IDP (Inbox)")).toBeInTheDocument();
    expect(screen.getByText("Tổng tài liệu")).toBeInTheDocument();
    expect(screen.getByText("6")).toBeInTheDocument();
    expect(screen.getAllByText("Cần duyệt").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Đang duyệt").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Thất bại").length).toBeGreaterThan(0);

    // Documents in table
    expect(screen.getByText("hoa_don_thang_10_2026.xlsx")).toBeInTheDocument();
    expect(screen.getByText("bao_cao_doanh_thu_t9_2026.xlsx")).toBeInTheDocument();
    expect(screen.getByText("bien_ban_hop_giao_ban_t10.docx")).toBeInTheDocument();

    // AI Badges
    const aiBadges = container.querySelectorAll("[data-ai-level]");
    expect(aiBadges.length).toBeGreaterThan(0);

    // Conflict icon
    const conflictIcon = container.querySelector("[aria-label='Có xung đột đối chiếu chéo']");
    expect(conflictIcon).toBeInTheDocument();

    // Lock indicator for FINANCIAL_REPORT (in review by Hoang Van Em)
    expect(screen.getByText("Đang được Hoang Van Em review")).toBeInTheDocument();

    // Review buttons for ROLE-05
    const reviewButtons = screen.getAllByRole("link", { name: /Duyệt/i });
    expect(reviewButtons.length).toBeGreaterThan(0);
  });

  it("handles ROLE-01 CEO: salary document is masked without review button", () => {
    const { container } = render(
      withIntl(
        <InboxView
          items={DEMO_REVIEW_QUEUE_ITEMS}
          counts={mockCounts}
          role="ROLE-01"
        />,
      ),
    );

    // Masked value for personal salary employee list
    const maskedElement = container.querySelector("[data-masked='true']");
    expect(maskedElement).toBeInTheDocument();

    // CEO sees "Xem" for viewable documents
    const viewButtons = screen.getAllByRole("link", { name: /Xem/i });
    expect(viewButtons.length).toBeGreaterThan(0);
  });

  it("handles ROLE-03 Sales Director: displays ForbiddenState", () => {
    render(
      withIntl(
        <InboxView
          items={DEMO_REVIEW_QUEUE_ITEMS}
          counts={mockCounts}
          role="ROLE-03"
        />,
      ),
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(
      screen.getByText("Giám đốc kinh doanh không thuộc phạm vi xử lý hàng chờ IDP."),
    ).toBeInTheDocument();
  });

  it("filters items by pillar", () => {
    render(
      withIntl(
        <InboxView
          items={DEMO_REVIEW_QUEUE_ITEMS}
          counts={mockCounts}
          role="ROLE-05"
        />,
      ),
    );

    // Select FIN pillar
    const pillarSelect = screen.getByLabelText("Trụ");
    fireEvent.change(pillarSelect, { target: { value: "FIN" } });

    // Invoices and financial reports should be present
    expect(screen.getByText("hoa_don_thang_10_2026.xlsx")).toBeInTheDocument();
    expect(screen.getByText("bao_cao_tai_chinh_q3_2026.pdf")).toBeInTheDocument();

    // Sales report (CUS) and HR list should be filtered out
    expect(screen.queryByText("bao_cao_doanh_thu_t9_2026.xlsx")).not.toBeInTheDocument();
    expect(screen.queryByText("danh_sach_nhan_su_thang_10.xlsx")).not.toBeInTheDocument();
  });

  it("filters items by conflict only", () => {
    render(
      withIntl(
        <InboxView
          items={DEMO_REVIEW_QUEUE_ITEMS}
          counts={mockCounts}
          role="ROLE-05"
        />,
      ),
    );

    const conflictCheckbox = screen.getByRole("checkbox", {
      name: "Có xung đột đối chiếu chéo",
    });
    fireEvent.click(conflictCheckbox);

    // Only meeting minutes has conflict
    expect(screen.getByText("bien_ban_hop_giao_ban_t10.docx")).toBeInTheDocument();
    expect(screen.queryByText("hoa_don_thang_10_2026.xlsx")).not.toBeInTheDocument();
  });

  it("renders LoadingState skeleton when isLoading is true", () => {
    const { container } = render(
      withIntl(
        <InboxView
          items={[]}
          counts={mockCounts}
          role="ROLE-05"
          isLoading={true}
        />,
      ),
    );

    expect(screen.getByRole("status")).toBeInTheDocument();
    const skeletonBars = container.querySelectorAll(".animate-pulse");
    expect(skeletonBars.length).toBe(8);
  });

  it("renders EmptyState when items array is empty", () => {
    render(
      withIntl(
        <InboxView
          items={[]}
          counts={{ total: 0, needs_review: 0, in_review: 0, failed: 0 }}
          role="ROLE-05"
        />,
      ),
    );

    expect(screen.getByText("Không còn tài liệu cần duyệt 🎉")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Xem danh sách tài liệu" })).toBeInTheDocument();
  });

  it("renders ErrorState with retry button when isError is true and no items", () => {
    const onRetry = vi.fn();
    render(
      withIntl(
        <InboxView
          items={[]}
          counts={mockCounts}
          role="ROLE-05"
          isError={true}
          onRetry={onRetry}
        />,
      ),
    );

    expect(screen.getByText("Không thể tải hàng chờ")).toBeInTheDocument();
    const retryBtn = screen.getByRole("button", { name: "Thử lại" });
    fireEvent.click(retryBtn);
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("renders stale warning banner when isStale is true", () => {
    render(
      withIntl(
        <InboxView
          items={DEMO_REVIEW_QUEUE_ITEMS}
          counts={mockCounts}
          role="ROLE-05"
          isStale={true}
        />,
      ),
    );

    expect(screen.getByText("Dữ liệu có thể đã cũ.")).toBeInTheDocument();
    expect(screen.getByText("hoa_don_thang_10_2026.xlsx")).toBeInTheDocument();
  });

  it("has zero serious/critical accessibility violations (TC-UI-006)", async () => {
    const { container } = render(
      withIntl(
        <InboxView
          items={DEMO_REVIEW_QUEUE_ITEMS}
          counts={mockCounts}
          role="ROLE-05"
        />,
      ),
    );

    await expectNoSeriousViolations(container);
  });
});
