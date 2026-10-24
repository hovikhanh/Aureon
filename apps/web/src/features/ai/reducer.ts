import type { SseEvent } from "@/lib/sse";
import type { ChatMessage, SourceRef, SuggestedAction, ToolCall } from "./types";

type Data = Record<string, unknown>;

/** Apply one EP-111 SSE event to the streaming assistant message (pure → unit-tested). */
export function applyEvent(msg: ChatMessage, e: SseEvent): { msg: ChatMessage; conversationId?: string } {
  const d = (e.data ?? {}) as Data;
  switch (e.event) {
    case "start":
      return { msg: { ...msg, id: (d.message_id as string) ?? msg.id }, conversationId: (d.conversation_id as string) ?? undefined };
    case "tool_call":
      return { msg: { ...msg, tools: [...msg.tools, { tool: String(d.tool), status: "running" }] } };
    case "tool_result": {
      const tools: ToolCall[] = msg.tools.map((t) =>
        t.tool === d.tool && t.status === "running"
          ? { ...t, status: (d.status as ToolCall["status"]) ?? "ok", latency_ms: d.latency_ms as number }
          : t,
      );
      return { msg: { ...msg, tools, sources: mergeSources(msg.sources, (d.sources as SourceRef[]) ?? []) } };
    }
    case "token":
      return { msg: { ...msg, content: msg.content + String(d.delta ?? "") } };
    case "done":
      return {
        msg: {
          ...msg,
          content: typeof d.answer === "string" && d.answer ? d.answer : msg.content,
          sources: mergeSources(msg.sources, (d.sources as SourceRef[]) ?? []),
          warnings: (d.warnings as string[]) ?? [],
          truncated: Boolean(d.truncated),
          actions: (d.suggested_actions as SuggestedAction[] | undefined) ?? [],
          streaming: false,
        },
      };
    case "error":
      return { msg: { ...msg, streaming: false, error: String(d.code ?? "INTERNAL_ERROR") } };
    default:
      return { msg };
  }
}

function mergeSources(a: SourceRef[], b: SourceRef[]): SourceRef[] {
  const seen = new Set(a.map((s) => `${s.type}:${s.id}`));
  return [...a, ...b.filter((s) => !seen.has(`${s.type}:${s.id}`))];
}

/** Split answer text into plain segments and `[n]` citation markers (1-based → sources[n-1]). */
export type Segment = { kind: "text"; text: string } | { kind: "cite"; n: number };

export function segmentCitations(text: string): Segment[] {
  const out: Segment[] = [];
  const re = /\[(\d{1,2})\]/g;
  let last = 0;
  for (let m = re.exec(text); m; m = re.exec(text)) {
    if (m.index > last) out.push({ kind: "text", text: text.slice(last, m.index) });
    out.push({ kind: "cite", n: Number(m[1]) });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}
