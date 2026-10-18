"use client";

import { useTranslations } from "next-intl";
import { Command, X } from "lucide-react";

export interface ShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ShortcutsModal({ isOpen, onClose }: ShortcutsModalProps) {
  const t = useTranslations("review.shortcutsModal");
  const tClose = useTranslations("review.actions");

  if (!isOpen) return null;

  const shortcuts = [
    { key: "Tab / Shift+Tab", desc: t("tab") },
    { key: "Enter", desc: t("enter") },
    { key: "Ctrl + Enter", desc: t("approve") },
    { key: "Ctrl + Backspace", desc: t("reject") },
    { key: "Esc", desc: t("close") },
    { key: "J / K", desc: t("nextPrev") },
    { key: "?", desc: t("help") },
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="shortcuts-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-xs p-4"
    >
      <div className="relative w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-lg animate-in fade-in-0 zoom-in-95">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          aria-label={tClose("release")}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>

        <div className="flex items-center gap-2 mb-4">
          <Command className="h-5 w-5 text-primary" aria-hidden="true" />
          <h2 id="shortcuts-title" className="text-base font-semibold text-foreground">
            {t("title")}
          </h2>
        </div>

        <div className="divide-y divide-border">
          {shortcuts.map((s) => (
            <div key={s.key} className="flex items-center justify-between py-2 text-xs">
              <span className="text-muted-foreground">{s.desc}</span>
              <kbd className="rounded border border-border bg-muted px-2 py-0.5 font-mono text-[11px] font-semibold text-foreground">
                {s.key}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
