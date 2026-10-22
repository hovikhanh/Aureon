"use client";
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { MessageSquarePlus, Send, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { SourceChip } from "@/components/ai/SourceChip";
import { ThinkingState, WaitHint } from "@/components/ai/ThinkingState";
import { api } from "@/lib/api-client";
import { qk } from "@/lib/query-keys";
import { cn } from "@/lib/utils";
import { segmentCitations } from "./reducer";
import type { ChatMessage, ConversationOut, MessageOut } from "./types";
import { fromHistory, useChat } from "./use-chat";

const KNOWN = ["AI_STREAM_TIMEOUT", "AI_PROVIDER_TIMEOUT", "AI_DISABLED", "AI_QUOTA_EXCEEDED", "RATE_LIMIT_EXCEEDED", "UNAUTHENTICATED", "FORBIDDEN_ROLE"];

function AssistantMessage({ m }: { m: ChatMessage }) {
  const t = useTranslations();
  return (
    <div className="flex flex-col gap-2" data-testid="assistant-message" data-streaming={m.streaming}>
      <div className="flex items-center gap-2 text-xs font-medium text-ai">
        <Sparkles className="h-4 w-4" aria-hidden />{t("ai.assistant")}<Badge variant="ai">{t("ai.badge")}</Badge>
      </div>
      <ThinkingState tools={m.tools} streaming={m.streaming && !m.content} />
      <WaitHint active={m.streaming && !m.content} />
      {m.content && (
        <div className="whitespace-pre-wrap rounded-2xl rounded-tl-sm border-l-4 border-ai bg-card px-4 py-3 text-sm leading-relaxed shadow-sm" data-testid="answer">
          {segmentCitations(m.content).map((s, i) =>
            s.kind === "text" ? <React.Fragment key={i}>{s.text}</React.Fragment> : <SourceChip key={i} n={s.n} source={m.sources[s.n - 1]} />,
          )}
          {m.streaming && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-ai align-middle" aria-hidden />}
        </div>
      )}
      {!m.streaming && m.sources.length > 0 && (
        <div className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground" data-testid="sources">
          {t("ai.sources")}:
          {m.sources.map((s, i) => <SourceChip key={`${s.id}-${i}`} n={i + 1} source={s} />)}
        </div>
      )}
      {m.warnings.map((w) => (
        <p key={w} className="text-xs text-warning">{w === "AI_NO_DATA_AVAILABLE" ? t("ai.warning.AI_NO_DATA_AVAILABLE") : t("ai.warning.default", { code: w })}</p>
      ))}
      {m.truncated && <p className="text-xs text-muted-foreground">{t("ai.truncated")}</p>}
      {m.error && <p role="alert" className="text-sm text-danger" data-testid="chat-error">{KNOWN.includes(m.error) ? t(`errors.${m.error}` as "errors.generic") : t("errors.generic")}</p>}
    </div>
  );
}

export function ChatView() {
  const t = useTranslations();
  const { messages, conversationId, busy, send, reset } = useChat();
  const [input, setInput] = React.useState("");
  const endRef = React.useRef<HTMLDivElement>(null);
  const conversations = useQuery({ queryKey: qk.conversations(), queryFn: ({ signal }) => api.get<ConversationOut[]>("/ai/conversations", undefined, signal) });

  React.useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [messages]);

  const openConversation = async (id: string) => {
    const history = await api.get<MessageOut[]>(`/ai/conversations/${id}/messages`);
    reset(id, history.filter((m) => m.sender !== "system").map(fromHistory));
  };
  const submit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const text = input;
    setInput("");
    void send(text);
  };

  return (
    <div className="mx-auto flex h-[calc(100dvh-7rem)] max-w-6xl gap-4">
      <aside className="hidden w-64 shrink-0 flex-col gap-2 rounded-lg border bg-card p-3 md:flex" data-testid="chat-history">
        <Button variant="outline" size="sm" onClick={() => reset()} data-testid="new-chat"><MessageSquarePlus className="h-4 w-4" />{t("buttons.newChat")}</Button>
        <h2 className="mt-2 text-xs font-semibold uppercase text-muted-foreground">{t("ai.history")}</h2>
        <ul className="flex-1 space-y-1 overflow-y-auto text-sm">
          {(conversations.data ?? []).map((c) => (
            <li key={c.id}>
              <button type="button" onClick={() => void openConversation(c.id)} className={cn("w-full truncate rounded px-2 py-1.5 text-left hover:bg-muted", c.id === conversationId && "bg-ai-subtle text-ai")}>
                {c.title || t("ai.untitled")}
              </button>
            </li>
          ))}
          {conversations.isSuccess && !conversations.data.length && <li className="px-2 text-xs text-muted-foreground">{t("ai.historyEmpty")}</li>}
        </ul>
      </aside>
      <section className="flex min-w-0 flex-1 flex-col rounded-lg border bg-muted/40">
        <div className="flex items-center gap-2 border-b bg-card px-4 py-3">
          <Sparkles className="h-5 w-5 text-ai" aria-hidden />
          <h1 className="font-semibold">{t("ai.title")}</h1>
          <Button variant="ghost" size="sm" className="ml-auto md:hidden" onClick={() => reset()}>{t("buttons.newChat")}</Button>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto p-4" data-testid="message-list" aria-live="polite">
          {!messages.length && (
            <div className="flex flex-col items-start gap-3 text-sm text-muted-foreground">
              <p>{t("ai.welcome")}</p>
              <div className="flex flex-wrap gap-2">
                {(["q1", "q2", "q3"] as const).map((k) => (
                  <Button key={k} variant="outline" size="sm" onClick={() => void send(t(`ai.suggestions.${k}`))}>{t(`ai.suggestions.${k}`)}</Button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) =>
            m.sender === "user" ? (
              <div key={m.id} className="flex justify-end" data-testid="user-message">
                <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2 text-sm text-primary-foreground">{m.content}</div>
              </div>
            ) : (
              <AssistantMessage key={m.id} m={m} />
            ),
          )}
          <div ref={endRef} />
        </div>
        <form onSubmit={submit} className="flex items-end gap-2 border-t bg-card p-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
            rows={1}
            maxLength={4000}
            aria-label={t("ai.inputLabel")}
            placeholder={t("ai.placeholder")}
            data-testid="chat-input"
            className="max-h-40 min-h-10 flex-1 resize-none rounded border bg-card px-3 py-2 text-sm"
          />
          <Button type="submit" variant="ai" disabled={busy || !input.trim()} aria-label={t("buttons.send")} data-testid="chat-send">
            <Send className="h-4 w-4" aria-hidden /><span className="hidden sm:inline">{t("buttons.send")}</span>
          </Button>
        </form>
      </section>
    </div>
  );
}
