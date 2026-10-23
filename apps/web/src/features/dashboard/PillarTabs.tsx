"use client";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { usePeriod } from "./period";
import type { PillarCode } from "./types";

/** SCR-03 optional five-pillar F.O.C.U.S layout (R-DEC-16): switch between visible pillars. */
export function PillarTabs({ pillars, active }: { pillars: { code: PillarCode; slug: string }[]; active: PillarCode }) {
  const t = useTranslations("pillar");
  const { withPeriod } = usePeriod();
  return (
    <nav aria-label={t("tabs")} className="mx-auto mb-4 flex max-w-5xl flex-wrap gap-2" data-testid="pillar-tabs">
      {pillars.map((p) => (
        <Link
          key={p.code}
          href={withPeriod(`/home/pillar/${p.slug}`)}
          aria-current={p.code === active ? "page" : undefined}
          className={cn("rounded-full border px-3 py-1 text-sm", p.code === active ? "border-primary bg-primary/10 font-medium text-primary" : "text-muted-foreground hover:bg-muted")}
          data-testid={`pillar-tab-${p.code}`}
        >
          {p.code} · {t(`${p.code}.name`)}
        </Link>
      ))}
    </nav>
  );
}
