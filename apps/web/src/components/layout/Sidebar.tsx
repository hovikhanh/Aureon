"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
import { getNavItems, isNavItemActive } from "@/features/navigation/nav-config";
import { NAV_ICONS } from "@/features/navigation/nav-icons";
import { useCurrentRole } from "@/features/navigation/role-context";
import { cn } from "@/lib/utils";

/**
 * Primary navigation (06 §2.1). Items come from nav-config.ts `getNavItems(role)` — the single
 * source of per-role visibility (06 §2.1 × 02 §3); an item a role has no right to is simply
 * absent. Labels use i18n keys `shell.nav.<id>`. The active item gets `aria-current="page"`
 * (06 §9), computed with `isNavItemActive` (exact or nested route). Icon-only "rail" mode at
 * tablet width keeps the accessible name via an `sr-only` label (06 §8).
 */
export function Sidebar({
  collapsed = false,
  onNavigate,
}: {
  /**
   * Force rail mode (icons only) at every width. When false, the rail is driven purely by CSS:
   * full on mobile drawer and desktop (xl), icons-only on tablet (md). Labels stay in the DOM as
   * `sr-only` so screen readers always read the accessible name (06 §8, §9).
   */
  collapsed?: boolean;
  /** Called after a link activates — lets the mobile drawer close itself. */
  onNavigate?: () => void;
}) {
  const role = useCurrentRole();
  const pathname = usePathname();
  const t = useTranslations("shell.nav");
  const items = getNavItems(role);

  return (
    <nav aria-label={t("landmark")} className="flex h-full flex-col gap-1 p-2">
      <ul className="flex flex-col gap-1">
        {items.map((item) => {
          const Icon = NAV_ICONS[item.id];
          const active = isNavItemActive(pathname, item.href);
          return (
            <li key={item.id}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                onClick={onNavigate}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-body font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-foreground hover:bg-accent hover:text-accent-foreground",
                  collapsed ? "justify-center" : "md:justify-center xl:justify-start",
                )}
                title={t(item.id)}
              >
                <Icon aria-hidden="true" className="h-5 w-5 shrink-0" />
                {/* Label: visible on mobile drawer + desktop full; `sr-only` on the tablet rail
                    (md) and when forced collapsed, so the accessible name is always present. */}
                <span className={cn(collapsed ? "sr-only" : "md:sr-only xl:not-sr-only")}>
                  {t(item.id)}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
