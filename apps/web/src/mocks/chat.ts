/**
 * Fake EP-111 chat SSE + EP-112 history (T-604). Event order and payloads mirror
 * `modules/ai/routes/router.py`: start → tool_call → tool_result → token… → done. The answer
 * only quotes snapshot metric values the caller may see (grounding, P05) — never invents numbers.
 */
import { SNAPSHOT, mockId } from "./fixtures";
import { fail, ok } from "./http";
import type { MockRequest } from "./router";
import { metricVisible, sessionFor, type MockMessage } from "./store";
import { proposeFromChat } from "./ai-actions";

export const SSE_ORDER = ["start", "tool_call", "tool_result", "token", "done"] as const;

function frame(id: number, event: string, data: unknown): string {
  return `id: ${id}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function answerFor(req: MockRequest) {
  const seen = SNAPSHOT.metrics.filter((m) => metricVisible(req.claims, m.code, m.pillar) && m.status !== "ok");
  const sources = seen.map((m) => ({
    type: "metric_value", id: m.code, label: m.code, period_key: m.period_key, value: m.value,
    lineage_url: `/dashboard/metrics/${m.code}/lineage`,
  }));
  const lines = seen.map((m) => `- ${m.code}: ${m.value ?? "—"} ${m.unit} (${m.status})`);
  const answer = lines.length
    ? `[mock] Chỉ số cần chú ý trong phạm vi của bạn:\n${lines.join("\n")}`
    : "[mock] Không có chỉ số nào lệch ngưỡng trong phạm vi của bạn.";
  return { answer, sources };
}

export function chatStream(req: MockRequest): Response {
  const body = (req.body ?? {}) as { message?: unknown; conversation_id?: unknown };
  if (typeof body.message !== "string" || !body.message.trim()) {
    return fail(422, "VALIDATION_ERROR", "request validation failed", { fields: [{ field: "message", code: "missing" }] });
  }
  const session = sessionFor(req.claims.sub);
  let conv = session.conversations.find((c) => c.id === body.conversation_id);
  if (!conv) {
    conv = { id: globalThis.crypto.randomUUID(), title: body.message.slice(0, 60), last_message_at: null, messages: [] };
    session.conversations.unshift(conv);
  }
  const now = new Date().toISOString();
  const proposed = proposeFromChat(req.claims, body.message, req.headers.get("x-request-id") ?? globalThis.crypto.randomUUID());
  const { answer, sources } = proposed.actions.length ? { answer: "[mock] Tôi đã soạn thao tác bên dưới — bạn xem và xác nhận.", sources: [] } : answerFor(req);
  const call = { tool: "get_metric_values", status: "ok", latency_ms: 5 };
  const user: MockMessage = { id: globalThis.crypto.randomUUID(), sender: "user", content: body.message, sources: [], function_calls: [], truncated: false, created_at: now };
  const asst: MockMessage = { id: globalThis.crypto.randomUUID(), sender: "assistant", content: answer, sources, function_calls: [call], truncated: false, created_at: now };
  conv.messages.push(user, asst);
  conv.last_message_at = now;

  const frames: string[] = [];
  let n = 0;
  const push = (event: string, data: unknown) => frames.push(frame(++n, event, data));
  push("start", { conversation_id: conv.id, message_id: asst.id, model_route: { task: "chat" } });
  push("tool_call", { call_id: call.tool, tool: call.tool });
  push("tool_result", { call_id: call.tool, tool: call.tool, status: call.status, latency_ms: call.latency_ms, sources });
  for (const word of answer.match(/\S+\s*/g) ?? []) push("token", { delta: word });
  push("done", { message_id: asst.id, answer, sources, function_calls: [call], suggested_actions: proposed.actions, truncated: false, warnings: proposed.warnings, usage: { tokens_in: 0, tokens_out: 0 } });

  const enc = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const f of frames) controller.enqueue(enc.encode(f));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "content-type": "text/event-stream", "cache-control": "no-store", "x-accel-buffering": "no", "x-request-id": mockId("req", now), "x-api-mode": "mock" },
  });
}

export function listConversations(req: MockRequest): Response {
  return ok(sessionFor(req.claims.sub).conversations.map(({ id, title, last_message_at }) => ({ id, title, last_message_at })));
}

export function conversationMessages(req: MockRequest): Response {
  const conv = sessionFor(req.claims.sub).conversations.find((c) => c.id === req.params.id);
  return conv ? ok(conv.messages) : fail(404, "NOT_FOUND", "conversation not found");
}
