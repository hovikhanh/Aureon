"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { UndoToast } from "@/components/ai/UndoToast";
import { useToast } from "@/components/ui/toast";
import { confirmAction, rejectAction, undoAction, useInvalidateAi } from "@/features/admin/ai/use-ai-admin";
import { useAiErrorText } from "@/features/admin/ai/use-ai-error";
import type { AiAction } from "@/features/admin/ai/types";

/**
 * Confirm / reject / undo an AI action (EP-AI-09/10/11) + the 10 s UndoToast after confirm (06 §5.1).
 * `onChange` gets the updated `AIActionOut` so the caller can patch its local copy (chat message).
 */
export function useActionFlow(onChange?: (a: AiAction) => void) {
  const t = useTranslations("aiAction");
  const toast = useToast();
  const invalidate = useInvalidateAi();
  const errorText = useAiErrorText();
  const [undoFor, setUndoFor] = React.useState<AiAction | null>(null);
  const confirm = async (id: string, edited?: Record<string, unknown>) => {
    const a = await confirmAction(id, edited);
    onChange?.(a);
    setUndoFor(a);
    void invalidate();
  };
  const reject = async (id: string, reason: string) => {
    const a = await rejectAction(id, reason);
    onChange?.(a);
    toast.push(t("rejected"), "info");
    void invalidate();
  };
  const undo = async () => {
    if (!undoFor) return;
    try {
      const a = await undoAction(undoFor.id);
      onChange?.(a);
      toast.push(t("undone"), "success");
    } catch (e) {
      toast.push(errorText(e), "danger");
    }
    void invalidate();
  };
  const toastEl = undoFor ? (
    <UndoToast key={undoFor.id} message={t("executed")} onUndo={undo} onClose={() => setUndoFor(null)} />
  ) : null;
  return { confirm, reject, errorText, toastEl };
}
