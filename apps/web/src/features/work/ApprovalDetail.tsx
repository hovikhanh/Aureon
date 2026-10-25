"use client";
/** SCR-43 detail (EP-WF-02) + decide (EP-WF-03): payload diff, timeline, Approve / Reject (reason required); 409 → banner + reload. */
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, apiRequest } from "@/lib/api-client";
import { formatDateTime, type AppLocale } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { ConfirmDialog } from "@/features/admin/common";
import { LoadError, useWorkError } from "./common";
import Link from "next/link";
import { useApprovalTitle, useMemberName } from "./ApprovalsView";
import { shortId } from "./logic";
import { useApproval, useWorkMutation } from "./use-work";

const cellText = (v: unknown) => (v === null || v === undefined ? "—" : typeof v === "object" ? JSON.stringify(v) : String(v));

/** `assignee_id` diff values are employee ids → names from `members[]` when readable. */
const ID_FIELDS = new Set(["assignee_id"]);

export function ApprovalDetail({ id, canReadOrg, onDone }: { id: string; canReadOrg: boolean; onDone: () => void }) {
  const t = useTranslations("work");
  const locale = useLocale() as AppLocale;
  const toast = useToast();
  const errText = useWorkError();
  const qc = useQueryClient();
  const title = useApprovalTitle(canReadOrg);
  const nameOf = useMemberName(canReadOrg);
  const valueText = (field: unknown, v: unknown) => (ID_FIELDS.has(String(field)) && typeof v === "string" ? (nameOf(v) ?? shortId(v)) : cellText(v));
  const q = useApproval(id);
  const [dialog, setDialog] = React.useState<null | "approve" | "reject">(null);
  const [conflict, setConflict] = React.useState(false);
  React.useEffect(() => setConflict(false), [id]);
  const decide = useWorkMutation((v: { decision: "approve" | "reject"; reason: string }) =>
    apiRequest(`/workflow/approval-requests/${id}/decide`, { method: "POST", idempotent: true, body: { decision: v.decision, reason: v.reason || null } }));
  const run = async (decision: "approve" | "reject", reason: string) => {
    try {
      await decide.mutateAsync({ decision, reason });
      toast.push(t(decision === "approve" ? "toast.approved" : "toast.rejected"));
      onDone();
    } catch (e) {
      if (e instanceof ApiError && e.code === "CONFLICT_STATE") {
        setConflict(true);
        setDialog(null);
        await qc.invalidateQueries({ queryKey: ["workflow"] });
        return;
      }
      toast.push(errText(e), "danger");
      throw e; // also shown inside the dialog
    }
  };
  const a = q.data;
  const diff = a?.payload_diff ?? [];
  const timeline = a?.timeline ?? [];
  return (
    <Card className="flex flex-col gap-4 p-4" data-testid="approval-detail">
      <h3 className="text-sm font-semibold">{t("approvals.detail")}</h3>
      {conflict && <p role="alert" className="rounded border border-warning bg-warning-subtle p-2 text-sm" data-testid="approval-conflict">{t("approvals.conflict")}</p>}
      {q.isError && <LoadError onRetry={() => void q.refetch()} />}
      {a && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium" data-testid="approval-title">{title(a)}</span>
            <Badge variant={a.status === "PENDING" ? "warning" : a.status === "APPROVED" ? "success" : "default"} data-testid="approval-status">{t(`approvalStatus.${a.status}`)}</Badge>
            {a.target_kind === "task_reassign" && a.target_id && (
              <Link href={`/work?task=${a.target_id}`} className="text-xs font-medium text-primary hover:underline" data-testid="approval-open-task">{t("approvals.openTask")}</Link>
            )}
          </div>
          <section>
            <h4 className="mb-1 text-xs font-medium text-muted-foreground">{t("approvals.diff")}</h4>
            <table className="w-full text-sm" data-testid="approval-diff">
              <thead className="text-left text-xs text-muted-foreground"><tr><th className="py-1">{t("approvals.field")}</th><th>{t("approvals.before")}</th><th>{t("approvals.after")}</th></tr></thead>
              <tbody>
                {diff.map((d, i) => (
                  <tr key={i} className="border-t"><td className="py-1 font-mono text-xs">{cellText(d.field)}</td><td className="text-muted-foreground line-through" data-raw={cellText(d.before)}>{valueText(d.field, d.before)}</td><td className="font-medium" data-raw={cellText(d.after)}>{valueText(d.field, d.after)}</td></tr>
                ))}
              </tbody>
            </table>
          </section>
          <section>
            <h4 className="mb-1 text-xs font-medium text-muted-foreground">{t("approvals.timeline")}</h4>
            {!timeline.length && <p className="text-sm text-muted-foreground">{t("approvals.noTimeline")}</p>}
            <ol className="flex flex-col gap-1 text-sm" data-testid="approval-timeline">
              {timeline.map((s, i) => (
                <li key={i} className="flex flex-wrap gap-2">
                  <span className="font-medium">{s.step === 0 && a.requested_by_name ? a.requested_by_name : s.actor_ref ? shortId(s.actor_ref) : "—"}</span>
                  <span>{["requested", "approve", "reject"].includes(s.decision) ? t(`approvals.decision.${s.decision as "approve"}`) : s.decision}</span>
                  {s.reason && <span className="text-muted-foreground">“{s.reason}”</span>}
                  {s.at && <span className="text-xs text-muted-foreground">{formatDateTime(s.at, locale)}</span>}
                </li>
              ))}
            </ol>
          </section>
          {a.status === "PENDING" && (
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDialog("reject")} data-testid="approval-reject">{t("approvals.reject")}</Button>
              <Button variant="success" onClick={() => setDialog("approve")} data-testid="approval-approve">{t("approvals.approve")}</Button>
            </div>
          )}
        </>
      )}
      <ConfirmDialog open={dialog === "approve"} onOpenChange={(o) => !o && setDialog(null)} title={t("approvals.approveTitle")} body={t("approvals.approveBody")}
        confirmLabel={t("approvals.approve")} testId="approve-dialog" onConfirm={(r) => run("approve", r)} />
      <ConfirmDialog open={dialog === "reject"} onOpenChange={(o) => !o && setDialog(null)} title={t("approvals.rejectTitle")} body={t("approvals.rejectBody")}
        confirmLabel={t("approvals.reject")} danger reasonRequired testId="reject-dialog" onConfirm={(r) => run("reject", r)} />
    </Card>
  );
}
