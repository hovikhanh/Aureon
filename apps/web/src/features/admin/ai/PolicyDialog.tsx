"use client";
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { ApiError } from "@/lib/api-client";
import { Field } from "@/features/admin/common";
import { levelKey, parseMoney } from "./logic";
import { createPolicy, patchPolicy, useAgents, useInvalidateAi } from "./use-ai-admin";
import { useAiErrorText } from "./use-ai-error";
import type { Policy, Tool } from "./types";

const ROLES = ["CEO", "DIR", "MGR", "EMP", "REV"] as const;
const LEVELS = ["L0", "L1", "L2", "L3"] as const;

/** Policy dialog (06 §3.4): tool, agent?, role?, money threshold, level, max_level, reason → EP-AI-19 / EP-AI-20. 422 reason → i18n. */
export function PolicyDialog({ value, tools, onClose }: { value: Policy | { tool_name: string } | null; tools: Tool[]; onClose: () => void }) {
  const t = useTranslations();
  const toast = useToast();
  const agents = useAgents();
  const invalidate = useInvalidateAi();
  const errText = useAiErrorText();
  const current = value && "id" in value ? value : null;
  const schema = React.useMemo(() => z.object({
    tool_name: z.string().min(1, t("orgAdmin.form.required")),
    agent_profile_code: z.string(),
    role_code: z.string(),
    max_amount: z.string(),
    level: z.enum(LEVELS),
    max_level: z.enum(LEVELS),
    is_active: z.boolean(),
    reason: z.string().trim().min(1, t("adminCommon.reasonRequired")),
  }), [t]);
  type V = z.infer<typeof schema>;
  const form = useForm<V>({ resolver: zodResolver(schema) });
  const [error, setError] = React.useState<string | null>(null);
  React.useEffect(() => {
    if (!value) return;
    setError(null);
    form.reset({ tool_name: value.tool_name, agent_profile_code: current?.agent_profile_code ?? "", role_code: current?.role_code ?? "", max_amount: current?.max_amount != null ? String(current.max_amount) : "",
      level: current?.level ?? "L1", max_level: current?.max_level ?? "L2", is_active: current?.is_active ?? true, reason: "" });
  }, [value, current, form]);
  const submit = form.handleSubmit(async (v) => {
    setError(null);
    const amount = parseMoney(v.max_amount);
    const money = amount === null ? { max_amount: null, currency: null } : { max_amount: amount, currency: "VND" };
    try {
      if (current) await patchPolicy(current.id, { level: v.level, max_level: v.max_level, ...money, is_active: v.is_active, reason: v.reason, version: current.version });
      else await createPolicy({ tool_name: v.tool_name, agent_profile_code: v.agent_profile_code || null, role_code: v.role_code || null, ...money, level: v.level, max_level: v.max_level, is_active: v.is_active, reason: v.reason });
      await invalidate();
      toast.push(t("aiAdmin.autonomy.saved"), "success");
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
  const levelSelect = (name: "level" | "max_level", id: string) => (
    <NativeSelect id={id} {...form.register(name)} data-testid={`policy-${name}`}>
      {LEVELS.map((l) => <option key={l} value={l}>{l} · {t(`aiAdmin.${levelKey(l)}`)}</option>)}
    </NativeSelect>
  );
  return (
    <Dialog open={value !== null} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent data-testid="policy-dialog">
        <DialogTitle>{t(current ? "aiAdmin.autonomy.editTitle" : "aiAdmin.autonomy.new")}</DialogTitle>
        <DialogDescription>{t("aiAdmin.autonomy.dialogHint")}</DialogDescription>
        <form onSubmit={(ev) => void submit(ev)} className="mt-4 flex flex-col gap-3" noValidate>
          <Field id="po-tool" label={t("aiAdmin.autonomy.col.tool")}>
            <NativeSelect id="po-tool" disabled={Boolean(current)} {...form.register("tool_name")} data-testid="policy-tool">
              {tools.map((x) => <option key={x.name} value={x.name}>{x.name}</option>)}
            </NativeSelect>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field id="po-agent" label={t("aiAdmin.autonomy.agent")}>
              <NativeSelect id="po-agent" disabled={Boolean(current)} {...form.register("agent_profile_code")} data-testid="policy-agent">
                <option value="">{t("aiAdmin.autonomy.any")}</option>
                {(agents.data ?? []).map((a) => <option key={a.code} value={a.code}>{a.code}</option>)}
              </NativeSelect>
            </Field>
            <Field id="po-role" label={t("aiAdmin.autonomy.role")}>
              <NativeSelect id="po-role" disabled={Boolean(current)} {...form.register("role_code")} data-testid="policy-role">
                <option value="">{t("aiAdmin.autonomy.any")}</option>
                {ROLES.map((r) => <option key={r} value={r}>{t(`role.${r}` as "role.CEO")}</option>)}
              </NativeSelect>
            </Field>
            <Field id="po-level" label={t("aiAdmin.autonomy.level")}>{levelSelect("level", "po-level")}</Field>
            <Field id="po-max" label={t("aiAdmin.autonomy.maxLevel")}>{levelSelect("max_level", "po-max")}</Field>
          </div>
          <Field id="po-amount" label={t("aiAdmin.autonomy.amount")}>
            <Input id="po-amount" inputMode="numeric" placeholder="50.000.000" {...form.register("max_amount")} data-testid="policy-amount" />
          </Field>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" {...form.register("is_active")} />{t("aiAdmin.autonomy.active")}</label>
          <Field id="po-reason" label={t("aiAdmin.kill.reason")} error={e.reason?.message}>
            <textarea id="po-reason" rows={2} className="w-full rounded-md border bg-background p-2 text-sm" {...form.register("reason")} aria-invalid={Boolean(e.reason)} data-testid="policy-reason" />
          </Field>
          {error && <p role="alert" className="text-sm text-danger" data-testid="policy-error">{error}</p>}
          <div className="mt-2 flex justify-end gap-2">
            <DialogClose asChild><Button type="button" variant="ghost">{t("buttons.cancel")}</Button></DialogClose>
            <Button type="submit" disabled={form.formState.isSubmitting} data-testid="policy-save">{t("buttons.save")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
