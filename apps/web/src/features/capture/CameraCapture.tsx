"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Camera, Check, RotateCcw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import {
  CAPTURE_CONSTRAINTS,
  CAPTURE_MIME,
  CAPTURE_QUALITY,
  type CameraErrorKind,
  blobToPhotoFile,
  cameraErrorKey,
  cameraErrorKind,
  cameraSupported,
  checkPhoto,
  stopStream,
} from "./camera";

/**
 * C4 "Chụp ảnh" (SCR-45, 04 §4 C4): opens the device camera via `getUserMedia`, shows a live
 * `<video>` preview, captures a frame to a canvas and returns image `File`s to the DropZone.
 * Those files then go through the SAME `/idp/documents` upload + IDP pipeline as any upload.
 *
 * States: `idle` → `starting` → `live` (preview) → `review` (per-shot confirm). Errors are
 * surfaced as a stable kind (unsupported / denied / not_found / in_use / unknown) with an i18n
 * message; the already-captured shots are never dropped on a recoverable error. Camera access
 * requires a secure context (HTTPS / localhost) — otherwise we show the `unsupported` state and
 * never pretend a file picker is a camera.
 */
export function CameraCapture({ onConfirm, disabled }: { onConfirm: (files: File[]) => void; disabled?: boolean }) {
  const t = useTranslations();
  const [open, setOpen] = React.useState(false);
  const [phase, setPhase] = React.useState<"starting" | "live" | "review">("starting");
  const [error, setError] = React.useState<CameraErrorKind | null>(null);
  const [shots, setShots] = React.useState<{ url: string; file: File }[]>([]);
  const [pending, setPending] = React.useState<{ url: string; blob: Blob } | null>(null);
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const streamRef = React.useRef<MediaStream | null>(null);

  const supported = typeof navigator !== "undefined" && cameraSupported(navigator, typeof window !== "undefined" && window.isSecureContext);

  const teardown = React.useCallback(() => {
    stopStream(streamRef.current);
    streamRef.current = null;
  }, []);

  const start = React.useCallback(async () => {
    setError(null);
    setPhase("starting");
    if (!supported) {
      setError("unsupported");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia(CAPTURE_CONSTRAINTS);
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => undefined);
      }
      setPhase("live");
    } catch (e) {
      setError(cameraErrorKind(e));
    }
  }, [supported]);

  // Open → start the camera; close → release it and reset transient state (keep nothing dangling).
  React.useEffect(() => {
    if (open) void start();
    return () => {
      teardown();
    };
  }, [open, start, teardown]);

  const reset = React.useCallback(() => {
    teardown();
    shots.forEach((s) => URL.revokeObjectURL(s.url));
    if (pending) URL.revokeObjectURL(pending.url);
    setShots([]);
    setPending(null);
    setError(null);
    setPhase("starting");
  }, [teardown, shots, pending]);

  const close = () => {
    setOpen(false);
    reset();
  };

  const snap = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const check = checkPhoto(blob.size, shots.length);
        if (!check.ok) {
          setError(check.issue === "too_many" ? "unknown" : "unknown");
          return;
        }
        setPending({ url: URL.createObjectURL(blob), blob });
        setPhase("review");
      },
      CAPTURE_MIME,
      CAPTURE_QUALITY,
    );
  };

  const keep = () => {
    if (!pending) return;
    const file = blobToPhotoFile(pending.blob, new Date(), shots.length + 1);
    setShots((xs) => [...xs, { url: pending.url, file }]);
    setPending(null);
    setPhase("live");
  };

  const retake = () => {
    if (pending) URL.revokeObjectURL(pending.url);
    setPending(null);
    setPhase("live");
  };

  const confirmAll = () => {
    onConfirm(shots.map((s) => s.file));
    // ownership of the object URLs passes to the DropZone preview list; just close.
    setOpen(false);
    teardown();
    setShots([]);
    setPending(null);
    setPhase("starting");
  };

  const errorMsg = error ? t(cameraErrorKey(error)) : null;

  return (
    <Dialog open={open} onOpenChange={(o) => (o ? setOpen(true) : close())}>
      <Button type="button" variant="outline" size="sm" onClick={() => setOpen(true)} disabled={disabled} data-testid="camera-open">
        <Camera className="h-4 w-4" aria-hidden />
        {t("capture.camera.open")}
      </Button>
      <DialogContent className="max-w-lg" data-testid="camera-dialog">
        <DialogTitle>{t("capture.camera.title")}</DialogTitle>
        <DialogDescription>{t("capture.camera.hint")}</DialogDescription>

        <div className="mt-3 flex flex-col gap-3">
          {error ? (
            <div className="rounded-md border border-danger bg-danger-subtle p-4 text-sm text-danger" role="alert" data-testid="camera-error">
              <p className="font-medium">{errorMsg}</p>
              {error !== "unsupported" && (
                <Button type="button" variant="outline" size="sm" className="mt-2" onClick={() => void start()} data-testid="camera-retry">
                  {t("capture.camera.retry")}
                </Button>
              )}
            </div>
          ) : (
            <div className="relative overflow-hidden rounded-lg bg-black">
              {/* Keep the <video> mounted across live/review so the stream is not re-requested. */}
              <video
                ref={videoRef}
                playsInline
                muted
                className={`aspect-video w-full object-cover ${phase === "review" ? "hidden" : ""}`}
                data-testid="camera-video"
                aria-label={t("capture.camera.preview")}
              />
              {phase === "review" && pending && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={pending.url} alt={t("capture.camera.shotPreview")} className="aspect-video w-full object-contain" data-testid="camera-shot" />
              )}
              {phase === "starting" && <div className="absolute inset-0 grid place-items-center text-sm text-white/80">{t("capture.camera.starting")}</div>}
            </div>
          )}

          {!error && phase === "live" && (
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm text-muted-foreground" data-testid="camera-count">
                {t("capture.camera.taken", { count: shots.length })}
              </span>
              <Button type="button" onClick={snap} data-testid="camera-snap">
                <Camera className="h-4 w-4" aria-hidden />
                {t("capture.camera.snap")}
              </Button>
            </div>
          )}

          {!error && phase === "review" && (
            <div className="flex items-center justify-end gap-2">
              <Button type="button" variant="outline" onClick={retake} data-testid="camera-retake">
                <RotateCcw className="h-4 w-4" aria-hidden />
                {t("capture.camera.retake")}
              </Button>
              <Button type="button" variant="success" onClick={keep} data-testid="camera-keep">
                <Check className="h-4 w-4" aria-hidden />
                {t("capture.camera.keep")}
              </Button>
            </div>
          )}

          {shots.length > 0 && (
            <ul className="flex flex-wrap gap-2" data-testid="camera-thumbs">
              {shots.map((s, i) => (
                <li key={s.url} className="relative">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={s.url} alt={t("capture.camera.thumb", { n: i + 1 })} className="h-16 w-16 rounded border object-cover" />
                  <button
                    type="button"
                    aria-label={t("capture.camera.removeShot", { n: i + 1 })}
                    className="absolute -right-1 -top-1 rounded-full bg-danger p-0.5 text-white"
                    onClick={() => {
                      URL.revokeObjectURL(s.url);
                      setShots((xs) => xs.filter((_, j) => j !== i));
                    }}
                  >
                    <X className="h-3 w-3" aria-hidden />
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="flex items-center justify-end gap-2 border-t pt-3">
            <DialogClose asChild>
              <Button type="button" variant="ghost" data-testid="camera-cancel">
                {t("capture.camera.cancel")}
              </Button>
            </DialogClose>
            <Button type="button" onClick={confirmAll} disabled={shots.length === 0} data-testid="camera-confirm">
              {t("capture.camera.confirm", { count: shots.length })}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
