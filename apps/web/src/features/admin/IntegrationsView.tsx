"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ApiError } from "@/lib/api-client";
import type { Api } from "@aureon/shared-types";
import {
  useConnectProvider,
  useDisconnectProvider,
  useIntegrationProviders,
} from "./use-integrations";

type ProviderStatusOut = Api.ProviderStatusOut;

const BADGE: Record<string, "success" | "danger" | "warning" | "outline"> = {
  connected: "success",
  expired: "danger",
  revoked: "warning",
  none: "outline",
};

/**
 * SCR `/settings/integrations` (M3.1, EP-INT-01..04): the caller connects/disconnects their own
 * Google/Outlook calendar. Tokens are never shown (R-DEC-117); connect redirects to the provider
 * consent screen (PKCE). A `expired` status prompts reconnect. Sync itself runs in the background.
 */
export function IntegrationsView() {
  const t = useTranslations("integrations");
  const providers = useIntegrationProviders();
  const connect = useConnectProvider();
  const disconnect = useDisconnectProvider();
  const [busy, setBusy] = React.useState<string | null>(null);

  const startConnect = (provider: string) => {
    setBusy(provider);
    connect.mutate(provider, {
      onSuccess: (out) => { if (out.authorize_url) window.location.assign(out.authorize_url); },
      onSettled: () => setBusy(null),
    });
  };

  const err = (providers.error ?? connect.error ?? disconnect.error) as unknown;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4" data-testid="integrations-view">
      <header>
        <h1 className="text-xl font-semibold">{t("title")}</h1>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </header>

      {err ? (
        <p role="alert" className="text-sm text-destructive" data-testid="integrations-error">
          {err instanceof ApiError ? err.message : t("errorGeneric")}
        </p>
      ) : null}

      {(providers.data ?? []).map((p: ProviderStatusOut) => {
        const connected = p.status === "connected";
        const expired = p.status === "expired";
        return (
          <Card key={p.provider} data-testid={`integration-${p.provider}`}>
            <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
              <CardTitle className="text-base">{t(`provider.${p.provider}`)}</CardTitle>
              <Badge variant={BADGE[p.status] ?? "outline"} data-testid={`integration-status-${p.provider}`}>
                {t(`status.${p.status}`)}
              </Badge>
            </CardHeader>
            <CardContent className="flex items-center justify-between gap-3">
              {!p.configured ? (
                <p className="text-sm text-muted-foreground">{t("notConfigured")}</p>
              ) : connected ? (
                <Button variant="outline" size="sm" onClick={() => disconnect.mutate(p.provider)} disabled={disconnect.isPending} data-testid={`integration-disconnect-${p.provider}`}>
                  {t("disconnect")}
                </Button>
              ) : (
                <Button size="sm" onClick={() => startConnect(p.provider)} disabled={!!busy} data-testid={`integration-connect-${p.provider}`}>
                  {expired ? t("reconnect") : t("connect")}
                </Button>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
