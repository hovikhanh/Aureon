/** Server wrapper of every `/work` screen: title + tab bar filtered by role/permissions (R-DEC-48). */
import { getServerSession } from "next-auth";
import { getTranslations } from "next-intl/server";
import { authOptions } from "@/lib/auth";
import { canDomain, visibleWorkTabs, type WorkTabKey } from "@/lib/permissions";
import { WorkTabs } from "./WorkTabs";

export interface WorkUser { id: string; role: string; permissions: string[]; scopePillars: string[] }

export async function workUser(): Promise<WorkUser> {
  const session = await getServerSession(authOptions);
  const u = session?.user;
  return { id: u?.id ?? "", role: u?.role ?? "", permissions: u?.permissions ?? [], scopePillars: u?.scopePillars ?? [] };
}

/** Members / org tree readable (EP-ORG-24): `hr:read` inside khối O, never EMP / REV (→ `FORBIDDEN_SCOPE`, 10 §7.2.1). */
export function canReadOrg(user: WorkUser): boolean {
  return canDomain(user.permissions, user.scopePillars, "hr") && user.role !== "EMP" && user.role !== "REV";
}

/** Capabilities of the task panel from the session (server-side; the API still enforces every rule). */
export function detailCaps(user: WorkUser) {
  return {
    isEmployee: user.role === "EMP",
    canReadAudit: user.permissions.includes("platform:read"),
    // EP-ORG-24 `/org/tree` is `require_pillar_permission("hr:read")`: a DIR outside khối O (CFO,
    // Sales) gets 403 — pickers then fall back to ids instead of calling it (M6).
    canReadOrg: canReadOrg(user),
  };
}

export async function WorkShell({ active, user, children }: { active: WorkTabKey; user: WorkUser; children: React.ReactNode }) {
  const t = await getTranslations("work.tabs");
  const tabs = visibleWorkTabs(user.role, user.permissions).map(({ key, href }) => ({ key, href }));
  return (
    <div className="flex flex-col gap-4" data-testid="work-shell">
      <h1 className="sr-only">{t("label")}</h1>
      <WorkTabs tabs={tabs} active={active} />
      {children}
    </div>
  );
}
