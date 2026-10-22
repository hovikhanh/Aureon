"use client";
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { buildUrl, newIdempotencyKey, toApiError } from "@/lib/api-client";

/** EP-20 multipart upload (C3) through the BFF proxy. */
export function UploadButton() {
  const t = useTranslations();
  const toast = useToast();
  const client = useQueryClient();
  const ref = React.useRef<HTMLInputElement>(null);
  const [busy, setBusy] = React.useState(false);
  const onFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));
    setBusy(true);
    try {
      const res = await fetch(buildUrl("/idp/documents"), { method: "POST", body: form, headers: { "idempotency-key": newIdempotencyKey() } });
      if (!res.ok) throw await toApiError(res);
      toast.push(t("idp.status.UPLOADED"), "info");
      void client.invalidateQueries({ queryKey: ["idp", "review-queue"] });
    } catch {
      toast.push(t("errors.generic"), "danger");
    } finally {
      setBusy(false);
      if (ref.current) ref.current.value = "";
    }
  };
  return (
    <>
      <input ref={ref} type="file" multiple hidden accept=".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.csv,.docx" onChange={(e) => void onFiles(e.target.files)} data-testid="upload-input" />
      <Button onClick={() => ref.current?.click()} disabled={busy} data-testid="upload-button">
        <Upload className="h-4 w-4" aria-hidden />{t("buttons.upload")}
      </Button>
    </>
  );
}
