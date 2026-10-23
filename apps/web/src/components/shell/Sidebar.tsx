"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { BookOpen, Briefcase, CalendarDays, ChevronsLeft, ChevronsRight, Home, Inbox, ListChecks, Settings, Sparkles, Target, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { visibleNav, type NavKey } from "@/lib/permissions";

const ICONS: Record<NavKey, typeof Home> = {
  home: Home,
  ask: Sparkles,
  goals: Target,
  work: ListChecks,
  meetings: CalendarDays,
  data: Inbox,
  business: Briefcase,
  knowledge: BookOpen,
  admin: Settings,
};

interface Props {
  role: string;
  permissions: string[];
  mobileOpen: boolean;
  collapsed: boolean;
  onCloseMobile: () => void;
  onToggleCollapsed: () => void;
}

export function Sidebar({ role, permissions, mobileOpen, collapsed, onCloseMobile, onToggleCollapsed }: Props) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  // IA v3 (06 §3.1/§3.2): 8 main items + the separate "Quản trị" group, filtered by role.
  const items = visibleNav(role, permissions);
  return (
    <>
      {mobileOpen && <div className="fixed inset-0 z-40 bg-black/40 md:hidden" onClick={onCloseMobile} aria-hidden />}
      <aside
        data-testid="sidebar"
        data-collapsed={collapsed}
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r bg-card transition-transform duration-250 md:sticky md:top-0 md:h-dvh md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          "md:w-16 xl:w-60",
          collapsed && "xl:w-16",
        )}
      >
        <div className="flex h-14 items-center gap-2 border-b px-4">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary font-bold text-primary-foreground">A</span>
          <span className={cn("font-semibold md:hidden xl:inline", collapsed && "xl:hidden")}>Aureon</span>
          <button type="button" className="ml-auto rounded p-1 hover:bg-muted md:hidden" onClick={onCloseMobile} aria-label={t("close")}>
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="flex flex-1 flex-col gap-1 p-2" aria-label="primary">
          {items.map((item) => {
            const Icon = ICONS[item.key];
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.key}
                href={item.href}
                data-group={item.group}
                onClick={onCloseMobile}
                data-testid={`nav-${item.key}`}
                aria-current={active ? "page" : undefined}
                title={t(item.key)}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium hover:bg-muted",
                  item.group === "admin" && "mt-auto border-t pt-3",
                  active && (item.key === "ask" ? "bg-ai-subtle text-ai" : "bg-primary/10 text-primary"),
                )}
              >
                <Icon className={cn("h-5 w-5 shrink-0", item.key === "ask" && "text-ai")} aria-hidden />
                <span className={cn("md:hidden xl:inline", collapsed && "xl:hidden")}>{t(item.key)}</span>
              </Link>
            );
          })}
        </nav>
        <button
          type="button"
          onClick={onToggleCollapsed}
          className="hidden items-center justify-center border-t p-3 hover:bg-muted xl:flex"
          aria-label={collapsed ? t("expand") : t("collapse")}
        >
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
        </button>
      </aside>
    </>
  );
}
