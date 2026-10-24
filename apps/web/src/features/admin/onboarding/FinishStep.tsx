"use client";
import * as React from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { useErrorText } from "@/features/admin/common";
import { elapsedMs, firstMissing, formatElapsed } from "./logic";
import type { StepProps } from "./OnboardingWizard";

/** Step 6 — summary of the derived `progress` + time, "Finish" → `finish` (422 `missing_steps` → back to the first missing step). */
export function FinishStep({ state, patch, goTo }: StepProps) {
  const t = useTranslations();
  const toast = useToast();
  const errText = useErrorText();
  const [busy, setBusy] = React.useState(false);
  const p = state.progress ?? {};
  const done = state.status === "completed";
  const finish = async () => {
    setBusy(true);
    try {
      await patch(state, "finish");
      toast.push(t("onboarding.finish.done"));
    } catch (e) {
      const step = e instanceof ApiError ? firstMissing(e.details.missing_steps) : null;
      if (step) { toast.push(t("onboarding.finish.missing", { step: t(`onboarding.steps.${step}`) }), "danger"); goTo(step); }
      else toast.push(errText(e), "danger");
    } finally { setBusy(false); }
  };
  const roles = Object.entries(p.users_by_role ?? {}).map(([r, n]) => `${t(`role.${r}` as "role.CEO")}: ${n}`).join(" · ");
  const items: [string, string | number][] = [
    ["departments", p.departments ?? 0], ["employees", p.employees ?? 0], ["withoutUser", p.employees_without_user ?? 0],
    ["users", roles || "0"], ["kpis", p.kpis ?? 0], ["objectives", p.objectives ?? 0], ["time", formatElapsed(elapsedMs(state, Date.now()))],
  ];
  return (
    <div className="flex flex-col gap-4" data-testid="finish-step">
      <dl className="grid gap-2 text-sm sm:grid-cols-2" data-testid="finish-summary">
        {items.map(([k, v]) => <div key={k} className="flex justify-between rounded border px-3 py-2"><dt className="text-muted-foreground">{t(`onboarding.finish.${k}`)}</dt><dd className="font-medium" data-testid={`finish-${k}`}>{v}</dd></div>)}
      </dl>
      {done ? (
        <div className="flex flex-wrap items-center gap-3" data-testid="finish-completed">
          <span className="flex-1 text-sm text-success">{t("onboarding.finish.done")}</span>
          <Link href="/home" className="text-sm text-primary underline">{t("onboarding.finish.toHome")}</Link>
          <Link href="/admin/org" className="text-sm text-primary underline">{t("onboarding.finish.toOrg")}</Link>
        </div>
      ) : (
        <div className="flex justify-end"><Button onClick={() => void finish()} disabled={busy} data-testid="onboarding-finish">{t("onboarding.finish.button")}</Button></div>
      )}
    </div>
  );
}
