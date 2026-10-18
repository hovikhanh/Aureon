import { useTranslations } from "next-intl";

/**
 * Placeholder page body for S1 shell routes (T-108). The real screens (SCR-01..05, SCR-07,
 * SCR-08, SCR-11, SCR-14) arrive in later tasks (T-109/T-111/T-218/...). Renders an h1 so each
 * route has a document heading inside the shell's `main` landmark.
 */
export function PlaceholderPage({ titleKey }: { titleKey: string }) {
  const t = useTranslations("shell.pages");
  return (
    <section className="flex flex-col gap-2">
      <h1 className="text-h1 text-foreground">{t(titleKey)}</h1>
      <p className="text-body text-muted-foreground">{t("placeholder")}</p>
    </section>
  );
}
