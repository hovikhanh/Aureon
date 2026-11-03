/** T-803F — pure logic for the /meetings/calendar view (M3.1, EP-CAL). */
import { describe, expect, it } from "vitest";
import type { Api } from "@aureon/shared-types";
import { defaultRange, groupByDay, isEditable, timeLabel } from "./calendar";

type CalendarEventOut = Api.CalendarEventOut;

const ev = (over: Partial<CalendarEventOut>): CalendarEventOut => ({
  id: over.id ?? crypto.randomUUID(),
  version: 1,
  source: "MANUAL",
  data_classification: "CONFIDENTIAL",
  created_at: "2026-10-20T00:00:00Z",
  updated_at: "2026-10-20T00:00:00Z",
  owner_id: "00000000-0000-0000-0000-000000000001",
  title: over.title ?? "E",
  starts_at: over.starts_at ?? "2026-10-20T02:00:00Z",
  ends_at: over.ends_at ?? null,
  description: null,
  location: null,
  event_source: over.event_source ?? "internal",
  visibility: "private",
  task_id: null,
});

describe("defaultRange", () => {
  it("spans 30 local calendar days as plain dates (EP-CAL-01 takes `date`, not datetime)", () => {
    const r = defaultRange(new Date(2026, 9, 20, 23, 30)); // local 20/10 23:30 — any time zone
    expect(r).toEqual({ from: "2026-10-20", to: "2026-11-19" });
    expect(defaultRange(new Date(2026, 11, 15, 0, 5))).toEqual({ from: "2026-12-15", to: "2027-01-14" });
  });
});

describe("timeLabel", () => {
  it("renders start only when no end, start–end otherwise", () => {
    expect(timeLabel({ starts_at: "2026-10-20T02:00:00Z", ends_at: null })).not.toContain("–");
    expect(timeLabel({ starts_at: "2026-10-20T02:00:00Z", ends_at: "2026-10-20T03:00:00Z" })).toContain("–");
  });
});

describe("isEditable", () => {
  it("is true only for internal events (provider-sourced are read-only here)", () => {
    expect(isEditable({ event_source: "internal" })).toBe(true);
    expect(isEditable({ event_source: "google" })).toBe(false);
    expect(isEditable({ event_source: "outlook" })).toBe(false);
  });
});

describe("groupByDay", () => {
  it("sorts chronologically and buckets by day", () => {
    const groups = groupByDay([
      ev({ title: "late", starts_at: "2026-10-21T06:00:00Z" }),
      ev({ title: "early", starts_at: "2026-10-20T02:00:00Z" }),
      ev({ title: "mid", starts_at: "2026-10-20T08:00:00Z" }),
    ]);
    expect(groups).toHaveLength(2); // two distinct days
    const [firstDay, secondDay] = groups;
    // first bucket is the earliest day, with its two events in time order
    expect(firstDay?.[1].map((e) => e.title)).toEqual(["early", "mid"]);
    expect(secondDay?.[1].map((e) => e.title)).toEqual(["late"]);
  });

  it("returns an empty list for no events", () => {
    expect(groupByDay([])).toEqual([]);
  });
});
