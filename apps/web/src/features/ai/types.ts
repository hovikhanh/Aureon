/** 10 §4.8 SourceRef / EP-111 SSE events (start → tool_call/tool_result → token → done | error). */
export interface SourceRef {
  type: "metric_value" | "record" | "document_page" | "tool_result";
  id: string;
  label: string;
  period_key?: string | null;
  value?: number | null;
  lineage_url?: string | null;
}

export interface ToolCall {
  tool: string;
  status: "running" | "ok" | "error" | "forbidden" | "timeout";
  latency_ms?: number;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  content: string;
  sources: SourceRef[];
  tools: ToolCall[];
  warnings: string[];
  streaming: boolean;
  truncated?: boolean;
  error?: string;
  /** EP-AI-02 `done.suggested_actions[]` (T-645F): `AIActionOut` (L2 stored) or L1 suggestion (no id). */
  actions?: SuggestedAction[];
}

export interface SuggestedAction {
  id?: string;
  action_name: string;
  tool_name?: string | null;
  autonomy_level: "L0" | "L1" | "L2" | "L3";
  status?: "proposed" | "confirmed" | "executed" | "rejected" | "undone" | "failed";
  input_preview?: Record<string, unknown>;
  on_behalf_of?: string;
  can_undo?: boolean;
  created_at?: string | null;
  agent_profile_code?: string | null;
}

export interface ConversationOut {
  id: string;
  title: string | null;
  last_message_at: string | null;
}

export interface MessageOut {
  id: string;
  sender: "user" | "assistant" | "system";
  content: string;
  sources: SourceRef[];
  function_calls: { tool: string; status: ToolCall["status"]; latency_ms: number }[];
  truncated: boolean;
  created_at: string;
}
