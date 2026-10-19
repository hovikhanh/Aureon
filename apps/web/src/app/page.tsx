"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/features/auth/auth-context";

export default function HomePage() {
  const t = useTranslations("home");
  const router = useRouter();
  const { isAuthenticated, isLoading, session } = useAuth();

  // Signed-in visitors go straight to their role home route; everyone else sees a landing
  // with a Sign in button (SCR-13 entry point).
  useEffect(() => {
    if (!isLoading && isAuthenticated && session) {
      router.replace(session.homeRoute);
    }
  }, [isLoading, isAuthenticated, session, router]);

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center p-6 text-center">
      <h1 className="text-h1 text-primary">{t("heading")}</h1>
      <p className="mt-2 max-w-xl text-body text-muted-foreground">{t("subtitle")}</p>

      {!isLoading && !isAuthenticated && (
        <Link
          href="/login"
          className="mt-8 inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-body font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {t("loginCta")}
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Link>
      )}
    </main>
  );
}
