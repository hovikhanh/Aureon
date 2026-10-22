import { Suspense } from "react";
import { getTranslations } from "next-intl/server";
import { LoginForm } from "@/features/auth/LoginForm";

export default async function LoginPage() {
  const t = await getTranslations("auth");
  const demo = process.env.DEMO_MODE === "true" || process.env.NEXT_PUBLIC_DEMO_MODE === "true";
  return (
    <main className="flex min-h-dvh items-center justify-center bg-muted p-4">
      <div className="w-full max-w-md rounded-2xl border bg-card p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-lg font-bold text-primary-foreground">A</span>
          <div>
            <h1 className="text-xl font-semibold">{t("title")}</h1>
            <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
          </div>
        </div>
        <Suspense>
          <LoginForm demoMode={demo} />
        </Suspense>
      </div>
    </main>
  );
}
