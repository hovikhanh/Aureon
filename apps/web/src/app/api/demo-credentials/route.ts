/**
 * SCR-13 demo autofill (T-610c, R-DEC-28): `POST { email }` → `{ data: { email, password } }`.
 * FE infrastructure (like `api/auth`), not a FastAPI endpoint. Gates + whitelist live in
 * `lib/demo-credentials.ts`; the e-mail travels in the body, never in a URL. No logging.
 */
import { NextResponse } from "next/server";
import { resolveDemoCredentials } from "@/lib/demo-credentials";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const NO_STORE = { "cache-control": "no-store" };

export async function POST(req: Request): Promise<Response> {
  const body = (await req.json().catch(() => null)) as { email?: unknown } | null;
  const { status, body: out } = resolveDemoCredentials(body?.email);
  return NextResponse.json(out, { status, headers: NO_STORE });
}
