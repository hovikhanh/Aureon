"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Mic, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  VOICE_CONSTRAINTS,
  VOICE_MIME,
  type VoiceErrorKind,
  type VoiceState,
  stopStream,
  voiceErrorKind,
  voiceSupported,
} from "./voice";

/**
 * C2 short voice note (SCR-28/44, R-DEC-97): records a SHORT utterance via MediaRecorder, then
 * sends an object-key reference to EP-DC-38 for STT (fixture-only at P0). Raw audio stays in memory
 * only — never persisted to localStorage, never uploaded as a stored asset here. This is NOT
 * meeting recording (R-DEC-22): meeting audio is blocked upstream.
 */
export function VoiceCapture({ onTranscribe, disabled }: { onTranscribe: (audioRef: string) => void; disabled?: boolean }) {
  const t = useTranslations("meetings.voice");
  const [state, setState] = React.useState<VoiceState>("idle");
  const [error, setError] = React.useState<VoiceErrorKind | null>(null);
  const recorderRef = React.useRef<MediaRecorder | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);

  // Decided after mount: the server has no `window`, so computing it during render made the SSR
  // HTML ("unsupported") differ from the first client render (button) → React #418 (M6).
  const [supported, setSupported] = React.useState<boolean | null>(null);
  React.useEffect(() => {
    setSupported(voiceSupported(navigator, window.isSecureContext, (window as unknown as { MediaRecorder?: unknown }).MediaRecorder));
  }, []);

  const start = async () => {
    setError(null);
    setState("starting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia(VOICE_CONSTRAINTS);
      streamRef.current = stream;
      const rec = new MediaRecorder(stream, { mimeType: VOICE_MIME });
      recorderRef.current = rec;
      rec.start();
      setState("recording");
    } catch (e) {
      setError(voiceErrorKind(e));
      setState("error");
      stopStream(streamRef.current);
      streamRef.current = null;
    }
  };

  const stop = () => {
    recorderRef.current?.stop();
    stopStream(streamRef.current);
    streamRef.current = null;
    recorderRef.current = null;
    setState("idle");
    // Raw audio is never stored; the backend STT works from an object reference (R-DEC-97).
    onTranscribe(`voice-note/${Date.now()}.webm`);
  };

  if (supported === null) return null; // same (empty) markup on the server and the first client render
  if (!supported) {
    return (
      <span className="text-xs text-muted-foreground" data-testid="voice-unsupported">
        {t("error.unsupported")}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-2">
      {state === "recording" ? (
        <Button type="button" variant="danger" size="sm" onClick={stop} data-testid="voice-stop">
          <Square className="h-4 w-4" aria-hidden />
          {t("stop")}
        </Button>
      ) : (
        <Button type="button" variant="outline" size="sm" onClick={() => void start()} disabled={disabled || state === "starting"} data-testid="voice-start">
          <Mic className="h-4 w-4" aria-hidden />
          {t("start")}
        </Button>
      )}
      {error && (
        <span className="text-xs text-danger" role="alert" data-testid="voice-error">
          {t(`error.${error}`)}
        </span>
      )}
    </span>
  );
}
