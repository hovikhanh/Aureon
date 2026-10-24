"use client";
import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api-client";
import { captureError } from "../errors";
import type { DocumentType } from "../types";
import { useDocTypes } from "../use-capture";

/** EP-DC-27 list (incl. inactive) + EP-DC-28 edit (names, active, classifier keywords; `version`). */
export function TypesTab() {
  const t = useTranslations("capture.admin.type");
  const q = useDocTypes(true);
  const [edit, setEdit] = React.useState<DocumentType | null>(null);
  if (q.isPending) return <div className="h-40 animate-pulse rounded bg-muted" />;
  return (
    <>
      <table className="w-full rounded-lg border bg-card text-sm" data-testid="types-table">
        <thead><tr className="border-b text-left text-muted-foreground">
          {(["code", "nameVi", "nameEn", "channels", "schema", "active"] as const).map((c) => <th key={c} className="px-3 py-2 font-medium">{t(c)}</th>)}<th />
        </tr></thead>
        <tbody>
          {(q.data ?? []).map((d) => (
            <tr key={d.id} className="border-b last:border-0" data-testid="type-row" data-code={d.code}>
              <td className="px-3 py-2 font-mono">{d.code}</td>
              <td className="px-3">{d.name_vi}</td>
              <td className="px-3">{d.name_en}</td>
              <td className="px-3">{d.channels_supported.join(", ")}</td>
              <td className="px-3 tabular-nums">{d.current_schema_version ? `v${d.current_schema_version}` : "—"}</td>
              <td className="px-3">{d.is_active ? "✓" : "—"}</td>
              <td className="px-3 text-right"><Button size="sm" variant="ghost" onClick={() => setEdit(d)} data-testid="type-edit">{t("edit")}</Button></td>
            </tr>
          ))}
        </tbody>
      </table>
      {edit && <TypeDialog type={edit} onClose={() => setEdit(null)} />}
    </>
  );
}

function TypeDialog({ type, onClose }: { type: DocumentType; onClose: () => void }) {
  const t = useTranslations();
  const toast = useToast();
  const client = useQueryClient();
  const [v, setV] = React.useState({ name_vi: type.name_vi, name_en: type.name_en, is_active: type.is_active, keywords: "" });
  const [error, setError] = React.useState<string | null>(null);
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const kw = v.keywords.split(",").map((x) => x.trim()).filter(Boolean);
      await api.patch(`/data-capture/document-types/${type.id}`, { name_vi: v.name_vi, name_en: v.name_en, is_active: v.is_active, ...(kw.length ? { classifier_keywords: kw } : {}), version: type.version });
      toast.push(t("capture.admin.type.saved"));
      void client.invalidateQueries({ queryKey: ["capture", "document-types"] });
      onClose();
    } catch (err) {
      setError(captureError(t, err));
    }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="type-dialog">
        <DialogTitle>{type.code}</DialogTitle>
        <form className="flex flex-col gap-3" onSubmit={(e) => void save(e)}>
          <Label className="flex flex-col gap-1">{t("capture.admin.type.nameVi")}<Input value={v.name_vi} onChange={(e) => setV({ ...v, name_vi: e.target.value })} required /></Label>
          <Label className="flex flex-col gap-1">{t("capture.admin.type.nameEn")}<Input value={v.name_en} onChange={(e) => setV({ ...v, name_en: e.target.value })} required /></Label>
          <Label className="flex flex-col gap-1">{t("capture.admin.type.keywords")}<Input value={v.keywords} onChange={(e) => setV({ ...v, keywords: e.target.value })} /></Label>
          <label className="flex items-center gap-2 text-sm"><Checkbox checked={v.is_active} onCheckedChange={(c) => setV({ ...v, is_active: c === true })} data-testid="type-active" />{t("capture.admin.type.active")}</label>
          {error && <p role="alert" className="text-sm text-danger">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>{t("buttons.cancel")}</Button>
            <Button type="submit" data-testid="type-save">{t("capture.admin.type.save")}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
