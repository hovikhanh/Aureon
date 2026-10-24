"use client";
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { OctagonX, Power } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { formatDateTime, formatNumber, formatPct, type AppLocale } from "@/lib/format";
import { cn } from "@/lib/utils";
import { KillSwitchDialog } from "./KillSwitchDialog";
import { agentName, costTone, levelKey } from "./logic";
import { useActions, useAgents, useKillSwitch, useUsage } from "./use-ai-admin";
import type { Viewer } from "./types";
import { ActionQueue } from "./ActionQueue";

/** SCR-64 Tổng quan (06 §3.4): kill switch card + dialog (EP-AI-12/13), ceiling L2, monthly cost (EP-AI-15), queue (EP-AI-07). */
export function OverviewTab({ viewer, onOpen }: { viewer: Viewer; onOpen: (tab: "agents") => void }) {
  void onOpen;
  return (
    <div className="flex flex-col gap-4" data-testid="ai-overview">
      <div className="grid gap-4 lg:grid-cols-3">
        <KillSwitchCard />
        <div className="flex flex-col gap-4">
          <CeilingCard />
          <QueueCountCard />
        </div>
        <CostCard />
      </div>
      <ActionQueue viewer={viewer} />
    </div>
  );
}

function KillSwitchCard() {
  const t = useTranslations("aiAdmin.kill");
  const locale = useLocale() as AppLocale;
  const ks = useKillSwitch();
  const agents = useAgents();
  const [open, setOpen] = React.useState(false);
  const d = ks.data;
  const scope = d?.agents?.length ? d.agents.map((c) => agentName(agents.data?.find((a) => a.code === c), c, locale)).join(", ") : t("scopeAll");
  return (
    <Card className={cn("flex flex-col gap-3 p-4", d?.enabled && "border-warning")} data-testid="kill-card" data-enabled={String(Boolean(d?.enabled))}>
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold">{t("title")}</h2>
        {d && <Badge variant={d.enabled ? "warning" : "success"} data-testid="kill-state">{d.enabled ? t("on") : t("off")}</Badge>}
      </div>
      {ks.isError && <p role="alert" className="text-sm text-danger">{t("error")}</p>}
      {d && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
          <dt className="text-muted-foreground">{t("mode")}</dt><dd data-testid="kill-mode">{d.enabled ? t(`modes.${d.mode}`) : "—"}</dd>
          <dt className="text-muted-foreground">{t("scope")}</dt><dd data-testid="kill-scope">{d.enabled ? scope : "—"}</dd>
          <dt className="text-muted-foreground">{t("lastChange")}</dt>
          <dd>{d.changed_at ? t("changedAt", { at: formatDateTime(d.changed_at, locale) }) : "—"}</dd>
          <dt className="text-muted-foreground">{t("reason")}</dt><dd data-testid="kill-reason">{d.reason ?? "—"}</dd>
        </dl>
      )}
      <div className="mt-auto">
        {d?.enabled
          ? <Button variant="outline" onClick={() => setOpen(true)} data-testid="kill-off"><Power className="h-4 w-4" aria-hidden />{t("turnOff")}</Button>
          : <Button variant="danger" onClick={() => setOpen(true)} disabled={!d} data-testid="kill-on"><OctagonX className="h-4 w-4" aria-hidden />{t("turnOn")}</Button>}
      </div>
      {d && <KillSwitchDialog open={open} onOpenChange={setOpen} current={d} agents={agents.data ?? []} />}
    </Card>
  );
}

function CeilingCard() {
  const t = useTranslations("aiAdmin");
  const ks = useKillSwitch();
  const ceiling = ks.data?.autonomy_ceiling ?? "L2";
  return (
    <Card className="p-4" data-testid="ceiling-card">
      <h2 className="font-semibold">{t("ceiling.title", { level: ceiling })}</h2>
      <p className="mt-1 text-sm text-muted-foreground">{t(levelKey(ceiling))} — {t("ceiling.hint")}</p>
    </Card>
  );
}

function QueueCountCard() {
  const t = useTranslations("aiAdmin.queue");
  const q = useActions({ status: "proposed" });
  return (
    <Card className="p-4" data-testid="queue-card">
      <h2 className="font-semibold">{t("title")}</h2>
      {q.isError ? <p role="alert" className="text-sm text-danger">{t("error")}</p>
        : <p className="mt-1 text-3xl font-semibold" data-testid="queue-count">{q.data?.length ?? "…"}</p>}
      <a href="#ai-queue" className="text-sm text-primary hover:underline">{t("open")}</a>
    </Card>
  );
}

function CostCard() {
  const t = useTranslations("aiAdmin.cost");
  const locale = useLocale() as AppLocale;
  const u = useUsage({ group_by: "agent" });
  const d = u.data;
  const tone = d ? costTone(d.used_pct) : "ok";
  return (
    <Card className="flex flex-col gap-2 p-4" data-testid="cost-card" data-tone={tone}>
      <h2 className="font-semibold">{t("title")}</h2>
      {u.isError && <p role="alert" className="text-sm text-danger">{t("error")}</p>}
      {d && (
        <>
          <p className="text-sm" data-testid="cost-used">{t("used", { used: formatNumber(d.used_usd, locale, 2), budget: formatNumber(d.budget_usd, locale, 2) })}</p>
          <div className="h-2 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.min(100, d.used_pct)} aria-label={t("title")}>
            <div className={cn("h-full", tone === "danger" ? "bg-danger" : tone === "warning" ? "bg-warning" : "bg-success")} style={{ width: `${Math.min(100, d.used_pct)}%` }} />
          </div>
          <p className="text-xs text-muted-foreground">{formatPct(d.used_pct, locale)}{tone !== "ok" && ` — ${t(tone)}`}</p>
        </>
      )}
      <Link href="/admin/ai/logs?tab=cost" className="mt-auto text-sm text-primary hover:underline" data-testid="cost-link">{t("link")}</Link>
    </Card>
  );
}
