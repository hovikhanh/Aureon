"use client";
/**
 * F4 check-in card (SCR-60, 06 §4 F4): current value / target, new value, 3-step confidence,
 * note, blocker → EP-PRF-02 (KR) / EP-PRF-04 (KPI). M2.4 (R-DEC-109): "AI điền sẵn" suggests the
 * latest grounded value + a confidence bar; the user always confirms/edits before writing (never
 * auto-written). The C2 mic button is hidden in M1.4. Success → toast + "Đã check-in".
 */
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useLocale, useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { Field } from "@/features/admin/common";
import { type AppLocale } from "@/lib/format";
import { KrConfidence, useGoalError } from "./common";
import { checkInSchema, toCheckInBody, type CheckInValues } from "./forms";
import { CONFIDENCES, formatValue } from "./logic";
import { postCheckIn, useGoalMutation, type CheckInDueOut } from "./use-goals";

export function CheckInCard({ card }: { card: CheckInDueOut }) {
  const t = useTranslations("goals");
  const locale = useLocale() as AppLocale;
  const toast = useToast();
  const errText = useGoalError();
  const [done, setDone] = React.useState(!card.due);
  const [error, setError] = React.useState<string | null>(null);
  const schema = React.useMemo(() => checkInSchema({ valueRequired: t("form.valueRequired"), tooLong: t("form.tooLong") }), [t]);
  const form = useForm<CheckInValues>({ resolver: zodResolver(schema), defaultValues: { value: "", confidence: card.confidence ?? "MEDIUM", note: "", blocker: "" } });
  const m = useGoalMutation((v: CheckInValues) => postCheckIn(card.target_type, card.target_id, toCheckInBody(v)));
  const e = form.formState.errors;
  const conf = form.watch("confidence");
  const idp = `ci-${card.target_id.slice(0, 8)}`;
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      await m.mutateAsync(v);
      toast.push(t("toast.checkedIn", { title: card.title }));
      setDone(true);
      form.reset({ value: "", confidence: v.confidence, note: "", blocker: "" });
    } catch (err) {
      setError(errText(err));
    }
  });
  return (
    <article className="flex flex-col gap-3 rounded border p-4" data-testid={`checkin-card-${card.target_id}`} data-target-type={card.target_type} data-done={done ? "true" : "false"}>
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">{card.target_type === "kpi" ? t("checkin.kpi") : t("checkin.kr")}</Badge>
          <h3 className="font-medium">{card.title}</h3>
        </div>
        {done ? <Badge variant="success" data-testid="checkin-done">✓ {t("checkin.done")}</Badge> : <Badge variant="warning" data-testid="checkin-due">{t("checkin.due")}</Badge>}
      </header>
      <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <span className="tabular-nums">{t("checkin.current", { value: formatValue(card.current_value, card.unit, locale), target: formatValue(card.target, card.unit, locale) })}</span>
        <KrConfidence value={card.confidence} />
      </p>
      <PrefillHint card={card} locale={locale} onUse={(v) => form.setValue("value", String(v), { shouldDirty: true, shouldValidate: true })} />
      <form onSubmit={(ev) => void submit(ev)} className="flex flex-col gap-3" noValidate>
        <Field id={`${idp}-v`} label={`${t("checkin.value")}${card.unit ? ` (${card.unit})` : ""}`} error={e.value?.message}>
          <Input id={`${idp}-v`} inputMode="decimal" {...form.register("value")} data-testid="checkin-value" />
        </Field>
        <fieldset className="flex flex-col gap-1.5">
          <legend className="text-sm font-medium">{t("checkin.confidence")}</legend>
          <div role="radiogroup" aria-label={t("checkin.confidence")} className="inline-flex w-fit overflow-hidden rounded border" data-testid="checkin-confidence">
            {CONFIDENCES.map((c) => (
              <button key={c} type="button" role="radio" aria-checked={conf === c} onClick={() => form.setValue("confidence", c, { shouldDirty: true })} data-testid={`checkin-conf-${c}`}
                className={`px-3 py-1 text-sm ${conf === c ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}>
                {t(`confidence.${c}`)}
              </button>
            ))}
          </div>
        </fieldset>
        <Field id={`${idp}-n`} label={t("checkin.note")} error={e.note?.message}><Input id={`${idp}-n`} {...form.register("note")} data-testid="checkin-note" /></Field>
        <Field id={`${idp}-b`} label={t("checkin.blocker")} error={e.blocker?.message}><Input id={`${idp}-b`} {...form.register("blocker")} data-testid="checkin-blocker" /></Field>
        {error && <p role="alert" className="text-sm text-danger" data-testid="checkin-error">{error}</p>}
        <div className="flex justify-end">
          <Button type="submit" disabled={m.isPending} data-testid="checkin-submit">{m.isPending ? t("checkin.saving") : t("checkin.submit")}</Button>
        </div>
      </form>
    </article>
  );
}

/** AI-prefill slot (R-DEC-109): shows the suggested value + a confidence bar; "Dùng gợi ý" fills
 * the form — the user still confirms/edits before writing. No suggestion → the rest is unchanged. */
function PrefillHint({ card, locale, onUse }: { card: CheckInDueOut; locale: AppLocale; onUse: (v: number) => void }) {
  const t = useTranslations("goals");
  const p = card.prefill;
  if (!p) return null;
  const band = p.confidence; // HIGH | MEDIUM | LOW
  const pct = band === "HIGH" ? 100 : band === "MEDIUM" ? 66 : 33;
  const tone = band === "HIGH" ? "bg-success" : band === "MEDIUM" ? "bg-warning" : "bg-danger";
  return (
    <div className="flex flex-col gap-2 rounded border border-ai/40 bg-ai-subtle/40 p-2 text-xs" data-testid="checkin-prefill" data-prefill="suggested" data-confidence={band}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium text-ai">{t("checkin.prefill")}</span>
        <span className="tabular-nums font-medium" data-testid="prefill-value">{formatValue(p.suggested_value, card.unit, locale)}</span>
        <KrConfidence value={band} />
        <Button type="button" variant="outline" size="sm" onClick={() => onUse(p.suggested_value)} data-testid="prefill-use">{t("checkin.prefillUse")}</Button>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded bg-muted" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={t("checkin.confidence")} data-testid="prefill-confidence-bar">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-muted-foreground">{p.confidence_reason}</p>
    </div>
  );
}
