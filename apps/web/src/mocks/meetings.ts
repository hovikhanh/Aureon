/**
 * Mock BFF for EP-DC-38 `POST /data-capture/natural-language` (C2, M2.3 R-DEC-96/97/22).
 *
 * Same envelope/errors as the real `NaturalLanguageService`: requires `idp:write` + an
 * Idempotency-Key; `context==="meeting"` → 422 `meeting_audio_blocked` (R-DEC-22); exactly one of
 * `text`/`audio_ref` (else 422). Returns a NOT-committed `NaturalLanguagePreviewOut` with a
 * MEETING_MINUTES classification + predicted `ACT-create_action_item` steps carrying the fuzzy
 * owner match status (R-DEC-103). `audio_ref` returns a canned transcript-derived preview (STT is
 * fixture-only at P0 — no real audio in the mock).
 */
import { ok } from "./http";
import type { MockRequest, Route } from "./router";
import { body, err, requireIdem } from "./capture-out";
import { newCaptureId, nowIso } from "./capture-store";

const W = "idp:write";

/** Predicted action items of the canned UC-02 transcript — mixed owner match status. */
const PREDICTED = [
  { title: "Chốt báo giá khách ABC trước thứ Sáu", owner_name: "Nguyễn Văn An", owner_match_status: "matched", due_date: "2026-11-06" },
  { title: "Rà soát tồn kho quý 4", owner_name: "Trần B.", owner_match_status: "ambiguous", due_date: null },
  { title: "Gửi hợp đồng bảo trì cho đối tác", owner_name: "chưa rõ", owner_match_status: "unmatched", due_date: null },
];

const EXTRACTED = [
  { field: "meeting_title", value: "Họp giao ban tuần", confidence: 0.94 },
  { field: "held_at", value: "2026-10-30", confidence: 0.91 },
  { field: "decision_count", value: 3, confidence: 0.88 },
];

const CANNED_TRANSCRIPT = "Biên bản họp giao ban: chốt báo giá khách ABC, rà soát tồn kho, gửi hợp đồng bảo trì.";

function naturalLanguage(req: MockRequest): Response {
  requireIdem(req);
  const b = body(req);
  if (b.context === "meeting") {
    throw err(422, "BUSINESS_RULE_VIOLATION", "meeting audio is not an IDP capture", { reason: "meeting_audio_blocked" });
  }
  const hasText = typeof b.text === "string" && b.text.trim().length > 0;
  const hasAudio = typeof b.audio_ref === "string" && b.audio_ref.trim().length > 0;
  if (hasText === hasAudio) {
    throw err(422, "VALIDATION_ERROR", "exactly one of text / audio_ref must be set", { field: "text" });
  }
  const id = newCaptureId("document");
  const confidence = 0.92;
  // C2 produces a virtual TRANSCRIPT document (no stored file); minimal DocumentOut for the preview.
  const now = nowIso();
  const document = {
    id, version: 1, channel: "C2", kind: "FILE", original_filename: null, mime_type: "text/plain",
    size_bytes: 0, page_count: 1, status: "NEEDS_REVIEW", status_reason: null, scan_status: "CLEAN",
    pillars: [] as string[], sensitivity_level: 2, submitted_at: now, document_type: "MEETING_MINUTES",
    committed_at: null, undo_deadline: null, can_undo: false, rolled_back_at: null,
  };
  // audio_ref path: STT fixture → the canned transcript (raw audio is never stored).
  const transcript = hasAudio ? CANNED_TRANSCRIPT : String(b.text);
  void transcript;
  return ok({
    document,
    document_type: { code: "MEETING_MINUTES", confidence },
    status: "NEEDS_REVIEW",
    predicted_actions: PREDICTED.map((p) => ({
      action_name: "ACT-create_action_item",
      params: { title: p.title, owner_name: p.owner_name, owner_match_status: p.owner_match_status, due_date: p.due_date },
      confidence,
    })),
    extracted: EXTRACTED,
  }, 201);
}

export const MEETINGS_ROUTES: readonly Route[] = [
  { method: "POST", pattern: "/data-capture/natural-language", permission: W, handler: naturalLanguage },
];
