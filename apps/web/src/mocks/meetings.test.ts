/** T-717F (mock) — EP-DC-38 `/data-capture/natural-language` mirrors 10 §7.2.4 (R-DEC-96/97/22). */
import { beforeEach, describe, expect, it } from "vitest";
import { MOCK_USERS, claimsFor } from "./fixtures";
import { handleMock } from "./router";
import { resetMockStore } from "./store";

const user = (email: string) => claimsFor(MOCK_USERS.find((u) => u.email === email)!);
const CEO = user("ceo@abc.demo");
/** A principal that lacks `idp:write` (route permission) — expect 403 FORBIDDEN_ROLE. */
const NO_WRITE = { ...CEO, permissions: CEO.permissions.filter((p) => p !== "idp:write") };
const IDEM = { "idempotency-key": "k-nl-1" };
type Err = { code: string; details: Record<string, unknown> };
type Json<T> = { data: T; error?: Err };

type Preview = {
  document_type: { code: string; confidence: number };
  status: string;
  predicted_actions: { action_name: string; params: Record<string, unknown> }[];
  extracted: { field: string; value: unknown }[];
};

async function post<T = Preview>(body: unknown, claims = CEO, headers: Record<string, string> = IDEM) {
  const res = await handleMock({
    method: "POST", path: "/data-capture/natural-language", query: new URLSearchParams(),
    headers: new Headers(headers), body, claims,
  });
  const json = (await res.json()) as Json<T>;
  return { status: res.status, json };
}

beforeEach(() => resetMockStore());

describe("EP-DC-38 C2 natural-language", () => {
  it("text → 201 NEEDS_REVIEW preview with MEETING_MINUTES + predicted action items", async () => {
    const r = await post({ text: "Họp giao ban: chốt báo giá ABC", channel: "C2" });
    expect(r.status).toBe(201);
    expect(r.json.data.document_type.code).toBe("MEETING_MINUTES");
    expect(r.json.data.status).toBe("NEEDS_REVIEW");
    expect(r.json.data.predicted_actions.length).toBeGreaterThanOrEqual(2);
    expect(r.json.data.predicted_actions.every((a) => a.action_name === "ACT-create_action_item")).toBe(true);
    const statuses = r.json.data.predicted_actions.map((a) => a.params.owner_match_status);
    expect(statuses).toContain("matched");
    expect(statuses).toContain("ambiguous");
    expect(r.json.data.extracted.length).toBeGreaterThan(0);
  });

  it("audio_ref → 201 canned transcript-derived preview (STT fixture, R-DEC-97)", async () => {
    const r = await post({ audio_ref: "obj/voice-note.webm", channel: "C2" });
    expect(r.status).toBe(201);
    expect(r.json.data.document_type.code).toBe("MEETING_MINUTES");
  });

  it("context=meeting → 422 BUSINESS_RULE_VIOLATION meeting_audio_blocked (R-DEC-22)", async () => {
    const r = await post({ audio_ref: "obj/x.webm", channel: "C2", context: "meeting" });
    expect(r.status).toBe(422);
    expect(r.json.error!.code).toBe("BUSINESS_RULE_VIOLATION");
    expect(r.json.error!.details.reason).toBe("meeting_audio_blocked");
  });

  it("neither text nor audio_ref → 422 VALIDATION_ERROR", async () => {
    const r = await post({ channel: "C2" });
    expect(r.status).toBe(422);
    expect(r.json.error!.code).toBe("VALIDATION_ERROR");
  });

  it("both text and audio_ref → 422 VALIDATION_ERROR (exactly one)", async () => {
    const r = await post({ text: "x", audio_ref: "obj/x.webm", channel: "C2" });
    expect(r.status).toBe(422);
    expect(r.json.error!.code).toBe("VALIDATION_ERROR");
  });

  it("missing Idempotency-Key → 400 BAD_REQUEST", async () => {
    const r = await post({ text: "x", channel: "C2" }, CEO, {});
    expect(r.status).toBe(400);
    expect(r.json.error!.code).toBe("BAD_REQUEST");
  });

  it("a principal without idp:write → 403 FORBIDDEN_ROLE", async () => {
    const r = await post({ text: "x", channel: "C2" }, NO_WRITE);
    expect(r.status).toBe(403);
  });
});
