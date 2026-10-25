"use client";
/**
 * SCR-43 `/work/approvals` (EP-WF-01..03): inbox `assigned_to=me` (kind, title_key+params,
 * requester, amount `1,2 tỷ`, due — overdue red, step); filters status (default PENDING) + kind;
 * detail panel `?id=<id>` (= notification link `/work/approvals?id=`) with `payload_diff` + timeline;
 * Approve / Reject (reason required) with Idempotency-Key; `409` → banner + reload. `params` carry ids
 * only → names from EP-ORG-24 `members[]` when the caller can read them (`canReadOrg`), else short ids.
 */
import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { formatDateTime, formatMoneyShort, type AppLocale } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { LoadError } from "./common";
import { ApprovalDetail } from "./ApprovalDetail";
import { approvalParams, approvalTitle } from "./logic";
import { useApprovals, useMembers, type ApprovalRequestOut } from "./use-work";

export const APPROVAL_STATUSES = ["PENDING", "APPROVED", "REJECTED", "EXPIRED", "CANCELLED"] as const;
export const APPROVAL_KINDS = ["task_reassign", "ai_action"] as const;

/** employee id → "Name" from `members[]` (cached query; disabled → undefined → short id). */
export function useMemberName(canReadOrg: boolean) {
  const members = useMembers(canReadOrg);
  const byId = React.useMemo(() => new Map((members.data ?? []).map((m) => [m.employee_id, m.full_name])), [members.data]);
  return React.useCallback((id: string) => byId.get(id), [byId]);
}

export function useApprovalTitle(canReadOrg: boolean) {
  const t = useTranslations("work");
  const nameOf = useMemberName(canReadOrg);
  return (a: Pick<ApprovalRequestOut, "title_key" | "target_kind" | "params">) => t(`approvalTitle.${approvalTitle(a.title_key, a.target_kind)}`, approvalParams(a.params, nameOf));
}

export function ApprovalsView({ canReadOrg }: { canReadOrg: boolean }) {
  const t = useTranslations("work");
  const locale = useLocale() as AppLocale;
  const sp = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const title = useApprovalTitle(canReadOrg);
  const status = (APPROVAL_STATUSES as readonly string[]).includes(sp.get("status") ?? "") ? (sp.get("status") as string) : "PENDING";
  const kind = (APPROVAL_KINDS as readonly string[]).includes(sp.get("kind") ?? "") ? (sp.get("kind") as string) : "";
  const selected = sp.get("id");
  const q = useApprovals({ status, target_kind: kind || null, sort_by: "due_at" });
  const set = (k: string, v: string | null) => {
    const next = new URLSearchParams(sp.toString());
    if (v) next.set(k, v);
    else next.delete(k);
    const qs = next.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };
  const rows = q.data?.data ?? [];
  return (
    <div className="flex flex-col gap-4" data-testid="approvals">
      <div>
        <h2 className="text-xl font-semibold">{t("approvals.title")}</h2>
        <p className="text-sm text-muted-foreground">{t("approvals.hint")}</p>
      </div>
      <Card className="flex flex-wrap items-end gap-3 p-3">
        <div className="flex flex-col gap-1">
          <Label htmlFor="ap-status" className="text-xs">{t("approvals.statusFilter")}</Label>
          <NativeSelect id="ap-status" value={status} onChange={(e) => set("status", e.target.value === "PENDING" ? null : e.target.value)} data-testid="ap-status">
            {APPROVAL_STATUSES.map((s) => <option key={s} value={s}>{t(`approvalStatus.${s}`)}</option>)}
          </NativeSelect>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="ap-kind" className="text-xs">{t("approvals.kind")}</Label>
          <NativeSelect id="ap-kind" value={kind} onChange={(e) => set("kind", e.target.value || null)} data-testid="ap-kind">
            <option value="">{t("approvals.allKinds")}</option>
            {APPROVAL_KINDS.map((k) => <option key={k} value={k}>{t(`approvalKind.${k}`)}</option>)}
          </NativeSelect>
        </div>
      </Card>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-2">
          {q.isError && <LoadError onRetry={() => void q.refetch()} />}
          {q.isSuccess && !rows.length && <p className="text-sm text-muted-foreground" data-testid="approvals-empty">{t("approvals.empty")}</p>}
          <ul className="flex flex-col gap-2" data-testid="approvals-list">
            {rows.map((a) => (
              <li key={a.id}>
                <button type="button" onClick={() => set("id", a.id)} aria-current={selected === a.id ? "true" : undefined} data-testid={`approval-${a.id}`} data-kind={a.target_kind}
                  className={cn("flex w-full flex-col gap-1 rounded-lg border bg-card p-3 text-left text-sm hover:bg-muted", selected === a.id && "border-primary")}>
                  <span className="flex flex-wrap items-center gap-2">
                    <Badge variant="primary">{t(`approvalKind.${a.target_kind === "task_reassign" ? "task_reassign" : "ai_action"}`)}</Badge>
                    <span className="font-medium">{title(a)}</span>
                  </span>
                  <span className="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
                    {a.requested_by_name && <span>{t("approvals.requester")}: {a.requested_by_name}</span>}
                    {a.amount !== null && a.amount !== undefined && <span data-testid="approval-amount">{t("approvals.amount")}: {formatMoneyShort(a.amount, locale)}</span>}
                    <span className={a.overdue ? "font-medium text-danger" : undefined} data-testid="approval-due">{t("approvals.dueAt")}: {formatDateTime(a.due_at, locale)}{a.overdue ? ` · ${t("approvals.overdue")}` : ""}</span>
                    <span>{t("approvals.step", { step: a.step })}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
        {selected ? <ApprovalDetail id={selected} canReadOrg={canReadOrg} onDone={() => set("id", null)} /> : <p className="text-sm text-muted-foreground">{t("approvals.select")}</p>}
      </div>
    </div>
  );
}
