"use client";
/**
 * `/business/sales/clients/[id]` — Account 360 (BRD §2.3 CRM-ACC-07/08, US-ACC-002, UX-004) on
 * EP-SAL-01/02/08: profile + contact person, the account's opportunities (open pipeline, won) and
 * contracts. Activities and a contact list need entities the model does not have yet (R-DEC-176).
 */
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { QueryError } from "@/components/QueryError";
import { formatDate, formatMoney, type AppLocale } from "@/lib/format";
import { isClosed } from "./crm";
import { useClient, useContracts, useDeals } from "./use-crm";

export function ClientDetailView({ id }: { id: string }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const client = useClient(id);
  const deals = useDeals({ client_id: id, sort_by: "expected_close_date", order: "desc" });
  const contracts = useContracts({ client_id: id });
  if (client.isPending) return <div className="h-40 animate-pulse rounded-lg bg-muted" />;
  if (client.isError || !client.data) return <QueryError error={client.error} onRetry={() => void client.refetch()} testId="client-error" />;
  const c = client.data;
  const list = deals.data ?? [];
  const open = list.filter((d) => !isClosed(d.stage));
  const won = list.filter((d) => d.stage === "closed_won");
  const contact = c.contacts[0];
  const kpis: [string, string][] = [
    [t("crm.openDeals"), String(open.length)],
    [t("crm.openPipeline"), formatMoney(open.reduce((a, d) => a + d.deal_value, 0), locale)],
    [t("crm.wonValue"), formatMoney(won.reduce((a, d) => a + d.deal_value, 0), locale)],
    [t("crm.contracts"), String(contracts.data?.length ?? 0)],
  ];
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4" data-testid="client-detail">
      <Link href="/business/sales/records?tab=clients" className="flex items-center gap-1 text-sm text-primary hover:underline"><ArrowLeft className="h-4 w-4" aria-hidden />{t("crm.clients")}</Link>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">{c.name}</h1>
        <Badge>{t.has(`records.enum.status.${c.status}`) ? t(`records.enum.status.${c.status}` as "crm.me") : c.status}</Badge>
      </div>
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4" data-testid="client-kpis">
        {kpis.map(([k, v]) => <Card key={k} className="p-3"><div className="text-xs text-muted-foreground">{k}</div><div className="text-lg font-semibold tabular-nums">{v}</div></Card>)}
      </section>
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-4 text-sm">
          <h2 className="font-semibold">{t("crm.overview")}</h2>
          <dl className="mt-2 flex flex-col gap-1">
            {([["tax_code", c.tax_code], ["industry", c.industry], ["website", c.website], ["address", c.address]] as const).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2"><dt className="text-muted-foreground">{t(`records.field.${k}` as "crm.me")}</dt><dd className="text-right">{v || "—"}</dd></div>
            ))}
          </dl>
          <h3 className="mt-3 font-semibold">{t("crm.contactPerson")}</h3>
          <p className="text-muted-foreground" data-testid="client-contact">{contact?.name ? `${contact.name}${contact.email ? ` · ${contact.email}` : ""}${contact.phone ? ` · ${contact.phone}` : ""}` : "—"}</p>
        </Card>
        <Card className="p-4 md:col-span-2">
          <h2 className="text-sm font-semibold">{t("crm.opportunities")}</h2>
          {deals.isError && <QueryError error={deals.error} />}
          {deals.isSuccess && list.length === 0 && <p className="mt-2 text-sm text-muted-foreground">{t("crm.noDeals")}</p>}
          <ul className="mt-2 divide-y text-sm" data-testid="client-deals">
            {list.map((d) => (
              <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <Link href={`/business/sales/deals/${d.id}`} className="font-medium hover:text-primary hover:underline">{d.name}</Link>
                <span className="flex items-center gap-2 tabular-nums">
                  <Badge variant="outline">{t(`sales.stage.${d.stage}` as "sales.stage.lead")}</Badge>
                  {formatMoney(d.deal_value, locale)} · {formatDate(d.expected_close_date, locale)}
                </span>
              </li>
            ))}
          </ul>
          <h2 className="mt-4 text-sm font-semibold">{t("crm.contracts")}</h2>
          {contracts.isError && <QueryError error={contracts.error} />}
          <ul className="mt-2 divide-y text-sm" data-testid="client-contracts">
            {(contracts.data ?? []).map((k) => (
              <li key={k.id} className="flex flex-wrap justify-between gap-2 py-2">
                <span className="font-medium">{k.contract_number}</span>
                <span className="tabular-nums">{formatMoney(k.contract_value, locale)} · {formatDate(k.effective_date, locale)}{k.expiry_date ? ` → ${formatDate(k.expiry_date, locale)}` : ""}</span>
              </li>
            ))}
            {contracts.isSuccess && !contracts.data?.length && <li className="py-2 text-muted-foreground">{t("crm.noContracts")}</li>}
          </ul>
        </Card>
      </div>
    </div>
  );
}
