"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { ForbiddenState } from "@/components/states/ForbiddenState";
import { useAuth } from "@/features/auth/auth-context";

export function RouteGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const t = useTranslations("auth");
  const { role, isAuthenticated, isLoading } = useAuth();

  // Require authentication for every route under the (app) group. Once the session has finished
  // restoring and there is still no session, send the user to /login (02 §6, SCR-13).
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center p-6" role="status" aria-live="polite">
        <span className="text-body-sm text-muted-foreground">{t("checkingSession")}</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center p-6" role="status" aria-live="polite">
        <span className="text-body-sm text-muted-foreground">{t("redirectingToLogin")}</span>
      </div>
    );
  }

  // 02 §4.2: Reviewer (ROLE-05) has no dashboard 4 pillars access (TC-DASH-004)
  if (pathname === "/dashboard" && role === "ROLE-05") {
    return (
      <div className="p-6">
        <ForbiddenState />
      </div>
    );
  }

  // 02 §3.6: Audit log is CEO-only (ROLE-01)
  if (pathname === "/audit" && role !== "ROLE-01") {
    return (
      <div className="p-6">
        <ForbiddenState />
      </div>
    );
  }

  // 02 §3.4: UC-07 Upload is only for CEO (ROLE-01) and Reviewer (ROLE-05)
  if (pathname === "/upload" && role !== "ROLE-01" && role !== "ROLE-05") {
    return (
      <div className="p-6">
        <ForbiddenState />
      </div>
    );
  }

  return <>{children}</>;
}
