"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { AdminHeader, useErrorText } from "@/features/admin/common";
import { canOpen, clockTone, currentStep, elapsedMs, formatElapsed, STEPS, type OnboardingState, type Step } from "./logic";
import { useOnboarding, usePatchOnboarding } from "./use-onboarding";
import { CompanyStep } from "./CompanyStep";
import { ImportStep } from "./ImportStep";
import { ReviewStep } from "./ReviewStep";
import { UsersStep } from "./UsersStep";
import { FinishStep } from "./FinishStep";

export interface Viewer { id: string; role: string; permissions: string[] }
export interface StepProps { state: OnboardingState; viewer: Viewer; patch: ReturnType<typeof usePatchOnboarding>; goTo: (s: Step) => void }

/** SCR-66 `/admin/onboarding` (T-648F, UC-07): 6-step wizard; progress saved with EP-ADM-13/14, reload resumes at the open step. */
export function OnboardingWizard({ viewer }: { viewer: Viewer }) {
  const t = useTranslations();
  const q = useOnboarding();
  if (q.isPending) return <div className="mx-auto h-96 max-w-6xl animate-pulse rounded-lg bg-muted" />;
  if (q.isError || !q.data) return <p role="alert" className="mx-auto max-w-6xl text-danger" data-testid="onboarding-error">{t("errors.generic")}</p>;
  return <Wizard state={q.data} viewer={viewer} />;
}

function Wizard({ state, viewer }: { state: OnboardingState; viewer: Viewer }) {
  const t = useTranslations();
  const toast = useToast();
  const errText = useErrorText();
  const patch = usePatchOnboarding();
  const cur = currentStep(state);
  const [view, setView] = React.useState<Step>(cur);
  React.useEffect(() => setView(cur), [cur]);
  const [busy, setBusy] = React.useState(false);
  const started = state.status !== "not_started";

  const start = async () => {
    setBusy(true);
    try { await patch(state, "start"); } catch (e) { toast.push(errText(e), "danger"); } finally { setBusy(false); }
  };

  const props: StepProps = { state, viewer, patch, goTo: setView };
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4" data-testid="onboarding" data-scr="SCR-66" data-status={state.status} data-step={view}>
      <AdminHeader title={t("onboarding.title")} hint={t("onboarding.hint")}>{started && <OnboardingClock state={state} />}</AdminHeader>
      {!started ? (
        <Card className="flex flex-col items-start gap-3 p-6" data-testid="onboarding-intro">
          <p className="text-sm">{t("onboarding.intro")}</p>
          <ol className="list-decimal pl-5 text-sm text-muted-foreground">{STEPS.map((s) => <li key={s}>{t(`onboarding.steps.${s}`)}</li>)}</ol>
          <Button onClick={() => void start()} disabled={busy || !viewer.permissions.includes("platform:admin")} data-testid="onboarding-start">{t("onboarding.start")}</Button>
        </Card>
      ) : (
        <>
          <Stepper state={state} view={view} onSelect={setView} />
          <Card className="p-4" data-testid={`step-${view}`}>
            {view === "company" && <CompanyStep {...props} />}
            {view === "org_import" && <ImportStep {...props} step="org_import" />}
            {view === "review" && <ReviewStep {...props} />}
            {view === "users" && <UsersStep {...props} />}
            {view === "goals_import" && <ImportStep {...props} step="goals_import" />}
            {view === "finish" && <FinishStep {...props} />}
          </Card>
        </>
      )}
    </div>
  );
}

/** Horizontal stepper — buttons in tab order, ←/→ move between the steps already reachable; `aria-current="step"`. */
function Stepper({ state, view, onSelect }: { state: OnboardingState; view: Step; onSelect: (s: Step) => void }) {
  const t = useTranslations();
  const refs = React.useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: React.KeyboardEvent, i: number) => {
    const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    const next = STEPS[i + d];
    if (!d || !next || !canOpen(state, next)) return;
    e.preventDefault();
    onSelect(next);
    refs.current[i + d]?.focus();
  };
  return (
    <ol className="flex flex-wrap gap-2" aria-label={t("onboarding.title")} data-testid="onboarding-stepper">
      {STEPS.map((s, i) => {
        const st = state.steps?.[s]?.status ?? "pending";
        const active = view === s;
        return (
          <li key={s}>
            <button ref={(el) => { refs.current[i] = el; }} type="button" disabled={!canOpen(state, s)} onClick={() => onSelect(s)} onKeyDown={(e) => onKey(e, i)}
              aria-current={active ? "step" : undefined} data-testid={`stepper-${s}`} data-status={st}
              className={`rounded-full px-3 py-1 text-sm disabled:opacity-50 ${active ? "bg-primary text-primary-foreground" : st === "done" || st === "skipped" ? "bg-success-subtle text-success" : "bg-muted text-muted-foreground"}`}>
              {i + 1}. {t(`onboarding.steps.${s}`)}{st === "done" ? " ✓" : st === "skipped" ? ` (${t("onboarding.skipped")})` : ""}
            </button>
          </li>
        );
      })}
    </ol>
  );
}

const TONE = { ok: "text-success border-success", warn: "text-warning border-warning", late: "text-danger border-danger" } as const;

/** "Trong 1 ngày" clock: time since `started_at` (stops at `completed_at`), green ≤ 8 h, yellow ≤ 24 h, red > 24 h. */
function OnboardingClock({ state }: { state: OnboardingState }) {
  const t = useTranslations();
  const [now, setNow] = React.useState(() => Date.now());
  React.useEffect(() => {
    if (state.completed_at) return;
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, [state.completed_at]);
  const ms = elapsedMs(state, now);
  const tone = clockTone(ms);
  return (
    <span className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm ${TONE[tone]}`} data-testid="onboarding-clock" data-tone={tone} title={t("onboarding.clockHint")}>
      <Clock className="h-4 w-4" aria-hidden />{t("onboarding.clock", { time: formatElapsed(ms) })}
    </span>
  );
}
