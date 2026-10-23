/**
 * Edge routing (T-502, T-607): v2.1 routes → **308** to the v3 route (06 §3.4, before auth so
 * bookmarks keep working); unauthenticated → /login; authenticated but outside the role/
 * permission of 06 §3.4 → /403 (rewrite, status 403).
 */
import { NextResponse, type NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";
import { legacyRedirect } from "@/lib/legacy-routes";
import { canAccess } from "@/lib/permissions";

export async function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const target = legacyRedirect(pathname);
  if (target) {
    const url = req.nextUrl.clone();
    url.pathname = target;
    return NextResponse.redirect(url, 308);
  }
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  if (pathname === "/login") {
    return token ? NextResponse.redirect(new URL("/", req.url)) : NextResponse.next();
  }
  if (!token) {
    const url = new URL("/login", req.url);
    url.searchParams.set("callbackUrl", pathname + search);
    return NextResponse.redirect(url);
  }
  if (!canAccess(pathname, token.role ?? "", token.permissions ?? [], token.scopePillars ?? [])) {
    return NextResponse.rewrite(new URL("/403", req.url), { status: 403 });
  }
  return NextResponse.next();
}

// Must be a static literal (Next.js). Covers every ROUTE_RULES prefix (lib/permissions.ts) and
// every v2.1 prefix of LEGACY_ROUTES (lib/legacy-routes.ts) — checked by permissions.test.ts.
export const config = {
  matcher: [
    "/login",
    "/home/:path*", "/ask/:path*", "/goals/:path*", "/work/:path*", "/meetings/:path*",
    "/data/:path*", "/business/:path*", "/knowledge/:path*", "/admin/:path*",
    "/dashboard/:path*", "/ai/:path*", "/approvals/:path*", "/idp/:path*", "/finance/:path*", "/hr/:path*",
  ],
};
