/** Route protection (T-502): unauthenticated → /login; authenticated but role lacks permission → /403. */
import { NextResponse, type NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";
import { canAccess } from "@/lib/permissions";

export async function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  if (pathname === "/login") {
    return token ? NextResponse.redirect(new URL("/", req.url)) : NextResponse.next();
  }
  if (!token) {
    const url = new URL("/login", req.url);
    url.searchParams.set("callbackUrl", pathname + search);
    return NextResponse.redirect(url);
  }
  if (!canAccess(pathname, token.permissions ?? [])) {
    return NextResponse.rewrite(new URL("/403", req.url), { status: 403 });
  }
  return NextResponse.next();
}

// Must be a static literal (Next.js). Keep in sync with ROUTE_RULES in lib/permissions.ts.
export const config = {
  matcher: ["/login", "/dashboard/:path*", "/idp/:path*", "/ai/:path*", "/finance/:path*", "/approvals/:path*", "/hr/:path*", "/admin/:path*"],
};
