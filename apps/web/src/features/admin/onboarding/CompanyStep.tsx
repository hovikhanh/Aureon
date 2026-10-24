"use client";
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api-client";
import { Field, useErrorText } from "@/features/admin/common";
import type { StepProps } from "./OnboardingWizard";
import { useOrganizations, type Organization } from "./use-onboarding";

/** Step 1 — company info: EP-ORG-02 (no org yet) or EP-ORG-04 → `complete_step company` with `refs.organization_id`. */
export function CompanyStep({ state, patch, goTo }: StepProps) {
  const t = useTranslations();
  const orgs = useOrganizations();
  if (orgs.isPending) return <div className="h-48 animate-pulse rounded bg-muted" />;
  if (orgs.isError) return <p role="alert" className="text-danger">{t("errors.generic")}</p>;
  return <CompanyForm org={orgs.data[0] ?? null} state={state} patch={patch} goTo={goTo} />;
}

function CompanyForm({ org, state, patch, goTo }: Omit<StepProps, "viewer"> & { org: Organization | null }) {
  const t = useTranslations();
  const toast = useToast();
  const errText = useErrorText();
  const client = useQueryClient();
  const schema = React.useMemo(() => z.object({
    code: z.string().trim().min(1, t("onboarding.company.required")).max(32),
    name: z.string().trim().min(1, t("onboarding.company.required")).max(255),
    legal_name: z.string().trim().max(255),
    tax_code: z.string().trim().regex(/^$|^\d{10}(-\d{3})?$/, t("onboarding.company.taxInvalid")),
  }), [t]);
  type V = z.infer<typeof schema>;
  const form = useForm<V>({ resolver: zodResolver(schema), defaultValues: { code: org?.code ?? "", name: org?.name ?? "", legal_name: org?.legal_name ?? "", tax_code: org?.tax_code ?? "" } });
  const { errors, isSubmitting } = form.formState;

  const submit = form.handleSubmit(async (v) => {
    try {
      const body = { name: v.name, legal_name: v.legal_name || null, tax_code: v.tax_code || null };
      const saved = org
        ? await api.patch<Organization>(`/org/organizations/${org.id}`, { ...body, version: org.version })
        : await api.post<Organization>("/org/organizations", { ...body, code: v.code });
      void client.invalidateQueries({ queryKey: ["org"] });
      await patch(state, "complete_step", "company", { organization_id: saved.id });
      goTo("org_import");
    } catch (e) {
      toast.push(errText(e), "danger");
    }
  });

  return (
    <form onSubmit={(e) => void submit(e)} className="grid gap-4 md:grid-cols-2" data-testid="company-form" noValidate>
      <p className="text-sm text-muted-foreground md:col-span-2">{t("onboarding.company.hint")}</p>
      <Field id="ob-code" label={t("onboarding.company.code")} error={errors.code?.message}>
        <Input id="ob-code" {...form.register("code")} disabled={Boolean(org)} data-testid="company-code" />
      </Field>
      <Field id="ob-name" label={t("onboarding.company.name")} error={errors.name?.message}>
        <Input id="ob-name" {...form.register("name")} data-testid="company-name" />
      </Field>
      <Field id="ob-legal" label={t("onboarding.company.legalName")} error={errors.legal_name?.message}>
        <Input id="ob-legal" {...form.register("legal_name")} data-testid="company-legal" />
      </Field>
      <Field id="ob-tax" label={t("onboarding.company.taxCode")} error={errors.tax_code?.message}>
        <Input id="ob-tax" {...form.register("tax_code")} inputMode="numeric" data-testid="company-tax" />
      </Field>
      <div className="flex justify-end md:col-span-2">
        <Button type="submit" disabled={isSubmitting} data-testid="company-save">{t("onboarding.saveContinue")}</Button>
      </div>
    </form>
  );
}
