"use client";
import * as React from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ApiError } from "@/lib/api-client";
import {
  useCalendarEvents,
  useCreateCalendarEvent,
  useDeleteCalendarEvent,
} from "./use-calendar";
import { defaultRange, groupByDay, isEditable, timeLabel } from "./calendar";

/**
 * SCR `/meetings/calendar` (M3.1): the caller's own calendar. Events are mức-3 Confidential —
 * never sent to an LLM (R-DEC-123); this view only reads/writes via EP-CAL. Create is a plain
 * internal event; two-way sync to Google/Outlook runs in the background once a provider is
 * connected under `/settings/integrations`.
 */
export function CalendarView() {
  const t = useTranslations("calendar");
  const range = React.useMemo(defaultRange, []);
  const list = useCalendarEvents(range);
  const create = useCreateCalendarEvent();
  const del = useDeleteCalendarEvent();
  const [title, setTitle] = React.useState("");
  const [start, setStart] = React.useState("");
  const [end, setEnd] = React.useState("");

  const events = React.useMemo(() => list.data ?? [], [list.data]);
  const grouped = React.useMemo(() => groupByDay(events), [events]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !start) return;
    create.mutate(
      {
        title: title.trim(),
        starts_at: new Date(start).toISOString(),
        ends_at: end ? new Date(end).toISOString() : null,
      },
      { onSuccess: () => { setTitle(""); setStart(""); setEnd(""); } },
    );
  };

  const err = (list.error ?? create.error ?? del.error) as unknown;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4" data-testid="calendar-view">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">{t("title")}</h1>
          <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/settings/integrations" data-testid="calendar-manage-integrations">{t("manageIntegrations")}</Link>
        </Button>
      </header>

      <Card>
        <CardHeader><CardTitle>{t("new.title")}</CardTitle></CardHeader>
        <CardContent>
          <form className="grid gap-3 sm:grid-cols-2" onSubmit={submit} data-testid="calendar-create-form">
            <div className="sm:col-span-2 flex flex-col gap-1">
              <Label htmlFor="cal-title">{t("new.name")}</Label>
              <Input id="cal-title" data-testid="cal-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t("new.namePlaceholder")} required />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="cal-start">{t("new.start")}</Label>
              <Input id="cal-start" data-testid="cal-start" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} required />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="cal-end">{t("new.end")}</Label>
              <Input id="cal-end" data-testid="cal-end" type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={create.isPending || !title.trim() || !start} data-testid="cal-submit">{t("new.submit")}</Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {err ? (
        <p role="alert" className="text-sm text-destructive" data-testid="calendar-error">
          {err instanceof ApiError ? err.message : t("errorGeneric")}
        </p>
      ) : null}

      {!list.isLoading && events.length === 0 && (
        <p className="text-sm text-muted-foreground" data-testid="calendar-empty">{t("empty")}</p>
      )}

      {grouped.map(([day, dayEvents]) => (
        <Card key={day}>
          <CardHeader><CardTitle className="text-base">{day}</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-2">
            {dayEvents.map((ev) => (
              <div key={ev.id} className="flex items-center justify-between gap-3 rounded-md border p-3" data-testid="calendar-event">
                <div className="min-w-0">
                  <p className="truncate font-medium">{ev.title}</p>
                  <p className="text-xs text-muted-foreground">{timeLabel(ev)}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge variant={isEditable(ev) ? "primary" : "outline"}>{t(`source.${ev.event_source}`)}</Badge>
                  {isEditable(ev) && (
                    <Button variant="ghost" size="sm" onClick={() => del.mutate(ev.id)} disabled={del.isPending} data-testid={`cal-delete-${ev.id}`}>
                      {t("delete")}
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
