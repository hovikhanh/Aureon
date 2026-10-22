/** Server-only: read/refresh the backend tokens stored in the NextAuth session cookie. */
import type { NextRequest, NextResponse } from "next/server";
import { encode, getToken, type JWT } from "next-auth/jwt";
import { refreshTokens } from "./auth";

const SECRET = process.env.NEXTAUTH_SECRET ?? "";
const SECURE = (process.env.NEXTAUTH_URL ?? "").startsWith("https://");
export const SESSION_COOKIE = SECURE ? "__Secure-next-auth.session-token" : "next-auth.session-token";
const MAX_AGE = 7 * 24 * 3600;

// Single-flight refresh per refresh token (concurrent widget queries share one rotation).
const inflight = new Map<string, Promise<JWT>>();

export async function readToken(req: NextRequest): Promise<{ token: JWT | null; refreshed: boolean }> {
  const token = await getToken({ req, secret: SECRET });
  if (!token?.accessToken) return { token: null, refreshed: false };
  if (Date.now() < token.expiresAt - 30_000) return { token, refreshed: false };
  const key = token.refreshToken;
  let p = inflight.get(key);
  if (!p) {
    p = refreshTokens(token);
    inflight.set(key, p);
    p.finally(() => setTimeout(() => inflight.delete(key), 30_000)).catch(() => undefined);
  }
  const next = await p;
  if (next.error) return { token: null, refreshed: false };
  return { token: next, refreshed: true };
}

export async function persistToken(res: NextResponse, token: JWT): Promise<void> {
  const value = await encode({ token, secret: SECRET, maxAge: MAX_AGE });
  res.cookies.set(SESSION_COOKIE, value, { httpOnly: true, sameSite: "lax", path: "/", secure: SECURE, maxAge: MAX_AGE });
}
