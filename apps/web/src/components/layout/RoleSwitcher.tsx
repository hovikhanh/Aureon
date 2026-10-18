"use client";

import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Loader2, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import type { RoleCode } from "@aureon/shared-types";
import { useAuthSafe } from "@/features/auth/auth-context";
import { DEMO_ACCOUNTS } from "@/features/auth/demo-accounts";
import { cn } from "@/lib/utils";

export function RoleSwitcher({ className }: { className?: string }) {
  const t = useTranslations();
  const auth = useAuthSafe();
  const currentRole = auth?.role ?? "ROLE-01";
  const switchRole = auth?.switchRole;
  const [isOpen, setIsOpen] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const [targetPendingRole, setTargetPendingRole] = useState<RoleCode | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // 02 §5.1 & TC-AUTH-017: Check if demo mode is enabled
  const isDemoModeEnabled = process.env.NEXT_PUBLIC_DEMO_MODE !== "false";

  // Close dropdown on click outside or escape key
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  if (!isDemoModeEnabled) {
    return null;
  }

  const handleSelectRole = async (roleCode: RoleCode) => {
    if (roleCode === currentRole) {
      setIsOpen(false);
      return;
    }
    if (!switchRole) {
      return;
    }
    try {
      setIsPending(true);
      setTargetPendingRole(roleCode);
      setErrorMessage(null);
      await switchRole(roleCode);
      setIsOpen(false);
    } catch {
      // 02 §5.2 R6: On failure keep old role and show error toast/message
      setErrorMessage(t("roleSwitcher.switchError"));
    } finally {
      setIsPending(false);
      setTargetPendingRole(null);
    }
  };

  const activeAccount = DEMO_ACCOUNTS.find((a) => a.roleCode === currentRole) ?? DEMO_ACCOUNTS[0];

  return (
    <div ref={menuRef} className={cn("relative inline-block text-left", className)}>
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          disabled={isPending}
          aria-haspopup="menu"
          aria-expanded={isOpen}
          aria-label={t("roleSwitcher.currentRoleLabel", {
            role: `${t(activeAccount.roleNameKey)} · ${activeAccount.roleCode}`,
          })}
          className={cn(
            "inline-flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1.5 text-body-sm font-medium text-foreground shadow-xs transition-colors",
            "hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
            isPending && "opacity-75 cursor-wait",
          )}
        >
          <span className="inline-flex items-center gap-1 rounded bg-primary/10 px-1.5 py-0.5 text-caption font-semibold text-primary">
            <Sparkles className="h-3 w-3" aria-hidden="true" />
            {t("roleSwitcher.demoBadge")}
          </span>
          <span className="font-semibold">{t(activeAccount.roleNameKey)}</span>
          <span className="text-muted-foreground text-caption">({activeAccount.roleCode})</span>
          {isPending ? (
            <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          )}
        </button>
      </div>

      {isOpen && (
        <div
          role="menu"
          aria-orientation="vertical"
          aria-label={t("roleSwitcher.switchTitle")}
          className="absolute right-0 z-50 mt-1.5 w-64 origin-top-right rounded-lg border border-border bg-card p-1 shadow-lg ring-1 ring-black/5 focus:outline-none"
        >
          <div className="px-2 py-1.5 text-caption font-semibold text-muted-foreground">
            {t("roleSwitcher.switchTitle")}
          </div>
          <div className="space-y-0.5">
            {DEMO_ACCOUNTS.map((account) => {
              const isSelected = account.roleCode === currentRole;
              const isSwitchingThis = isPending && targetPendingRole === account.roleCode;
              return (
                <button
                  key={account.roleCode}
                  type="button"
                  role="menuitem"
                  onClick={() => handleSelectRole(account.roleCode)}
                  disabled={isPending}
                  className={cn(
                    "flex w-full items-center justify-between rounded-md px-2.5 py-2 text-left text-body-sm transition-colors",
                    isSelected
                      ? "bg-accent font-semibold text-foreground"
                      : "text-foreground hover:bg-accent hover:text-foreground",
                    isPending && !isSwitchingThis && "opacity-50 cursor-not-allowed",
                  )}
                >
                  <div className="flex flex-col">
                    <span className="font-medium text-foreground">{t(account.roleNameKey)}</span>
                    <span className="text-caption text-muted-foreground">
                      {account.roleCode} · {t(account.userNameKey)}
                    </span>
                  </div>
                  {isSwitchingThis ? (
                    <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden="true" />
                  ) : isSelected ? (
                    <Check className="h-4 w-4 text-primary" aria-hidden="true" />
                  ) : null}
                </button>
              );
            })}
          </div>
          {errorMessage && (
            <div className="mt-1 border-t border-border px-2 py-1.5 text-caption font-medium text-critical">
              {errorMessage}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
