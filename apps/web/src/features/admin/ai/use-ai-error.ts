"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { ApiError } from "@/lib/api-client";
import { useErrorText } from "@/features/admin/common";

/** 422 `details.reason` of EP-AI-17/19/20 → `aiAdmin.reason.*`; 409 → "Dữ liệu đã đổi, tải lại"; else admin default. */
export const AI_REASONS = ["above_ceiling", "above_tool_max", "critical_field", "not_configurable", "execution_max_l2", "invalid_tool"];

export function useAiErrorText(): (e: unknown) => string {
  const t = useTranslations();
  const base = useErrorText();
  return React.useCallback((e: unknown) => {
    if (e instanceof ApiError) {
      const reason = String(e.details.reason ?? "");
      if (AI_REASONS.includes(reason)) return t(`aiAdmin.reason.${reason}` as "aiAdmin.reason.above_ceiling");
      if (e.code === "CONFLICT_STATE") return t("aiAdmin.conflict");
      if (e.code === "UNDO_EXPIRED") return t("aiAction.undoExpired");
    }
    return base(e);
  }, [t, base]);
}
