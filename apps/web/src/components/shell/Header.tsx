"use client";
import * as React from "react";
import { useRouter } from "next/navigation";
import { signOut } from "next-auth/react";
import { useLocale, useTranslations } from "next-intl";
import { Globe, LogOut, Menu } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { setLocale } from "@/lib/locale-action";
import type { ShellUser } from "./AppShell";
import { NotificationBell } from "./NotificationBell";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts.at(-2)?.[0] ?? "") + (parts.at(-1)?.[0] ?? "")).toUpperCase() || "?";
}

export function Header({ user, onOpenMenu }: { user: ShellUser; onOpenMenu: () => void }) {
  const t = useTranslations();
  const locale = useLocale();
  const router = useRouter();
  const [pending, startTransition] = React.useTransition();

  const switchLocale = (next: "vi" | "en") =>
    startTransition(async () => {
      await setLocale(next);
      router.refresh();
    });

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-card/95 px-4 backdrop-blur">
      <button type="button" onClick={onOpenMenu} className="rounded p-1.5 hover:bg-muted md:hidden" aria-label={t("nav.menu")} data-testid="menu-button">
        <Menu className="h-5 w-5" />
      </button>
      <span className="font-semibold md:hidden">Aureon</span>
      <div className="ml-auto flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" aria-label={t("header.language")} data-testid="locale-switcher" disabled={pending}>
              <Globe className="h-4 w-4" aria-hidden />
              <span className="uppercase">{locale}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onSelect={() => switchLocale("vi")} data-testid="locale-vi">{t("header.vi")}</DropdownMenuItem>
            <DropdownMenuItem onSelect={() => switchLocale("en")} data-testid="locale-en">{t("header.en")}</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        {user.role !== "AI" && <NotificationBell />}
        <Badge variant="primary" data-testid="role-badge" className="hidden sm:inline-flex">{t(`role.${user.role}` as "role.CEO")}</Badge>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button type="button" className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/15 text-sm font-semibold text-primary" aria-label={t("header.account")} data-testid="avatar">
              {initials(user.name)}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuLabel>
              <div className="font-medium text-foreground">{user.name}</div>
              <div>{user.email}</div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => void signOut({ callbackUrl: "/login" })} data-testid="logout">
              <LogOut className="h-4 w-4" aria-hidden /> {t("buttons.logout")}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
