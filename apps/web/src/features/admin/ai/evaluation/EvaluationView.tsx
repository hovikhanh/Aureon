"use client";
/**
 * SCR-64 `/admin/ai/evaluation` (M3.4, EP-AI-27/28, R-DEC-140) — read-only Evaluation Engine runs.
 * Each row is one standard-suite run (suite · prompt/model/provider) with its three axis scores
 * (grounding / accuracy / tool_choice) and overall score, colour-banded. Runs are produced by the
 * `run_eval` CLI — this view never triggers an LLM call.
 */
import { useTranslations } from "next-intl";
import type { Api } from "@aureon/shared-types";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { type Band, fmtPct, scoreBand, sortRunsByFinished } from "./logic";
import { useEvaluations } from "./use-evaluations";

const BAND_CLASS: Record<Band, string> = {
  good: "text-success",
  warn: "text-warning",
  bad: "text-danger",
};

function Score({ pct, label }: { pct: number; label: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={`font-mono text-sm font-semibold ${BAND_CLASS[scoreBand(pct)]}`}>{fmtPct(pct)}</span>
    </div>
  );
}

export function EvaluationView() {
  const t = useTranslations("aiEvaluation");
  const q = useEvaluations();
  const runs = sortRunsByFinished(q.data?.data ?? []);

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-6" data-testid="ai-evaluation-view">
      <div>
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>
      {q.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {q.isError && <p className="text-sm text-danger">{t("loadError")}</p>}
      {q.data && runs.length === 0 && (
        <p className="text-sm text-muted-foreground" data-testid="ai-evaluation-empty">{t("empty")}</p>
      )}
      {runs.length > 0 && (
        <ul className="flex flex-col gap-3" data-testid="ai-evaluation-runs">
          {runs.map((r) => (
            <EvaluationRow key={r.id} r={r} t={t} />
          ))}
        </ul>
      )}
    </div>
  );
}

function EvaluationRow({ r, t }: { r: Api.AIEvaluationOut; t: ReturnType<typeof useTranslations> }) {
  return (
    <li>
      <Card className="flex flex-col gap-3 p-4" data-testid="ai-evaluation-row">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{r.suite}</span>
            <Badge variant="outline">{r.prompt_version}</Badge>
            <span className="text-xs text-muted-foreground">
              {r.provider} · {r.model} · {r.gateway_mode}
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            {t("passed", { passed: r.passed, total: r.total })}
          </span>
        </div>
        <div className="flex flex-wrap gap-6">
          <Score pct={r.score_pct} label={t("axis.score")} />
          <Score pct={r.grounding_pct} label={t("axis.grounding")} />
          <Score pct={r.accuracy_pct} label={t("axis.accuracy")} />
          <Score pct={r.tool_choice_pct} label={t("axis.toolChoice")} />
        </div>
      </Card>
    </li>
  );
}
