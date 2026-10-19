"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Search, Filter } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { ActorType } from "@aureon/shared-types";
import { LoadingState } from "@/components/states";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { ForbiddenState } from "@/components/states/ForbiddenState";
import { useAuth } from "@/features/auth/auth-context";
import { getAuditLogsApi } from "./audit-api";
import { AuditLogTable } from "./AuditLogTable";

type FilterActor = ActorType | "ALL";
const ACTOR_OPTIONS: FilterActor[] = ["ALL", "USER", "AI", "SYSTEM"];

/**
 * SCR-14 — Audit log (EP-52; ROLE-01 only; 06 §4.11). CEO looks up "who did what,
 * what the AI did". Filters by action substring + actor type. Salary always masked
 * (enforced server-side). Loading / empty / error states per 06 §4.11.
 */
export function AuditLogView() {
  const t = useTranslations("audit");
  const { role, session, isLoading: isAuthLoading } = useAuth();

  const [action, setAction] = useState("");
  const [actorType, setActorType] = useState<FilterActor>("ALL");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["audit-logs", action, actorType],
    queryFn: () =>
      getAuditLogsApi(
        {
          action: action || undefined,
          actorType: actorType !== "ALL" ? actorType : undefined,
          pageSize: 50,
        },
        session?.accessToken,
      ),
    enabled: !!session?.accessToken && role === "ROLE-01",
    retry: 1,
    staleTime: 15_000,
  });

  // SCR-14 is ROLE-01 only (02 §3.6); never silently hide (06 §3.2).
  if (!isAuthLoading && role !== "ROLE-01") {
    return (
      <div className="space-y-6">
        <header>
          <h1 className="text-h1 text-foreground">{t("title")}</h1>
        </header>
        <ForbiddenState />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-h1 text-foreground">{t("title")}</h1>
        <p className="text-body text-muted-foreground">{t("subtitle")}</p>
      </header>

      <div className="flex flex-wrap items-center gap-3">
        <label className="relative flex-1 min-w-[220px]">
          <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <span className="sr-only">{t("searchLabel")}</span>
          <input
            type="search"
            value={action}
            onChange={(e) => setAction(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="h-10 w-full rounded-md border border-border bg-background pl-9 pr-3 text-body outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </label>

        <label className="flex items-center gap-2">
          <Filter aria-hidden className="h-4 w-4 text-muted-foreground" />
          <span className="sr-only">{t("filters.actorLabel")}</span>
          <select
            value={actorType}
            onChange={(e) => setActorType(e.target.value as FilterActor)}
            className="h-10 rounded-md border border-border bg-background px-3 text-body outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {ACTOR_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === "ALL" ? t("filters.actorAll") : t(`actor.${opt === "USER" ? "user" : opt === "AI" ? "ai" : "system"}` as Parameters<typeof t>[0])}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isLoading || isAuthLoading ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState
          title={t("error.title")}
          description={t("error.description")}
          onRetry={() => void refetch()}
        />
      ) : !data || data.data.length === 0 ? (
        <EmptyState title={t("empty.title")} description={t("empty.description")} />
      ) : (
        <>
          <p className="text-caption text-muted-foreground" aria-live="polite">
            {t("count", { count: data.meta.total })}
          </p>
          <AuditLogTable rows={data.data} />
        </>
      )}
    </div>
  );
}
