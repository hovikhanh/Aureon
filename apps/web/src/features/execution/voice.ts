/**
 * C2 "nói để nhập liệu ngắn" (short voice note) — pure, node-testable logic, no DOM/React.
 *
 * The UI (VoiceCapture.tsx) uses `getUserMedia({audio})` + `MediaRecorder` to record a SHORT
 * note, then sends it to EP-DC-38 for STT (R-DEC-97, fixture-only at P0 — raw audio is never
 * stored or persisted to localStorage). This is NOT meeting recording: meeting audio capture is
 * blocked (R-DEC-22) — picking a `meeting` context yields a 422 `meeting_audio_blocked`.
 * Mirrors `features/capture/camera.ts` (support detection, stable error kinds, limits).
 */

/** Max note length — keeps C2 voice to short utterances, not meetings. */
export const MAX_VOICE_SECONDS = 60;
export const VOICE_MIME = "audio/webm";

export type VoiceState = "idle" | "starting" | "recording" | "review" | "error";

export type VoiceErrorKind =
  | "unsupported" // no getUserMedia / MediaRecorder, or insecure context
  | "denied" // user refused the mic permission
  | "not_found" // no microphone device
  | "in_use" // device busy / hardware error
  | "too_long" // exceeded MAX_VOICE_SECONDS
  | "unknown";

/** Recording needs a secure context AND getUserMedia AND MediaRecorder. */
export function voiceSupported(
  nav: Navigator | undefined,
  isSecureContext: boolean,
  recorder: unknown,
): boolean {
  if (!nav || !isSecureContext) return false;
  const md = (nav as Navigator & { mediaDevices?: MediaDevices }).mediaDevices;
  return Boolean(md && typeof md.getUserMedia === "function" && typeof recorder === "function");
}

/** Map a getUserMedia DOMException (or any thrown value) to a stable UI error kind. */
export function voiceErrorKind(err: unknown): VoiceErrorKind {
  const name = err && typeof err === "object" && "name" in err ? String((err as { name: unknown }).name) : "";
  switch (name) {
    case "NotAllowedError":
    case "SecurityError":
      return "denied";
    case "NotFoundError":
    case "OverconstrainedError":
      return "not_found";
    case "NotReadableError":
    case "AbortError":
      return "in_use";
    default:
      return "unknown";
  }
}

export const voiceErrorKey = (kind: VoiceErrorKind): string => `meetings.voice.error.${kind}`;

export const VOICE_CONSTRAINTS: MediaStreamConstraints = { audio: true, video: false };

/** True when a recording of `seconds` is within the short-note limit. */
export function withinLimit(seconds: number): boolean {
  return seconds > 0 && seconds <= MAX_VOICE_SECONDS;
}

/** Stop every track of a live stream (release the mic). Null-safe for teardown/tests. */
export function stopStream(stream: MediaStream | null | undefined): void {
  stream?.getTracks().forEach((t) => t.stop());
}
