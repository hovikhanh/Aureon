"use client";
/** Shared bits of the M1.2 admin screens (T-617F): error text, page header, confirm-with-reason dialog. */
import * as React from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";

const KNOWN = ["FORBIDDEN_ROLE", "FORBIDDEN_SCOPE", "CONFLICT_STATE", "VALIDATION_ERROR", "DUPLICATE_RESOURCE", "BUSINESS_RULE_VIOLATION", "RATE_LIMIT_EXCEEDED"];
const REASONS = ["has_live_children", "parent_cycle", "overlap", "future", "team_outside_department", "position_outside_department", "manager_self", "self_change", "ai_not_grantable", "pillars_only_dir", "not_found"];

/** i18n text for an API error — `BUSINESS_RULE_VIOLATION` is refined by `details.reason`. */
export function useErrorText(): (e: unknown) => string {
  const t = useTranslations();
  return React.useCallback((e: unknown) => {
    if (!(e instanceof ApiError)) return t("errors.generic");
    const reason = String(e.details.reason ?? "");
    if (e.code === "BUSINESS_RULE_VIOLATION" && REASONS.includes(reason)) return t(`adminCommon.reason.${reason}` as "adminCommon.reason.overlap");
    return KNOWN.includes(e.code) ? t(`errors.${e.code}` as "errors.generic") : t("errors.generic");
  }, [t]);
}

export function AdminHeader({ title, hint, children }: { title: string; hint?: string; children?: React.ReactNode }) {
  const t = useTranslations();
  return (
    <div className="flex flex-col gap-1">
      <nav aria-label={t("adminCommon.breadcrumb")} className="text-xs text-muted-foreground">
        <Link href="/admin" className="hover:underline">{t("nav.admin")}</Link> › <span>{title}</span>
      </nav>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{title}</h1>
        <div className="flex flex-wrap items-center gap-2">{children}</div>
      </div>
      {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
    </div>
  );
}

/** Confirm dialog; `reasonRequired` adds a mandatory reason textarea (EP-ADM-09/10). */
export function ConfirmDialog({ open, onOpenChange, title, body, confirmLabel, danger, reasonRequired, onConfirm, testId }: {
  open: boolean; onOpenChange: (o: boolean) => void; title: string; body?: string; confirmLabel: string; danger?: boolean;
  reasonRequired?: boolean; onConfirm: (reason: string) => Promise<void>; testId: string;
}) {
  const t = useTranslations();
  const errText = useErrorText();
  const [reason, setReason] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  React.useEffect(() => { if (open) { setReason(""); setError(null); } }, [open]);
  const submit = async () => {
    if (reasonRequired && !reason.trim()) return setError(t("adminCommon.reasonRequired"));
    setBusy(true);
    try {
      await onConfirm(reason.trim());
      onOpenChange(false);
    } catch (e) {
      setError(errText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid={testId}>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription className={body ? "mt-2 text-sm text-muted-foreground" : "sr-only"}>{body ?? title}</DialogDescription>
        {reasonRequired && (
          <div className="mt-4 flex flex-col gap-1.5">
            <Label htmlFor={`${testId}-reason`}>{t("adminCommon.reason.label")}</Label>
            <textarea id={`${testId}-reason`} value={reason} onChange={(e) => { setReason(e.target.value); setError(null); }} rows={3} maxLength={500}
              aria-invalid={Boolean(error)} className="rounded border bg-card px-3 py-2 text-sm aria-[invalid=true]:border-danger" data-testid={`${testId}-reason`} />
          </div>
        )}
        {error && <p role="alert" className="mt-2 text-sm text-danger" data-testid={`${testId}-error`}>{error}</p>}
        <div className="mt-6 flex justify-end gap-2">
          <DialogClose asChild><Button variant="ghost">{t("buttons.cancel")}</Button></DialogClose>
          <Button variant={danger ? "danger" : "default"} onClick={() => void submit()} disabled={busy} data-testid={`${testId}-confirm`}>{confirmLabel}</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function Field({ id, label, error, children }: { id: string; label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}
