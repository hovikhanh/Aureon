"use client";
import * as React from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { PenLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { ActionsHistory } from "./ActionsHistory";
import { DropZone } from "./DropZone";
import { InboxFilters, type Filters } from "./InboxFilters";
import { IncidentDialog } from "./IncidentDialog";
import { InboxRow, type RowAction } from "./InboxRow";
import { SourceDrawer } from "./SourceDrawer";
import { UndoDialog } from "./UndoDialog";
import { captureError } from "./errors";
import { INBOX_GROUPS, type InboxGroup, type InboxItem } from "./types";
import { useDocTypes, useInbox } from "./use-capture";

const LIMIT = 20;

/** SCR-45 `/data` Data Inbox (T-635F): C3 DropZone, C1 menu, groups with `meta.counts`, filters, row actions. */
export function InboxView({ permissions, role }: { permissions: string[]; role: string }) {
  const t = useTranslations();
  const canWrite = permissions.includes("idp:write");
  const canReview = permissions.includes("idp:approve");
  const canReport = canReview && ["REV", "DIR", "MGR"].includes(role);
  const [group, setGroup] = React.useState<InboxGroup | "all">("all");
  const [filters, setFilters] = React.useState<Filters>({ channel: "", document_type: "", mine: false, q: "", date_from: "", date_to: "" });
  const [offset, setOffset] = React.useState(0);
  const [act, setAct] = React.useState<{ a: RowAction; item: InboxItem } | null>(null);
  const types = useDocTypes();
  const params = { group: group === "all" ? undefined : group, ...filters, mine: filters.mine || undefined, limit: LIMIT, offset };
  const inbox = useInbox(params);
  const counts = (inbox.data?.meta?.counts ?? {}) as Record<string, number>;
  const total = inbox.data?.meta?.pagination?.total ?? 0;
  const rows = inbox.data?.data ?? [];
  const formTypes = (types.data ?? []).filter((d) => d.channels_supported.includes("C1"));
  const filtered = Boolean(group !== "all" || filters.channel || filters.document_type || filters.mine || filters.q || filters.date_from || filters.date_to);
  const close = () => setAct(null);
  const typeName = (code: string, fallback: string) => (t.has(`capture.docType.${code}`) ? t(`capture.docType.${code}`) : fallback);

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4" data-testid="data-inbox" data-scr="SCR-45">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{t("capture.inbox.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("capture.inbox.subtitle")}</p>
        </div>
        {canWrite && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild><Button variant="outline" data-testid="manual-menu"><PenLine className="h-4 w-4" aria-hidden />{t("capture.manual.menu")}</Button></DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuLabel>{t("capture.manual.menuHint")}</DropdownMenuLabel>
              {formTypes.length === 0 && <DropdownMenuItem disabled>{t("capture.manual.none")}</DropdownMenuItem>}
              {formTypes.map((d) => <DropdownMenuItem key={d.code} asChild><Link href={`/data/new/${d.code}`} data-testid={`manual-${d.code}`}>{typeName(d.code, d.name_vi)}</Link></DropdownMenuItem>)}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      {canWrite && <DropZone />}
      <div role="tablist" aria-label={t("capture.inbox.col.status")} className="flex flex-wrap gap-1 border-b" data-testid="inbox-groups">
        {(["all", ...INBOX_GROUPS] as const).map((g) => (
          <button key={g} role="tab" type="button" aria-selected={group === g} onClick={() => { setGroup(g); setOffset(0); }} data-testid={`group-${g}`}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${group === g ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {t(`capture.inbox.group.${g}`)}
            {g !== "all" && <span className="ml-1 rounded-full bg-muted px-1.5 text-xs tabular-nums" data-testid={`count-${g}`}>{counts[g] ?? 0}</span>}
          </button>
        ))}
      </div>
      <InboxFilters value={filters} types={types.data ?? []} onChange={(f) => { setFilters(f); setOffset(0); }} />
      {inbox.isError && <p role="alert" className="text-danger">{captureError(t, inbox.error)}</p>}
      {inbox.isPending && <div className="h-64 animate-pulse rounded-lg bg-muted" />}
      {inbox.isSuccess && rows.length === 0 && (
        <div className="rounded-lg border bg-card p-8 text-center" data-testid="inbox-empty">
          <p className="font-medium">{filtered ? t("capture.inbox.emptyFiltered") : t("capture.inbox.empty")}</p>
          {!filtered && canWrite && <p className="mt-1 text-sm text-muted-foreground">{t("capture.inbox.emptyHint")}</p>}
        </div>
      )}
      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border bg-card">
          <table className="w-full text-sm" data-testid="inbox-table">
            <thead><tr className="border-b text-left text-muted-foreground">
              {(["name", "type", "channel", "submitter", "status", "records", "submitted", "actions"] as const).map((c) => <th key={c} className={`px-0 py-2 pr-3 font-medium first:pl-3 ${c === "records" || c === "actions" ? "text-right" : ""}`}>{t(`capture.inbox.col.${c}`)}</th>)}
            </tr></thead>
            <tbody className="[&_td:first-child]:pl-3 [&_td:last-child]:pr-3">
              {rows.map((r) => <InboxRow key={r.document.id} item={r} canReview={canReview} canReport={canReport} onAction={(a, item) => setAct({ a, item })} />)}
            </tbody>
          </table>
        </div>
      )}
      {total > LIMIT && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <span className="text-muted-foreground">{t("capture.inbox.pageInfo", { from: offset + 1, to: Math.min(offset + LIMIT, total), total })}</span>
          <Button size="sm" variant="outline" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - LIMIT))}>{t("capture.inbox.prev")}</Button>
          <Button size="sm" variant="outline" disabled={offset + LIMIT >= total} onClick={() => setOffset((o) => o + LIMIT)}>{t("capture.inbox.next")}</Button>
        </div>
      )}
      <SourceDrawer documentId={act?.a === "source" ? act.item.document.id : null} filename={act?.item.document.original_filename} onClose={close} />
      <ActionsHistory documentId={act?.a === "history" ? act.item.document.id : null} onClose={close} />
      <IncidentDialog documentId={act?.a === "incident" ? act.item.document.id : null} onClose={close} />
      {act?.a === "undo" && <UndoDialog documentId={act.item.document.id} deadline={act.item.undo_deadline} open onClose={close} />}
    </div>
  );
}
