/**
 * Pure C4 "Chụp ảnh" (photo capture) logic — node-testable, no DOM/React.
 *
 * The camera UI (CameraCapture.tsx) uses `getUserMedia` to open the device camera, draws a frame
 * to a canvas and produces an image `File`. A confirmed photo is pushed into the DropZone's file
 * list and travels through the SAME `/idp/documents` upload + pipeline as any uploaded file (C4
 * flow = C3 flow, 04 §3). These helpers keep the capture rules (support detection, filename,
 * limits, permission/error mapping) independent of the browser so they can be unit-tested.
 */
import { MAX_FILE_BYTES } from "./logic";

/** Max photos per capture session — stays within the DropZone 100-file / 50-MB limits (FR-DC-01). */
export const MAX_PHOTOS = 20;
/** Captured frames are encoded as JPEG (broad support, small size for OCR). */
export const CAPTURE_MIME = "image/jpeg";
export const CAPTURE_EXT = "jpg";
/** JPEG quality for the canvas export (0–1). */
export const CAPTURE_QUALITY = 0.92;

export type CameraErrorKind =
  | "unsupported" // browser has no getUserMedia (or insecure context)
  | "denied" // user refused the permission
  | "not_found" // no camera device
  | "in_use" // device busy / hardware error
  | "unknown";

/**
 * True when the current browser can open a camera. Camera access needs a secure context
 * (HTTPS or localhost) AND `navigator.mediaDevices.getUserMedia` — a plain file picker does
 * not count as capture (task requirement).
 */
export function cameraSupported(nav: Navigator | undefined, isSecureContext: boolean): boolean {
  if (!nav || !isSecureContext) return false;
  const md = (nav as Navigator & { mediaDevices?: MediaDevices }).mediaDevices;
  return Boolean(md && typeof md.getUserMedia === "function");
}

/** Map a DOMException (or any thrown value) from `getUserMedia` to a stable UI error kind. */
export function cameraErrorKind(err: unknown): CameraErrorKind {
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

/** The i18n key under `capture.camera.error.*` for an error kind. */
export const cameraErrorKey = (kind: CameraErrorKind): string => `capture.camera.error.${kind}`;

/** A timestamped, collision-safe filename for a captured photo, e.g. `chup-anh-20261026-150312-1.jpg`. */
export function photoFilename(now: Date, index: number): string {
  const p = (n: number, w = 2) => String(n).padStart(w, "0");
  const stamp = `${now.getFullYear()}${p(now.getMonth() + 1)}${p(now.getDate())}-${p(now.getHours())}${p(now.getMinutes())}${p(now.getSeconds())}`;
  return `chup-anh-${stamp}-${index}.${CAPTURE_EXT}`;
}

/** Back-camera preference for mobile; desktop falls back automatically. */
export const CAPTURE_CONSTRAINTS: MediaStreamConstraints = {
  video: { facingMode: { ideal: "environment" }, width: { ideal: 1600 }, height: { ideal: 1200 } },
  audio: false,
};

export interface PhotoCheck {
  ok: boolean;
  issue: "too_many" | "too_large" | "empty" | null;
}

/**
 * Validate a captured blob before adding it to the upload list (same bounds as uploaded files,
 * FR-DC-01): within the per-session photo count, non-empty, ≤ 50 MB.
 */
export function checkPhoto(sizeBytes: number, existingCount: number): PhotoCheck {
  if (existingCount >= MAX_PHOTOS) return { ok: false, issue: "too_many" };
  if (sizeBytes === 0) return { ok: false, issue: "empty" };
  if (sizeBytes > MAX_FILE_BYTES) return { ok: false, issue: "too_large" };
  return { ok: true, issue: null };
}

/** Wrap a captured blob as an image `File` with a timestamped name (channel decided server-side). */
export function blobToPhotoFile(blob: Blob, now: Date, index: number): File {
  return new File([blob], photoFilename(now, index), { type: CAPTURE_MIME, lastModified: now.getTime() });
}

/** Stop every track of a live stream (release the camera). Null-safe for teardown/tests. */
export function stopStream(stream: MediaStream | null | undefined): void {
  stream?.getTracks().forEach((t) => t.stop());
}
