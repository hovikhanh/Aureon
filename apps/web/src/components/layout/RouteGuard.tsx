"use client";

import { usePathname } from "next/navigation";
import { type ReactNode } from "react";
import { ForbiddenState } from "@/components/states/ForbiddenState";
import { useAuth } from "@/features/auth/auth-context";

export function RouteGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { role } = useAuth();

  // 02 §4.2: Reviewer (ROLE-05) has no dashboard 4 pillars access (TC-DASH-004)
  if (pathname === "/dashboard" && role === "ROLE-05") {
    return (
      <div className="p-6">
        <ForbiddenState />
      </div>
    );
  }

  // 02 §3.6: Audit log is CEO-only (ROLE-01)
  if (pathname === "/audit" && role !== "ROLE-01") {
    return (
      <div className="p-6">
        <ForbiddenState />
      </div>
    );
  }

  // 02 §3.4: UC-07 Upload is only for CEO (ROLE-01) and Reviewer (ROLE-05)
  if (pathname === "/upload" && role !== "ROLE-01" && role !== "ROLE-05") {
    return (
      <div className="p-6">
        <ForbiddenState />
      </div>
    );
  }

  return <>{children}</>;
}
