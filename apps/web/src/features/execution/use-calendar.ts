"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { Api } from "@aureon/shared-types";

type CalendarEventOut = Api.CalendarEventOut;
type CalendarEventCreate = Api.CalendarEventCreate;
type CalendarEventUpdate = Api.CalendarEventUpdate;

export interface CalendarRange {
  from?: string;
  to?: string;
}

/** EP-CAL-01 — the caller's own events in a date window (one query per widget, CLAUDE §5.8). */
export function useCalendarEvents(range: CalendarRange) {
  return useQuery({
    queryKey: qk.calendarEvents(range as Record<string, unknown>),
    queryFn: ({ signal }) =>
      api.get<CalendarEventOut[]>("/calendar/events", { from: range.from, to: range.to }, signal),
  });
}

/** EP-CAL-02 — create an event; fresh Idempotency-Key per submit. */
export function useCreateCalendarEvent() {
  const qc = useQueryClient();
  return useMutation<CalendarEventOut, unknown, CalendarEventCreate>({
    mutationFn: (body) => api.post<CalendarEventOut>("/calendar/events", body),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["calendar", "events"] }),
  });
}

/** EP-CAL-04 — patch an event (optimistic concurrency via `version`). */
export function useUpdateCalendarEvent() {
  const qc = useQueryClient();
  return useMutation<CalendarEventOut, unknown, { id: string; body: CalendarEventUpdate }>({
    mutationFn: ({ id, body }) => api.patch<CalendarEventOut>(`/calendar/events/${id}`, body),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["calendar", "events"] }),
  });
}

/** EP-CAL-05 — soft-delete an event (204). */
export function useDeleteCalendarEvent() {
  const qc = useQueryClient();
  return useMutation<void, unknown, string>({
    mutationFn: (id) =>
      apiRequest<void>(`/calendar/events/${id}`, { method: "DELETE" }).then(() => undefined),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["calendar", "events"] }),
  });
}
