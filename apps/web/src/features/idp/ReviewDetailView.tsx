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
import { ApiError, api } from "@/lib/api-client";
import { display, FieldRow, MONEY_TYPES, type FieldDraft } from "./FieldRow";
import { RejectDialog } from "./RejectDialog";
import { SourceViewer } from "./SourceViewer";
import type { ApproveOut, FieldPatchOut, ReviewField } from "./types";
import { useReview, useReviewLock } from "./use-review";

const KNOWN = ["REVIEW_LOCKED", "CONFLICT_STATE", "VALIDATION_ERROR", "ACTION_REJECTED", "FORBIDDEN_ROLE"];

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
  const fields = React.useMemo(() => review.data?.fields ?? [], [review.data]);

  React.useEffect(() => {
    setDrafts(Object.fromEntries(fields.map((f) => [f.id, { confirmed: f.is_confirmed, value: display(f.effective_value), reason: f.correction_reason ?? "" }])));
  }, [fields]);

  const label = (f: ReviewField) => (t.has(`idp.fieldName.${f.field_name}`) ? t(`idp.fieldName.${f.field_name}` as "idp.fieldName.subtotal") : f.field_name) + (f.row_index !== null ? ` #${f.row_index + 1}` : "");
  const errMsg = (e: unknown) => (e instanceof ApiError && KNOWN.includes(e.code) ? t(`errors.${e.code}` as "errors.generic") : t("errors.generic"));

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
        const patched = await api.patch<FieldPatchOut>(`/idp/documents/${documentId}/fields`, { fields: edits }, review.ifMatch());
        if (!patched.validations_ok) {
          const byField = Object.fromEntries(patched.fields.filter((f) => f.validation.some((v) => v.status === "fail")).map((f) => [f.id, f.validation.filter((v) => v.status === "fail").map((v) => v.message).join("; ")]));
          setErrors(byField);
          client.setQueryData(["idp", "review", documentId], { ...review.data, fields: patched.fields, validation_errors: patched.validation_errors });
          toast.push(t("errors.VALIDATION_ERROR"), "danger");
          return;
        }
      }
      await api.post<ApproveOut>(`/idp/documents/${documentId}/review/approve`, {}, review.ifMatch());
      lock.markDecided();
      toast.push(t("idp.committed"));
      void client.invalidateQueries({ queryKey: ["idp"] });
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

  if (review.isPending) return <div className="h-96 animate-pulse rounded-lg bg-muted" />;
  if (review.isError || !review.data) return <p role="alert" className="text-danger">{errMsg(review.error)}</p>;
  const d = review.data;
  const active = fields.find((f) => f.id === activeId) ?? null;
  const decidable = ["NEEDS_REVIEW", "IN_REVIEW"].includes(d.document.status);

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
          {fields.map((f) => (
            <FieldRow key={f.id} field={f} label={label(f)} draft={drafts[f.id] ?? { confirmed: false, value: "", reason: "" }} error={errors[f.id]} active={f.id === activeId} disabled={busy || !decidable}
              onFocus={() => setActiveId(f.id)} onChange={(nd) => setDrafts((x) => ({ ...x, [f.id]: nd }))} />
          ))}
          <div className="sticky bottom-0 -mx-4 -mb-4 flex flex-wrap justify-end gap-2 border-t bg-card p-4">
            <RejectDialog disabled={busy || !decidable} onReject={reject} />
            <Button variant="success" onClick={() => void approve()} disabled={busy || !decidable} data-testid="approve">
              <Check className="h-4 w-4" aria-hidden />{busy ? t("idp.saving") : t("buttons.approve")}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
