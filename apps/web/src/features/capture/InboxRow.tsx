"use client";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { MoreHorizontal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { formatDateTime, type AppLocale } from "@/lib/format";
import type { InboxItem } from "./types";

export type RowAction = "source" | "undo" | "history" | "incident";
const TONE: Record<string, "success" | "danger" | "warning" | "default"> = { COMMITTED: "success", AUTO_APPROVED: "success", REJECTED: "danger", FAILED: "danger", NEEDS_REVIEW: "warning", IN_REVIEW: "warning", APPROVED: "warning" };

/** One SCR-45 row: name / type / channel / submitter / status / record count + row actions. */
export function InboxRow({ item, canReview, canReport, onAction }: { item: InboxItem; canReview: boolean; canReport: boolean; onAction: (a: RowAction, item: InboxItem) => void }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const d = item.document;
  const type = item.document_type ? (t.has(`capture.docType.${item.document_type}`) ? t(`capture.docType.${item.document_type}`) : item.document_type) : t("capture.docType.unknown");
  const name = d.kind === "MANUAL" ? t("capture.inbox.manualName", { type }) : d.original_filename ?? t("capture.inbox.noFile");
  const committed = ["COMMITTED", "AUTO_APPROVED", "ROLLED_BACK"].includes(d.status);
  const reviewable = canReview && ["NEEDS_REVIEW", "IN_REVIEW", "APPROVED"].includes(d.status);
  const importing = item.channel === "C5" && d.status === "VALIDATING" && item.batch_id;
  return (
    <tr className="border-b last:border-0" data-testid="inbox-row" data-status={d.status} data-doc={d.id}>
      <td className="max-w-72 py-2 pr-3"><span className="block truncate font-medium" title={name}>{name}</span></td>
      <td className="pr-3">{type}</td>
      <td className="pr-3 whitespace-nowrap">{t(`capture.channel.${item.channel}` as "capture.channel.C1")}</td>
      <td className="pr-3">{item.submitted_by_name ?? "—"}</td>
      <td className="pr-3"><Badge variant={TONE[d.status] ?? "default"} data-testid="inbox-status">{t.has(`capture.status.${d.status}`) ? t(`capture.status.${d.status}`) : d.status}</Badge></td>
      <td className="pr-3 text-right tabular-nums">{item.record_count ?? "—"}</td>
      <td className="pr-3 whitespace-nowrap tabular-nums">{formatDateTime(d.submitted_at, locale)}</td>
      <td className="whitespace-nowrap text-right">
        {reviewable && <Link href={`/data/review/${d.id}`} className="mr-2 text-sm text-primary hover:underline" data-testid="inbox-review">{t("capture.action.review")}</Link>}
        {importing && <Link href={`/data/imports/${item.batch_id}`} className="mr-2 text-sm text-primary hover:underline">{t("capture.action.import")}</Link>}
        {item.can_undo && <button type="button" className="mr-2 text-sm text-danger hover:underline" onClick={() => onAction("undo", item)} data-testid="inbox-undo">{t("capture.action.undo")}</button>}
        <DropdownMenu>
          <DropdownMenuTrigger className="rounded p-1 hover:bg-muted" aria-label={t("capture.action.more")} data-testid="inbox-more"><MoreHorizontal className="h-4 w-4" /></DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {d.kind !== "MANUAL" && <DropdownMenuItem onSelect={() => onAction("source", item)} data-testid="inbox-source">{t("capture.action.source")}</DropdownMenuItem>}
            {committed && <DropdownMenuItem onSelect={() => onAction("history", item)} data-testid="inbox-history">{t("capture.action.history")}</DropdownMenuItem>}
            {committed && canReport && d.status !== "ROLLED_BACK" && <DropdownMenuItem onSelect={() => onAction("incident", item)} data-testid="inbox-incident">{t("capture.action.incident")}</DropdownMenuItem>}
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}
