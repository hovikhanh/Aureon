/**
 * E2E support (T-618): age the backend access token inside the NextAuth session cookie so the
 * next BFF call must refresh (stand-in for waiting the 15-min access TTL). Uses the same
 * `NEXTAUTH_SECRET` as the web server (root `.env`, compose `env_file`). Real project only.
 */
import type { BrowserContext } from "@playwright/test";
import { decode, encode } from "next-auth/jwt";
import { rootEnv } from "./seed";

const COOKIE = "next-auth.session-token";

export async function expireAccessToken(context: BrowserContext): Promise<void> {
  const secret = process.env.NEXTAUTH_SECRET ?? rootEnv().NEXTAUTH_SECRET ?? "";
  if (!secret) throw new Error("NEXTAUTH_SECRET missing — cannot edit the session cookie");
  const cookie = (await context.cookies()).find((c) => c.name === COOKIE);
  if (!cookie) throw new Error(`${COOKIE} not found — is the user signed in?`);
  const token = await decode({ token: cookie.value, secret });
  if (!token) throw new Error("session cookie could not be decoded");
  const value = await encode({ token: { ...token, expiresAt: 0 }, secret, maxAge: 7 * 24 * 3600 });
  await context.addCookies([{ ...cookie, value }]);
}
