"use client";
/**
 * F4 check-in card (SCR-60, 06 §4 F4): current value / target, new value, 3-step confidence,
 * note, blocker → EP-PRF-02 (KR) / EP-PRF-04 (KPI). "AI điền sẵn" slot stays a placeholder
 * (`prefill: null` until M2.4); the C2 mic button is hidden in M1.4. Success → toast + "Đã check-in".
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
      <div className="rounded border border-dashed border-ai/40 bg-ai-subtle/40 p-2 text-xs text-muted-foreground" data-testid="checkin-prefill" data-prefill="null">
        <span className="font-medium text-ai">{t("checkin.prefill")}</span> · {t("checkin.prefillSoon")}
      </div>
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
