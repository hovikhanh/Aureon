"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { Api } from "@aureon/shared-types";

type ProviderStatusOut = Api.ProviderStatusOut;
type ConnectOut = Api.ConnectOut;

/** EP-INT-01 — the caller's calendar providers + connection status (no tokens). */
export function useIntegrationProviders() {
  return useQuery({
    queryKey: qk.integrationProviders(),
    queryFn: ({ signal }) => api.get<ProviderStatusOut[]>("/integrations/providers", undefined, signal),
  });
}

/** EP-INT-02 — start OAuth: returns the consent URL to redirect to (fresh Idempotency-Key). */
export function useConnectProvider() {
  return useMutation<ConnectOut, unknown, string>({
    mutationFn: (provider) => api.post<ConnectOut>(`/integrations/${provider}/connect`, {}),
  });
}

/** EP-INT-04 — disconnect a provider (204), then refresh the status list. */
export function useDisconnectProvider() {
  const qc = useQueryClient();
  return useMutation<void, unknown, string>({
    mutationFn: (provider) =>
      apiRequest<void>(`/integrations/${provider}/disconnect`, { method: "DELETE" }).then(() => undefined),
    onSuccess: () => void qc.invalidateQueries({ queryKey: qk.integrationProviders() }),
  });
}
