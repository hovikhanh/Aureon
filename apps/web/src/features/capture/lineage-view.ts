/**
 * LineageChip view model (EP-DC-26): `restricted` (out of scope — no ids, no file names leak),
 * `none` (record not written from a document), or the links grouped by source document, newest
 * commit first, revoked links last.
 */
import type { LineageLink, LineageOut } from "./types";

export type LineageView =
  | { kind: "restricted" }
  | { kind: "none" }
  | { kind: "links"; documents: { source_document_id: string; filename: string | null; document_type: string | null; links: LineageLink[]; revoked: boolean }[] };

export function lineageView(out: LineageOut | undefined | null): LineageView {
  if (!out) return { kind: "none" };
  if (out.restricted) return { kind: "restricted" };
  const links = out.links ?? [];
  if (!links.length) return { kind: "none" };
  const byDoc = new Map<string, LineageLink[]>();
  for (const l of links) byDoc.set(l.source_document_id, [...(byDoc.get(l.source_document_id) ?? []), l]);
  const documents = [...byDoc.entries()].map(([id, ls]) => ({
    source_document_id: id, filename: ls[0]!.original_filename, document_type: ls[0]!.document_type, links: ls,
    revoked: ls.every((l) => l.revoked_at !== null),
  }));
  const last = (d: (typeof documents)[number]) => d.links.map((l) => l.committed_at ?? "").sort().at(-1) ?? "";
  documents.sort((a, b) => Number(a.revoked) - Number(b.revoked) || last(b).localeCompare(last(a)));
  return { kind: "links", documents };
}

/** Where a link points inside its source: page, sheet + row, or nothing (manual entry). */
export function linkLocation(l: LineageLink): { page?: number; sheet?: string; row?: number } {
  return { ...(l.page_number !== null ? { page: l.page_number } : {}), ...(l.sheet_name ? { sheet: l.sheet_name } : {}), ...(l.row_index !== null ? { row: l.row_index } : {}) };
}
