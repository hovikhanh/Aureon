/**
 * Web health (T-515): proxies FastAPI `GET /health` so orchestration can probe the web tier and
 * its backend link in one call. Web up but API unreachable → 503 `{ status: "down", web: "ok" }`.
 */
import { NextResponse } from "next/server";
import { API_URL } from "@/lib/server-env";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const NO_STORE = { "cache-control": "no-store" };

export async function GET(): Promise<Response> {
  try {
    const upstream = await fetch(`${API_URL}/health`, { cache: "no-store", signal: AbortSignal.timeout(5000) });
    const body: unknown = await upstream.json();
    return NextResponse.json({ web: "ok", api: body }, { status: upstream.status, headers: NO_STORE });
  } catch {
    return NextResponse.json({ status: "down", web: "ok", api: "unavailable" }, { status: 503, headers: NO_STORE });
  }
}
