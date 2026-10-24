import Link from "next/link";
import { getServerSession } from "next-auth";
import { getTranslations } from "next-intl/server";
import { authOptions } from "@/lib/auth";
import { canAccess } from "@/lib/permissions";

const CARDS = [
  { href: "/admin/org", key: "org", scr: "SCR-51" },
  { href: "/admin/positions", key: "positions", scr: "SCR-52" },
  { href: "/admin/users", key: "users", scr: "SCR-53" },
  { href: "/admin/roles", key: "roles", scr: "SCR-54" },
  { href: "/admin/audit", key: "audit", scr: "SCR-14" },
  { href: "/admin/data-capture", key: "dataCapture", scr: "SCR-63" },
  { href: "/admin/ai", key: "ai", scr: "SCR-64" },
] as const;

/** SCR-50 `/admin` (T-617F) — overview + cards to the sub-pages the role may open (default deny). */
export default async function Page() {
  const t = await getTranslations();
  const session = await getServerSession(authOptions);
  const u = session?.user;
  const open = CARDS.filter((c) => canAccess(c.href, u?.role ?? "", u?.permissions ?? [], u?.scopePillars ?? []));
  return (
    <div className="mx-auto max-w-5xl" data-testid="admin-overview" data-scr="SCR-50">
      <h1 className="text-2xl font-semibold">{t("nav.admin")}</h1>
      <p className="mt-1 text-sm text-muted-foreground">{t("navHint.admin")}</p>
      <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" data-testid="admin-cards">
        {open.map((c) => (
          <li key={c.href}>
            <Link href={c.href} className="block h-full rounded-lg border bg-card p-4 hover:bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary" data-testid={`admin-card-${c.key}`}>
              <div className="font-medium text-primary">{t(`adminHome.${c.key}.title`)}</div>
              <p className="mt-1 text-sm text-muted-foreground">{t(`adminHome.${c.key}.body`)}</p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
