"use client";
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { captureError } from "@/features/capture/errors";
import { UndoDialog } from "@/features/capture/UndoDialog";
import { commitDocument, invalidateWrites, useDocument, useImportRows } from "@/features/capture/use-capture";
import { todayIso, useOrgTree } from "@/features/admin/org/use-org";
import type { StepProps } from "./OnboardingWizard";

const WAITING = ["NEEDS_REVIEW", "IN_REVIEW", "VALIDATING"];

/**
 * Step 3 — review: tree to be created (valid rows of the import grouped by department) + error rows; the C5
 * document goes through review (R-DEC-62) → `APPROVED` → commit EP-DC-23 (Action Registry, undo 7 days) →
 * real tree EP-ORG-24 next to "Undo import" (EP-DC-24) → `complete_step review`.
 */
export function ReviewStep({ state, patch, goTo }: StepProps) {
  const t = useTranslations();
  const toast = useToast();
  const client = useQueryClient();
  const refs = (state.steps?.org_import?.refs ?? {}) as Record<string, unknown>;
  const docId = typeof refs.document_id === "string" ? refs.document_id : null;
  const batchId = typeof refs.org_import_id === "string" ? refs.org_import_id : "";
  const doc = useDocument(docId);
  const status = doc.data?.status ?? "";
  const [busy, setBusy] = React.useState(false);
  const [undoOpen, setUndoOpen] = React.useState(false);
  const refetch = doc.refetch;
  React.useEffect(() => {
    if (!WAITING.includes(status)) return;
    const id = setInterval(() => void refetch(), 10_000);
    return () => clearInterval(id);
  }, [status, refetch]);

  if (!docId) return <p className="text-sm text-muted-foreground">{t("onboarding.review.noImport")}</p>;
  if (doc.isPending) return <div className="h-40 animate-pulse rounded bg-muted" />;
  if (doc.isError) return <p role="alert" className="text-danger">{captureError(t, doc.error)}</p>;

  const commit = async () => {
    setBusy(true);
    try {
      await commitDocument(docId, doc.data.version);
      invalidateWrites(client);
      toast.push(t("onboarding.review.committed"));
    } catch (e) { toast.push(captureError(t, e), "danger"); } finally { setBusy(false); }
  };
  const confirm = async () => {
    setBusy(true);
    try { await patch(state, "complete_step", "review", { document_id: docId }); goTo("users"); } catch (e) { toast.push(captureError(t, e), "danger"); } finally { setBusy(false); }
  };

  return (
    <div className="flex flex-col gap-4" data-testid="review-step" data-doc-status={status}>
      <p className="text-sm text-muted-foreground">{t("onboarding.review.hint")}</p>
      {status === "COMMITTED" ? (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-success" data-testid="review-committed">{t("onboarding.review.committed")}</span>
            <span className="flex-1" />
            <Button variant="outline" onClick={() => setUndoOpen(true)} data-testid="review-undo"><Undo2 className="h-4 w-4" aria-hidden />{t("onboarding.review.undo")}</Button>
            <Button onClick={() => void confirm()} disabled={busy} data-testid="review-confirm">{t("onboarding.saveContinue")}</Button>
          </div>
          <RealTree />
          <UndoDialog documentId={docId} deadline={doc.data.undo_deadline ?? null} open={undoOpen} onClose={() => { setUndoOpen(false); void doc.refetch(); }} />
        </>
      ) : (
        <>
          {WAITING.includes(status) && <p role="status" className="rounded border border-warning bg-warning-subtle p-3 text-sm" data-testid="review-waiting">{t("onboarding.review.waiting")}</p>}
          {status === "APPROVED" && (
            <div className="flex items-center gap-3"><span className="flex-1 text-sm">{t("onboarding.review.approved")}</span>
              <Button onClick={() => void commit()} disabled={busy} data-testid="review-commit">{t("onboarding.review.commit")}</Button></div>
          )}
          {["REJECTED", "ROLLED_BACK", "FAILED"].includes(status) && (
            <div className="flex items-center gap-3"><span role="alert" className="flex-1 text-sm text-danger" data-testid="review-rejected">{t("onboarding.review.rejected")}</span>
              <Button variant="outline" onClick={() => goTo("org_import")}>{t("onboarding.review.reimport")}</Button></div>
          )}
          <PlannedTree batchId={batchId} />
        </>
      )}
    </div>
  );
}

/** Tree to be created — valid rows of the import grouped by `department_code` (preview, before commit). */
function PlannedTree({ batchId }: { batchId: string }) {
  const t = useTranslations();
  const valid = useImportRows(batchId, { status: "valid", limit: 100 }, Boolean(batchId));
  const invalid = useImportRows(batchId, { status: "invalid", limit: 100 }, Boolean(batchId));
  const groups = new Map<string, number>();
  for (const r of valid.data?.data ?? []) {
    const k = String((r.values as Record<string, unknown>).department_code ?? "—");
    groups.set(k, (groups.get(k) ?? 0) + 1);
  }
  const bad = invalid.data?.data ?? [];
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <section aria-label={t("onboarding.review.planned")} data-testid="planned-tree">
        <h3 className="mb-2 text-sm font-medium">{t("onboarding.review.planned")}</h3>
        <ul className="text-sm">{[...groups].map(([d, n]) => <li key={d} className="flex justify-between border-b py-1" data-testid="planned-dept"><span>{d}</span><span>{t("onboarding.review.people", { n })}</span></li>)}</ul>
      </section>
      <section aria-label={t("onboarding.review.errors")}>
        <h3 className="mb-2 text-sm font-medium">{t("onboarding.review.errors")} ({bad.length})</h3>
        <ul className="text-sm text-danger" data-testid="planned-errors">{bad.map((r) => <li key={r.row_number}>{t("capture.import.row", { n: r.row_number })}: {r.errors.map((e) => e.field ?? e.rule_code).join(", ")}</li>)}</ul>
      </section>
    </div>
  );
}

/** Real tree EP-ORG-24 after commit. */
function RealTree() {
  const t = useTranslations();
  const tree = useOrgTree(todayIso());
  if (tree.isPending) return <div className="h-32 animate-pulse rounded bg-muted" />;
  if (tree.isError) return <p role="alert" className="text-danger">{t("errors.generic")}</p>;
  return (
    <section aria-label={t("onboarding.review.real")} data-testid="real-tree">
      <h3 className="mb-2 text-sm font-medium">{t("onboarding.review.real")}</h3>
      <ul className="grid gap-1 text-sm sm:grid-cols-2">{tree.data.data.departments.map((d) => <li key={d.id} className="flex justify-between rounded border px-2 py-1" data-testid="real-dept"><span>{d.code} — {d.name}</span><span>{t("onboarding.review.people", { n: d.headcount })}</span></li>)}</ul>
    </section>
  );
}
