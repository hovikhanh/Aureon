import Link from "next/link";
import { getServerSession } from "next-auth";
import { getTranslations } from "next-intl/server";
import { authOptions } from "@/lib/auth";
import { canAccess, type NavKey } from "@/lib/permissions";

/** A screen already built (lite) under this IA item; shown only when the role may open it. */
export interface SubLink {
  href: string;
  labelKey: "invoices" | "employees" | "audit" | "review";
}

/** "Sắp có" frame (06 §3.4): IA item visible to its roles, screen built in a later phase. */
export async function ComingSoon({ item, scr, phase, links = [] }: { item: NavKey; scr: string; phase: string; links?: SubLink[] }) {
  const t = await getTranslations();
  const session = await getServerSession(authOptions);
  const role = session?.user.role ?? "";
  const perms = session?.user.permissions ?? [];
  const open = links.filter((l) => canAccess(l.href, role, perms));
  return (
    <div className="mx-auto max-w-3xl" data-testid="coming-soon" data-scr={scr}>
      <h1 className="text-2xl font-semibold">{t(`nav.${item}`)}</h1>
      <p className="mt-1 text-sm text-muted-foreground">{t(`navHint.${item}`)}</p>
      <div className="mt-6 rounded-lg border border-dashed bg-card p-6 text-sm">
        <p className="font-medium">{t("comingSoon.title")}</p>
        <p className="mt-1 text-muted-foreground">{t("comingSoon.body", { phase })}</p>
      </div>
      {open.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2" data-testid="coming-soon-links">
          {open.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="inline-flex rounded-lg border bg-card px-3 py-2 text-sm font-medium text-primary hover:bg-muted" data-testid={`sublink-${l.labelKey}`}>
                {t(`nav.${l.labelKey}`)}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
