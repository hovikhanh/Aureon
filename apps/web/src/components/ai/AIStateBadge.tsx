import type { ComponentType } from "react";
import { BotOff, Check, PencilLine, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import type { AIStateLevel } from "@aureon/shared-types";
import type { AIStateBadgeProps } from "@/features/dashboard/types";
import { cn } from "@/lib/utils";

/**
 * AIStateBadge — AI autonomy level L0–L3 (06 §6.3, P02).
 *
 * HARD RULE (06 §6.3, CLAUDE.md § Frontend): every AI-produced surface uses the `--ai` token
 * family (`bg-ai` / `text-ai` / `bg-ai-muted`) and NEVER `--primary`; status colors are also
 * never used for AI content (06 §6.2). The badge always carries icon + text (not color alone)
 * so meaning survives for colour-blind / high-contrast users (06 §6.3, §9 WCAG AA).
 *
 * Label keys are `ai.state.*` (06 §7.2): off / suggest / draft / done.
 */
interface LevelStyle {
  /** `ai.state.*` message key for this level. */
  labelKey: "off" | "suggest" | "draft" | "done";
  icon: ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  /** Container classes — all within the `--ai`/neutral families, never `--primary`. */
  container: string;
}

const LEVEL_STYLE: Record<AIStateLevel, LevelStyle> = {
  // L0 "AI tắt": neutral outline, AI-off icon (06 §6.3).
  L0: {
    labelKey: "off",
    icon: BotOff,
    container: "border border-neutral-300 bg-background text-neutral-600",
  },
  // L1 "AI gợi ý": --ai outline, white bg, sparkles icon.
  L1: {
    labelKey: "suggest",
    icon: Sparkles,
    container: "border border-ai bg-background text-ai",
  },
  // L2 "AI soạn · chờ xác nhận": --ai-muted bg, --ai text, pencil icon.
  L2: {
    labelKey: "draft",
    icon: PencilLine,
    container: "border border-ai bg-ai-muted text-ai-muted-foreground",
  },
  // L3 "AI đã làm": solid --ai bg, white text, check icon.
  L3: {
    labelKey: "done",
    icon: Check,
    container: "border border-ai bg-ai text-ai-foreground",
  },
};

export function AIStateBadge({ level, className }: AIStateBadgeProps) {
  const t = useTranslations("ai.state");
  const style = LEVEL_STYLE[level];
  const Icon = style.icon;
  const label = t(style.labelKey);
  return (
    <span
      data-ai-level={level}
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-caption font-medium",
        style.container,
        className,
      )}
    >
      <Icon aria-hidden="true" className="h-3.5 w-3.5" />
      <span>{label}</span>
    </span>
  );
}
