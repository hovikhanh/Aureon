import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { OnboardingWizard } from "@/features/admin/onboarding/OnboardingWizard";

/** SCR-66 `/admin/onboarding` (T-648F, UC-07) — ADM/CEO with `platform:admin` (guard in middleware, R-DEC-79). */
export default async function Page() {
  const session = await getServerSession(authOptions);
  const u = session?.user;
  return <OnboardingWizard viewer={{ id: u?.id ?? "", role: u?.role ?? "", permissions: u?.permissions ?? [] }} />;
}
