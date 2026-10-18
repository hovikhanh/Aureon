"use client";

/**
 * Current-role context (T-108).
 *
 * The shell needs the active RoleCode to filter the sidebar (nav-config.ts `getNavItems`)
 * and to resolve the post-login home route (`HOME_ROUTE`). Auth/session does not exist yet
 * (T-106/T-107); until then the role is supplied as a prop to `RoleProvider`. T-107 will feed
 * the real `UserOut.role.code` (05 §4.2) through the same provider, so consumers do not change.
 */
import { createContext, useContext, type ReactNode } from "react";
import type { RoleCode } from "@aureon/shared-types";

const RoleContext = createContext<RoleCode | null>(null);

export function RoleProvider({ role, children }: { role: RoleCode; children: ReactNode }) {
  return <RoleContext.Provider value={role}>{children}</RoleContext.Provider>;
}

/** Read the active role. Throws if used outside `RoleProvider` so misuse fails fast. */
export function useCurrentRole(): RoleCode {
  const role = useContext(RoleContext);
  if (role === null) {
    throw new Error("useCurrentRole must be used within a RoleProvider");
  }
  return role;
}
