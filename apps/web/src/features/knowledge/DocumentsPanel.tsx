"use client";
/**
 * SCR-49 Documents panel (M3.4, R-DEC-142b, 03 §3.5): Knowledge/RAG search over the SOP/document
 * library (EP-24). A debounced query box drives `useDocumentSearch`; each hit shows the document
 * title, the matched page, a snippet, and a relevance score, with a link to the lineage page view.
 * Empty query → no request (hook `enabled`); no numbers are fabricated — results are page excerpts.
 */
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { FileText, Search } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useDocumentSearch } from "./use-knowledge";

export function DocumentsPanel() {
  const t = useTranslations("documents");
  const [term, setTerm] = useState("");
  const [q, setQ] = useState("");
  // Debounce the query 300ms so each keystroke does not fire EP-24.
  useEffect(() => {
    const id = setTimeout(() => setQ(term), 300);
    return () => clearTimeout(id);
  }, [term]);
  const search = useDocumentSearch(q);
  const hits = search.data?.data ?? [];

  return (
    <div className="flex flex-col gap-4" data-testid="documents-panel">
      <h2 className="text-lg font-semibold">{t("title")}</h2>
      <div className="relative max-w-xl">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          className="pl-9"
          value={term}
          placeholder={t("placeholder")}
          aria-label={t("placeholder")}
          data-testid="documents-search-input"
          onChange={(e) => setTerm(e.target.value)}
        />
      </div>

      {q.length === 0 && <p className="text-sm text-muted-foreground">{t("hint")}</p>}
      {search.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {search.isError && <p className="text-sm text-danger">{t("loadError")}</p>}
      {search.data && hits.length === 0 && q.length > 0 && (
        <p className="text-sm text-muted-foreground" data-testid="documents-empty">{t("empty")}</p>
      )}
      {hits.length > 0 && (
        <ul className="flex flex-col gap-2" data-testid="documents-results">
          {hits.map((h) => (
            <li key={`${h.document_id}-${h.page_number}`}>
              <Card className="flex flex-col gap-1 p-4" data-testid="document-hit">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <a
                    href={`/idp/documents/${h.document_id}?page=${h.page_number}`}
                    className="flex items-center gap-2 font-medium text-ai hover:underline"
                  >
                    <FileText className="h-4 w-4" aria-hidden />
                    {h.title}
                  </a>
                  <div className="flex items-center gap-2">
                    {h.doc_type && <Badge variant="outline">{h.doc_type}</Badge>}
                    <span className="text-xs text-muted-foreground">
                      {t("page", { n: h.page_number })} · {Math.round((h.score ?? 0) * 100)}%
                    </span>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">{h.snippet}</p>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
