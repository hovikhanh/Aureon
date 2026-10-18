"use client";

import { useState, type ReactNode } from "react";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useTranslations } from "next-intl";
import type { RoleCode } from "@aureon/shared-types";
import { RoleProvider } from "@/features/navigation/role-context";
import { cn } from "@/lib/utils";
import { RoleSwitcher } from "./RoleSwitcher";
import { Sidebar } from "./Sidebar";
import { SkipLink } from "./SkipLink";
import { Topbar } from "./Topbar";

/**
 * Application shell (06 §3, §8). Composes: skip-link → top bar → sidebar + main landmark.
 *
 * Responsive behaviour (06 §8):
 * - < 768 px (mobile, 375): sidebar is an off-canvas drawer toggled from the top bar; a backdrop
 *   closes it. Hidden by default.
 * - 768–1279 px (tablet): a fixed icon-only "rail".
 * - >= 1280 px (desktop): full sidebar with labels; a desktop toggle collapses it to the rail.
 *
 * The active `role` is held in `RoleProvider` so the Sidebar can filter nav items via nav-config.
 * T-107 will pass the session role; for now it is a prop (default ROLE-01 at the route layout).
 */
export function AppShell({
  role = "ROLE-01",
  children,
  roleSwitcherSlot,
}: {
  role?: RoleCode;
  children: ReactNode;
  roleSwitcherSlot?: ReactNode;
}) {
  const t = useTranslations("shell");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);

  const effectiveRoleSwitcher =
    roleSwitcherSlot !== undefined ? roleSwitcherSlot : <RoleSwitcher />;

  return (
    <RoleProvider role={role}>
      <div className="flex min-h-screen flex-col">
        <SkipLink />
        <Topbar
          onToggleSidebar={() => setDrawerOpen((open) => !open)}
          sidebarOpen={drawerOpen}
          roleSwitcherSlot={effectiveRoleSwitcher}
        />

        <div className="flex flex-1">
          {/* Mobile drawer backdrop */}
          {drawerOpen ? (
            <button
              type="button"
              aria-label={t("closeSidebar")}
              onClick={() => setDrawerOpen(false)}
              className="fixed inset-0 z-30 bg-neutral-900/40 md:hidden"
            />
          ) : (
            <span className="sr-only">{t("sidebarClosed")}</span>
          )}

          {/* Sidebar: off-canvas drawer < md, static rail/full >= md */}
          <aside
            id="app-sidebar"
            className={cn(
              "fixed inset-y-0 left-0 z-40 w-64 border-r border-border bg-background pt-14 transition-transform md:static md:z-auto md:translate-x-0 md:pt-0",
              drawerOpen ? "translate-x-0" : "-translate-x-full",
              // Tablet: rail (icons only). Desktop (xl): full unless collapsed.
              desktopCollapsed ? "md:w-16 xl:w-16" : "md:w-16 xl:w-64",
            )}
          >
            <Sidebar
              collapsed={desktopCollapsed ? true : undefined}
              onNavigate={() => setDrawerOpen(false)}
            />
            {/* Desktop collapse toggle (full <-> rail); hidden below xl where the rail is fixed. */}
            <div className="hidden border-t border-border p-2 xl:block">
              <button
                type="button"
                onClick={() => setDesktopCollapsed((c) => !c)}
                aria-pressed={desktopCollapsed}
                aria-label={desktopCollapsed ? t("expandSidebar") : t("collapseSidebar")}
                className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-body text-foreground hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              >
                {desktopCollapsed ? (
                  <PanelLeftOpen aria-hidden="true" className="h-5 w-5 shrink-0" />
                ) : (
                  <PanelLeftClose aria-hidden="true" className="h-5 w-5 shrink-0" />
                )}
                <span className={cn(desktopCollapsed && "sr-only")}>
                  {desktopCollapsed ? t("expandSidebar") : t("collapseSidebar")}
                </span>
              </button>
            </div>
          </aside>

          <main id="main-content" className="flex-1 p-4 md:p-6">
            {children}
          </main>
        </div>
      </div>
    </RoleProvider>
  );
}
