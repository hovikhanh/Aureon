import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { cn } from "@/lib/utils";

/** SCR-44 "Họp & lịch" (06 §3.1: cuộc họp, biên bản → việc, lịch) — the calendar was reachable only by URL. */
export async function MeetingsTabs({ active }: { active: "meetings" | "calendar" }) {
  const t = await getTranslations("meetings.tabs");
  const tabs = [{ key: "meetings", href: "/meetings" }, { key: "calendar", href: "/meetings/calendar" }] as const;
  return (
    <nav aria-label={t("label")} className="mx-auto flex w-full max-w-3xl gap-1 border-b" data-testid="meetings-tabs">
      {tabs.map((tab) => (
        <Link key={tab.key} href={tab.href} aria-current={active === tab.key ? "page" : undefined} data-testid={`meetings-tab-${tab.key}`}
          className={cn("-mb-px border-b-2 px-3 py-2 text-sm", active === tab.key ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground hover:text-foreground")}>
          {t(tab.key)}
        </Link>
      ))}
    </nav>
  );
}
