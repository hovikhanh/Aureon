import { useTranslations } from "next-intl";

export default function HomePage() {
  const t = useTranslations("home");
  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="text-h1 text-primary">{t("heading")}</h1>
      <p className="mt-2 text-body text-muted-foreground">{t("subtitle")}</p>
    </main>
  );
}
