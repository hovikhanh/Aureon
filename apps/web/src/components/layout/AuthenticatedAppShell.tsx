"use client";

import { type ReactNode } from "react";
import { useAuth } from "@/features/auth/auth-context";
import { AppShell } from "./AppShell";

export function AuthenticatedAppShell({ children }: { children: ReactNode }) {
  const { role } = useAuth();
  return <AppShell role={role}>{children}</AppShell>;
}
