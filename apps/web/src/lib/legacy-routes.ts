/**
 * v2.1 → v3 route map (06 §3.4, R-DEC-25, T-607). `middleware.ts` answers these with a
 * permanent **308** (method + body preserved), keeping the query string. Order matters: the
 * first matching prefix wins, so more specific prefixes come first.
 */
export const LEGACY_ROUTES: readonly (readonly [from: string, to: string])[] = [
  ["/dashboard/pillar", "/home/pillar"],
  ["/dashboard", "/home"],
  ["/ai", "/ask"],
  ["/approvals", "/work/approvals"],
  ["/idp/review", "/data/review"],
  ["/finance/invoices", "/business/finance/invoices"],
  ["/hr/employees", "/business/hr/employees"],
];

/** v3 path for a v2.1 path (sub-paths carried over), or `null` when it is not a legacy route. */
export function legacyRedirect(pathname: string): string | null {
  for (const [from, to] of LEGACY_ROUTES) {
    if (pathname === from || pathname.startsWith(`${from}/`)) return to + pathname.slice(from.length);
  }
  return null;
}
