/** T-803F — pure logic for the /meetings/calendar view (M3.1, EP-CAL). No React, no I/O. */
import type { Api } from "@aureon/shared-types";

type CalendarEventOut = Api.CalendarEventOut;

const ymd = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/**
 * A 30-day window from today (local calendar day) → `YYYY-MM-DD` bounds: EP-CAL-01 `from`/`to` are
 * **dates** (10 §7.2.8). Sending `toISOString()` passed only where local midnight is `T00:00:00Z`;
 * at UTC+7 it was `…T17:00:00.000Z` → `422` and an empty calendar (M6).
 */
export function defaultRange(now: Date = new Date()): { from: string; to: string } {
  const to = new Date(now);
  to.setDate(to.getDate() + 30);
  return { from: ymd(now), to: ymd(to) };
}

/** Group key = the start day, localized (vi-VN). */
export function dayKey(iso: string): string {
  return new Date(iso).toLocaleDateString("vi-VN", {
    weekday: "long", day: "2-digit", month: "2-digit", year: "numeric",
  });
}

/** `HH:MM` or `HH:MM–HH:MM` when the event has an end. */
export function timeLabel(ev: Pick<CalendarEventOut, "starts_at" | "ends_at">): string {
  const opts: Intl.DateTimeFormatOptions = { hour: "2-digit", minute: "2-digit" };
  const start = new Date(ev.starts_at).toLocaleTimeString("vi-VN", opts);
  if (!ev.ends_at) return start;
  return `${start}–${new Date(ev.ends_at).toLocaleTimeString("vi-VN", opts)}`;
}

/** Only internal events can be deleted/edited locally; provider-sourced events are read-only here. */
export function isEditable(ev: Pick<CalendarEventOut, "event_source">): boolean {
  return ev.event_source === "internal";
}

/** Chronologically sort then bucket by day — one entry `[dayLabel, events]` per day. */
export function groupByDay(events: CalendarEventOut[]): [string, CalendarEventOut[]][] {
  const m = new Map<string, CalendarEventOut[]>();
  for (const ev of [...events].sort((a, b) => a.starts_at.localeCompare(b.starts_at))) {
    const k = dayKey(ev.starts_at);
    const bucket = m.get(k);
    if (bucket) bucket.push(ev);
    else m.set(k, [ev]);
  }
  return [...m.entries()];
}
