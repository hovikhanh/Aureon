import type { ReactNode } from "react";
import { AuthenticatedAppShell } from "@/components/layout/AuthenticatedAppShell";
import { RouteGuard } from "@/components/layout/RouteGuard";

/**
 * Route-group layout for the authenticated app (06 §3, T-107).
 * Mounts AuthenticatedAppShell (with active role and Role Switcher), and RouteGuard.
 */
export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthenticatedAppShell>
      <RouteGuard>{children}</RouteGuard>
    </AuthenticatedAppShell>
  );
}
