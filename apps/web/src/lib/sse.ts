/** Minimal SSE-over-POST client (EventSource cannot POST). Parses `event:`/`data:` frames. */
import { API_PROXY, ApiError, newIdempotencyKey, toApiError } from "./api-client";

export interface SseEvent {
  event: string;
  data: unknown;
  id?: string;
}

export function parseSseChunk(buffer: string): { events: SseEvent[]; rest: string } {
  const events: SseEvent[] = [];
  const frames = buffer.split(/\r?\n\r?\n/);
  const rest = frames.pop() ?? "";
  for (const frame of frames) {
    let event = "message";
    let id: string | undefined;
    const data: string[] = [];
    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith(":")) continue;
      const idx = line.indexOf(":");
      const field = idx === -1 ? line : line.slice(0, idx);
      const value = idx === -1 ? "" : line.slice(idx + 1).replace(/^ /, "");
      if (field === "event") event = value;
      else if (field === "data") data.push(value);
      else if (field === "id") id = value;
    }
    if (!data.length) continue;
    const raw = data.join("\n");
    let parsed: unknown = raw;
    try {
      parsed = JSON.parse(raw);
    } catch {
      /* plain text payload */
    }
    events.push({ event, data: parsed, id });
  }
  return { events, rest };
}

export async function streamSse(
  path: string,
  body: unknown,
  onEvent: (e: SseEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_PROXY}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json", accept: "text/event-stream", "idempotency-key": newIdempotencyKey() },
    body: JSON.stringify(body),
    credentials: "same-origin",
    signal,
  });
  if (res.status === 401 && typeof window !== "undefined") window.location.assign("/login");
  if (!res.ok || !res.body) throw res.ok ? new ApiError(res.status, "STREAM_ERROR", "empty body") : await toApiError(res);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { events, rest } = parseSseChunk(buffer);
    buffer = rest;
    events.forEach(onEvent);
  }
  if (buffer.trim()) parseSseChunk(`${buffer}\n\n`).events.forEach(onEvent);
}
