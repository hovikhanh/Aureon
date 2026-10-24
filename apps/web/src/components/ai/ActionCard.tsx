"use client";
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Check, Pencil, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatDateTime, formatMoney, type AppLocale } from "@/lib/format";
import { canDecide, diffEdits, isEditable, isMoneyField, selfServiceHref, type CardAction } from "./action-card-logic";

export interface ActionCardProps {
  action: CardAction & { created_at?: string | null; agent_profile_code?: string | null };
  viewerId: string;
  permissions: string[];
  onConfirm?: (edited?: Record<string, unknown>) => Promise<void>;
  onReject?: (reason: string) => Promise<void>;
  /** Extra header line (e.g. "for <user>" in the SCR-64 queue). */
  meta?: React.ReactNode;
  /** API error → i18n text (caller owns the error mapping). */
  errorText?: (e: unknown) => string;
}

/**
 * ActionCard (06 §5.1, R-DEC-78): autonomy label (L1 AI gợi ý / L2 AI soạn / L3 AI đã làm, `ai` token),
 * action name i18n, `input_preview` key–value (money per P04). Confirm (editable fields) / Reject (reason)
 * only for the served user; L1 = "Tự làm" deep link (not stored).
 */
export function ActionCard({ action, viewerId, permissions, onConfirm, onReject, meta, errorText }: ActionCardProps) {
  const t = useTranslations("aiAction");
  const locale = useLocale() as AppLocale;
  const preview = action.input_preview ?? {};
  const decide = canDecide(action, viewerId, permissions);
  const [mode, setMode] = React.useState<"view" | "edit" | "reject">("view");
  const [edits, setEdits] = React.useState<Record<string, string>>({});
  const [reason, setReason] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const actName = action.action_name.replace(/^ACT-/, "");
  const show = (k: string, v: unknown) => (isMoneyField(k) && typeof v === "number" ? formatMoney(v, locale) : String(v ?? "—"));
  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try { await fn(); setMode("view"); } catch (e) { setError(errorText ? errorText(e) : t("error")); } finally { setBusy(false); }
  };
  return (
    <article className="flex flex-col gap-2 rounded-lg border border-ai/40 bg-card p-3 text-sm" data-testid="action-card" data-action={action.id ?? actName} data-status={action.status ?? "suggested"}>
      <header className="flex flex-wrap items-center gap-2">
        <Badge variant="ai" data-testid="action-level">{t(`level.${action.autonomy_level}` as "level.L2")}</Badge>
        <span className="font-medium">{t.has(`name.${actName}` as "name.create_task") ? t(`name.${actName}` as "name.create_task") : actName}</span>
        {action.status && action.status !== "proposed" && <Badge variant="outline" data-testid="action-status">{t(`status.${action.status}` as "status.executed")}</Badge>}
        {action.created_at && <span className="ml-auto text-xs text-muted-foreground">{formatDateTime(action.created_at, locale)}</span>}
      </header>
      {meta}
      <dl className="grid grid-cols-[minmax(6rem,auto)_1fr] gap-x-3 gap-y-1" data-testid="action-preview">
        {Object.entries(preview).map(([k, v]) => (
          <React.Fragment key={k}>
            <dt className="text-muted-foreground">{t.has(`field.${k}` as "field.title") ? t(`field.${k}` as "field.title") : k}</dt>
            <dd>{mode === "edit" && isEditable(k, v)
              ? <Input aria-label={k} className="h-8" defaultValue={String(v ?? "")} onChange={(e) => setEdits({ ...edits, [k]: e.target.value })} data-testid={`action-edit-${k}`} />
              : show(k, v)}</dd>
          </React.Fragment>
        ))}
      </dl>
      {action.autonomy_level === "L1" && (
        <div><Button asChild size="sm" variant="outline"><Link href={selfServiceHref(action.action_name)} data-testid="action-self">{t("doItMyself")}</Link></Button></div>
      )}
      {decide && mode === "reject" && (
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium" htmlFor={`rej-${action.id}`}>{t("rejectReason")}</label>
          <Input id={`rej-${action.id}`} value={reason} onChange={(e) => setReason(e.target.value)} data-testid="action-reject-reason" />
        </div>
      )}
      {error && <p role="alert" className="text-xs text-danger" data-testid="action-error">{error}</p>}
      {decide && (
        <footer className="flex flex-wrap gap-2">
          {mode === "reject" ? (
            <>
              <Button size="sm" variant="danger" disabled={busy || !reason.trim()} onClick={() => void run(() => onReject!(reason.trim()))} data-testid="action-reject-submit">{t("reject")}</Button>
              <Button size="sm" variant="ghost" onClick={() => setMode("view")}>{t("cancel")}</Button>
            </>
          ) : (
            <>
              <Button size="sm" variant="ai" disabled={busy} onClick={() => void run(() => onConfirm!(diffEdits(preview, edits)))} data-testid="action-confirm"><Check className="h-4 w-4" aria-hidden />{t("confirm")}</Button>
              {mode === "view" && <Button size="sm" variant="outline" onClick={() => setMode("edit")} data-testid="action-edit"><Pencil className="h-4 w-4" aria-hidden />{t("edit")}</Button>}
              <Button size="sm" variant="ghost" onClick={() => setMode("reject")} data-testid="action-reject"><X className="h-4 w-4" aria-hidden />{t("reject")}</Button>
            </>
          )}
        </footer>
      )}
    </article>
  );
}
