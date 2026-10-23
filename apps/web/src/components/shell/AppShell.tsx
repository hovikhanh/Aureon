"use client";
import * as React from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

export interface ShellUser {
  id: string;
  email: string;
  name: string;
  role: string;
  permissions: string[];
  scopePillars?: string[];
}

export function AppShell({ user, children }: { user: ShellUser; children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [collapsed, setCollapsed] = React.useState(false);
  return (
    <div className="flex min-h-dvh">
      <Sidebar
        role={user.role}
        permissions={user.permissions}
        pillars={user.scopePillars ?? []}
        mobileOpen={mobileOpen}
        collapsed={collapsed}
        onCloseMobile={() => setMobileOpen(false)}
        onToggleCollapsed={() => setCollapsed((c) => !c)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header user={user} onOpenMenu={() => setMobileOpen(true)} />
        <main id="main" className="min-w-0 flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
