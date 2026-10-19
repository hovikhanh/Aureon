"use client";

import { useParams } from "next/navigation";
import { DocumentDetailView } from "@/features/idp/documents/DocumentDetailView";

/**
 * SCR-07 Document detail (EP-25, 06 §4.4).
 * Route: /documents/[documentId]
 * Shows metadata, status timeline, processing jobs, review history and
 * affected metrics (P01 drill-through). Accessible by ROLE-01..05 within
 * their EP-24 scope; out-of-scope documents render a ForbiddenState.
 */
export default function DocumentDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  return <DocumentDetailView documentId={documentId} />;
}
