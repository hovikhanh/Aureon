/** T-717F — pure C2 short-voice state logic (mirrors camera.test.ts). */
import { describe, expect, it } from "vitest";
import {
  MAX_VOICE_SECONDS,
  voiceErrorKey,
  voiceErrorKind,
  voiceSupported,
  withinLimit,
} from "./voice";

const navWith = (gum: unknown): Navigator =>
  ({ mediaDevices: { getUserMedia: gum } }) as unknown as Navigator;
const Recorder = function () {} as unknown;

describe("voiceSupported", () => {
  it("needs a secure context + getUserMedia + MediaRecorder", () => {
    expect(voiceSupported(navWith(() => {}), true, Recorder)).toBe(true);
    expect(voiceSupported(navWith(() => {}), false, Recorder)).toBe(false); // insecure
    expect(voiceSupported(navWith(undefined), true, Recorder)).toBe(false); // no gUM
    expect(voiceSupported(navWith(() => {}), true, undefined)).toBe(false); // no recorder
    expect(voiceSupported(undefined, true, Recorder)).toBe(false);
  });
});

describe("voiceErrorKind", () => {
  it("maps DOMException names to stable kinds", () => {
    expect(voiceErrorKind({ name: "NotAllowedError" })).toBe("denied");
    expect(voiceErrorKind({ name: "SecurityError" })).toBe("denied");
    expect(voiceErrorKind({ name: "NotFoundError" })).toBe("not_found");
    expect(voiceErrorKind({ name: "NotReadableError" })).toBe("in_use");
    expect(voiceErrorKind({ name: "Whatever" })).toBe("unknown");
    expect(voiceErrorKind("boom")).toBe("unknown");
  });
  it("builds the i18n key", () => {
    expect(voiceErrorKey("denied")).toBe("meetings.voice.error.denied");
  });
});

describe("withinLimit", () => {
  it("accepts 1..MAX, rejects 0 and over-limit", () => {
    expect(withinLimit(1)).toBe(true);
    expect(withinLimit(MAX_VOICE_SECONDS)).toBe(true);
    expect(withinLimit(0)).toBe(false);
    expect(withinLimit(MAX_VOICE_SECONDS + 1)).toBe(false);
  });
});
