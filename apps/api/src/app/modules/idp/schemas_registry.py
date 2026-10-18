"""Extraction Schema Registry for the 7 standard document types (T-207; 04 §5; EP-50).

Maintains schema definitions, field validations, sensitivity labels,
and provides filtering per user role (masking SALARY for non-HR / non-Reviewer roles).
"""

from app.modules.idp.enums import DocType, FieldValueType, SensitivityLabel
from app.modules.idp.schemas import ExtractionSchemaFieldOut, ExtractionSchemaOut

EXTRACTION_SCHEMAS: dict[DocType, list[ExtractionSchemaFieldOut]] = {
    DocType.FINANCIAL_REPORT: [
        ExtractionSchemaFieldOut(
            field_key="company_name",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["Khớp hồ sơ công ty ABC"],
        ),
        ExtractionSchemaFieldOut(
            field_key="tax_code",
            value_type=FieldValueType.TAX_CODE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["10 hoặc 13 số"],
        ),
        ExtractionSchemaFieldOut(
            field_key="period",
            value_type=FieldValueType.PERIOD,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["Hợp lệ, không ở tương lai"],
        ),
        ExtractionSchemaFieldOut(
            field_key="revenue",
            value_type=FieldValueType.MONEY,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= 0", "XD-01"],
        ),
        ExtractionSchemaFieldOut(
            field_key="revenue_by_month",
            table_key="revenue_by_month",
            value_type=FieldValueType.TABLE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["Σ revenue các tháng = revenue kỳ (±0.5%)", "XD-01"],
        ),
        ExtractionSchemaFieldOut(
            field_key="cogs",
            value_type=FieldValueType.MONEY,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= 0"],
        ),
        ExtractionSchemaFieldOut(
            field_key="gross_profit",
            value_type=FieldValueType.MONEY,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["= revenue − cogs (±0.5%)"],
        ),
        ExtractionSchemaFieldOut(
            field_key="operating_expenses",
            value_type=FieldValueType.MONEY,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= 0"],
        ),
        ExtractionSchemaFieldOut(
            field_key="net_profit",
            value_type=FieldValueType.MONEY,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["<= gross_profit"],
        ),
        ExtractionSchemaFieldOut(
            field_key="cash_end_of_period",
            value_type=FieldValueType.MONEY,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= 0"],
        ),
        ExtractionSchemaFieldOut(
            field_key="receivables",
            value_type=FieldValueType.MONEY,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= 0"],
        ),
    ],
    DocType.INVOICE: [
        ExtractionSchemaFieldOut(
            field_key="invoice_number",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["Duy nhất theo (ký hiệu, số)"],
        ),
        ExtractionSchemaFieldOut(
            field_key="invoice_series",
            value_type=FieldValueType.TEXT,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="issue_date",
            value_type=FieldValueType.DATE,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["Không ở tương lai"],
        ),
        ExtractionSchemaFieldOut(
            field_key="seller_name",
            value_type=FieldValueType.TEXT,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="seller_tax_code",
            value_type=FieldValueType.TAX_CODE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["10 hoặc 13 số"],
        ),
        ExtractionSchemaFieldOut(
            field_key="customer_name",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["XD-02"],
        ),
        ExtractionSchemaFieldOut(
            field_key="customer_tax_code",
            value_type=FieldValueType.TAX_CODE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["10 hoặc 13 số"],
        ),
        ExtractionSchemaFieldOut(
            field_key="subtotal",
            value_type=FieldValueType.MONEY,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= 0"],
        ),
        ExtractionSchemaFieldOut(
            field_key="vat_rate",
            value_type=FieldValueType.PERCENT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["∈ {0%, 5%, 8%, 10%}"],
        ),
        ExtractionSchemaFieldOut(
            field_key="vat_amount",
            value_type=FieldValueType.MONEY,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["≈ subtotal × vat_rate (±1.000 đ)"],
        ),
        ExtractionSchemaFieldOut(
            field_key="total_amount",
            value_type=FieldValueType.MONEY,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["= subtotal + vat_amount"],
        ),
        ExtractionSchemaFieldOut(
            field_key="due_date",
            value_type=FieldValueType.DATE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= issue_date"],
        ),
        ExtractionSchemaFieldOut(
            field_key="payment_status",
            value_type=FieldValueType.ENUM,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["PAID, UNPAID, PARTIAL"],
        ),
        ExtractionSchemaFieldOut(
            field_key="line_items",
            table_key="line_items",
            value_type=FieldValueType.TABLE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["Σ amount ≈ subtotal"],
        ),
    ],
    DocType.SALES_REPORT: [
        ExtractionSchemaFieldOut(
            field_key="period",
            value_type=FieldValueType.PERIOD,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="pipeline_value_by_stage",
            table_key="pipeline_value_by_stage",
            value_type=FieldValueType.TABLE,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["value >= 0"],
        ),
        ExtractionSchemaFieldOut(
            field_key="deals_won_count",
            value_type=FieldValueType.NUMBER,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= 0"],
        ),
        ExtractionSchemaFieldOut(
            field_key="deals_won_value",
            value_type=FieldValueType.MONEY,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= 0"],
        ),
        ExtractionSchemaFieldOut(
            field_key="deals_lost_count",
            value_type=FieldValueType.NUMBER,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= 0"],
        ),
        ExtractionSchemaFieldOut(
            field_key="revenue_by_customer",
            table_key="revenue_by_customer",
            value_type=FieldValueType.TABLE,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["XD-02"],
        ),
        ExtractionSchemaFieldOut(
            field_key="sales_target",
            value_type=FieldValueType.MONEY,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= 0"],
        ),
        ExtractionSchemaFieldOut(
            field_key="nps_score",
            value_type=FieldValueType.NUMBER,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["-100..100"],
        ),
    ],
    DocType.CONTRACT: [
        ExtractionSchemaFieldOut(
            field_key="contract_number",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["Duy nhất"],
        ),
        ExtractionSchemaFieldOut(
            field_key="party_a_name",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="party_a_tax_code",
            value_type=FieldValueType.TAX_CODE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["10 hoặc 13 số"],
        ),
        ExtractionSchemaFieldOut(
            field_key="party_b_name",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["XD-02"],
        ),
        ExtractionSchemaFieldOut(
            field_key="party_b_tax_code",
            value_type=FieldValueType.TAX_CODE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["10 hoặc 13 số"],
        ),
        ExtractionSchemaFieldOut(
            field_key="contract_value",
            value_type=FieldValueType.MONEY,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["> 0"],
        ),
        ExtractionSchemaFieldOut(
            field_key="sign_date",
            value_type=FieldValueType.DATE,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["<= hôm nay"],
        ),
        ExtractionSchemaFieldOut(
            field_key="effective_date",
            value_type=FieldValueType.DATE,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="expiry_date",
            value_type=FieldValueType.DATE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= effective_date"],
        ),
        ExtractionSchemaFieldOut(
            field_key="payment_terms",
            value_type=FieldValueType.TEXT,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="signatories",
            table_key="signatories",
            value_type=FieldValueType.TABLE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
    ],
    DocType.MEETING_MINUTES: [
        ExtractionSchemaFieldOut(
            field_key="meeting_date",
            value_type=FieldValueType.DATE,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="meeting_title",
            value_type=FieldValueType.TEXT,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="chairperson",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["XD-03"],
        ),
        ExtractionSchemaFieldOut(
            field_key="attendees",
            table_key="attendees",
            value_type=FieldValueType.TABLE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["XD-03"],
        ),
        ExtractionSchemaFieldOut(
            field_key="decisions",
            table_key="decisions",
            value_type=FieldValueType.TABLE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="action_items",
            table_key="action_items",
            value_type=FieldValueType.TABLE,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["assignee khớp XD-03", "due_date >= meeting_date"],
        ),
    ],
    DocType.EMPLOYEE_LIST: [
        ExtractionSchemaFieldOut(
            field_key="employee_code",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["Duy nhất"],
        ),
        ExtractionSchemaFieldOut(
            field_key="full_name",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="title",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="department",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="start_date",
            value_type=FieldValueType.DATE,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["<= hôm nay"],
        ),
        ExtractionSchemaFieldOut(
            field_key="end_date",
            value_type=FieldValueType.DATE,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[">= start_date"],
        ),
        ExtractionSchemaFieldOut(
            field_key="status",
            value_type=FieldValueType.ENUM,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["ACTIVE, ON_LEAVE, TERMINATED"],
        ),
        ExtractionSchemaFieldOut(
            field_key="salary",
            value_type=FieldValueType.MONEY,
            required=False,
            sensitivity=SensitivityLabel.SALARY,
            validation_rules=["> 0"],
        ),
    ],
    DocType.KPI_OKR: [
        ExtractionSchemaFieldOut(
            field_key="period",
            value_type=FieldValueType.PERIOD,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="metric_code",
            value_type=FieldValueType.ENUM,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["XD-04: phải thuộc 18 metric"],
        ),
        ExtractionSchemaFieldOut(
            field_key="metric_name",
            value_type=FieldValueType.TEXT,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="target_value",
            value_type=FieldValueType.NUMBER,
            required=True,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="unit",
            value_type=FieldValueType.TEXT,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="owner",
            value_type=FieldValueType.TEXT,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=["XD-03"],
        ),
        ExtractionSchemaFieldOut(
            field_key="objective",
            value_type=FieldValueType.TEXT,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
        ExtractionSchemaFieldOut(
            field_key="key_result",
            value_type=FieldValueType.TEXT,
            required=False,
            sensitivity=SensitivityLabel.NONE,
            validation_rules=[],
        ),
    ],
}


def get_extraction_schemas_for_role(
    user_role_code: str,
    doc_type: DocType | None = None,
) -> list[ExtractionSchemaOut]:
    """Retrieve extraction schemas filtered according to user role permissions.

    - Non-ROLE-05 users cannot see fields with sensitivity=SALARY (DS3).
    - If doc_type is given, returns only that schema; else all 7 schemas.
    """
    is_reviewer = user_role_code == "ROLE-05"
    can_view_salary = is_reviewer

    types_to_fetch = [doc_type] if doc_type is not None else list(EXTRACTION_SCHEMAS.keys())
    result: list[ExtractionSchemaOut] = []

    for dt in types_to_fetch:
        raw_fields = EXTRACTION_SCHEMAS.get(dt, [])
        filtered_fields: list[ExtractionSchemaFieldOut] = []
        for field in raw_fields:
            if field.sensitivity == SensitivityLabel.SALARY and not can_view_salary:
                continue
            filtered_fields.append(field)

        result.append(
            ExtractionSchemaOut(
                doc_type=dt,
                field_set_version="1.0.0",
                fields=filtered_fields,
            )
        )

    return result
