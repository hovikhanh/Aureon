/**
 * `/meetings` (SCR-44, M2.3) — pure, node-testable logic for the natural-language capture preview
 * (EP-DC-38) and the chair-approval of predicted action items. No DOM/React here.
 *
 * EP-DC-38 returns a NOT-committed `NaturalLanguagePreviewOut`: a classified document plus
 * `predicted_actions` (ACT-create_action_item steps). A Task is created ONLY after the chair
 * approves a predicted item (L2 "AI soạn"); an owner that is `ambiguous`/`unmatched` must be
 * resolved by a human first (R-DEC-103).
 */
import type { Api } from "@aureon/shared-types";

type ExtractedFieldPreviewOut = Api.ExtractedFieldPreviewOut;
type NaturalLanguagePreviewOut = Api.NaturalLanguagePreviewOut;
type PredictedActionOut = Api.PredictedActionOut;

/** Fuzzy owner match (execution.name_match_status, R-DEC-103). */
export type MatchStatus = "matched" | "ambiguous" | "unmatched";

export const MATCH_STATUSES: readonly MatchStatus[] = ["matched", "ambiguous", "unmatched"] as const;

/** ConfidenceBadge-style variant per match status (reuses the success/warning/danger scale). */
export const MATCH_VARIANT: Record<MatchStatus, "success" | "warning" | "danger"> = {
  matched: "success",
  ambiguous: "warning",
  unmatched: "danger",
};

/** i18n key for a match status under `meetings.match.*`. */
export const matchKey = (s: MatchStatus): string => `match.${s}`;

/** The owner match status a predicted action carries (mock/backend puts it in `params`). */
export function ownerMatch(a: PredictedActionOut): MatchStatus {
  const raw = a.params?.owner_match_status;
  return MATCH_STATUSES.includes(raw as MatchStatus) ? (raw as MatchStatus) : "unmatched";
}

/** A chair may only create a Task from an item whose owner is unambiguously matched. */
export function canCreateTask(a: PredictedActionOut): boolean {
  return a.action_name === "ACT-create_action_item" && ownerMatch(a) === "matched";
}

/** Human-readable owner name from the predicted action params (may be null). */
export function ownerName(a: PredictedActionOut): string | null {
  const v = a.params?.owner_name;
  return typeof v === "string" && v.trim() ? v : null;
}

export function actionTitle(a: PredictedActionOut): string {
  const v = a.params?.title;
  return typeof v === "string" ? v : "";
}

/** Count of predicted items blocked on a human owner decision. */
export function unresolvedOwners(preview: NaturalLanguagePreviewOut | undefined): number {
  if (!preview) return 0;
  return preview.predicted_actions.filter((a) => ownerMatch(a) !== "matched").length;
}

/** Extracted fields that are not masked (level-4 fields arrive as `{masked:true}`). */
export function visibleExtracted(fields: ExtractedFieldPreviewOut[]): ExtractedFieldPreviewOut[] {
  return fields.filter((f) => f.value !== null && f.value !== undefined);
}
