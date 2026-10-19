"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle, Info } from "lucide-react";
import type { RoleCode } from "@aureon/shared-types";
import { LoadingState } from "@/components/states";
import { ErrorState } from "@/components/states/ErrorState";
import { EmptyState } from "@/components/states/EmptyState";
import { useAuth } from "@/features/auth/auth-context";
import { getSchemasApi } from "@/features/idp/idp-api";
import { cn } from "@/lib/utils";
import { DEMO_SCHEMAS, type DocSchema } from "./demo-fixtures";

/* -------------------------------------------------------------------------- */
/* Constants                                                                   */
/* -------------------------------------------------------------------------- */
const DOC_TYPE_KEYS = [
  "INVOICE",
  "SALES_REPORT",
  "KPI_OKR",
  "MEETING_MINUTES",
  "FINANCIAL_REPORT",
  "CONTRACT",
  "EMPLOYEE_LIST",
] as const;

const SENSITIVITY_COLORS: Record<string, string> = {
  SALARY:
    "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/30 dark:text-rose-300 dark:border-rose-900",
  PII: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/30 dark:text-amber-300 dark:border-amber-900",
  CONFIDENTIAL:
    "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/30 dark:text-purple-300 dark:border-purple-900",
  NONE: "bg-muted text-muted-foreground border-border",
};

/* -------------------------------------------------------------------------- */
/* SchemaTable                                                                 */
/* -------------------------------------------------------------------------- */
function SchemaTable({ schema, role }: { schema: DocSchema; role: RoleCode }) {
  const t = useTranslations("schemas");
  const tIdp = useTranslations("idp");

  const canViewSalary = role === "ROLE-04" || role === "ROLE-05";

  const visibleFields = schema.fields.filter(
    (f) => canViewSalary || f.sensitivity !== "SALARY",
  );

  return (
    <div>
      <div className="mb-3 flex items-center gap-3">
        <span className="text-sm font-medium text-muted-foreground">
          {t("fieldCount", { count: visibleFields.length })}
        </span>
        <span className="text-sm text-muted-foreground">·</span>
        <span className="text-sm text-muted-foreground">
          {t("requiredCount", { count: visibleFields.filter((f) => f.required).length })}
        </span>
        <span className="text-sm text-muted-foreground">·</span>
        <span className="text-xs text-muted-foreground">
          {t("version", { version: schema.field_set_version })}
        </span>
      </div>

      {!canViewSalary && schema.fields.some((f) => f.sensitivity === "SALARY") && (
        <div className="mb-3 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-300">
          <Info className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          {t("salaryNote")}
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm" data-testid={`schema-table-${schema.doc_type}`}>
          <thead>
            <tr className="border-b border-border bg-muted/50 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-3">{t("table.fieldKey")}</th>
              <th className="px-4 py-3">{t("table.valueType")}</th>
              <th className="px-4 py-3 text-center">{t("table.required")}</th>
              <th className="px-4 py-3">{t("table.sensitivity")}</th>
              <th className="px-4 py-3 hidden md:table-cell">{t("table.validationRules")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {visibleFields.map((field) => (
              <tr
                key={field.field_key}
                className="transition-colors hover:bg-muted/30"
                data-testid={`field-row-${field.field_key}`}
              >
                <td className="px-4 py-3">
                  <span className="font-mono text-xs font-medium text-foreground">
                    {field.field_key}
                  </span>
                  {field.table_key && (
                    <span className="ml-2 text-[10px] text-muted-foreground">
                      [{field.table_key}]
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className="rounded bg-secondary px-2 py-0.5 text-[11px] font-medium text-secondary-foreground">
                    {t(`valueTypes.${field.value_type}` as Parameters<typeof t>[0])}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  {field.required ? (
                    <CheckCircle2
                      className="mx-auto h-4 w-4 text-emerald-500"
                      aria-label={tIdp("schemaRequired")}
                    />
                  ) : (
                    <XCircle
                      className="mx-auto h-4 w-4 text-muted-foreground/50"
                      aria-label={tIdp("schemaOptional")}
                    />
                  )}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "inline-block rounded-full border px-2 py-0.5 text-[11px] font-medium",
                      SENSITIVITY_COLORS[field.sensitivity] ?? SENSITIVITY_COLORS.NONE,
                    )}
                  >
                    {t(`sensitivity.${field.sensitivity}` as Parameters<typeof t>[0])}
                  </span>
                </td>
                <td className="px-4 py-3 hidden md:table-cell">
                  {field.validation_rules.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {field.validation_rules.map((rule) => (
                        <span
                          key={rule}
                          className="rounded bg-muted px-1.5 py-0.5 text-[11px] font-mono text-muted-foreground"
                        >
                          {rule}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* SchemasView                                                                 */
/* -------------------------------------------------------------------------- */
export function SchemasView() {
  const t = useTranslations("schemas");
  const tIdp = useTranslations("idp");
  const { role, session } = useAuth();
  const [selectedDocType, setSelectedDocType] = useState("INVOICE");

  const {
    data: schemas,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["extraction-schemas"],
    queryFn: () => getSchemasApi(undefined, session?.accessToken),
    // Gate on the hydrated token so the request carries auth on its first fire.
    enabled: !!session?.accessToken,
    retry: 1,
    staleTime: 5 * 60_000,
    placeholderData: DEMO_SCHEMAS,
  });

  const selectedSchema = (schemas ?? DEMO_SCHEMAS).find((s) => s.doc_type === selectedDocType);

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-6" data-testid="schemas-view">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground">{t("title")}</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      {/* Doc type selector */}
      <div className="rounded-xl border border-border bg-card p-4">
        <p className="mb-2 text-sm font-medium text-foreground">{t("docTypeSelectLabel")}</p>
        <div className="flex flex-wrap gap-2">
          {DOC_TYPE_KEYS.map((dt) => (
            <button
              key={dt}
              type="button"
              onClick={() => setSelectedDocType(dt)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring",
                selectedDocType === dt
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-background text-foreground hover:bg-muted",
              )}
              aria-pressed={selectedDocType === dt}
              data-testid={`doc-type-btn-${dt}`}
            >
              {tIdp(`docTypes.${dt}` as Parameters<typeof tIdp>[0])}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="rounded-xl border border-border bg-card p-4 sm:p-6">
        {isLoading ? (
          <LoadingState rows={6} />
        ) : isError ? (
          <ErrorState onRetry={() => refetch()} />
        ) : !selectedSchema ? (
          <EmptyState title={t("empty.title")} description={t("empty.description")} />
        ) : (
          <SchemaTable schema={selectedSchema as DocSchema} role={role as RoleCode} />
        )}
      </div>
    </div>
  );
}
