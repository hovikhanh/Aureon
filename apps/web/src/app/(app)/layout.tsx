import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";
import type { RoleCode } from "@aureon/shared-types";

/**
 * Route-group layout for the authenticated app (06 §3). Mounts the shell around every page.
 *
 * Auth/session is not built yet (T-106/T-107); the active role is a fixed placeholder here.
 * T-107 will replace this constant with the real session role (`UserOut.role.code`, 05 §4.2)
 * and pass it to `AppShell` — no other shell code changes.
 */
const CURRENT_ROLE: RoleCode = "ROLE-01";

export default function AppLayout({ children }: { children: ReactNode }) {
  return <AppShell role={CURRENT_ROLE}>{children}</AppShell>;
}
