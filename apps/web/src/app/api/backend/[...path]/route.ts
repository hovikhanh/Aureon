/**
 * BFF proxy: browser → `/api/backend/<path>` → FastAPI `/api/v1/<path>` with the session's
 * Bearer token. Tokens never reach client JS. SSE responses are streamed through unbuffered.
 */
import { NextResponse, type NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";
import { API_BASE, isMockMode } from "@/lib/server-env";
import { clearSession, persistToken, readToken } from "@/lib/session-token";
import { decodeMockToken } from "@/mocks/auth";
import { handleMock } from "@/mocks/router";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const FORWARD_REQ = ["content-type", "accept", "accept-language", "idempotency-key", "if-match"];
const FORWARD_RES = ["content-type", "cache-control", "etag", "x-request-id", "vary"];

const UNAUTH = { error: { code: "UNAUTHENTICATED", message: "no session", details: {} } };

/** T-604: API_MODE=mock → in-process mock router (no backend); claims from the mock token. */
async function mock(req: NextRequest, path: string[]): Promise<Response> {
  const secret = process.env.NEXTAUTH_SECRET;
  if (!secret) return NextResponse.json({ error: { code: "INTERNAL_ERROR", message: "auth not configured", details: {} } }, { status: 500 });
  const token = await getToken({ req, secret });
  const claims = decodeMockToken(token?.accessToken);
  if (!claims) return NextResponse.json(UNAUTH, { status: 401 });
  if ((req.headers.get("content-type") ?? "").startsWith("multipart/form-data")) {
    return handleMock({ method: req.method, path: `/${path.join("/")}`, query: req.nextUrl.searchParams, headers: req.headers, body: await multipartBody(req), claims });
  }
  const raw = ["GET", "HEAD"].includes(req.method) ? "" : await req.text();
  let body: unknown = undefined;
  try {
    body = raw ? JSON.parse(raw) : undefined;
  } catch {
    return NextResponse.json({ error: { code: "BAD_REQUEST", message: "invalid JSON body", details: {} } }, { status: 400 });
  }
  return handleMock({ method: req.method, path: `/${path.join("/")}`, query: req.nextUrl.searchParams, headers: req.headers, body, claims });
}

/** Mock-only: multipart upload (EP-DC-01 `files`, EP-DC-17 `file`) → file metadata (+ CSV text) for the mock router. */
async function multipartBody(req: NextRequest): Promise<Record<string, unknown>> {
  const form = await req.formData();
  const meta = async (f: File) => ({ name: f.name, size: f.size, type: f.type, ...(f.name.toLowerCase().endsWith(".csv") && f.size < 1_000_000 ? { text: await f.text() } : {}) });
  const files = await Promise.all(form.getAll("files").filter((f): f is File => typeof f !== "string").map(meta));
  const one = form.get("file");
  const docType = form.get("document_type");
  return { files, file: one && typeof one !== "string" ? await meta(one) : null, document_type: typeof docType === "string" && docType ? docType : null };
}

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }): Promise<Response> {
  const { path } = await ctx.params;
  if (isMockMode()) return mock(req, path);
  const { token, refreshed, revoked } = await readToken(req);
  if (!token) {
    const res = NextResponse.json(UNAUTH, { status: 401 });
    if (revoked) clearSession(res); // otherwise /login → / → 401 → /login loops on a dead session
    return res;
  }
  const headers = new Headers({ authorization: `Bearer ${token.accessToken}` });
  for (const h of FORWARD_REQ) {
    const v = req.headers.get(h);
    if (v) headers.set(h, v);
  }
  const url = `${API_BASE}/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`;
  const hasBody = !["GET", "HEAD"].includes(req.method);
  let upstream: Response;
  try {
    upstream = await fetch(url, {
      method: req.method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      cache: "no-store",
      signal: req.signal,
    });
  } catch {
    return NextResponse.json({ error: { code: "DEPENDENCY_UNAVAILABLE", message: "api unreachable", details: {} } }, { status: 502 });
  }
  const out = new Headers();
  for (const h of FORWARD_RES) {
    const v = upstream.headers.get(h);
    if (v) out.set(h, v);
  }
  if ((upstream.headers.get("content-type") ?? "").includes("text/event-stream")) {
    out.set("cache-control", "no-store");
    out.set("x-accel-buffering", "no");
    out.set("connection", "keep-alive");
  }
  const res = new NextResponse(upstream.status === 204 ? null : upstream.body, { status: upstream.status, headers: out });
  if (refreshed) await persistToken(res, token);
  return res;
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as PUT, proxy as DELETE };
