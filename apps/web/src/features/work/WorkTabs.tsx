"use client";
/** Tab bar of `/work` (06 §3.4 M1.3, R-DEC-48) — tabs pre-filtered by `visibleWorkTabs` on the server. */
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { WorkTabKey } from "@/lib/permissions";
import { cn } from "@/lib/utils";
import { useApprovals } from "./use-work";

export function WorkTabs({ tabs, active }: { tabs: { key: WorkTabKey; href: string }[]; active: WorkTabKey }) {
  const t = useTranslations("work.tabs");
  const hasApprovals = tabs.some((x) => x.key === "approvals");
  const inbox = useApprovals({ status: "PENDING", limit: 1 }, hasApprovals);
  const pending = Number(inbox.data?.meta?.pending_count ?? 0);
  return (
    <nav aria-label={t("label")} className="flex flex-wrap gap-1 border-b" data-testid="work-tabs">
      {tabs.map((tab) => (
        <Link key={tab.key} href={tab.href} aria-current={tab.key === active ? "page" : undefined} data-testid={`work-tab-${tab.key}`}
          className={cn("-mb-px flex items-center gap-2 border-b-2 px-3 py-2 text-sm", tab.key === active ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground hover:text-foreground")}>
          {t(tab.key)}
          {tab.key === "approvals" && pending > 0 && (
            <span className="rounded-full bg-danger px-1.5 text-xs text-white" aria-label={t("pendingBadge", { count: pending })} data-testid="approvals-badge">{pending > 99 ? "99+" : pending}</span>
          )}
        </Link>
      ))}
    </nav>
  );
}
