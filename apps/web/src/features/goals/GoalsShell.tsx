/** Server wrapper of every `/goals` screen: tab bar Cây mục tiêu · Check-in filtered by role (06 §3.4 M1.4). */
import Link from "next/link";
import { getServerSession } from "next-auth";
import { getTranslations } from "next-intl/server";
import { authOptions } from "@/lib/auth";
import { visibleGoalsTabs, type GoalsTabKey } from "@/lib/permissions";
import { cn } from "@/lib/utils";

export interface GoalsUser { id: string; role: string; permissions: string[] }

export async function goalsUser(): Promise<GoalsUser> {
  const session = await getServerSession(authOptions);
  return { id: session?.user.id ?? "", role: session?.user.role ?? "", permissions: session?.user.permissions ?? [] };
}

/** Session capabilities (display only — the API enforces scope, R-DEC-57). */
export const goalCaps = (u: GoalsUser) => ({
  userId: u.id,
  isEmployee: u.role === "EMP",
  canManage: u.role !== "EMP" && u.permissions.includes("execution:write"),
  canFilterDepartment: (u.role === "CEO" || u.role === "DIR") && u.permissions.includes("hr:read"),
  /** CEO goals may sit at company level (no department); DIR/MGR goals are pinned to their scope (`goal_scope.pin_department`). */
  companyWide: u.role === "CEO",
  /** KPI/OKR owner picker reads `/platform/users` (EP-ADM, `platform:read`: CEO/ADM); others own what they create. */
  canPickOwner: u.permissions.includes("platform:read"),
});
export type GoalCaps = ReturnType<typeof goalCaps>;

export async function GoalsShell({ active, user, children }: { active: GoalsTabKey | null; user: GoalsUser; children: React.ReactNode }) {
  const t = await getTranslations("goals.tabs");
  const tabs = visibleGoalsTabs(user.role, user.permissions);
  return (
    <div className="flex flex-col gap-4" data-testid="goals-shell">
      <nav aria-label={t("label")} className="flex flex-wrap gap-1 border-b" data-testid="goals-tabs">
        {tabs.map((tab) => (
          <Link key={tab.key} href={tab.href} aria-current={tab.key === active ? "page" : undefined} data-testid={`goals-tab-${tab.key}`}
            className={cn("-mb-px border-b-2 px-3 py-2 text-sm", tab.key === active ? "border-primary font-medium text-primary" : "border-transparent text-muted-foreground hover:text-foreground")}>
            {t(tab.key)}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  );
}
