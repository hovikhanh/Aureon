"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { IncidentsTab } from "./IncidentsTab";
import { RulesTab } from "./RulesTab";
import { SchemasTab } from "./SchemasTab";
import { TypesTab } from "./TypesTab";

type Tab = "types" | "schemas" | "rules" | "incidents";

/**
 * SCR-63 `/admin/data-capture` (T-638F): document types (EP-DC-27/28), ExtractionSchema
 * draft → publish (EP-DC-29..32), validation rules (EP-DC-33..35). The "Sự cố" tab (EP-DC-37)
 * needs `idp:approve` — hidden for ADM (parent decision 3).
 */
export function DataCaptureAdmin({ permissions }: { permissions: string[] }) {
  const t = useTranslations("capture.admin");
  const tabs: Tab[] = ["types", "schemas", "rules", ...(permissions.includes("idp:approve") ? (["incidents"] as const) : [])];
  const [tab, setTab] = React.useState<Tab>("types");
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4" data-testid="capture-admin" data-scr="SCR-63">
      <div>
        <h1 className="text-2xl font-semibold">{t("title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>
      <div role="tablist" className="flex gap-1 border-b">
        {tabs.map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k} aria-controls={`panel-${k}`} onClick={() => setTab(k)} data-testid={`admin-tab-${k}`}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${tab === k ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            {t(`tabs.${k}`)}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`}>
        {tab === "types" && <TypesTab />}
        {tab === "schemas" && <SchemasTab />}
        {tab === "rules" && <RulesTab />}
        {tab === "incidents" && <IncidentsTab />}
      </div>
    </div>
  );
}
