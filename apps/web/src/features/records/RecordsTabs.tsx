"use client";
import * as React from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { RecordCrud, type RecordCaps } from "./RecordCrud";
import { resourcesOf, type Domain } from "./specs";

/** Tabs of one domain's records (`?tab=<resource>` deep link). */
export function RecordsTabs({ domain, caps }: { domain: Domain; caps: RecordCaps }) {
  const t = useTranslations("records");
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const specs = resourcesOf(domain);
  const active = specs.find((s) => s.key === params.get("tab")) ?? specs[0]!;
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4" data-testid={`records-page-${domain}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t(`title.${domain}`)}</h1>
        {!caps.canWrite && <p className="text-sm text-muted-foreground" data-testid="records-readonly">{t("readOnly")}</p>}
      </div>
      <div className="flex flex-wrap gap-1 rounded-md border p-1" role="tablist">
        {specs.map((s) => (
          <Button key={s.key} size="sm" role="tab" aria-selected={s.key === active.key} variant={s.key === active.key ? "default" : "ghost"}
            onClick={() => router.replace(`${pathname}?tab=${s.key}`, { scroll: false })} data-testid={`records-tab-${s.key}`}>
            {t(`resource.${s.key}` as "me")}
          </Button>
        ))}
      </div>
      <RecordCrud key={active.key} spec={active} caps={caps} />
    </div>
  );
}
