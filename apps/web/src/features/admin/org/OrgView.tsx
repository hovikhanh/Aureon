"use client";
/**
 * SCR-51 `/admin/org` (T-617F, 06 §3.4): left = Organization → Department (by `parent_id`) →
 * Team → Employee with headcount (EP-ORG-24); top = `as_of` picker (past → read only + label);
 * right = detail panel (info, head, assignment history EP-ORG-21) + actions (EP-ORG-07..15/22).
 */
import * as React from "react";
import { LineageChip } from "@/components/ai/LineageChip";
import { useLocale, useTranslations } from "next-intl";
import { Building2, ChevronDown, ChevronRight, Users } from "lucide-react";
import { apiRequest } from "@/lib/api-client";
import { formatDate, type AppLocale } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toast";
import { AdminHeader, ConfirmDialog } from "../common";
import { nestDepartments, type DeptNode } from "./org-tree";
import { AssignDialog, DepartmentDialog, TeamDialog } from "./OrgForms";
import { todayIso, useAssignmentHistory, useOrgMutation, useOrgTree, type TreeDept, type TreeMember } from "./use-org";

type Sel = { kind: "org" } | { kind: "dept"; id: string } | { kind: "team"; id: string; deptId: string } | { kind: "emp"; id: string; deptId: string };
type DialogState = null | "newDept" | "editDept" | "newTeam" | "assign" | "transfer" | "archiveDept" | "archiveTeam";

export function OrgView({ canEdit }: { canEdit: boolean }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const today = todayIso();
  const [asOf, setAsOf] = React.useState(today);
  const tree = useOrgTree(asOf);
  const [sel, setSel] = React.useState<Sel>({ kind: "org" });
  const [dialog, setDialog] = React.useState<DialogState>(null);
  const past = asOf < today;
  const editable = canEdit && !past;
  const data = tree.data?.data;
  const depts = React.useMemo(() => data?.departments ?? [], [data]);
  const nodes = React.useMemo(() => nestDepartments(depts), [depts]);
  const everyone = React.useMemo(() => depts.flatMap((d) => d.members).sort((a, b) => a.employee_code.localeCompare(b.employee_code)), [depts]);
  const dept = sel.kind === "org" ? null : depts.find((d) => d.id === (sel.kind === "dept" ? sel.id : sel.deptId)) ?? null;
  const total = depts.reduce((s, d) => s + d.headcount, 0);

  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-4" data-testid="org-admin">
      <AdminHeader title={t("orgAdmin.title")} hint={t("orgAdmin.hint")}>
        <Label htmlFor="as-of" className="text-sm">{t("orgAdmin.asOf")}</Label>
        <Input id="as-of" type="date" className="w-44" value={asOf} max={today} onChange={(e) => { if (e.target.value) { setAsOf(e.target.value); setSel({ kind: "org" }); } }} data-testid="org-as-of" />
        {past && <Button size="sm" variant="outline" onClick={() => setAsOf(today)} data-testid="org-as-of-today">{t("orgAdmin.backToToday")}</Button>}
        {editable && <Button size="sm" onClick={() => setDialog("newDept")} data-testid="org-new-dept">{t("orgAdmin.newDept")}</Button>}
        {editable && <Button size="sm" variant="outline" onClick={() => setDialog("assign")} data-testid="org-assign">{t("orgAdmin.assign")}</Button>}
      </AdminHeader>
      {past && <p className="rounded border border-warning bg-warning-subtle px-3 py-2 text-sm" data-testid="org-past-banner">{t("orgAdmin.pastBanner", { date: formatDate(asOf, locale) })}</p>}
      {tree.isPending && <div className="h-64 animate-pulse rounded-lg bg-muted" />}
      {tree.isError && <p role="alert" className="text-danger">{t("errors.generic")}</p>}
      {data && (
        <div className="grid gap-4 lg:grid-cols-[minmax(320px,2fr)_3fr]">
          <Card className="max-h-[70vh] overflow-auto p-2">
            <ul role="tree" aria-label={t("orgAdmin.treeLabel")} data-testid="org-tree">
              <li role="treeitem" aria-expanded aria-selected={sel.kind === "org"}>
                <NodeButton active={sel.kind === "org"} onClick={() => setSel({ kind: "org" })} testId="org-node-root" icon={<Building2 className="h-4 w-4" aria-hidden />} label={data.organization.name} count={total} />
                <ul role="group" className="ml-3 border-l pl-2">
                  {nodes.map((n) => <DeptBranch key={n.dept.id} node={n} sel={sel} onSelect={setSel} />)}
                </ul>
              </li>
            </ul>
            {!depts.length && <p className="p-3 text-sm text-muted-foreground">{t("orgAdmin.empty")}</p>}
          </Card>
          <Card className="p-4" data-testid="org-panel">
            {sel.kind === "org" && <OrgPanel name={data.organization.name} code={data.organization.code} depts={depts.length} headcount={total} />}
            {sel.kind === "dept" && dept && (
              <DeptPanel dept={dept} depts={depts} editable={editable} onAction={setDialog} onSelect={setSel} />
            )}
            {sel.kind === "team" && dept && <TeamPanel dept={dept} teamId={sel.id} editable={editable} onAction={setDialog} onSelect={setSel} />}
            {sel.kind === "emp" && dept && <EmployeePanel dept={dept} member={dept.members.find((m) => m.employee_id === sel.id) ?? null} depts={depts} editable={editable} onTransfer={() => setDialog("transfer")} />}
          </Card>
        </div>
      )}
      {data && editable && (
        <>
          <DepartmentDialog open={dialog === "newDept" || dialog === "editDept"} onOpenChange={(o) => !o && setDialog(null)} orgId={data.organization.id} departments={depts} members={everyone}
            editing={dialog === "editDept" ? dept : null} defaultParent={dialog === "newDept" && sel.kind === "dept" ? sel.id : null} />
          <TeamDialog open={dialog === "newTeam"} onOpenChange={(o) => !o && setDialog(null)} department={dept} />
          <AssignDialog open={dialog === "assign" || dialog === "transfer"} onOpenChange={(o) => !o && setDialog(null)} departments={depts} employees={everyone}
            employee={dialog === "transfer" && sel.kind === "emp" ? everyone.find((m) => m.employee_id === sel.id) ?? null : null} defaultDept={dialog === "assign" && dept ? dept.id : null} />
          <ArchiveDialogs dialog={dialog} setDialog={setDialog} sel={sel} dept={dept} onDone={() => setSel({ kind: "org" })} />
        </>
      )}
    </div>
  );
}

function NodeButton({ active, onClick, icon, label, count, testId, sub }: { active: boolean; onClick: () => void; icon?: React.ReactNode; label: string; count?: number; testId: string; sub?: string }) {
  return (
    <button type="button" onClick={onClick} data-testid={testId} aria-current={active || undefined}
      className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm hover:bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary ${active ? "bg-primary/10 font-medium text-primary" : ""}`}>
      {icon}
      <span className="min-w-0 flex-1 truncate">{label}{sub && <span className="ml-1 text-xs text-muted-foreground">{sub}</span>}</span>
      {count !== undefined && <Badge variant="outline" className="tabular-nums">{count}</Badge>}
    </button>
  );
}

function DeptBranch({ node, sel, onSelect }: { node: DeptNode<TreeDept>; sel: Sel; onSelect: (s: Sel) => void }) {
  const t = useTranslations();
  const d = node.dept;
  const inside = sel.kind !== "org" && (sel.kind === "dept" ? sel.id : sel.deptId) === d.id;
  const [open, setOpen] = React.useState(false);
  React.useEffect(() => { if (inside) setOpen(true); }, [inside]);
  const loose = d.members.filter((m) => !m.team_id);
  return (
    <li role="treeitem" aria-expanded={open} aria-selected={sel.kind === "dept" && sel.id === d.id} data-testid="org-dept" data-code={d.code}>
      <div className="flex items-center">
        <button type="button" onClick={() => setOpen(!open)} className="rounded p-1 hover:bg-muted" aria-label={t(open ? "orgAdmin.collapse" : "orgAdmin.expand", { name: d.name })}>
          {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </button>
        <NodeButton active={sel.kind === "dept" && sel.id === d.id} onClick={() => { onSelect({ kind: "dept", id: d.id }); setOpen(true); }} testId={`org-node-${d.code}`} label={d.name} sub={d.code} count={node.total} />
      </div>
      {open && (
        <ul role="group" className="ml-4 border-l pl-2">
          {node.children.map((c) => <DeptBranch key={c.dept.id} node={c} sel={sel} onSelect={onSelect} />)}
          {d.teams.map((tm) => (
            <li key={tm.id} role="treeitem" aria-selected={sel.kind === "team" && sel.id === tm.id}>
              <NodeButton active={sel.kind === "team" && sel.id === tm.id} onClick={() => onSelect({ kind: "team", id: tm.id, deptId: d.id })} testId={`org-node-${tm.code}`} icon={<Users className="h-3.5 w-3.5" aria-hidden />} label={tm.name} sub={tm.code} count={tm.headcount} />
              <ul role="group" className="ml-4">
                {d.members.filter((m) => m.team_id === tm.id).map((m) => <MemberItem key={m.employee_id} m={m} deptId={d.id} sel={sel} onSelect={onSelect} />)}
              </ul>
            </li>
          ))}
          {loose.map((m) => <MemberItem key={m.employee_id} m={m} deptId={d.id} sel={sel} onSelect={onSelect} />)}
        </ul>
      )}
    </li>
  );
}

function MemberItem({ m, deptId, sel, onSelect }: { m: TreeMember; deptId: string; sel: Sel; onSelect: (s: Sel) => void }) {
  return (
    <li role="treeitem" aria-selected={sel.kind === "emp" && sel.id === m.employee_id} data-testid="org-member" data-code={m.employee_code}>
      <NodeButton active={sel.kind === "emp" && sel.id === m.employee_id} onClick={() => onSelect({ kind: "emp", id: m.employee_id, deptId })} testId={`org-emp-${m.employee_code}`} label={m.full_name} sub={m.employee_code} />
    </li>
  );
}

function Info({ rows }: { rows: [string, React.ReactNode][] }) {
  return (
    <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5 text-sm">
      {rows.map(([k, v]) => <React.Fragment key={k}><dt className="text-muted-foreground">{k}</dt><dd>{v}</dd></React.Fragment>)}
    </dl>
  );
}

function OrgPanel({ name, code, depts, headcount }: { name: string; code: string; depts: number; headcount: number }) {
  const t = useTranslations();
  return (
    <div>
      <h2 className="text-lg font-semibold">{name}</h2>
      <Info rows={[[t("orgAdmin.field.code"), code], [t("orgAdmin.field.departments"), depts], [t("orgAdmin.field.headcount"), headcount]]} />
      <p className="mt-4 text-sm text-muted-foreground">{t("orgAdmin.pickNode")}</p>
    </div>
  );
}

function DeptPanel({ dept, depts, editable, onAction, onSelect }: { dept: TreeDept; depts: TreeDept[]; editable: boolean; onAction: (d: DialogState) => void; onSelect: (s: Sel) => void }) {
  const t = useTranslations();
  const head = depts.flatMap((d) => d.members).find((m) => m.employee_id === dept.manager_id);
  const parent = depts.find((d) => d.id === dept.parent_id);
  return (
    <div data-testid="dept-panel">
      <div className="flex items-center gap-2"><h2 className="text-lg font-semibold">{dept.name}</h2><LineageChip entity="hr.departments" id={dept.id} /></div>
      <Info rows={[[t("orgAdmin.field.code"), dept.code], [t("orgAdmin.field.parent"), parent?.name ?? t("common.none")], [t("orgAdmin.field.head"), head ? `${head.full_name} (${head.employee_code})` : t("common.none")],
        [t("orgAdmin.field.headcount"), dept.headcount], [t("orgAdmin.field.teams"), dept.teams.length]]} />
      {editable && (
        <div className="mt-4 flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => onAction("editDept")} data-testid="dept-edit">{t("orgAdmin.edit")}</Button>
          <Button size="sm" variant="outline" onClick={() => onAction("newDept")} data-testid="dept-add-child">{t("orgAdmin.addChild")}</Button>
          <Button size="sm" variant="outline" onClick={() => onAction("newTeam")} data-testid="dept-add-team">{t("orgAdmin.addTeam")}</Button>
          <Button size="sm" variant="outline" onClick={() => onAction("assign")} data-testid="dept-assign">{t("orgAdmin.assign")}</Button>
          <Button size="sm" variant="danger" onClick={() => onAction("archiveDept")} data-testid="dept-archive">{t("orgAdmin.archive")}</Button>
        </div>
      )}
      <h3 className="mt-6 text-sm font-semibold">{t("orgAdmin.members", { n: dept.members.length })}</h3>
      <ul className="mt-2 divide-y text-sm" data-testid="dept-members">
        {dept.members.map((m) => (
          <li key={m.employee_id}>
            <button type="button" className="flex w-full justify-between px-1 py-1.5 text-left hover:bg-muted" onClick={() => onSelect({ kind: "emp", id: m.employee_id, deptId: dept.id })}>
              <span>{m.full_name} <span className="text-xs text-muted-foreground">{m.employee_code}</span></span>
              <span className="text-xs text-muted-foreground">{dept.teams.find((x) => x.id === m.team_id)?.code ?? ""}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function TeamPanel({ dept, teamId, editable, onAction, onSelect }: { dept: TreeDept; teamId: string; editable: boolean; onAction: (d: DialogState) => void; onSelect: (s: Sel) => void }) {
  const t = useTranslations();
  const team = dept.teams.find((x) => x.id === teamId);
  if (!team) return null;
  const lead = dept.members.find((m) => m.employee_id === team.lead_employee_id);
  const members = dept.members.filter((m) => m.team_id === team.id);
  return (
    <div data-testid="team-panel">
      <h2 className="text-lg font-semibold">{team.name}</h2>
      <Info rows={[[t("orgAdmin.field.code"), team.code], [t("orgAdmin.field.department"), dept.name], [t("orgAdmin.field.lead"), lead?.full_name ?? t("common.none")], [t("orgAdmin.field.headcount"), team.headcount]]} />
      {editable && <div className="mt-4"><Button size="sm" variant="danger" onClick={() => onAction("archiveTeam")} data-testid="team-archive">{t("orgAdmin.archive")}</Button></div>}
      <ul className="mt-4 divide-y text-sm">
        {members.map((m) => (
          <li key={m.employee_id}><button type="button" className="w-full px-1 py-1.5 text-left hover:bg-muted" onClick={() => onSelect({ kind: "emp", id: m.employee_id, deptId: dept.id })}>{m.full_name} <span className="text-xs text-muted-foreground">{m.employee_code}</span></button></li>
        ))}
      </ul>
    </div>
  );
}

function EmployeePanel({ dept, member, depts, editable, onTransfer }: { dept: TreeDept; member: TreeMember | null; depts: TreeDept[]; editable: boolean; onTransfer: () => void }) {
  const t = useTranslations();
  const locale = useLocale() as AppLocale;
  const history = useAssignmentHistory(member?.employee_id ?? null);
  if (!member) return null;
  const nameOf = (id: string | null) => depts.find((d) => d.id === id)?.name ?? id?.slice(0, 8) ?? t("common.none");
  const teamOf = (id: string | null) => depts.flatMap((d) => d.teams).find((x) => x.id === id)?.code ?? "";
  const people = depts.flatMap((d) => d.members);
  const manager = people.find((m) => m.employee_id === member.manager_id);
  const rows = [...(history.data?.data ?? [])].reverse();
  return (
    <div data-testid="emp-panel">
      <div className="flex items-center gap-2"><h2 className="text-lg font-semibold">{member.full_name}</h2><LineageChip entity="hr.employees" id={member.employee_id} /></div>
      <Info rows={[[t("orgAdmin.field.code"), member.employee_code], [t("orgAdmin.field.department"), dept.name], [t("orgAdmin.field.team"), teamOf(member.team_id) || t("common.none")],
        [t("orgAdmin.field.position"), member.position_title ?? t("common.none")], [t("orgAdmin.field.manager"), manager?.full_name ?? t("common.none")]]} />
      {editable && <div className="mt-4"><Button size="sm" variant="outline" onClick={onTransfer} data-testid="emp-transfer">{t("orgAdmin.transfer")}</Button></div>}
      <h3 className="mt-6 text-sm font-semibold">{t("orgAdmin.history")}</h3>
      {history.isPending && <div className="mt-2 h-16 animate-pulse rounded bg-muted" />}
      {history.isError && <p role="alert" className="mt-2 text-sm text-danger">{t("errors.generic")}</p>}
      <ol className="mt-2 flex flex-col gap-2 text-sm" data-testid="emp-history">
        {rows.map((a) => (
          <li key={a.id} className="rounded border px-3 py-2" data-testid="emp-history-row">
            <div className="font-medium">{nameOf(a.department_id)}{a.team_id && <span className="ml-1 text-xs text-muted-foreground">{teamOf(a.team_id)}</span>}</div>
            <div className="text-xs tabular-nums text-muted-foreground">
              {formatDate(a.valid_from, locale)} → {a.valid_to ? formatDate(a.valid_to, locale) : t("orgAdmin.present")}{a.reason ? ` · ${a.reason}` : ""}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function ArchiveDialogs({ dialog, setDialog, sel, dept, onDone }: { dialog: DialogState; setDialog: (d: DialogState) => void; sel: Sel; dept: TreeDept | null; onDone: () => void }) {
  const t = useTranslations();
  const toast = useToast();
  const archive = useOrgMutation((path: string) => apiRequest(path, { method: "DELETE" }));
  const team = sel.kind === "team" ? dept?.teams.find((x) => x.id === sel.id) : undefined;
  return (
    <>
      <ConfirmDialog open={dialog === "archiveDept"} onOpenChange={(o) => !o && setDialog(null)} testId="archive-dept" danger title={t("orgAdmin.archiveDeptTitle", { name: dept?.name ?? "" })}
        body={t("orgAdmin.archiveBody")} confirmLabel={t("orgAdmin.archive")}
        onConfirm={async () => { await archive.mutateAsync(`/hr/departments/${dept?.id}`); toast.push(t("orgAdmin.toast.archived", { name: dept?.name ?? "" })); onDone(); }} />
      <ConfirmDialog open={dialog === "archiveTeam"} onOpenChange={(o) => !o && setDialog(null)} testId="archive-team" danger title={t("orgAdmin.archiveTeamTitle", { name: team?.name ?? "" })}
        body={t("orgAdmin.archiveBody")} confirmLabel={t("orgAdmin.archive")}
        onConfirm={async () => { await archive.mutateAsync(`/org/teams/${team?.id}`); toast.push(t("orgAdmin.toast.archived", { name: team?.name ?? "" })); onDone(); }} />
    </>
  );
}
