import Link from "next/link";
import { useTranslations } from "next-intl";
import { ForbiddenState } from "@/components/states";

// Forbidden (403) landing (06 §3.2 / 02 §4.1): shown instead of silently hiding out-of-scope
// content. Offers a link back to the dashboard home. Real redirects are wired with auth (T-107).
export default function ForbiddenPage() {
  const t = useTranslations("shell.nav");
  return (
    <ForbiddenState
      action={
        <Link
          href="/dashboard"
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-body font-medium text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {t("dashboard")}
        </Link>
      }
    />
  );
}
