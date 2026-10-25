"use client";
import { useTranslations } from "next-intl";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { CHANNELS, type DocumentType } from "./types";

export interface Filters { channel: string; document_type: string; mine: boolean; q: string; date_from: string; date_to: string }

/** SCR-45 filters (EP-DC-13 query): channel, document type, mine, date range, file-name search. */
export function InboxFilters({ value, types, onChange }: { value: Filters; types: DocumentType[]; onChange: (f: Filters) => void }) {
  const t = useTranslations("capture");
  const set = <K extends keyof Filters>(k: K, v: Filters[K]) => onChange({ ...value, [k]: v });
  return (
    <div className="flex flex-wrap items-end gap-3 text-sm" data-testid="inbox-filters">
      <label className="flex flex-col gap-1">{t("inbox.filter.channel")}
        <NativeSelect value={value.channel} onChange={(e) => set("channel", e.target.value)} className="w-44" data-testid="filter-channel">
          <option value="">{t("inbox.filter.all")}</option>
          {CHANNELS.map((c) => <option key={c} value={c}>{t(`channel.${c}`)}</option>)}
        </NativeSelect>
      </label>
      <label className="flex flex-col gap-1">{t("inbox.filter.docType")}
        <NativeSelect value={value.document_type} onChange={(e) => set("document_type", e.target.value)} className="w-48" data-testid="filter-type">
          <option value="">{t("inbox.filter.all")}</option>
          {types.map((d) => <option key={d.code} value={d.code}>{t.has(`docType.${d.code}`) ? t(`docType.${d.code}`) : d.name_vi}</option>)}
        </NativeSelect>
      </label>
      <label className="flex flex-col gap-1">{t("inbox.filter.dateFrom")}
        <Input type="date" value={value.date_from} onChange={(e) => set("date_from", e.target.value)} className="w-40" />
      </label>
      <label className="flex flex-col gap-1">{t("inbox.filter.dateTo")}
        <Input type="date" value={value.date_to} onChange={(e) => set("date_to", e.target.value)} className="w-40" />
      </label>
      <label className="flex flex-col gap-1">{t("inbox.filter.search")}
        <Input type="search" value={value.q} onChange={(e) => set("q", e.target.value)} className="w-56" data-testid="filter-q" />
      </label>
      <label className="flex items-center gap-2 pb-2">
        <Checkbox checked={value.mine} onCheckedChange={(c) => set("mine", c === true)} data-testid="filter-mine" />{t("inbox.filter.mine")}
      </label>
    </div>
  );
}
