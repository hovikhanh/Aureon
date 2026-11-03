"use client";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { MetricDetailContent } from "./MetricDetailContent";

/** SCR-12 metric drill-down as the P01 dialog (06): the body lives in `MetricDetailContent`. */
export function MetricDetailPanel({ code, onClose }: { code: string | null; onClose: () => void }) {
  return (
    <Dialog open={Boolean(code)} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-2xl" data-testid="metric-detail-panel" data-code={code ?? undefined}>
        {/* keyed by code so the lineage toggle resets when another metric opens */}
        <MetricDetailContent key={code ?? ""} code={code} Title={DialogTitle} Desc={DialogDescription} />
      </DialogContent>
    </Dialog>
  );
}
