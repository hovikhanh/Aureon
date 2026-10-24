"use client";
import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { ArrowLeft, Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { UndoToast } from "@/components/ai/UndoToast";
import { ApiError, api, apiRequest } from "@/lib/api-client";
import { captureError } from "@/features/capture/errors";
import { commitDocument, invalidateWrites, undoDocument } from "@/features/capture/use-capture";
import { display, FieldRow, MONEY_TYPES, type FieldDraft } from "./FieldRow";
import { PlannedActions } from "./PlannedActions";
import { RejectDialog } from "./RejectDialog";
import { RowGrid } from "./RowGrid";
import { SourceViewer } from "./SourceViewer";
import type { ApproveOut, FieldPatchOut, ReviewField } from "./types";
import { useReview, useReviewLock } from "./use-review";

const KNOWN = ["REVIEW_LOCKED", "CONFLICT_STATE", "VALIDATION_ERROR", "ACTION_REJECTED", "FORBIDDEN_ROLE"];
const reviewErr = (t: ReturnType<typeof useTranslations>, e: unknown) =>
  e instanceof ApiError && (typeof e.details.reason === "string" || Array.isArray(e.details.missing)) ? captureError(t, e) : e instanceof ApiError && KNOWN.includes(e.code) ? t(`errors.${e.code}` as "errors.generic") : t("errors.generic");

export function ReviewDetailView({ documentId }: { documentId: string }) {
  const t = useTranslations();
  const router = useRouter();
  const toast = useToast();
  const client = useQueryClient();
  const review = useReview(documentId);
  const lock = useReviewLock(documentId, review.isSuccess);
  const [drafts, setDrafts] = React.useState<Record<string, FieldDraft>>({});
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [committed, setCommitted] = React.useState<ApproveOut | null>(null);
  const fields = React.useMemo(() => review.data?.fields ?? [], [review.data]);

  React.useEffect(() => {
    setDrafts(Object.fromEntries(fields.map((f) => [f.id, { confirmed: f.is_confirmed, value: display(f.effective_value), reason: f.correction_reason ?? "" }])));
  }, [fields]);

  const label = (f: ReviewField) => (t.has(`idp.fieldName.${f.field_name}`) ? t(`idp.fieldName.${f.field_name}` as "idp.fieldName.subtotal") : f.field_name) + (f.row_index !== null ? ` #${f.row_index + 1}` : "");
  const errMsg = (e: unknown) => reviewErr(t, e);

  const validate = (): boolean => {
    const next: Record<string, string> = {};
    for (const f of fields) {
      const d = drafts[f.id];
      if (d && d.value !== display(f.effective_value) && MONEY_TYPES.has(f.value_type) && !d.reason.trim()) next[f.id] = t("idp.field.reasonRequired");
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const approve = async () => {
    if (!validate()) return;
    setBusy(true);
    try {
      const edits = fields.flatMap((f) => {
        const d = drafts[f.id];
        if (!d) return [];
        if (d.value !== display(f.effective_value)) return [{ field_id: f.id, action: d.value === "" ? "clear" : "correct", value: d.value === "" ? null : d.value, reason: d.reason || null }];
        if (d.confirmed && !f.is_confirmed) return [{ field_id: f.id, action: "confirm", value: null, reason: null }];
        return [];
      });
      if (edits.length) {
        const patched = await api.patch<FieldPatchOut>(`/idp/documents/${documentId}/fields`, { fields: edits });
        if (!patched.validations_ok) {
          const byField = Object.fromEntries(patched.fields.filter((f) => f.validation.some((v) => v.status === "fail")).map((f) => [f.id, f.validation.filter((v) => v.status === "fail").map((v) => v.message).join("; ")]));
          setErrors(byField);
          client.setQueryData(["idp", "review", documentId], { ...review.data, fields: patched.fields, validation_errors: patched.validation_errors });
          toast.push(t("errors.VALIDATION_ERROR"), "danger");
          return;
        }
      }
      const res = await apiRequest<ApproveOut>(`/idp/documents/${documentId}/review/approve`, { method: "POST", body: { version: review.data?.document.version }, idempotent: true });
      lock.markDecided();
      invalidateWrites(client);
      const pending = (res.meta?.pending_permissions ?? []) as string[];
      if (res.data.document.status === "APPROVED") toast.push(t("capture.review.approvedPending", { perms: pending.join(", ") }), "info");
      else if (res.data.actions.length) return setCommitted(res.data);
      else toast.push(t("idp.committed"));
      router.push("/data/review");
    } catch (e) {
      toast.push(errMsg(e), "danger");
    } finally {
      setBusy(false);
    }
  };

  const reject = async (reason: string) => {
    await api.post(`/idp/documents/${documentId}/review/reject`, { reason });
    lock.markDecided();
    toast.push(t("idp.rejected"));
    void client.invalidateQueries({ queryKey: ["idp"] });
    router.push("/data/review");
  };

  const commit = async () => {
    setBusy(true);
    try {
      const out = await commitDocument(documentId, review.data?.document.version);
      invalidateWrites(client);
      setCommitted(out as unknown as ApproveOut);
    } catch (e) {
      toast.push(errMsg(e), "danger");
    } finally {
      setBusy(false);
    }
  };

  if (review.isPending) return <div className="h-96 animate-pulse rounded-lg bg-muted" />;
  if (review.isError || !review.data) return <p role="alert" className="text-danger">{errMsg(review.error)}</p>;
  const d = review.data;
  const active = fields.find((f) => f.id === activeId) ?? null;
  const decidable = ["NEEDS_REVIEW", "IN_REVIEW"].includes(d.document.status) && !committed;
  const planned = d.planned_actions ?? [];
  const pendingWrite = planned.some((p) => !p.permitted);
  const criticalLeft = fields.filter((f) => f.is_critical && !(drafts[f.id]?.confirmed ?? f.is_confirmed)).length;
  const gridRows = d.rows ?? [];
  const activeRow = active?.row_index ?? null;
  const editorFields = gridRows.length ? fields.filter((f) => f.row_index === null || f.row_index === activeRow) : fields;
  /** Confirms every field of the selected row, then moves to the next row (keyboard-friendly walk through the grid). */
  const confirmRow = () => {
    setDrafts((x) => ({ ...x, ...Object.fromEntries(fields.filter((f) => f.row_index === activeRow).map((f) => [f.id, { ...(x[f.id] ?? { value: display(f.effective_value), reason: "" }), confirmed: true }])) }));
    const next = gridRows.find((r) => activeRow !== null && r.row_index > activeRow);
    if (next?.fields[0]) setActiveId(next.fields[0].id);
  };
  const records = committed?.actions.reduce((n, a) => n + a.ids.length, 0) ?? 0;

  return (
    <div className="mx-auto flex max-w-[1600px] flex-col gap-4" data-testid="review-detail">
      <div className="flex flex-wrap items-center gap-3">
        <Link href="/data/review" className="flex items-center gap-1 text-sm text-primary"><ArrowLeft className="h-4 w-4" />{t("buttons.back")}</Link>
        <h1 className="min-w-0 truncate text-xl font-semibold">{d.document.original_filename ?? t("idp.detailTitle")}</h1>
        <Badge>{t(`idp.status.${d.document.status}` as "idp.status.NEEDS_REVIEW")}</Badge>
        <ConfidenceBadge value={d.document_confidence} />
      </div>
      {lock.lockError && <p role="alert" className="rounded border border-warning bg-warning-subtle px-3 py-2 text-sm">{t(KNOWN.includes(lock.lockError) ? (`errors.${lock.lockError}` as "errors.generic") : "errors.generic")}</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="lg:sticky lg:top-20 lg:h-[calc(100dvh-10rem)]"><SourceViewer pages={d.pages} active={active} fieldLabel={label} /></div>
        <Card className="flex flex-col gap-3 p-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">{t("idp.fields", { count: fields.length })}</h2>
            <span className={d.validation_errors.length ? "text-sm text-danger" : "text-sm text-success"}>
              {d.validation_errors.length ? `${t("idp.validationErrors")}: ${d.validation_errors.length}` : `✓ ${t("idp.validationOk")}`}
            </span>
          </div>
          {(gridRows.length > 0 || planned.length > 0) && (
            <div className="flex flex-col gap-3">
              {gridRows.length > 0 && <RowGrid rows={gridRows} activeId={activeId} onSelect={setActiveId} label={label} />}
              <PlannedActions items={planned} />
            </div>
          )}
          {gridRows.length > 0 && activeRow === null && <p className="text-sm text-muted-foreground">{t("capture.review.selectRow")}</p>}
          {gridRows.length > 0 && activeRow !== null && decidable && (
            <Button size="sm" variant="outline" className="self-start" onClick={confirmRow} data-testid="confirm-row">{t("capture.review.confirmRow")} · {t("capture.review.rowEditor", { n: activeRow })}</Button>
          )}
          {editorFields.map((f) => (
            <FieldRow key={f.id} field={f} label={label(f)} draft={drafts[f.id] ?? { confirmed: false, value: "", reason: "" }} error={errors[f.id]} active={f.id === activeId} disabled={busy || !decidable}
              onFocus={() => setActiveId(f.id)} onChange={(nd) => setDrafts((x) => ({ ...x, [f.id]: nd }))} />
          ))}
          <div className="sticky bottom-0 -mx-4 -mb-4 flex flex-wrap justify-end gap-2 border-t bg-card p-4">
            <RejectDialog disabled={busy || !decidable} onReject={reject} />
            {criticalLeft > 0 && decidable && <span className="mr-auto self-center text-sm text-danger" data-testid="critical-left">{t("capture.review.criticalLeft", { count: criticalLeft })}</span>}
            {d.document.status === "APPROVED" && !committed && <span className="mr-auto self-center text-sm text-muted-foreground" data-testid="approved-state">{t("capture.review.approvedState")}</span>}
            {d.can_commit && !committed && (
              <Button variant="success" onClick={() => void commit()} disabled={busy} data-testid="commit">
                <Check className="h-4 w-4" aria-hidden />{busy ? t("capture.review.committing") : t("capture.review.commit")}
              </Button>
            )}
            {d.document.status !== "APPROVED" && (
              <Button variant="success" onClick={() => void approve()} disabled={busy || !decidable || criticalLeft > 0} data-testid="approve">
                <Check className="h-4 w-4" aria-hidden />{busy ? t("idp.saving") : pendingWrite ? t("capture.review.approvePending") : t("buttons.approve")}
              </Button>
            )}
          </div>
        </Card>
      </div>
      {committed && (
        <UndoToast message={t("capture.review.committedToast", { count: records })} onClose={() => { setCommitted(null); router.push("/data/review"); }}
          onUndo={async () => { await undoDocument(documentId, t("capture.undo.quickReason"), "mistake"); invalidateWrites(client); toast.push(t("capture.undo.done", { count: committed.actions.length })); }} />
      )}
    </div>
  );
}
