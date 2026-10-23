/**
 * Read the DIR khối (`scope_pillars`, R-DEC-12a) from an access token for **display only**
 * (which pillar cards to render). The payload is not verified here — the API verifies every
 * request and enforces scope server-side. Mock tokens (`mock.<base64url>`) carry the same claim.
 */
const PILLAR_CODES = new Set(["F", "O", "C", "U", "S"]);

export function scopePillarsOf(accessToken: string): string[] {
  const parts = accessToken.split(".");
  const payload = parts[1]; // JWT: header.payload.sig · mock: mock.payload
  if (!payload) return [];
  try {
    const claims = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as { scope_pillars?: unknown };
    const raw = Array.isArray(claims.scope_pillars) ? claims.scope_pillars : [];
    return raw.filter((p): p is string => typeof p === "string" && PILLAR_CODES.has(p));
  } catch {
    return [];
  }
}
