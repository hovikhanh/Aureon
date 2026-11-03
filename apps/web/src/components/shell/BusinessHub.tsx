import Link from "next/link";
import { getServerSession } from "next-auth";
import { getTranslations } from "next-intl/server";
import { authOptions } from "@/lib/auth";
import { canAccess } from "@/lib/permissions";

/** A built Business screen surfaced as a hub card, shown only when the role may open it. */
interface HubCard {
  href: string;
  /** i18n keys under `businessHub.cards.<key>` for title + description. */
  key: "finance" | "sales" | "invoices" | "employees";
}

const CARDS: readonly HubCard[] = [
  { href: "/business/finance", key: "finance" },
  { href: "/business/sales", key: "sales" },
  { href: "/business/finance/invoices", key: "invoices" },
  { href: "/business/hr/employees", key: "employees" },
];

/**
 * SCR-46 `/business` landing (06 §3.4). M2.2 shipped Finance Lite, Sales pipeline, Invoices and
 * the HR roster, so the landing is a real hub into those screens — not a "coming soon" frame. Each
 * card is filtered by the caller's role/permission with the same `canAccess` the middleware uses
 * (default deny), so a role sees only the screens it may open.
 */
export async function BusinessHub() {
  const t = await getTranslations();
  const session = await getServerSession(authOptions);
  const role = session?.user.role ?? "";
  const perms = session?.user.permissions ?? [];
  const pillars = session?.user.scopePillars ?? [];
  const open = CARDS.filter((c) => canAccess(c.href, role, perms, pillars));
  return (
    <div className="mx-auto max-w-5xl" data-testid="business-hub" data-scr="SCR-46">
      <h1 className="text-2xl font-semibold">{t("nav.business")}</h1>
      <p className="mt-1 text-sm text-muted-foreground">{t("navHint.business")}</p>
      {open.length === 0 ? (
        <p className="mt-6 text-sm text-muted-foreground" data-testid="business-hub-empty">{t("businessHub.empty")}</p>
      ) : (
        <ul className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2" data-testid="business-hub-cards">
          {open.map((c) => (
            <li key={c.href}>
              <Link
                href={c.href}
                className="flex h-full flex-col rounded-lg border bg-card p-5 transition-colors hover:border-primary hover:bg-muted"
                data-testid={`hub-card-${c.key}`}
              >
                <span className="text-base font-semibold text-primary">{t(`businessHub.cards.${c.key}.title`)}</span>
                <span className="mt-1 text-sm text-muted-foreground">{t(`businessHub.cards.${c.key}.desc`)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
