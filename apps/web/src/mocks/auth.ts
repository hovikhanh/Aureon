/**
 * Mock login (T-604, R-DEC-25) — `authorize()` branch when `API_MODE=mock`. Issues an opaque
 * `mock.<base64url(claims)>` access token holding the same claim set as the real RS256 JWT
 * (`sub, email, role, permissions[], scope_pillars, department_id`). Never valid against the
 * real API (no signature) and mock mode is refused in production (`resolveApiMode`).
 *
 * Password: when `MOCK_LOGIN_PASSWORD` is set it must match; otherwise any non-empty password
 * is accepted (dev / CI only). Demo quick-login (`demo=true`) needs no password.
 */
import { MOCK_USERS, claimsFor, type MockClaims } from "./fixtures";

const PREFIX = "mock.";
const TTL_S = 7 * 24 * 3600;

export interface MockLogin {
  id: string;
  email: string;
  name: string;
  role: string;
  permissions: string[];
  scopePillars: string[];
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

function b64url(s: string): string {
  return Buffer.from(s, "utf8").toString("base64url");
}

export function encodeMockToken(claims: MockClaims): string {
  return PREFIX + b64url(JSON.stringify(claims));
}

export function decodeMockToken(token: string | undefined): MockClaims | null {
  if (!token?.startsWith(PREFIX)) return null;
  try {
    const c = JSON.parse(Buffer.from(token.slice(PREFIX.length), "base64url").toString("utf8")) as MockClaims;
    return typeof c.sub === "string" && Array.isArray(c.permissions) ? c : null;
  } catch {
    return null;
  }
}

/** Throws `Error("INVALID_CREDENTIALS")` like the real branch (error code = message). */
export function mockAuthorize(
  email: string,
  password: string,
  demo: boolean,
  env: Record<string, string | undefined> = process.env,
): MockLogin {
  const user = MOCK_USERS.find((u) => u.email === email.trim().toLowerCase());
  const expected = env.MOCK_LOGIN_PASSWORD;
  const passOk = demo ? true : expected ? password === expected : password.length > 0;
  if (!user || !passOk) throw new Error("INVALID_CREDENTIALS");
  const claims = claimsFor(user);
  return {
    id: claims.sub,
    email: claims.email,
    name: claims.name,
    role: claims.role,
    permissions: claims.permissions,
    scopePillars: claims.scope_pillars,
    accessToken: encodeMockToken(claims),
    refreshToken: `${PREFIX}refresh`,
    expiresAt: Date.now() + TTL_S * 1000,
  };
}
