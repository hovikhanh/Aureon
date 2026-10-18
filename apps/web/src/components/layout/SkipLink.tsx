import { useTranslations } from "next-intl";

/**
 * Skip-to-content link (06 §9 keyboard): visually hidden until focused, then jumps to the
 * `#main-content` landmark. First focusable element in the shell.
 */
export function SkipLink() {
  const t = useTranslations("shell");
  return (
    <a
      href="#main-content"
      className="sr-only rounded-md bg-primary px-4 py-2 text-body font-medium text-primary-foreground focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    >
      {t("skipToContent")}
    </a>
  );
}
