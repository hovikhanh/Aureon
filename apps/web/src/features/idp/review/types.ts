import type {
  DocType,
  DocumentOut,
  ExtractedFieldOut,
  ExtractionResultOut,
  RoleCode,
} from "@aureon/shared-types";

export interface FieldEditState {
  fieldId: string;
  originalValue: unknown;
  currentValue: unknown;
  isCorrected: boolean;
  isConfirmed: boolean;
}

export interface ReviewState {
  document: DocumentOut;
  reviewId: string;
  docType: DocType;
  fields: ExtractedFieldOut[];
  fieldEdits: Record<string, FieldEditState>;
  selectedFieldId: string | null;
  acceptedConflicts: { rule: string; note: string }[];
  lockExpiresAt: Date;
  isSubmitting: boolean;
}

export interface ReviewViewProps {
  document: DocumentOut;
  reviewId: string;
  extraction: ExtractionResultOut;
  role: RoleCode;
  onApprove: (acceptedConflicts: { rule: string; note: string }[]) => Promise<void>;
  onReject: (reasonCode: string, note?: string) => Promise<void>;
  onRelease?: () => Promise<void>;
  onChangeDocType?: (newType: DocType) => Promise<void>;
  onFieldCorrect?: (fieldId: string, value: unknown) => void;
  onFieldConfirm?: (fieldId: string) => void;
}
