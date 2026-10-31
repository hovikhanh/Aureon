/** C4 camera-capture pure logic (node-testable): support detection, error mapping, filename,
 *  per-session photo checks, blob→File. Pairs with CameraCapture.tsx (DOM) covered by e2e. */
import { describe, expect, it } from "vitest";
import { MAX_FILE_BYTES } from "./logic";
import {
  CAPTURE_MIME,
  MAX_PHOTOS,
  blobToPhotoFile,
  cameraErrorKey,
  cameraErrorKind,
  cameraSupported,
  checkPhoto,
  photoFilename,
} from "./camera";

describe("cameraSupported", () => {
  it("needs a secure context AND getUserMedia", () => {
    const withMedia = { mediaDevices: { getUserMedia: () => undefined } } as unknown as Navigator;
    const noMedia = {} as Navigator;
    expect(cameraSupported(withMedia, true)).toBe(true);
    expect(cameraSupported(withMedia, false)).toBe(false); // insecure context (plain http)
    expect(cameraSupported(noMedia, true)).toBe(false); // no mediaDevices
    expect(cameraSupported(undefined, true)).toBe(false);
  });
});

describe("cameraErrorKind / key", () => {
  it("maps DOMException names to stable kinds", () => {
    expect(cameraErrorKind({ name: "NotAllowedError" })).toBe("denied");
    expect(cameraErrorKind({ name: "SecurityError" })).toBe("denied");
    expect(cameraErrorKind({ name: "NotFoundError" })).toBe("not_found");
    expect(cameraErrorKind({ name: "OverconstrainedError" })).toBe("not_found");
    expect(cameraErrorKind({ name: "NotReadableError" })).toBe("in_use");
    expect(cameraErrorKind({ name: "AbortError" })).toBe("in_use");
    expect(cameraErrorKind({ name: "WeirdError" })).toBe("unknown");
    expect(cameraErrorKind("boom")).toBe("unknown");
    expect(cameraErrorKind(null)).toBe("unknown");
  });
  it("prefixes the i18n key", () => {
    expect(cameraErrorKey("denied")).toBe("capture.camera.error.denied");
    expect(cameraErrorKey("unsupported")).toBe("capture.camera.error.unsupported");
  });
});

describe("photoFilename", () => {
  it("is timestamped, indexed and jpg", () => {
    const d = new Date(2026, 9, 26, 15, 3, 12); // 2026-10-26 15:03:12 (month is 0-based)
    expect(photoFilename(d, 1)).toBe("chup-anh-20261026-150312-1.jpg");
    expect(photoFilename(d, 2)).toBe("chup-anh-20261026-150312-2.jpg");
  });
});

describe("checkPhoto (FR-DC-01 bounds)", () => {
  it("rejects over the per-session count", () => {
    expect(checkPhoto(100, MAX_PHOTOS).issue).toBe("too_many");
    expect(checkPhoto(100, MAX_PHOTOS - 1).ok).toBe(true);
  });
  it("rejects empty and over-size blobs", () => {
    expect(checkPhoto(0, 0).issue).toBe("empty");
    expect(checkPhoto(MAX_FILE_BYTES + 1, 0).issue).toBe("too_large");
    expect(checkPhoto(MAX_FILE_BYTES, 0).ok).toBe(true);
  });
});

describe("blobToPhotoFile", () => {
  it("wraps a blob as an image File with a timestamped name", () => {
    const blob = new Blob([new Uint8Array([1, 2, 3])], { type: CAPTURE_MIME });
    const d = new Date(2026, 9, 26, 15, 3, 12);
    const file = blobToPhotoFile(blob, d, 3);
    expect(file).toBeInstanceOf(File);
    expect(file.type).toBe(CAPTURE_MIME);
    expect(file.name).toBe("chup-anh-20261026-150312-3.jpg");
    expect(file.size).toBe(3);
  });
});
