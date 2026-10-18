"use client";

import { useState } from "react";
import { ArrowRight, Lock, Mail, ShieldAlert, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/features/auth/auth-context";
import { DEMO_ACCOUNTS } from "@/features/auth/demo-accounts";
import { cn } from "@/lib/utils";

export default function LoginPage() {
  const t = useTranslations();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isDemoModeEnabled = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setErrorMessage(t("auth.invalidCredentials"));
      return;
    }
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      await login(email.trim(), password);
    } catch {
      // 06 §4.10, TC-AUTH-002: Same generic message for wrong password or missing user
      setErrorMessage(t("auth.invalidCredentials"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = async (demoEmail: string) => {
    setEmail(demoEmail);
    // For demo purposes, the user can type password or we submit via demo account
    // When password is known or set in env, login proceeds
    setPassword("Demo@123");
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      await login(demoEmail, "Demo@123");
    } catch {
      setErrorMessage(t("auth.invalidCredentials"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-caption font-semibold text-primary">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            Aureon Demo
          </span>
          <h1 className="mt-3 text-h1 font-bold tracking-tight text-foreground">
            {t("auth.loginTitle")}
          </h1>
          <p className="mt-2 text-body-sm text-muted-foreground">{t("auth.loginSubtitle")}</p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5" noValidate>
          {errorMessage && (
            <div
              role="alert"
              className="flex items-center gap-2 rounded-lg border border-critical/20 bg-critical/10 p-3 text-body-sm font-medium text-critical"
            >
              <ShieldAlert className="h-5 w-5 shrink-0" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-body-sm font-medium text-foreground">
                {t("auth.emailLabel")}
              </label>
              <div className="relative mt-1">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <Mail className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t("auth.emailPlaceholder")}
                  className={cn(
                    "block w-full rounded-lg border border-border bg-card py-2 pr-3 pl-9 text-body-sm text-foreground",
                    "placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none",
                  )}
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-body-sm font-medium text-foreground">
                {t("auth.passwordLabel")}
              </label>
              <div className="relative mt-1">
                <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                  <Lock className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={t("auth.passwordPlaceholder")}
                  className={cn(
                    "block w-full rounded-lg border border-border bg-card py-2 pr-3 pl-9 text-body-sm text-foreground",
                    "placeholder:text-muted-foreground focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none",
                  )}
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className={cn(
              "flex w-full items-center justify-center gap-2 rounded-lg bg-primary py-2.5 px-4 text-body-sm font-semibold text-primary-foreground shadow-xs transition-colors",
              "hover:bg-primary/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
              isSubmitting && "opacity-75 cursor-wait",
            )}
          >
            {isSubmitting ? t("auth.submitting") : t("auth.submitButton")}
            {!isSubmitting && <ArrowRight className="h-4 w-4" aria-hidden="true" />}
          </button>
        </form>

        {isDemoModeEnabled && (
          <div className="mt-8 border-t border-border pt-6">
            <div className="flex items-center gap-1.5 text-caption font-semibold text-primary">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              {t("auth.demoUsersTitle")}
            </div>
            <p className="mt-1 text-caption text-muted-foreground">
              {t("auth.demoUsersSubtitle")}
            </p>

            <div className="mt-3 grid gap-2">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.roleCode}
                  type="button"
                  onClick={() => handleQuickLogin(acc.email)}
                  disabled={isSubmitting}
                  className={cn(
                    "flex w-full items-center justify-between rounded-lg border border-border bg-card p-2.5 text-left text-body-sm transition-colors",
                    "hover:border-primary/50 hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring",
                    isSubmitting && "opacity-50 cursor-not-allowed",
                  )}
                >
                  <div className="flex flex-col">
                    <span className="font-semibold text-foreground">
                      {t(acc.roleNameKey)} ({acc.roleCode})
                    </span>
                    <span className="text-caption text-muted-foreground">
                      {t(acc.userNameKey)} · {acc.email}
                    </span>
                  </div>
                  <span className="text-caption font-medium text-primary">
                    {t("auth.quickLogin", { role: acc.roleCode })}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
