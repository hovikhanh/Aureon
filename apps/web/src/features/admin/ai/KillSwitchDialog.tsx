"use client";
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLocale, useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { Field } from "@/features/admin/common";
import { agentName } from "./logic";
import { putKillSwitch, useInvalidateAi } from "./use-ai-admin";
import { useAiErrorText } from "./use-ai-error";
import type { Agent, KillSwitch } from "./types";

/** "Dừng AI khẩn cấp" (06 §3.4): mode, agents (all or a subset), mandatory reason — also to turn off (EP-AI-13). */
export function KillSwitchDialog({ open, onOpenChange, current, agents }: { open: boolean; onOpenChange: (o: boolean) => void; current: KillSwitch; agents: Agent[] }) {
  const t = useTranslations();
  const locale = useLocale();
  const toast = useToast();
  const invalidate = useInvalidateAi();
  const errText = useAiErrorText();
  const turningOn = !current.enabled;
  const schema = React.useMemo(() => z.object({
    mode: z.enum(["WRITE_OFF", "L0"]),
    all: z.boolean(),
    agents: z.array(z.string()),
    reason: z.string().trim().min(1, t("adminCommon.reasonRequired")),
  }).superRefine((v, ctx) => {
    if (!v.all && v.agents.length === 0) ctx.addIssue({ code: "custom", path: ["agents"], message: t("aiAdmin.kill.agentsRequired") });
  }), [t]);
  type V = z.infer<typeof schema>;
  const form = useForm<V>({ resolver: zodResolver(schema), defaultValues: { mode: "WRITE_OFF", all: true, agents: [], reason: "" } });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => {
    if (open) {
      setError(null);
      form.reset({ mode: current.mode ?? "WRITE_OFF", all: !current.agents?.length, agents: current.agents ?? [], reason: "" });
    }
  }, [open, current, form]);
  const all = form.watch("all");
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    try {
      await putKillSwitch(turningOn ? { enabled: true, mode: v.mode, agents: v.all ? [] : v.agents, reason: v.reason } : { enabled: false, mode: current.mode, agents: [], reason: v.reason });
      await invalidate();
      toast.push(t(turningOn ? "aiAdmin.kill.onToast" : "aiAdmin.kill.offToast"), turningOn ? "info" : "success");
      onOpenChange(false);
    } catch (e) {
      setError(errText(e));
    }
  });
  const e = form.formState.errors;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="kill-dialog">
        <DialogTitle>{t(turningOn ? "aiAdmin.kill.dialogOn" : "aiAdmin.kill.dialogOff")}</DialogTitle>
        <DialogDescription>{t(turningOn ? "aiAdmin.kill.dialogOnBody" : "aiAdmin.kill.dialogOffBody")}</DialogDescription>
        <form onSubmit={(ev) => void submit(ev)} className="mt-4 flex flex-col gap-3" noValidate>
          {turningOn && (
            <>
              <Field id="ks-mode" label={t("aiAdmin.kill.mode")}>
                <NativeSelect id="ks-mode" {...form.register("mode")} data-testid="kill-mode-select">
                  <option value="WRITE_OFF">{t("aiAdmin.kill.modes.WRITE_OFF")}</option>
                  <option value="L0">{t("aiAdmin.kill.modes.L0")}</option>
                </NativeSelect>
              </Field>
              <fieldset className="flex flex-col gap-1.5" data-testid="kill-agents">
                <legend className="text-sm font-medium">{t("aiAdmin.kill.scope")}</legend>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...form.register("all")} data-testid="kill-all" />{t("aiAdmin.kill.scopeAll")}</label>
                {!all && (
                  <div className="grid grid-cols-2 gap-1 pl-5">
                    {agents.map((a) => (
                      <label key={a.code} className="flex items-center gap-2 text-sm">
                        <input type="checkbox" value={a.code} {...form.register("agents")} data-testid={`kill-agent-${a.code}`} />{agentName(a, a.code, locale)}
                      </label>
                    ))}
                  </div>
                )}
                {e.agents && <p className="text-xs text-danger">{e.agents.message}</p>}
              </fieldset>
            </>
          )}
          <Field id="ks-reason" label={t("aiAdmin.kill.reason")} error={e.reason?.message}>
            <textarea id="ks-reason" rows={3} className="w-full rounded-md border bg-background p-2 text-sm" {...form.register("reason")} aria-invalid={Boolean(e.reason)} data-testid="kill-reason-input" />
          </Field>
          {error && <p role="alert" className="text-sm text-danger" data-testid="kill-error">{error}</p>}
          <div className="mt-2 flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("buttons.cancel")}</Button></DialogClose>
            <Button type="submit" variant={turningOn ? "danger" : "default"} disabled={form.formState.isSubmitting} data-testid="kill-submit">
              {t(turningOn ? "aiAdmin.kill.turnOn" : "aiAdmin.kill.turnOff")}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
