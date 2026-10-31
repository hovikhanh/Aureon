"use client";
/**
 * InsightCard (06 §5.1, 03 §7.1, R-DEC-107/112): the 9-part grounded insight — Observation,
 * Evidence (SourceChip, every number clickable to lineage), Impact, Root Cause, Risk,
 * Recommendation, Expected Outcome, Confidence (Cao/TB/Thấp + reason), Action. "Tại sao?" expands
 * the reasoning parts; the headline (observation + evidence + confidence) is always visible.
 * AI-generated → the `ai` colour token + "AI gợi ý" badge (never presented as fact without source).
 */
import * as React from "react";
import { useTranslations } from "next-intl";
import { Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Api } from "@aureon/shared-types";
import { SourceChip } from "@/components/ai/SourceChip";
import { KrConfidence } from "@/features/goals/common";

type InsightOut = Api.InsightOut;

export function InsightCard({ insight }: { insight: InsightOut }) {
  const t = useTranslations("insight");
  const [open, setOpen] = React.useState(false);
  const band = insight.confidence.band.toUpperCase(); // high|medium|low → HIGH|...
  const sev = insight.severity ?? "info";
  return (
    <article
      className="flex flex-col gap-3 rounded-lg border-l-4 border-ai bg-card p-4 shadow-sm"
      data-testid="insight-card"
      data-kind={insight.kind}
      data-severity={sev}
    >
      <header className="flex flex-wrap items-center gap-2 text-xs font-medium text-ai">
        <Sparkles className="h-4 w-4" aria-hidden />
        <Badge variant="ai">{t("badge")}</Badge>
        {insight.pillar && <Badge variant="outline" data-testid="insight-pillar">{insight.pillar}</Badge>}
        <KrConfidence value={band} />
      </header>

      <p className="text-sm font-medium leading-relaxed" data-testid="insight-observation">
        {insight.observation}
      </p>

      {insight.evidence && insight.evidence.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5" data-testid="insight-evidence">
          <span className="text-xs text-muted-foreground">{t("evidence")}:</span>
          {insight.evidence.map((e, i) => (
            <SourceChip key={`${e.id}-${i}`} n={i + 1} source={e} />
          ))}
        </div>
      )}

      {insight.impact && (
        <p className="text-sm text-muted-foreground" data-testid="insight-impact">
          <span className="font-medium text-foreground">{t("impact")}: </span>{insight.impact}
        </p>
      )}

      <div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
          data-testid="insight-why"
        >
          {open ? t("hideWhy") : t("why")}
        </Button>
      </div>

      {open && (
        <dl className="flex flex-col gap-2 rounded border bg-muted/40 p-3 text-sm" data-testid="insight-reasoning">
          {insight.root_cause && (
            <Part term={t("rootCause")} desc={insight.root_cause} testid="insight-root-cause" />
          )}
          {insight.risk && <Part term={t("risk")} desc={insight.risk} testid="insight-risk" />}
          {insight.recommendations && insight.recommendations.length > 0 && (
            <div data-testid="insight-recommendation">
              <dt className="font-medium">{t("recommendation")}</dt>
              <dd>
                <ul className="list-disc pl-5">
                  {insight.recommendations.map((r, i) => (
                    <li key={i}>{r.text}</li>
                  ))}
                </ul>
              </dd>
            </div>
          )}
          {insight.expected_outcome && (
            <Part
              term={t("expectedOutcome")}
              desc={JSON.stringify(insight.expected_outcome)}
              testid="insight-expected-outcome"
            />
          )}
          <Part term={t("confidence")} desc={insight.confidence.reason} testid="insight-confidence-reason" />
        </dl>
      )}
    </article>
  );
}

function Part({ term, desc, testid }: { term: string; desc: string; testid: string }) {
  return (
    <div data-testid={testid}>
      <dt className="font-medium">{term}</dt>
      <dd className="text-muted-foreground">{desc}</dd>
    </div>
  );
}
