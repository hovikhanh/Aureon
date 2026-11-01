"use client";
/**
 * "AI đã làm" feed (M3.2, R-DEC-130): the viewer's own Autonomy-L3 executed actions (EP-AI-07
 * `status=executed`) plus a direct 24h undo (EP-AI-10). One query per widget (FR-DSH-07).
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { undoAction, useInvalidateAi } from "@/features/admin/ai/use-ai-admin";
import { useAiErrorText } from "@/features/admin/ai/use-ai-error";
import type { AiAction } from "@/features/admin/ai/types";

const PARAMS = { status: "executed", autonomy_level: "L3" } as const;

export function useAiFeed() {
  return useQuery({
    queryKey: qk.aiActions(PARAMS),
    queryFn: () => api.get<AiAction[]>("/ai/actions", PARAMS),
  });
}

/** Undo an already-executed action by id (within the 24h window); toast + cache refresh. */
export function useFeedUndo() {
  const t = useTranslations("aiAction");
  const toast = useToast();
  const invalidate = useInvalidateAi();
  const errorText = useAiErrorText();
  const [busy, setBusy] = React.useState<string | null>(null);
  const undo = async (id: string) => {
    setBusy(id);
    try {
      await undoAction(id);
      toast.push(t("undone"), "success");
    } catch (e) {
      toast.push(errorText(e), "danger");
    } finally {
      setBusy(null);
      void invalidate();
    }
  };
  return { undo, busy };
}
