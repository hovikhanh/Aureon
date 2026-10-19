"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Camera, CameraOff, Loader2, Trash2, WifiOff } from "lucide-react";
import { useTranslations } from "next-intl";
import { blurScoreFromContext, isTooBlurry } from "./c4-image";

export interface CapturedPage {
  id: string;
  dataUrl: string;
  blob: Blob;
  /** Variance-of-Laplacian sharpness; lower = blurrier (IDP-E05, client-side). */
  blurScore: number;
  /** True when the client flags this photo for re-capture (IDP-E05). */
  isBlurry: boolean;
}

export interface CameraCaptureC4Props {
  /** Submit all captured pages (channel C4). The parent uploads via EP-20. */
  onSubmit: (pages: CapturedPage[]) => void;
  isSubmitting: boolean;
}

/**
 * SCR-08 C4 — PWA mobile camera capture (06 §4.2, FR-DC-04, US-DC-004, T-222).
 * Uses the native getUserMedia + <canvas> APIs only (no extra dependency): open the rear
 * camera, capture several page photos, review/remove them, then submit. Each captured frame
 * becomes a JPEG page; the parent merges them into one multi-page PDF (FR-DC-04) and uploads
 * it with channel=C4. An offline banner warns when the network is unavailable.
 *
 * Blur scoring runs on the client (IDP-E05, variance-of-Laplacian in c4-image.ts, no image
 * library); blurry pages are flagged with a "chụp lại" warning (DEC-123 hướng A). Advanced
 * auto crop/deskew is intentionally left for a later iteration.
 */
export function CameraCaptureC4({ onSubmit, isSubmitting }: CameraCaptureC4Props) {
  const t = useTranslations("upload.c4");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pages, setPages] = useState<CapturedPage[]>([]);
  const [online, setOnline] = useState(true);

  const supported =
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices &&
    typeof navigator.mediaDevices.getUserMedia === "function";

  useEffect(() => {
    if (typeof navigator !== "undefined") setOnline(navigator.onLine);
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setActive(false);
  }, []);

  // Always release the camera when unmounting.
  useEffect(() => () => stopStream(), [stopStream]);

  const startCamera = useCallback(async () => {
    setError(null);
    if (!supported) {
      setError(t("notSupported"));
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => undefined);
      }
      setActive(true);
    } catch {
      setError(t("cameraError"));
      setActive(false);
    }
  }, [supported, t]);

  const capture = useCallback(() => {
    const video = videoRef.current;
    if (!video || !active) return;
    const w = video.videoWidth || 1280;
    const h = video.videoHeight || 720;
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, w, h);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
    // IDP-E05: score sharpness on the client; flag blurry frames for re-capture.
    let blurScore = 0;
    try {
      blurScore = blurScoreFromContext(ctx, w, h);
    } catch {
      blurScore = 0;
    }
    const blurry = isTooBlurry(blurScore);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        setPages((prev) => [
          ...prev,
          { id: `${Date.now()}-${prev.length}`, dataUrl, blob, blurScore, isBlurry: blurry },
        ]);
      },
      "image/jpeg",
      0.9,
    );
  }, [active]);

  const removePage = useCallback((id: string) => {
    setPages((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const blurryCount = pages.filter((p) => p.isBlurry).length;

  if (!supported) {
    return (
      <div className="flex min-h-[200px] flex-col items-center justify-center gap-2 text-center">
        <CameraOff className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">{t("notSupported")}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4" data-testid="camera-c4">
      <div>
        <h3 className="text-base font-semibold text-foreground">{t("title")}</h3>
        <p className="mt-0.5 text-sm text-muted-foreground">{t("subtitle")}</p>
      </div>

      {!online && (
        <div
          role="status"
          className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300"
        >
          <WifiOff className="h-4 w-4 shrink-0" aria-hidden="true" />
          {t("offline")}
        </div>
      )}

      {error && (
        <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
          {error}
        </div>
      )}

      {/* Camera viewport */}
      <div className="relative overflow-hidden rounded-xl border border-border bg-black/90">
        <video
          ref={videoRef}
          playsInline
          muted
          aria-label={t("title")}
          className="mx-auto block max-h-[52vh] w-full object-contain"
        />
        {!active && (
          <div className="absolute inset-0 flex items-center justify-center">
            <button
              type="button"
              onClick={startCamera}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <Camera className="h-4 w-4" aria-hidden="true" />
              {t("start")}
            </button>
          </div>
        )}
      </div>

      {/* Controls */}
      {active && (
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={capture}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <Camera className="h-4 w-4" aria-hidden="true" />
            {t("capture")}
          </button>
          <button
            type="button"
            onClick={stopStream}
            className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <CameraOff className="h-4 w-4" aria-hidden="true" />
            {t("stop")}
          </button>
        </div>
      )}

      {/* Captured pages */}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("pagesTitle", { count: pages.length })}
        </h4>
        {blurryCount > 0 && (
          <div
            role="status"
            className="mb-2 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300"
          >
            <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
            {t("blurWarning", { count: blurryCount })}
          </div>
        )}
        {pages.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("noPages")}</p>
        ) : (
          <ul className="grid grid-cols-3 gap-2 sm:grid-cols-4">
            {pages.map((p, i) => (
              <li key={p.id} className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={p.dataUrl}
                  alt={t("pageLabel", { n: i + 1 })}
                  className="aspect-[3/4] w-full rounded-md border border-border object-cover"
                />
                <span className="absolute left-1 top-1 rounded bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-white">
                  {i + 1}
                </span>
                {p.isBlurry && (
                  <span
                    className="absolute bottom-1 left-1 inline-flex items-center gap-0.5 rounded bg-amber-500/90 px-1 py-0.5 text-[10px] font-medium text-white"
                    aria-label={t("blurBadge")}
                  >
                    <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                    {t("blurBadge")}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => removePage(p.id)}
                  aria-label={t("remove")}
                  className="absolute right-1 top-1 rounded bg-black/60 p-1 text-white hover:bg-black/80"
                >
                  <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Submit */}
      <button
        type="button"
        disabled={pages.length === 0 || isSubmitting}
        onClick={() => onSubmit(pages)}
        className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
        {isSubmitting ? t("submitting") : t("submit", { count: pages.length })}
      </button>
    </div>
  );
}
