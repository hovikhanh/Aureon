import { describe, expect, it } from "vitest";
import type { Api } from "@aureon/shared-types";
import { byDecidedDesc, nextReview, onlyReviewDue, reviewDue } from "./decisions";

const TODAY = "2026-11-02T00:00:00Z";

function decision(p: Partial<Api.DecisionOut> = {}): Api.DecisionOut {
  return {
    id: "d1",
    version: 1,
    source: "meeting",
    data_classification: "internal",
    created_at: "2026-10-01T00:00:00Z",
    updated_at: "2026-10-01T00:00:00Z",
    meeting_id: null,
    content: "Mở rộng kho Hà Nội",
    rationale: null,
    alternatives_rejected: null,
    expected_outcome: null,
    owner_id: null,
    decided_at: "2026-10-01T00:00:00Z",
    due_date: null,
    review_at: ["2026-10-31T00:00:00Z", "2026-11-30T00:00:00Z"],
    actual_outcome: null,
    outcome_verified_at: null,
    initiative_id: null,
    source_insight_id: null,
    status: "open",
    done_at: null,
    source_document_id: null,
    ...p,
  };
}

describe("reviewDue", () => {
  it("is true when a review date has passed and the outcome is unverified", () => {
    expect(reviewDue(decision(), TODAY)).toBe(true);
  });
  it("is false when the outcome is already verified", () => {
    expect(reviewDue(decision({ outcome_verified_at: "2026-11-01T00:00:00Z" }), TODAY)).toBe(false);
  });
  it("is false when every review date is still in the future", () => {
    expect(reviewDue(decision({ review_at: ["2026-12-01T00:00:00Z"] }), TODAY)).toBe(false);
  });
  it("is false when there are no review dates", () => {
    expect(reviewDue(decision({ review_at: [] }), TODAY)).toBe(false);
  });
});

describe("nextReview", () => {
  it("returns the soonest upcoming review when one exists", () => {
    expect(nextReview(decision(), TODAY)).toBe("2026-11-30T00:00:00Z");
  });
  it("falls back to the most recent past-due review when none are upcoming", () => {
    const d = decision({ review_at: ["2026-09-01T00:00:00Z", "2026-10-15T00:00:00Z"] });
    expect(nextReview(d, TODAY)).toBe("2026-10-15T00:00:00Z");
  });
  it("returns null when there are no review dates", () => {
    expect(nextReview(decision({ review_at: [] }), TODAY)).toBeNull();
  });
});

describe("onlyReviewDue / byDecidedDesc", () => {
  it("keeps only review-due decisions", () => {
    const rows = [
      decision({ id: "due" }),
      decision({ id: "verified", outcome_verified_at: "2026-11-01T00:00:00Z" }),
      decision({ id: "future", review_at: ["2026-12-01T00:00:00Z"] }),
    ];
    expect(onlyReviewDue(rows, TODAY).map((d) => d.id)).toEqual(["due"]);
  });
  it("sorts newest-decided first", () => {
    const rows = [
      decision({ id: "old", decided_at: "2026-09-01T00:00:00Z" }),
      decision({ id: "new", decided_at: "2026-10-20T00:00:00Z" }),
    ];
    expect(byDecidedDesc(rows).map((d) => d.id)).toEqual(["new", "old"]);
  });
});
