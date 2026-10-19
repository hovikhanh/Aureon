"use client";

import { useEffect, useRef, useState } from "react";
import { LogOut, UserCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useAuthSafe } from "@/features/auth/auth-context";
import { cn } from "@/lib/utils";

/**
 * User menu (06 §2.2): avatar trigger that opens a dropdown showing the signed-in account
 * (name, email, role) and a Sign out action. Logout clears the session + query cache and
 * routes back to /login (auth-context.logout). Hidden when there is no active session.
 */
export function UserMenu({ className }: { className?: string }) {
  const t = useTranslations();
  const auth = useAuthSafe();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setIsOpen(false);
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

  // No session → nothing to show (the route guard handles redirects).
  if (!auth?.isAuthenticated || !auth.user) {
    return null;
  }

  const { user, role, logout } = auth;
  const roleNameKey = `shell.roles.${roleLabelKey(role)}`;

  return (
    <div ref={menuRef} className={cn("relative inline-block text-left", className)}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label={t("shell.userMenu")}
        className="inline-flex items-center justify-center rounded-full p-1 text-foreground hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <UserCircle aria-hidden="true" className="h-7 w-7" />
      </button>

      {isOpen && (
        <div
          role="menu"
          aria-orientation="vertical"
          aria-label={t("shell.userMenu")}
          className="absolute right-0 z-50 mt-1.5 w-64 origin-top-right rounded-lg border border-border bg-card p-1 shadow-lg ring-1 ring-black/5 focus:outline-none"
        >
          <div className="border-b border-border px-3 py-2.5">
            <p className="truncate text-body-sm font-semibold text-foreground">{user.full_name}</p>
            <p className="truncate text-caption text-muted-foreground">{user.email}</p>
            <p className="mt-0.5 text-caption text-muted-foreground">
              {t(roleNameKey)} ({role})
            </p>
          </div>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setIsOpen(false);
              logout();
            }}
            className="mt-1 flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-body-sm font-medium text-foreground transition-colors hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            {t("auth.logout")}
          </button>
        </div>
      )}
    </div>
  );
}

function roleLabelKey(role: string): string {
  switch (role) {
    case "ROLE-01":
      return "CEO";
    case "ROLE-02":
      return "CFO";
    case "ROLE-03":
      return "SALES_DIRECTOR";
    case "ROLE-04":
      return "HR_MANAGER";
    case "ROLE-05":
      return "REVIEWER";
    default:
      return "CEO";
  }
}
