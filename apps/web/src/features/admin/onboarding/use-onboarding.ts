"use client";
/** SCR-66 data hooks (T-648F): EP-ADM-13/14 state; the wizard calls existing EPs only (R-DEC-75). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { Api } from "@aureon/shared-types";
import { api, apiRequest } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import type { OnboardingState, Step } from "./logic";

export type Organization = Api.OrganizationOut;
export type UserAdmin = Api.UserAdminOut;
type Action = "start" | "complete_step" | "skip_step" | "reopen_step" | "finish" | "reset";

export const useOnboarding = () => useQuery({ queryKey: qk.onboarding(), queryFn: ({ signal }) => api.get<OnboardingState>("/platform/onboarding", undefined, signal) });

/** EP-ADM-14 with the current `version` (stale → 409); the returned state replaces the cache. */
export function usePatchOnboarding() {
  const client = useQueryClient();
  return async (state: OnboardingState, action: Action, step?: Step, refs?: Record<string, unknown>, reason?: string) => {
    const body = { action, step: step ?? null, refs: refs ?? null, reason: reason ?? null, version: action === "start" ? null : state.version ?? 0 };
    const next = await api.patch<OnboardingState>("/platform/onboarding", body);
    client.setQueryData(qk.onboarding(), next);
    return next;
  };
}

export const useOrganizations = () =>
  useQuery({ queryKey: ["org", "organizations"], queryFn: ({ signal }) => api.get<Organization[]>("/org/organizations", { limit: 20 }, signal) });

/** EP-ADM-01 — every user (to hide employees that already have an account). */
export const useAllUsers = () =>
  useQuery({ queryKey: qk.users({ onboarding: true }), queryFn: ({ signal }) => apiRequest<UserAdmin[]>("/platform/users", { query: { limit: 100 }, signal }).then((r) => r.data) });
