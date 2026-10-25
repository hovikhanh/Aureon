"use client";
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api-client";
import { captureError } from "./errors";

/** "Báo sự cố" (EP-DC-36, R-DEC-69): critical-field incident on a committed document — `idp:approve` only. */
export function IncidentDialog({ documentId, onClose }: { documentId: string | null; onClose: () => void }) {
  const t = useTranslations();
  const toast = useToast();
  const client = useQueryClient();
  const [field, setField] = React.useState("");
  const [desc, setDesc] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!field.trim() || !desc.trim()) return setError(t("capture.errors.required"));
    setBusy(true);
    try {
      await api.post("/data-capture/incidents", { source_document_id: documentId, field_name: field.trim(), description: desc.trim() });
      toast.push(t("capture.admin.incident.reported_ok"));
      void client.invalidateQueries({ queryKey: ["capture", "incidents"] });
      setField(""); setDesc(""); setError(null);
      onClose();
    } catch (err) {
      setError(captureError(t, err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open={Boolean(documentId)} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="incident-dialog">
        <DialogTitle>{t("capture.admin.incident.report")}</DialogTitle>
        <form className="flex flex-col gap-3" onSubmit={(e) => void submit(e)}>
          <Label className="flex flex-col gap-1">{t("capture.admin.incident.fieldName")}
            <Input value={field} onChange={(e) => setField(e.target.value)} maxLength={100} data-testid="incident-field" />
          </Label>
          <Label className="flex flex-col gap-1">{t("capture.admin.incident.description")}
            <textarea className="min-h-20 rounded-md border bg-card px-3 py-2 text-sm" value={desc} onChange={(e) => setDesc(e.target.value)} maxLength={1000} data-testid="incident-desc" />
          </Label>
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>{t("buttons.cancel")}</Button>
            <Button type="submit" disabled={busy} data-testid="incident-send">{t("capture.admin.incident.send")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
