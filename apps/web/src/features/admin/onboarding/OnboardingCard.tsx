"use client";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useOnboarding } from "./use-onboarding";

/** SCR-50 card "Onboarding" (06 §3.4): highlighted while EP-ADM-13 `status ≠ completed`; a load error just shows the plain card. */
export function OnboardingCard() {
  const t = useTranslations();
  const q = useOnboarding();
  const pending = q.data !== undefined && q.data.status !== "completed";
  return (
    <Link href="/admin/onboarding" data-testid="admin-card-onboarding" data-pending={pending}
      className={`block h-full rounded-lg border bg-card p-4 hover:bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary ${pending ? "border-primary ring-1 ring-primary" : ""}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-primary">{t("adminHome.onboarding.title")}</span>
        {pending && <span className="rounded-full bg-warning-subtle px-2 py-0.5 text-xs text-warning" data-testid="onboarding-pending">{t("adminHome.onboarding.pending")}</span>}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{t("adminHome.onboarding.body")}</p>
    </Link>
  );
}
