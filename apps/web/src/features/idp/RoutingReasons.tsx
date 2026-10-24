"use client";
import { useTranslations } from "next-intl";
import { AlertTriangle } from "lucide-react";

const KNOWN = new Set(["CRITICAL_FIELD", "LOW_CLASSIFICATION_CONFIDENCE", "LOW_DOCUMENT_CONFIDENCE", "VALIDATION_FAILED", "SUSPICIOUS_CONTENT", "C5_REVIEW", "MISSING_TARGET_PERMISSION"]);

/** Why a document is in review (`routing_reasons`, pipeline / C1 / C5 codes) — i18n per code, `LOW_CONFIDENCE:<field>` carries the field. */
export function routingLabel(t: ReturnType<typeof useTranslations>, code: string): string {
  const [head = "", arg] = code.split(":");
  const key = head.toUpperCase();
  if (key === "LOW_CONFIDENCE") return t("idp.routing.LOW_CONFIDENCE", { field: arg ?? "" });
  return KNOWN.has(key) ? t(`idp.routing.${key}` as "idp.routing.C5_REVIEW") : t("idp.routing.other", { code });
}

export function RoutingReasons({ reasons }: { reasons: string[] }) {
  const t = useTranslations();
  if (!reasons.length) return null;
  const suspicious = reasons.some((r) => r.toUpperCase() === "SUSPICIOUS_CONTENT");
  return (
    <div className={`flex flex-wrap items-center gap-2 rounded border px-3 py-2 text-sm ${suspicious ? "border-danger bg-danger-subtle" : "border-warning bg-warning-subtle"}`} data-testid="routing-reasons">
      <AlertTriangle className="h-4 w-4" aria-hidden />
      <span className="font-medium">{t("idp.routing.title")}:</span>
      {reasons.map((r) => <span key={r} className="rounded bg-card px-2 py-0.5" data-testid="routing-reason" data-code={r}>{routingLabel(t, r)}</span>)}
    </div>
  );
}
