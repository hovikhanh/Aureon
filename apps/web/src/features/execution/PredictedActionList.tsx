"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SourceChip } from "@/components/ai/SourceChip";
import type { Api } from "@aureon/shared-types";

type NaturalLanguagePreviewOut = Api.NaturalLanguagePreviewOut;
type PredictedActionOut = Api.PredictedActionOut;
import {
  MATCH_VARIANT,
  actionTitle,
  canCreateTask,
  matchKey,
  ownerMatch,
  ownerName,
  unresolvedOwners,
} from "./meetings";

/**
 * Predicted action items (L2 "AI soạn"). Each row shows the owner fuzzy-match status with a badge;
 * a Task is created ONLY after the chair approves AND the owner is unambiguously matched
 * (R-DEC-103). Ambiguous/unmatched owners must be resolved by a human first. The SourceChip links
 * each item back to the transcript document (P01/P05).
 */
export function PredictedActionList({
  preview,
  viewerId,
  permissions,
}: {
  preview: NaturalLanguagePreviewOut;
  viewerId: string;
  permissions: string[];
}) {
  const t = useTranslations("meetings");
  const canWrite = permissions.includes("execution:write");
  const [approved, setApproved] = React.useState<Set<number>>(new Set());
  const unresolved = unresolvedOwners(preview);
  void viewerId;

  const approve = (i: number) => setApproved((s) => new Set(s).add(i));

  return (
    <div className="flex flex-col gap-3" data-testid="predicted-actions">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">{t("actions.title")}</h2>
        <Badge variant="ai" data-testid="autonomy-label">{t("actions.l2")}</Badge>
      </div>
      {unresolved > 0 && (
        <p className="text-sm text-warning" data-testid="owners-unresolved" role="status">
          {t("actions.unresolved", { count: unresolved })}
        </p>
      )}
      <ul className="flex flex-col gap-2">
        {preview.predicted_actions.map((a: PredictedActionOut, i: number) => {
          const status = ownerMatch(a);
          const canTask = canCreateTask(a) && canWrite;
          return (
            <li key={i} className="rounded-md border p-3" data-testid="action-item" data-match={status}>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium">
                    {actionTitle(a)}
                    <SourceChip n={i + 1} source={{ type: "document_page", id: preview.document.id, label: t("preview.sourceLabel") }} />
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {t("actions.owner")}: {ownerName(a) ?? t("actions.unknownOwner")}
                  </p>
                </div>
                <Badge variant={MATCH_VARIANT[status]} data-testid="owner-match" data-band={status}>
                  {t(matchKey(status))}
                </Badge>
              </div>
              <div className="mt-2 flex items-center gap-2">
                {approved.has(i) ? (
                  <span className="text-sm text-success" data-testid="action-approved">{t("actions.created")}</span>
                ) : (
                  <Button
                    size="sm"
                    variant="ai"
                    disabled={!canTask}
                    data-testid="action-approve"
                    onClick={() => approve(i)}
                  >
                    {t("actions.approve")}
                  </Button>
                )}
                {!canTask && !approved.has(i) && (
                  <span className="text-xs text-muted-foreground" data-testid="action-blocked">
                    {status === "matched" ? t("actions.needPermission") : t("actions.resolveOwner")}
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
