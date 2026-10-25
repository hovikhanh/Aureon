"use client";
/** SCR-55 `/work/projects`: progress bar vs plan marker, "Trễ" flag (`late`), overdue count; filters late/status/department; create (MGR+). */
import * as React from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { formatDate, formatPct, type AppLocale } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/select";
import { LoadError } from "./common";
import { CreateProjectDialog } from "./CreateProjectDialog";
import { useMembers, useProjects, type ProjectOut } from "./use-work";

export const PROJECT_STATUSES = ["planned", "active", "on_hold", "done", "cancelled"] as const;

export function ProgressBar({ progress, planned }: { progress: number | null | undefined; planned: number | null | undefined }) {
  const t = useTranslations("work.projects");
  const locale = useLocale() as AppLocale;
  const p = progress ?? 0;
  return (
    <div className="flex min-w-36 items-center gap-2" aria-label={t("progressLabel", { progress: formatPct(p, locale), planned: planned === null || planned === undefined ? "—" : formatPct(planned, locale) })}>
      <div className="relative h-2 flex-1 rounded-full bg-muted">
        <div className="h-2 rounded-full bg-primary" style={{ width: `${Math.min(100, p)}%` }} />
        {planned !== null && planned !== undefined && <div className="absolute -top-1 h-4 w-0.5 bg-foreground" style={{ left: `${Math.min(100, planned)}%` }} data-testid="planned-marker" />}
      </div>
      <span className="w-14 text-right text-xs tabular-nums">{progress === null || progress === undefined ? "—" : formatPct(p, locale)}</span>
    </div>
  );
}

export function ProjectsView({ canCreate, canReadOrg, userId }: { canCreate: boolean; canReadOrg: boolean; userId: string }) {
  const t = useTranslations("work");
  const locale = useLocale() as AppLocale;
  const [late, setLate] = React.useState(false);
  const [status, setStatus] = React.useState("");
  const [dept, setDept] = React.useState("");
  const [creating, setCreating] = React.useState(false);
  const members = useMembers(canReadOrg);
  const departments = [...new Map((members.data ?? []).map((m) => [m.department_id, m.department_name])).entries()];
  const deptName = new Map(departments);
  const q = useProjects({ late: late || null, status: status || null, department_id: dept || null, sort_by: "planned_end_date", limit: 100 });
  const rows: ProjectOut[] = q.data?.data ?? [];
  return (
    <div className="flex flex-col gap-4" data-testid="projects">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">{t("projects.title")}</h2>
          <p className="text-sm text-muted-foreground">{t("projects.hint")}</p>
        </div>
        {canCreate && <Button onClick={() => setCreating(true)} data-testid="project-create">{t("projects.create")}</Button>}
      </div>
      <Card className="flex flex-wrap items-end gap-3 p-3">
        <span className="flex items-center gap-1.5 pb-2">
          <Checkbox id="pf-late" checked={late} onCheckedChange={(v) => setLate(v === true)} data-testid="projects-late" />
          <Label htmlFor="pf-late" className="text-sm font-normal">{t("projects.onlyLate")}</Label>
        </span>
        <div className="flex flex-col gap-1">
          <Label htmlFor="pf-status" className="text-xs">{t("projects.status")}</Label>
          <NativeSelect id="pf-status" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="projects-status">
            <option value="">{t("projects.allStatuses")}</option>
            {PROJECT_STATUSES.map((s) => <option key={s} value={s}>{t(`projectStatus.${s}`)}</option>)}
          </NativeSelect>
        </div>
        {departments.length > 1 && (
          <div className="flex flex-col gap-1">
            <Label htmlFor="pf-dept" className="text-xs">{t("projects.department")}</Label>
            <NativeSelect id="pf-dept" value={dept} onChange={(e) => setDept(e.target.value)} data-testid="projects-dept">
              <option value="">{t("board.allDepartments")}</option>
              {departments.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
            </NativeSelect>
          </div>
        )}
      </Card>
      {q.isError && <LoadError onRetry={() => void q.refetch()} />}
      {q.isSuccess && !rows.length && <p className="text-sm text-muted-foreground" data-testid="projects-empty">{t("projects.empty")}</p>}
      {rows.length > 0 && (
        <Card className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="projects-table">
            <thead className="text-left text-xs text-muted-foreground">
              <tr>{["code", "name", "department", "status", "progress", "overdue", "due"].map((h) => <th key={h} className="px-3 py-2 font-medium">{t(`projects.${h}` as "projects.code")}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.id} className="border-t" data-testid={`project-row-${p.code}`} data-late={p.late ? "true" : "false"}>
                  <td className="px-3 py-2 font-mono text-xs"><Link href={`/work/projects/${p.id}`} className="text-primary hover:underline">{p.code}</Link></td>
                  <td className="px-3 py-2">
                    <Link href={`/work/projects/${p.id}`} className="hover:underline">{p.name}</Link>
                    {p.late && <Badge variant="danger" className="ml-2" data-testid="project-late">{t("projects.late")}</Badge>}
                  </td>
                  <td className="px-3 py-2 text-xs">{(p.department_id && deptName.get(p.department_id)) || "—"}</td>
                  <td className="px-3 py-2"><Badge>{t(`projectStatus.${p.status}` as "projectStatus.active")}</Badge></td>
                  <td className="px-3 py-2"><ProgressBar progress={p.progress_pct} planned={p.planned_pct} /></td>
                  <td className="px-3 py-2 tabular-nums">
                    <Link href={`/work/projects/${p.id}?tab=tasks`} className={(p.overdue_tasks ?? 0) > 0 ? "text-danger hover:underline" : "hover:underline"}>{p.overdue_tasks ?? 0}</Link>
                  </td>
                  <td className="px-3 py-2 text-xs">{p.due_date ? formatDate(`${p.due_date}T00:00:00+07:00`, locale) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {canCreate && <CreateProjectDialog open={creating} onOpenChange={setCreating} ownerId={userId} />}
    </div>
  );
}
