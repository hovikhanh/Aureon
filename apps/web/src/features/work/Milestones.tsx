"use client";
/** SCR-56 "Tổng quan": milestone timeline (dot per `due_date`; `late` red, `done` green) + add / mark done (EP-TASK-15/16). */
import * as React from "react";
import { useLocale, useTranslations } from "next-intl";
import { Check } from "lucide-react";
import { apiRequest } from "@/lib/api-client";
import { formatDate, type AppLocale } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import { useWorkError } from "./common";
import { useWorkMutation, type MilestoneOut, type ProjectDetailOut } from "./use-work";

const dot = (m: MilestoneOut) => (m.status === "done" ? "bg-success" : m.late ? "bg-danger" : "bg-muted-foreground");

export function Milestones({ project, canEdit }: { project: ProjectDetailOut; canEdit: boolean }) {
  const t = useTranslations("work");
  const locale = useLocale() as AppLocale;
  const toast = useToast();
  const errText = useWorkError();
  const [title, setTitle] = React.useState("");
  const [due, setDue] = React.useState("");
  const add = useWorkMutation((body: { title: string; due_date: string }) => apiRequest(`/work/projects/${project.id}/milestones`, { method: "POST", body, idempotent: true }));
  const done = useWorkMutation((m: MilestoneOut) => apiRequest(`/work/projects/${project.id}/milestones/${m.id}`, { method: "PATCH", body: { status: "done", version: m.version } }));
  const run = async (p: Promise<unknown>, ok: string) => {
    try {
      await p;
      toast.push(ok);
      return true;
    } catch (e) {
      toast.push(errText(e), "danger");
      return false;
    }
  };
  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    if (!title.trim() || !due) return;
    if (await run(add.mutateAsync({ title: title.trim(), due_date: due }), t("project.milestoneAdded"))) { setTitle(""); setDue(""); }
  };
  const rows = project.milestones ?? [];
  return (
    <Card className="flex flex-col gap-4 p-4" data-testid="milestones">
      <h3 className="text-sm font-semibold">{t("project.milestones")}</h3>
      {!rows.length && <p className="text-sm text-muted-foreground">{t("project.noMilestones")}</p>}
      <ol className="relative flex flex-col gap-3 border-l pl-5">
        {rows.map((m) => (
          <li key={m.id} className="relative flex flex-wrap items-center gap-2 text-sm" data-testid={`milestone-${m.id}`} data-late={m.late ? "true" : "false"} data-status={m.status}>
            <span className={cn("absolute -left-[1.6rem] h-3 w-3 rounded-full ring-2 ring-card", dot(m))} aria-hidden />
            <span className="font-medium">{m.title}</span>
            <span className={cn("text-xs", m.late ? "text-danger" : "text-muted-foreground")}>{formatDate(`${m.due_date}T00:00:00+07:00`, locale)}</span>
            <Badge variant={m.status === "done" ? "success" : m.late ? "danger" : "default"}>{m.late ? t("project.milestoneLate") : t(`milestoneStatus.${m.status}` as "milestoneStatus.planned")}</Badge>
            {canEdit && m.status !== "done" && (
              <Button size="icon" variant="ghost" aria-label={t("project.markDone", { title: m.title })} onClick={() => void run(done.mutateAsync(m), t("project.milestoneDone"))} data-testid={`milestone-done-${m.id}`}>
                <Check className="h-4 w-4" />
              </Button>
            )}
          </li>
        ))}
      </ol>
      {canEdit && (
        <form onSubmit={(e) => void submit(e)} className="flex flex-wrap items-end gap-2" data-testid="milestone-form">
          <div className="flex flex-col gap-1"><Label htmlFor="ms-title" className="text-xs">{t("project.milestoneTitle")}</Label><Input id="ms-title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} data-testid="ms-title" /></div>
          <div className="flex flex-col gap-1"><Label htmlFor="ms-due" className="text-xs">{t("project.milestoneDue")}</Label><Input id="ms-due" type="date" value={due} onChange={(e) => setDue(e.target.value)} data-testid="ms-due" /></div>
          <Button type="submit" variant="outline" disabled={add.isPending || !title.trim() || !due} data-testid="ms-add">{t("project.addMilestone")}</Button>
        </form>
      )}
    </Card>
  );
}
