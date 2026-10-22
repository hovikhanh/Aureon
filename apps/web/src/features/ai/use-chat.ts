"use client";
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useLocale } from "next-intl";
import { ApiError } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { streamSse } from "@/lib/sse";
import { applyEvent } from "./reducer";
import type { ChatMessage, MessageOut } from "./types";

let seq = 0;
const tmpId = (p: string) => `${p}-${Date.now()}-${++seq}`;

export function fromHistory(m: MessageOut): ChatMessage {
  return {
    id: m.id,
    sender: m.sender === "user" ? "user" : "assistant",
    content: m.content,
    sources: m.sources,
    tools: m.function_calls.map((f) => ({ tool: f.tool, status: f.status, latency_ms: f.latency_ms })),
    warnings: [],
    streaming: false,
    truncated: m.truncated,
  };
}

/** EP-111 SSE chat: token-by-token render into the last assistant message. */
export function useChat() {
  const locale = useLocale();
  const client = useQueryClient();
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const abort = React.useRef<AbortController | null>(null);

  const send = React.useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || busy) return;
      const user: ChatMessage = { id: tmpId("u"), sender: "user", content: message, sources: [], tools: [], warnings: [], streaming: false };
      const asstId = tmpId("a");
      let current: ChatMessage = { id: asstId, sender: "assistant", content: "", sources: [], tools: [], warnings: [], streaming: true };
      setMessages((xs) => [...xs, user, current]);
      setBusy(true);
      abort.current = new AbortController();
      const update = (next: ChatMessage) => {
        current = next;
        setMessages((xs) => xs.map((m) => (m.id === asstId ? { ...next, id: asstId } : m)));
      };
      try {
        await streamSse(
          "/ai/chat/stream",
          { message, conversation_id: conversationId ?? undefined, locale: locale === "en" ? "en" : "vi" },
          (e) => {
            const r = applyEvent(current, e);
            if (r.conversationId) setConversationId(r.conversationId);
            update(r.msg);
          },
          abort.current.signal,
        );
        if (current.streaming) update({ ...current, streaming: false });
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          update({ ...current, streaming: false, error: err instanceof ApiError ? err.code : "NETWORK_ERROR" });
        }
      } finally {
        setBusy(false);
        void client.invalidateQueries({ queryKey: qk.conversations() });
      }
    },
    [busy, conversationId, locale, client],
  );

  const reset = React.useCallback((id: string | null = null, history: ChatMessage[] = []) => {
    abort.current?.abort();
    setConversationId(id);
    setMessages(history);
    setBusy(false);
  }, []);

  return { messages, conversationId, busy, send, reset };
}
