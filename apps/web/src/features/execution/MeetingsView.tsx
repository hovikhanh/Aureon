"use client";
import * as React from "react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { useNaturalLanguage } from "./use-meetings";
import { PredictedActionList } from "./PredictedActionList";
import { VoiceCapture } from "./VoiceCapture";
import { visibleExtracted } from "./meetings";

/**
 * SCR-44 `/meetings` (M2.3): paste/upload a transcript OR dictate a short note → EP-DC-38 returns a
 * NOT-committed preview; the chair approves predicted action items (L2) to create tasks. Meeting
 * AUDIO recording is blocked (R-DEC-22) — voice here is for short C2 notes only.
 */
export function MeetingsView({ viewerId, permissions }: { viewerId: string; permissions: string[] }) {
  const t = useTranslations("meetings");
  const [text, setText] = React.useState("");
  const nl = useNaturalLanguage();
  const preview = nl.data;

  const submitText = () => {
    if (!text.trim()) return;
    nl.mutate({ text, channel: "C2" });
  };
  const submitAudio = (audioRef: string) => nl.mutate({ audio_ref: audioRef, channel: "C2" });

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4" data-testid="meetings-view">
      <header>
        <h1 className="text-xl font-semibold">{t("title")}</h1>
        <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
      </header>

      <Card>
        <CardHeader><CardTitle>{t("paste.title")}</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <label htmlFor="transcript" className="sr-only">{t("paste.label")}</label>
          <textarea
            id="transcript"
            data-testid="transcript-input"
            className="min-h-32 w-full rounded-md border bg-background p-3 text-sm"
            placeholder={t("paste.placeholder")}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex items-center gap-2">
            <Button data-testid="transcript-submit" disabled={!text.trim() || nl.isPending} onClick={submitText}>
              {t("paste.submit")}
            </Button>
            <VoiceCapture onTranscribe={submitAudio} disabled={nl.isPending} />
          </div>
          <p className="text-xs text-muted-foreground">{t("voice.notMeeting")}</p>
        </CardContent>
      </Card>

      {nl.isError && (
        <p role="alert" className="text-sm text-danger" data-testid="meetings-error">
          {nl.error instanceof ApiError && nl.error.code === "BUSINESS_RULE_VIOLATION"
            ? t("voice.error.meetingBlocked")
            : t("errorGeneric")}
        </p>
      )}

      {preview && (
        <section className="flex flex-col gap-4" data-testid="meetings-preview" aria-live="polite">
          <Card>
            <CardHeader>
              <CardTitle>
                {t("preview.docType")} · <span data-testid="preview-doctype">{preview.document_type.code}</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                {visibleExtracted(preview.extracted).map((f) => (
                  <React.Fragment key={f.field}>
                    <dt className="text-muted-foreground">{f.field}</dt>
                    <dd data-testid={`extracted-${f.field}`}>{String(f.value)}</dd>
                  </React.Fragment>
                ))}
              </dl>
            </CardContent>
          </Card>
          <PredictedActionList
            preview={preview}
            viewerId={viewerId}
            permissions={permissions}
          />
        </section>
      )}
    </div>
  );
}
