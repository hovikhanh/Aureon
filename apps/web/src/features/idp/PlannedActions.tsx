"use client";
import { useTranslations } from "next-intl";
import { Check, X } from "lucide-react";
import type { PlannedAction } from "./types";

/** SCR-18b "Sẽ ghi" panel (EP-DC-05 `planned_actions`): ACT, record count, ✓/✗ caller permission. */
export function PlannedActions({ items }: { items: PlannedAction[] }) {
  const t = useTranslations("capture");
  return (
    <section className="rounded-lg border p-3" data-testid="planned-actions" aria-label={t("review.willWrite")}>
      <h3 className="mb-2 text-sm font-semibold">{t("review.willWrite")}</h3>
      {items.length === 0 && <p className="text-sm text-muted-foreground">{t("review.willWriteEmpty")}</p>}
      <ul className="space-y-1 text-sm">
        {items.map((a) => (
          <li key={a.action_name} className="flex items-center justify-between gap-2" data-testid="planned-action" data-permitted={a.permitted}>
            <span>{t.has(`act.${a.action_name}`) ? t(`act.${a.action_name}`) : a.action_name} <span className="tabular-nums text-muted-foreground">× {a.count}</span></span>
            {a.permitted
              ? <span className="flex items-center gap-1 text-xs text-success"><Check className="h-3.5 w-3.5" aria-hidden />{t("review.permitted")}</span>
              : <span className="flex items-center gap-1 text-xs text-danger"><X className="h-3.5 w-3.5" aria-hidden />{t("review.notPermitted", { perm: a.required_permission })}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}
