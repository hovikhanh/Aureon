"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { CHAT_WAIT_GIVE_UP_MS, CHAT_WAIT_SLOW_MS, CHAT_WAIT_THINKING_MS } from "@/lib/api-client";
import { ChevronDown, Loader2, Wrench } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import type { ToolCall } from "@/features/ai/types";

/** T-509: elapsed-time hint while waiting for the first token (10 s / 30 s / 90 s). */
export function WaitHint({ active }: { active: boolean }) {
  const t = useTranslations("ai.wait");
  const [ms, setMs] = React.useState(0);
  React.useEffect(() => {
    if (!active) return;
    const start = Date.now();
    setMs(0);
    const id = window.setInterval(() => setMs(Date.now() - start), 1000);
    return () => window.clearInterval(id);
  }, [active]);
  if (!active || ms < CHAT_WAIT_THINKING_MS) return null;
  const key = ms >= CHAT_WAIT_GIVE_UP_MS ? "giveUp" : ms >= CHAT_WAIT_SLOW_MS ? "slow" : "thinking";
  return (
    <p className="text-xs text-muted-foreground" role="status" aria-live="polite" data-testid="wait-hint" data-phase={key}>
      {t(key)}
    </p>
  );
}

/** 06 §5.1 ThinkingState — collapsible list of tools the AI is using / used. */
export function ThinkingState({ tools, streaming }: { tools: ToolCall[]; streaming: boolean }) {
  const t = useTranslations("ai");
  const running = tools.find((x) => x.status === "running");
  if (!tools.length) {
    return streaming ? (
      <p className="flex items-center gap-2 text-sm text-ai" data-testid="thinking"><Loader2 className="h-4 w-4 animate-spin" aria-hidden />{t("state.thinking")}</p>
    ) : null;
  }
  return (
    <Collapsible defaultOpen className="rounded-lg border border-ai/30 bg-ai-subtle/60 text-sm" data-testid="tool-calls">
      <CollapsibleTrigger className="flex w-full items-center gap-2 px-3 py-2 text-left text-ai">
        {running ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Wrench className="h-4 w-4" aria-hidden />}
        <span className="flex-1">{running ? t("state.tool", { tool: running.tool }) : t("toolCalls", { count: tools.length })}</span>
        <ChevronDown className="h-4 w-4" aria-hidden />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <ul className="space-y-1 px-3 pb-2 text-xs text-muted-foreground">
          {tools.map((x, i) => (
            <li key={`${x.tool}-${i}`} data-testid="tool-call">
              {x.status === "running" ? t("state.tool", { tool: x.tool }) : t("state.toolDone", { tool: x.tool, ms: x.latency_ms ?? 0 })}
            </li>
          ))}
        </ul>
      </CollapsibleContent>
    </Collapsible>
  );
}
