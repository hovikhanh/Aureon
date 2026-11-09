/** Server-side display capabilities of the CRM views (the API enforces scope — R-DEC-175). */
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { canDomain } from "@/lib/permissions";

export async function crmCaps() {
  const u = (await getServerSession(authOptions))?.user;
  const perms = u?.permissions ?? [];
  const pillars = u?.scopePillars ?? [];
  const role = u?.role ?? "";
  // deal records: sales:read in khối C (REV's sales:read is review-scoped `r`, EMP has none)
  const canSeeDeals = canDomain(perms, pillars, "sales") && role !== "REV" && role !== "EMP";
  // stage moves: sales:write in khối C (the CEO included since D-21 — full sales writes)
  const canMove = canSeeDeals && canDomain(perms, pillars, "sales", "write");
  // user names: only `/platform/users` maps a user id to a name (CEO / ADM) — others see a plain label
  return { userId: u?.id ?? "", canSeeDeals, canMove, canReadUsers: perms.includes("platform:read") };
}
