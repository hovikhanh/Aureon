"use client";
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { Field } from "@/features/admin/common";
import { agentName, levelKey, levelOptions } from "./logic";
import { patchAgent, useInvalidateAi } from "./use-ai-admin";
import { useAiErrorText } from "./use-ai-error";
import type { Agent, Tool } from "./types";

/** Agent edit panel (EP-AI-17): enable, max level (L3/L4 disabled "Mở ở M3"), budget, allowed tools, reason. 409 → toast reload. */
export function AgentEditDialog({ agent, tools, onClose }: { agent: Agent | null; tools: Tool[]; onClose: () => void }) {
  const t = useTranslations();
  const locale = useLocale();
  const toast = useToast();
  const invalidate = useInvalidateAi();
  const errText = useAiErrorText();
  const schema = React.useMemo(() => z.object({
    is_enabled: z.boolean(),
    max_autonomy_level: z.enum(["L0", "L1", "L2", "L3"]),
    monthly_budget_usd: z.string().trim().refine((v) => v === "" || (Number(v) >= 0 && !Number.isNaN(Number(v))), t("aiAdmin.agents.budgetInvalid")),
    allowed_tools: z.array(z.string()),
    reason: z.string().trim().min(1, t("adminCommon.reasonRequired")),
  }), [t]);
  type V = z.infer<typeof schema>;
  const form = useForm<V>({ resolver: zodResolver(schema) });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => {
    if (agent) {
      setError(null);
      form.reset({ is_enabled: agent.is_enabled, max_autonomy_level: agent.max_autonomy_level, monthly_budget_usd: agent.monthly_budget_usd ?? "", allowed_tools: agent.allowed_tools ?? [], reason: "" });
    }
  }, [agent, form]);
  const assignable = tools.filter((x) => x.kind !== "APPROVAL" && !x.p1_frozen);
  const submit = form.handleSubmit(async (v) => {
    if (!agent) return;
    setError(null);
    try {
      await patchAgent(agent.code, { is_enabled: v.is_enabled, max_autonomy_level: v.max_autonomy_level, monthly_budget_usd: v.monthly_budget_usd === "" ? null : Number(v.monthly_budget_usd),
        allowed_tools: v.allowed_tools, reason: v.reason, version: agent.version });
      await invalidate();
      toast.push(t("aiAdmin.agents.saved"), "success");
      onClose();
    } catch (e) {
      if (e instanceof ApiError && e.code === "CONFLICT_STATE") {
        toast.push(t("aiAdmin.conflict"), "danger");
        await invalidate();
        onClose();
        return;
      }
      setError(errText(e));
    }
  });
  const e = form.formState.errors;
  return (
    <Dialog open={agent !== null} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-2xl" data-testid="agent-dialog">
        <DialogTitle>{agent ? agentName(agent, agent.code, locale) : ""}</DialogTitle>
        <DialogDescription>{t("aiAdmin.agents.editHint")}</DialogDescription>
        <form onSubmit={(ev) => void submit(ev)} className="mt-4 flex flex-col gap-3" noValidate>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...form.register("is_enabled")} data-testid="agent-enabled-input" />{t("aiAdmin.agents.enabled")}</label>
          <fieldset className="flex flex-col gap-1">
            <legend className="text-sm font-medium">{t("aiAdmin.agents.col.max")}</legend>
            <div className="flex flex-wrap gap-3">
              {levelOptions().map((o) => (
                <label key={o.value} className={`flex items-center gap-1.5 text-sm ${o.disabled ? "text-muted-foreground" : ""}`} title={o.disabled ? t("aiAdmin.openInM3") : undefined}>
                  <input type="radio" value={o.value} disabled={o.disabled} {...(o.value === "L4" ? {} : form.register("max_autonomy_level"))} data-testid={`agent-level-${o.value}`} />
                  {o.value} {o.value !== "L4" && `· ${t(`aiAdmin.${levelKey(o.value)}`)}`}{o.disabled && <span className="text-xs">({t("aiAdmin.openInM3")})</span>}
                </label>
              ))}
            </div>
          </fieldset>
          <Field id="ag-budget" label={t("aiAdmin.agents.col.budget")} error={e.monthly_budget_usd?.message}>
            <Input id="ag-budget" inputMode="decimal" placeholder={t("aiAdmin.agents.noBudget")} {...form.register("monthly_budget_usd")} data-testid="agent-budget" />
          </Field>
          <fieldset className="flex max-h-48 flex-col gap-1 overflow-y-auto rounded border p-2">
            <legend className="px-1 text-sm font-medium">{t("aiAdmin.agents.col.tools")}</legend>
            <div className="grid grid-cols-2 gap-1">
              {assignable.map((x) => (
                <label key={x.name} className="flex items-center gap-1.5 font-mono text-xs">
                  <input type="checkbox" value={x.name} {...form.register("allowed_tools")} data-testid={`agent-tool-${x.name}`} />{x.name}
                </label>
              ))}
            </div>
          </fieldset>
          <Field id="ag-reason" label={t("aiAdmin.kill.reason")} error={e.reason?.message}>
            <textarea id="ag-reason" rows={2} className="w-full rounded-md border bg-background p-2 text-sm" {...form.register("reason")} aria-invalid={Boolean(e.reason)} data-testid="agent-reason" />
          </Field>
          {error && <p role="alert" className="text-sm text-danger" data-testid="agent-error">{error}</p>}
          <div className="mt-2 flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("buttons.cancel")}</Button></DialogClose>
            <Button type="submit" disabled={form.formState.isSubmitting} data-testid="agent-save">{t("buttons.save")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
