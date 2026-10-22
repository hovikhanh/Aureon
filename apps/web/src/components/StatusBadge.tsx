"use client";
import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/badge";
import type { CardStatus } from "@/features/dashboard/types";

const ICON: Record<CardStatus, string> = { ok: "●", warning: "◐", critical: "○", no_data: "–", unavailable: "!" };
const VARIANT = { ok: "success", warning: "warning", critical: "danger", no_data: "default", unavailable: "default" } as const;

/** 06 §7.3 — colour never alone: icon + label. */
export function StatusBadge({ status }: { status: CardStatus }) {
  const t = useTranslations("status");
  return (
    <Badge variant={VARIANT[status]} data-testid="status-badge" data-status={status}>
      <span aria-hidden>{ICON[status]}</span>
      {t(status)}
    </Badge>
  );
}
