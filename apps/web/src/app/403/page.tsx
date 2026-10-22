import Link from "next/link";
import { ShieldX } from "lucide-react";
import { getTranslations } from "next-intl/server";

export default async function ForbiddenPage() {
  const t = await getTranslations("errors");
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-3 p-6 text-center" data-testid="forbidden">
      <ShieldX className="h-12 w-12 text-danger" aria-hidden />
      <h1 className="text-2xl font-semibold">{t("forbiddenTitle")}</h1>
      <p className="max-w-md text-muted-foreground">{t("forbiddenBody")}</p>
      <Link href="/" className="text-primary underline">{t("goHome")}</Link>
    </main>
  );
}
