/** Server wrapper of every `/work` screen: title + tab bar filtered by role/permissions (R-DEC-48). */
import { getServerSession } from "next-auth";
import { getTranslations } from "next-intl/server";
import { authOptions } from "@/lib/auth";
import { visibleWorkTabs, type WorkTabKey } from "@/lib/permissions";
import { WorkTabs } from "./WorkTabs";

export interface WorkUser { id: string; role: string; permissions: string[] }

export async function workUser(): Promise<WorkUser> {
  const session = await getServerSession(authOptions);
  return { id: session?.user.id ?? "", role: session?.user.role ?? "", permissions: session?.user.permissions ?? [] };
}

/** Capabilities of the task panel from the session (server-side; the API still enforces every rule). */
export function detailCaps(user: WorkUser) {
  return {
    isEmployee: user.role === "EMP",
    canReadAudit: user.permissions.includes("platform:read"),
    canReadOrg: user.permissions.includes("hr:read") && user.role !== "EMP",
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
