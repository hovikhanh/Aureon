"use client";
/**
 * Header notification bell (T-617F, 06 §3.4 — every role except the AI actor): badge =
 * `meta.unread_count` (hidden at 0, "99+" over 99); polls EP-NTF-01 `unread_only=true&limit=10`
 * every 60 s and on window focus; popover with the 10 newest (title, relative time, unread
 * dot); click → EP-NTF-02 + navigate `link`; "mark all read" (EP-NTF-03); "email settings"
 * dialog per kind (EP-NTF-04/05). `aria-label` carries the count; `aria-live` on increase.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocale, useTranslations } from "next-intl";
import { Bell } from "lucide-react";
import type { Api } from "@aureon/shared-types";
import { apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useToast } from "@/components/ui/toast";
import { badgeText, relativeTime, safeInAppLink } from "./notification-utils";

export const POLL_MS = 60_000;

export function NotificationBell() {
  const t = useTranslations();
  const locale = useLocale();
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [prefsOpen, setPrefsOpen] = React.useState(false);
  const res = useQuery({
    queryKey: qk.notifications(),
    queryFn: ({ signal }) => apiRequest<Api.NotificationOut[]>("/notifications", { query: { unread_only: true, limit: 10 }, signal }),
    refetchInterval: POLL_MS,
    refetchOnWindowFocus: true,
  });
  const unread = Number(res.data?.meta?.unread_count ?? 0);
  const items = res.data?.data ?? [];
  const prev = React.useRef<number | null>(null);
  const [announce, setAnnounce] = React.useState("");
  React.useEffect(() => {
    if (!res.isSuccess) return;
    if (prev.current !== null && unread > prev.current) setAnnounce(t("notifications.newArrived", { n: unread }));
    prev.current = unread;
  }, [unread, res.isSuccess, t]);
  const refresh = () => qc.invalidateQueries({ queryKey: qk.notifications() });
  const read = useMutation({ mutationFn: (id: string) => apiRequest(`/notifications/${id}/read`, { method: "POST", idempotent: true }), onSettled: refresh });
  const readAll = useMutation({ mutationFn: () => apiRequest<{ updated: number }>("/notifications/read-all", { method: "POST", idempotent: true, body: {} }), onSettled: refresh });
  const openItem = async (n: Api.NotificationOut) => {
    setOpen(false);
    await read.mutateAsync(n.id).catch(() => undefined);
    const href = safeInAppLink(n.link);
    if (href) router.push(href);
  };
  const badge = badgeText(unread);
  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button type="button" className="relative flex h-9 w-9 items-center justify-center rounded-full hover:bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
            aria-label={unread ? t("notifications.labelUnread", { n: unread }) : t("notifications.label")} data-testid="notification-bell">
            <Bell className="h-5 w-5" aria-hidden />
            {badge && <span className="absolute -right-0.5 -top-0.5 min-w-[18px] rounded-full bg-danger px-1 text-center text-[10px] font-semibold leading-[18px] text-white" data-testid="notification-badge">{badge}</span>}
          </button>
        </PopoverTrigger>
        <PopoverContent align="end" className="w-80 p-0" data-testid="notification-popover">
          <div className="flex items-center justify-between border-b px-3 py-2">
            <span className="text-sm font-semibold">{t("notifications.title")}</span>
            <Button size="sm" variant="ghost" disabled={!unread || readAll.isPending} onClick={() => readAll.mutate()} data-testid="notification-read-all">{t("notifications.readAll")}</Button>
          </div>
          {res.isError && <p role="alert" className="px-3 py-4 text-sm text-danger">{t("errors.generic")}</p>}
          {res.isSuccess && !items.length && <p className="px-3 py-6 text-center text-sm text-muted-foreground" data-testid="notification-empty">{t("notifications.empty")}</p>}
          <ul className="max-h-96 divide-y overflow-auto">
            {items.map((n) => (
              <li key={n.id}>
                <button type="button" onClick={() => void openItem(n)} className="flex w-full gap-2 px-3 py-2 text-left hover:bg-muted focus-visible:bg-muted focus-visible:outline-none" data-testid="notification-item">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.read_at ? "bg-transparent" : "bg-primary"}`} aria-hidden />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm">{n.title}</span>
                    <span className="block text-xs text-muted-foreground">{t(`notifications.kind.${n.kind}` as "notifications.kind.system")} · <time dateTime={n.created_at}>{relativeTime(n.created_at, locale)}</time></span>
                  </span>
                  {!n.read_at && <span className="sr-only">{t("notifications.unread")}</span>}
                </button>
              </li>
            ))}
          </ul>
          <div className="border-t px-3 py-2 text-right">
            <button type="button" className="text-xs font-medium text-primary hover:underline" onClick={() => { setOpen(false); setPrefsOpen(true); }} data-testid="notification-prefs-open">{t("notifications.emailSettings")}</button>
          </div>
        </PopoverContent>
      </Popover>
      <span className="sr-only" aria-live="polite" data-testid="notification-live">{announce}</span>
      <PreferencesDialog open={prefsOpen} onOpenChange={setPrefsOpen} />
    </>
  );
}

function PreferencesDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const t = useTranslations();
  const toast = useToast();
  const qc = useQueryClient();
  const res = useQuery({
    queryKey: qk.notificationPrefs(),
    enabled: open,
    queryFn: ({ signal }) => apiRequest<Api.NotificationPreferenceOut[]>("/notifications/preferences", { signal }),
  });
  const [draft, setDraft] = React.useState<Record<string, boolean>>({});
  React.useEffect(() => { if (res.data) setDraft(Object.fromEntries(res.data.data.map((p) => [p.kind, p.email_enabled]))); }, [res.data]);
  const save = useMutation({
    mutationFn: () => apiRequest<Api.NotificationPreferenceOut[]>("/notifications/preferences", { method: "PATCH", body: { items: Object.entries(draft).map(([kind, email_enabled]) => ({ kind, email_enabled })) } }),
    onSuccess: (data) => { qc.setQueryData(qk.notificationPrefs(), data); toast.push(t("notifications.prefsSaved")); onOpenChange(false); },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="notification-prefs">
        <DialogTitle>{t("notifications.emailSettings")}</DialogTitle>
        <DialogDescription className="mt-1 text-sm text-muted-foreground">{t("notifications.prefsHint")}</DialogDescription>
        {res.isPending && <div className="mt-4 h-40 animate-pulse rounded bg-muted" />}
        {res.isError && <p role="alert" className="mt-4 text-sm text-danger">{t("errors.generic")}</p>}
        <ul className="mt-4 flex flex-col gap-2">
          {(res.data?.data ?? []).map((p) => (
            <li key={p.kind}>
              <label className="flex items-center justify-between gap-3 text-sm">
                <span>{t(`notifications.kind.${p.kind}` as "notifications.kind.system")}</span>
                <input type="checkbox" className="h-4 w-4" checked={draft[p.kind] ?? false} onChange={(e) => setDraft((d) => ({ ...d, [p.kind]: e.target.checked }))} data-testid={`pref-${p.kind}`} />
              </label>
            </li>
          ))}
        </ul>
        {save.isError && <p role="alert" className="mt-2 text-sm text-danger">{t("errors.generic")}</p>}
        <div className="mt-6 flex justify-end gap-2">
          <DialogClose asChild><Button variant="ghost">{t("buttons.cancel")}</Button></DialogClose>
          <Button onClick={() => save.mutate()} disabled={save.isPending || !res.isSuccess} data-testid="notification-prefs-save">{t("buttons.save")}</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
