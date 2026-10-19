"use client";

import type { ReactNode } from "react";
import { Menu } from "lucide-react";
import { useTranslations } from "next-intl";
import { UserMenu } from "./UserMenu";

/**
 * Top bar (06 §2.2): company/app name on the left, and on the right a slot for the Role Switcher
 * (SCR-12) plus the user menu (account summary + sign out). The menu toggle is only shown
 * on small screens to open the sidebar drawer (06 §8).
 */
export function Topbar({
  onToggleSidebar,
  sidebarOpen,
  roleSwitcherSlot,
}: {
  onToggleSidebar: () => void;
  /** Reflected into the toggle's `aria-expanded`. */
  sidebarOpen: boolean;
  /** Role Switcher slot (SCR-12); empty until T-107. */
  roleSwitcherSlot?: ReactNode;
}) {
  const t = useTranslations("shell");
  return (
    <header className="flex h-14 items-center gap-3 border-b border-border bg-background px-4">
      <button
        type="button"
        onClick={onToggleSidebar}
        aria-expanded={sidebarOpen}
        aria-controls="app-sidebar"
        aria-label={t("toggleSidebar")}
        className="inline-flex items-center justify-center rounded-md p-2 text-foreground hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:hidden"
      >
        <Menu aria-hidden="true" className="h-5 w-5" />
      </button>

      <span className="text-h3 font-semibold text-foreground">{t("companyName")}</span>

      <div className="ml-auto flex items-center gap-2">
        {/* Role Switcher (SCR-12). */}
        <div data-slot="role-switcher">{roleSwitcherSlot}</div>
        {/* User menu: account summary + sign out. */}
        <UserMenu />
      </div>
    </header>
  );
}
