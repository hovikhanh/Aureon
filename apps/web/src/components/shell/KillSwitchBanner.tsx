"use client";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { OctagonAlert } from "lucide-react";
import { agentName, bannerHasAdminLink, bannerState } from "@/features/admin/ai/logic";
import { useAgents, useKillSwitch } from "@/features/admin/ai/use-ai-admin";

/**
 * KillSwitchBanner (06 §5.1, T-646F): polls EP-AI-12 every 60 s + on focus; warning colour (never the
 * `ai` token); text by mode + agent scope; ADM/CEO get "Mở AI Control Center"; not dismissible;
 * hidden when off or on load error.
 */
export function KillSwitchBanner({ role, permissions }: { role: string; permissions: string[] }) {
  if (!permissions.includes("ai:query")) return null;
  return <Banner role={role} />;
}

function Banner({ role }: { role: string }) {
  const t = useTranslations("killSwitch");
  const locale = useLocale();
  const ks = useKillSwitch(true);
  const state = bannerState(ks.data, ks.isError);
  const agents = useAgents();
  if (!state) return null;
  const scope = state.scope === "all" ? t("scopeAll") : t("scopeAgents", { agents: state.scope.map((c) => agentName(agents.data?.find((a) => a.code === c), c, locale)).join(", ") });
  return (
    <div role="status" aria-live="polite" data-testid="kill-switch-banner" data-mode={ks.data?.mode}
      className="flex flex-wrap items-center gap-2 border-b border-warning bg-warning-subtle px-4 py-2 text-sm text-foreground">
      <OctagonAlert className="h-4 w-4 shrink-0 text-warning" aria-hidden />
      <span className="font-medium" data-testid="kill-switch-text">{t(state.textKey.replace("killSwitch.", "") as "banner.L0")}</span>
      <span className="text-muted-foreground" data-testid="kill-switch-scope">{scope}</span>
      {bannerHasAdminLink(role) && <Link href="/admin/ai" className="ml-auto font-medium underline" data-testid="kill-switch-link">{t("open")}</Link>}
    </div>
  );
}
