"use client";

import { useTranslations } from "next-intl";
import { Bot, User as UserIcon, Settings } from "lucide-react";
import type { ActorType, AuditLogOut } from "@aureon/shared-types";
import { cn } from "@/lib/utils";

function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  } catch {
    return iso;
  }
}

const ACTOR_ICON: Record<ActorType, typeof Bot> = {
  USER: UserIcon,
  AI: Bot,
  SYSTEM: Settings,
};

/** Render a before/after JSON payload compactly. Salary is already masked server-side. */
function PayloadCell({ payload }: { payload: Record<string, unknown> | null }) {
  if (!payload || Object.keys(payload).length === 0) return <span className="text-muted-foreground">—</span>;
  const entries = Object.entries(payload);
  const shown = entries.slice(0, 3);
  return (
    <ul className="space-y-0.5 font-mono text-caption tabular-nums">
      {shown.map(([k, v]) => (
        <li key={k} className="truncate" title={`${k}: ${String(v)}`}>
          <span className="text-muted-foreground">{k}:</span> {String(v)}
        </li>
      ))}
      {entries.length > shown.length ? (
        <li className="text-muted-foreground">+{entries.length - shown.length}…</li>
      ) : null}
    </ul>
  );
}

export function AuditLogTable({ rows }: { rows: AuditLogOut[] }) {
  const t = useTranslations("audit");

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full border-collapse text-left text-body">
        <thead>
          <tr className="border-b border-border bg-muted/40 text-caption text-muted-foreground">
            <th scope="col" className="px-4 py-3 font-medium">{t("table.occurredAt")}</th>
            <th scope="col" className="px-4 py-3 font-medium">{t("table.actor")}</th>
            <th scope="col" className="px-4 py-3 font-medium">{t("table.action")}</th>
            <th scope="col" className="px-4 py-3 font-medium">{t("table.target")}</th>
            <th scope="col" className="px-4 py-3 font-medium">{t("table.before")}</th>
            <th scope="col" className="px-4 py-3 font-medium">{t("table.after")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const Icon = ACTOR_ICON[row.actor_type] ?? UserIcon;
            const actorLabel =
              row.actor_type === "AI"
                ? t("actor.ai")
                : row.actor_type === "SYSTEM"
                  ? t("actor.system")
                  : (row.actor?.full_name ?? t("actor.unknown"));
            return (
              <tr key={row.id} className="border-b border-border last:border-0 align-top">
                <td className="whitespace-nowrap px-4 py-3 font-mono text-caption tabular-nums">
                  {formatDateTime(row.occurred_at)}
                </td>
                <td className="px-4 py-3">
                  <span className="flex items-center gap-2">
                    <Icon aria-hidden className={cn("h-4 w-4", row.actor_type === "AI" ? "text-ai" : "text-muted-foreground")} />
                    <span>
                      <span className="block">{actorLabel}</span>
                      {row.actor_role_code ? (
                        <span className="block text-caption text-muted-foreground">{row.actor_role_code}</span>
                      ) : null}
                    </span>
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-caption">{row.action}</td>
                <td className="px-4 py-3 font-mono text-caption">
                  <span className="block">{row.target_type}</span>
                  {row.target_id ? (
                    <span className="block truncate text-muted-foreground" title={row.target_id}>
                      {row.target_id.slice(0, 8)}…
                    </span>
                  ) : null}
                </td>
                <td className="px-4 py-3"><PayloadCell payload={row.before} /></td>
                <td className="px-4 py-3"><PayloadCell payload={row.after} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
