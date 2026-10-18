import type {
  DocType,
  DocumentStatus,
  Pillar,
  ReviewQueueCountsOut,
  ReviewQueueItemOut,
  ReviewQueueMetaOut,
} from "@aureon/shared-types";

export type ConfidenceFilter = "ALL" | "HIGH" | "MEDIUM" | "LOW";

export interface QueueFiltersState {
  pillar: Pillar | "ALL";
  docType: DocType | "ALL";
  status: DocumentStatus | "ALL";
  confidence: ConfidenceFilter;
  batchId: string;
  hasConflictOnly: boolean;
}

export interface QueueQueryParams {
  page?: number;
  pageSize?: number;
  pillar?: Pillar | "ALL";
  docType?: DocType | "ALL";
  status?: DocumentStatus | "ALL";
  batchId?: string;
  hasConflict?: boolean;
  minConfidence?: number;
  maxConfidence?: number;
}

export interface ReviewQueueData {
  items: ReviewQueueItemOut[];
  meta: ReviewQueueMetaOut;
  counts: ReviewQueueCountsOut;
}
