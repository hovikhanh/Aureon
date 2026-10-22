/**
 * NextAuth (Credentials → EP-02 `POST /auth/login`). JWT strategy: the backend RS256 access
 * token + rotating refresh token live only in the encrypted httpOnly session cookie; the browser
 * session exposes user/role/permissions but never the tokens (CLAUDE §5.8).
 */
import type { NextAuthOptions } from "next-auth";
import type { JWT } from "next-auth/jwt";
import CredentialsProvider from "next-auth/providers/credentials";
import { API_BASE, demoPasswordFor } from "./server-env";

interface TokenOut {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: { id: string; email: string; full_name: string; role_code: string; permissions: string[] };
}

async function postJson(path: string, body: unknown): Promise<{ ok: boolean; json: unknown }> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  return { ok: res.ok, json: await res.json().catch(() => null) };
}

function errorCode(json: unknown): string {
  const code = (json as { error?: { code?: unknown } } | null)?.error?.code;
  return typeof code === "string" ? code : "INTERNAL_ERROR";
}

export async function refreshTokens(token: JWT): Promise<JWT> {
  try {
    const { ok, json } = await postJson("/auth/refresh", { refresh_token: token.refreshToken });
    if (!ok) return { ...token, error: "RefreshFailed" };
    const d = (json as { data: TokenOut }).data;
    return {
      ...token,
      accessToken: d.access_token,
      refreshToken: d.refresh_token,
      expiresAt: Date.now() + d.expires_in * 1000,
      permissions: d.user.permissions,
      role: d.user.role_code,
      error: undefined,
    };
  } catch {
    return { ...token, error: "RefreshFailed" };
  }
}

export const authOptions: NextAuthOptions = {
  session: { strategy: "jwt", maxAge: 7 * 24 * 3600 },
  pages: { signIn: "/login", error: "/login" },
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: { email: { type: "email" }, password: { type: "password" }, demo: { type: "text" } },
      async authorize(creds) {
        const email = (creds?.email ?? "").trim();
        let password = creds?.password ?? "";
        if (creds?.demo === "true" && !password) password = demoPasswordFor(email) ?? "";
        if (!email || !password) throw new Error("INVALID_CREDENTIALS");
        let res: { ok: boolean; json: unknown };
        try {
          res = await postJson("/auth/login", { email, password });
        } catch {
          throw new Error("DEPENDENCY_UNAVAILABLE");
        }
        if (!res.ok) throw new Error(errorCode(res.json));
        const d = (res.json as { data: TokenOut }).data;
        return {
          id: d.user.id,
          email: d.user.email,
          name: d.user.full_name,
          role: d.user.role_code,
          permissions: d.user.permissions,
          accessToken: d.access_token,
          refreshToken: d.refresh_token,
          expiresAt: Date.now() + d.expires_in * 1000,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        return {
          ...token,
          uid: user.id,
          name: user.name,
          email: user.email,
          role: user.role,
          permissions: user.permissions,
          accessToken: user.accessToken,
          refreshToken: user.refreshToken,
          expiresAt: user.expiresAt,
        };
      }
      // Refresh happens only in the BFF proxy (single-flight) so the rotating refresh token is
      // never replayed concurrently (reuse detection would revoke the chain — 02 §5).
      return token;
    },
    async session({ session, token }) {
      session.user = {
        id: token.uid,
        email: token.email ?? "",
        name: token.name ?? "",
        role: token.role,
        permissions: token.permissions,
      };
      if (token.error) session.error = token.error;
      return session;
    },
  },
};
