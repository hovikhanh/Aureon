"use client";
/**
 * SCR-64 `/admin/acceptance` (M3.5, R-DEC-145, 09 §2.2 / BRD §19.1) — read-only MVP acceptance
 * dashboard. One row per gate G1–G4 with its status badge, current value vs threshold, and the
 * source it reads (metric code or endpoint). An overall banner summarises the four gates. True
 * thresholds are confirmed at pilot; this page only reads existing instrumentation.
 */
import { useTranslations } from "next-intl";
import type { Api } from "@aureon/shared-types";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatValue, gateTone, overallStatus, type Tone } from "./logic";
import { useAcceptance } from "./use-acceptance";

const BADGE: Record<Tone, "success" | "warning" | "danger" | "outline"> = {
  success: "success",
  warning: "warning",
  danger: "danger",
  muted: "outline",
};

export function AcceptanceView() {
  // Root scope: BE gate keys are fully-qualified ("acceptance.g1", "acceptance.g1_threshold").
  const t = useTranslations();
  const tr = (k: string) => t(`acceptance.${k}`);
  const q = useAcceptance();
  const gates = q.data?.data.gates ?? [];
  const overall = overallStatus(gates.map((g) => g.status));

  return (
    <div className="mx-auto flex max-w-[1200px] flex-col gap-6" data-testid="acceptance-view">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{tr("title")}</h1>
          <p className="text-sm text-muted-foreground">{tr("subtitle")}</p>
        </div>
        {gates.length > 0 && (
          <Badge variant={BADGE[gateTone(overall)]} data-testid="acceptance-overall">
            {tr(`status.${overall}`)}
          </Badge>
        )}
      </div>
      {q.isLoading && <p className="text-sm text-muted-foreground">{tr("loading")}</p>}
      {q.isError && <p className="text-sm text-danger">{tr("loadError")}</p>}
      {q.data && gates.length === 0 && (
        <p className="text-sm text-muted-foreground" data-testid="acceptance-empty">{tr("empty")}</p>
      )}
      {gates.length > 0 && (
        <ul className="flex flex-col gap-3" data-testid="acceptance-gates">
          {gates.map((g) => (
            <GateRow key={g.gate} g={g} t={t} tr={tr} />
          ))}
        </ul>
      )}
    </div>
  );
}

function GateRow({
  g,
  t,
  tr,
}: {
  g: Api.AcceptanceGateOut;
  t: ReturnType<typeof useTranslations>;
  tr: (k: string) => string;
}) {
  return (
    <li>
      <Card className="flex flex-wrap items-center justify-between gap-3 p-4" data-testid="acceptance-gate">
        <div className="flex flex-col">
          <span className="font-medium">
            {g.gate} · {t.has(g.label_key) ? t(g.label_key) : g.label_key}
          </span>
          <span className="text-xs text-muted-foreground">
            {t.has(g.threshold_key) ? t(g.threshold_key) : g.threshold_key} · {tr("source")}: {g.source_ref}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm" data-testid="acceptance-gate-value">
            {formatValue(g.value, g.unit)}
          </span>
          <Badge variant={BADGE[gateTone(g.status)]} data-testid="acceptance-gate-status">
            {tr(`status.${g.status}`)}
          </Badge>
        </div>
      </Card>
    </li>
  );
}
