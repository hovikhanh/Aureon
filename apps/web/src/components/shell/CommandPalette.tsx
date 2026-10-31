"use client";
/**
 * ⌘K / Ctrl+K command palette (M2.4, R-DEC-112, 06 §3 CEO Assistant entry). Opens from anywhere:
 * "Hỏi AI" jumps to /ask with the typed question prefilled; the rest are quick navigation. No new
 * dependency — a plain dialog + keydown listener (cmdk is not in the stack). Secret-free: it only
 * routes, never carries data.
 */
import * as React from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Search, Sparkles } from "lucide-react";

interface Item {
  id: string;
  label: string;
  href: string;
  ai?: boolean;
}

export function CommandPalette() {
  const t = useTranslations("palette");
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  React.useEffect(() => {
    if (open) inputRef.current?.focus();
    else setQ("");
  }, [open]);

  const go = React.useCallback(
    (href: string) => {
      setOpen(false);
      router.push(href);
    },
    [router],
  );

  const nav: Item[] = [
    { id: "home", label: t("nav.home"), href: "/home" },
    { id: "checkins", label: t("nav.checkins"), href: "/goals/check-ins" },
    { id: "goals", label: t("nav.goals"), href: "/goals" },
  ];
  const term = q.trim().toLowerCase();
  const askHref = term ? `/ask?q=${encodeURIComponent(q.trim())}` : "/ask";
  const matches = term ? nav.filter((n) => n.label.toLowerCase().includes(term)) : nav;

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 p-4 pt-[12vh]" role="dialog" aria-modal="true" aria-label={t("title")} data-testid="command-palette" onMouseDown={() => setOpen(false)}>
      <div className="w-full max-w-lg overflow-hidden rounded-xl border bg-popover shadow-2xl" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 border-b px-3">
          <Search className="h-4 w-4 text-muted-foreground" aria-hidden />
          <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") go(askHref); }}
            placeholder={t("placeholder")} aria-label={t("placeholder")}
            className="h-11 w-full bg-transparent text-sm outline-none" data-testid="palette-input" />
        </div>
        <ul className="max-h-80 overflow-auto p-1 text-sm">
          <li>
            <button type="button" onClick={() => go(askHref)} data-testid="palette-ask"
              className="flex w-full items-center gap-2 rounded px-3 py-2 text-left text-ai hover:bg-ai-subtle/60">
              <Sparkles className="h-4 w-4" aria-hidden />
              <span className="font-medium">{term ? t("askWith", { q: q.trim() }) : t("ask")}</span>
            </button>
          </li>
          {matches.map((n) => (
            <li key={n.id}>
              <button type="button" onClick={() => go(n.href)} data-testid={`palette-${n.id}`}
                className="flex w-full items-center gap-2 rounded px-3 py-2 text-left hover:bg-muted">
                {n.label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
