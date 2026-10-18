"""Table Extraction Engine for IDP documents (T-208; 04 §5.1, §5.2; FR-DC-11; TC-IDP-012).

Extracts tabular rows into ExtractedField rows with row_index, table_key, and normalized cell values
for:
1. line_items (INVOICE)
2. action_items (MEETING_MINUTES)
3. employees (EMPLOYEE_LIST)
4. revenue_by_month (FINANCIAL_REPORT)
"""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.modules.idp.enums import FieldValueType, SensitivityLabel, SourceLocationKind
from app.modules.idp.models import ExtractedField
from app.modules.idp.normalizer import normalize_field_value

# Table column definitions (04 §5.3, §5.4, §5.7, §5.8)
TABLE_DEFINITIONS: dict[str, list[dict[str, Any]]] = {
    "line_items": [
        {
            "field_key": "description",
            "value_type": FieldValueType.TEXT,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "quantity",
            "value_type": FieldValueType.NUMBER,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "unit_price",
            "value_type": FieldValueType.MONEY,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "amount",
            "value_type": FieldValueType.MONEY,
            "sensitivity": SensitivityLabel.NONE,
        },
    ],
    "action_items": [
        {
            "field_key": "title",
            "value_type": FieldValueType.TEXT,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "assignee",
            "value_type": FieldValueType.PERSON_NAME,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "due_date",
            "value_type": FieldValueType.DATE,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "status",
            "value_type": FieldValueType.ENUM,
            "sensitivity": SensitivityLabel.NONE,
        },
    ],
    "employees": [
        {
            "field_key": "employee_code",
            "value_type": FieldValueType.TEXT,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "full_name",
            "value_type": FieldValueType.PERSON_NAME,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "title",
            "value_type": FieldValueType.TEXT,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "department",
            "value_type": FieldValueType.TEXT,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "start_date",
            "value_type": FieldValueType.DATE,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "status",
            "value_type": FieldValueType.ENUM,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "salary",
            "value_type": FieldValueType.MONEY,
            "sensitivity": SensitivityLabel.SALARY,
        },
    ],
    "revenue_by_month": [
        {
            "field_key": "month",
            "value_type": FieldValueType.PERIOD,
            "sensitivity": SensitivityLabel.NONE,
        },
        {
            "field_key": "revenue",
            "value_type": FieldValueType.MONEY,
            "sensitivity": SensitivityLabel.NONE,
        },
    ],
}


def extract_table_rows(
    db: Session,
    doc_id: UUID,
    job_id: UUID,
    table_key: str,
    raw_rows: list[dict[str, Any]],
    page_id: UUID | None = None,
    source_kind: SourceLocationKind = SourceLocationKind.CELL,
) -> list[ExtractedField]:
    """Persist structured table rows into individual ExtractedField records.

    Each cell receives a full ExtractedField record with:
    - table_key
    - row_index
    - field_key
    - normalized value + raw_text
    - source_location
    """
    col_defs = TABLE_DEFINITIONS.get(table_key, [])
    col_map = {col["field_key"]: col for col in col_defs}

    extracted_records: list[ExtractedField] = []

    for r_idx, row_data in enumerate(raw_rows):
        for col_idx, (col_key, raw_val) in enumerate(row_data.items()):
            col_def = col_map.get(col_key)
            val_type = col_def["value_type"] if col_def else FieldValueType.TEXT
            sens = col_def["sensitivity"] if col_def else SensitivityLabel.NONE

            normalized_val, raw_text = normalize_field_value(val_type, raw_val)
            conf = 0.95 if normalized_val is not None else 0.50

            src_loc = {
                "kind": source_kind.value,
                "page": 1,
                "row": r_idx + 1,
                "col": col_idx + 1,
                "bbox": [0.1, 0.1, 0.9, 0.9],
            }

            field = ExtractedField(
                id=uuid4(),
                extraction_job_id=job_id,
                source_document_id=doc_id,
                document_page_id=page_id,
                field_key=col_key,
                table_key=table_key,
                row_index=r_idx,
                record_group=r_idx + 1,
                value_type=val_type,
                value=normalized_val,
                raw_text=raw_text,
                confidence=conf,
                source_location=src_loc,
                source_kind=source_kind,
                sensitivity=sens,
            )
            db.add(field)
            extracted_records.append(field)

    db.flush()
    return extracted_records
