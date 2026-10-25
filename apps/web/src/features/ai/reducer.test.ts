import { describe, expect, it } from "vitest";
import { applyEvent, segmentCitations } from "./reducer";
import type { ChatMessage } from "./types";

const empty: ChatMessage = { id: "tmp", sender: "assistant", content: "", sources: [], tools: [], warnings: [], streaming: true };

describe("chat stream reducer", () => {
  it("applies start → tool → token → done", () => {
    let r = applyEvent(empty, { event: "start", data: { conversation_id: "c1", message_id: "m1" } });
    expect(r.conversationId).toBe("c1");
    r = applyEvent(r.msg, { event: "tool_call", data: { tool: "get_finance_metric" } });
    expect(r.msg.tools[0]?.status).toBe("running");
    r = applyEvent(r.msg, { event: "tool_result", data: { tool: "get_finance_metric", status: "ok", latency_ms: 12, sources: [{ type: "metric_value", id: "revenue_q3", label: "Doanh thu Q3" }] } });
    expect(r.msg.tools[0]).toMatchObject({ status: "ok", latency_ms: 12 });
    r = applyEvent(r.msg, { event: "token", data: { delta: "Doanh thu " } });
    r = applyEvent(r.msg, { event: "token", data: { delta: "45 tỷ [1]" } });
    expect(r.msg.content).toBe("Doanh thu 45 tỷ [1]");
    r = applyEvent(r.msg, { event: "done", data: { answer: "Doanh thu 45 tỷ [1]", sources: [], warnings: [] } });
    expect(r.msg.streaming).toBe(false);
    expect(r.msg.sources).toHaveLength(1);
  });
  it("segments citations", () => {
    expect(segmentCitations("A [1] b [2]")).toEqual([
      { kind: "text", text: "A " }, { kind: "cite", n: 1 }, { kind: "text", text: " b " }, { kind: "cite", n: 2 },
    ]);
  });
});

describe("done.suggested_actions (T-645F, TC-M16-19)", () => {
  it("keeps the ActionCards of the done event", () => {
    const action = { id: "a1", action_name: "ACT-create_task", autonomy_level: "L2", status: "proposed", on_behalf_of: "u1", input_preview: { title: "X" } };
    const r = applyEvent(empty, { event: "done", data: { answer: "ok", suggested_actions: [action], warnings: [] } });
    expect(r.msg.actions).toEqual([action]);
    expect(applyEvent(empty, { event: "done", data: { answer: "ok" } }).msg.actions).toEqual([]);
  });
});
