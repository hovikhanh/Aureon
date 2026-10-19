export interface SchemaField {
  field_key: string;
  table_key: string | null;
  value_type: string;
  required: boolean;
  sensitivity: string;
  validation_rules: string[];
}

export interface DocSchema {
  doc_type: string;
  field_set_version: string;
  fields: SchemaField[];
}

export const DEMO_SCHEMAS: DocSchema[] = [
  {
    doc_type: "INVOICE",
    field_set_version: "v1.2",
    fields: [
      { field_key: "invoice_number", table_key: null, value_type: "text", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "issue_date", table_key: null, value_type: "date", required: true, sensitivity: "NONE", validation_rules: ["VR-INV-03"] },
      { field_key: "supplier_name", table_key: null, value_type: "text", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "supplier_tax_code", table_key: null, value_type: "text", required: false, sensitivity: "NONE", validation_rules: ["VR-MST-01"] },
      { field_key: "subtotal", table_key: null, value_type: "money", required: true, sensitivity: "NONE", validation_rules: ["VR-INV-01"] },
      { field_key: "vat_amount", table_key: null, value_type: "money", required: true, sensitivity: "NONE", validation_rules: ["VR-INV-02"] },
      { field_key: "total_amount", table_key: null, value_type: "money", required: true, sensitivity: "NONE", validation_rules: ["VR-INV-01"] },
      { field_key: "payment_due", table_key: null, value_type: "date", required: false, sensitivity: "NONE", validation_rules: ["VR-INV-03"] },
    ],
  },
  {
    doc_type: "SALES_REPORT",
    field_set_version: "v1.0",
    fields: [
      { field_key: "period", table_key: null, value_type: "text", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "total_revenue", table_key: null, value_type: "money", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "new_customers", table_key: null, value_type: "number", required: false, sensitivity: "NONE", validation_rules: [] },
      { field_key: "active_customers", table_key: null, value_type: "number", required: false, sensitivity: "NONE", validation_rules: [] },
      { field_key: "churn_rate", table_key: null, value_type: "percent", required: false, sensitivity: "NONE", validation_rules: [] },
    ],
  },
  {
    doc_type: "FINANCIAL_REPORT",
    field_set_version: "v1.1",
    fields: [
      { field_key: "period", table_key: null, value_type: "text", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "revenue", table_key: null, value_type: "money", required: true, sensitivity: "NONE", validation_rules: ["VR-BCTC-01"] },
      { field_key: "cogs", table_key: null, value_type: "money", required: true, sensitivity: "NONE", validation_rules: ["VR-BCTC-01"] },
      { field_key: "gross_profit", table_key: null, value_type: "money", required: true, sensitivity: "NONE", validation_rules: ["VR-BCTC-01"] },
      { field_key: "operating_expenses", table_key: null, value_type: "money", required: false, sensitivity: "NONE", validation_rules: [] },
      { field_key: "net_profit", table_key: null, value_type: "money", required: true, sensitivity: "NONE", validation_rules: ["VR-BCTC-02"] },
    ],
  },
  {
    doc_type: "CONTRACT",
    field_set_version: "v1.0",
    fields: [
      { field_key: "contract_number", table_key: null, value_type: "text", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "sign_date", table_key: null, value_type: "date", required: true, sensitivity: "NONE", validation_rules: ["VR-CON-02"] },
      { field_key: "effective_date", table_key: null, value_type: "date", required: true, sensitivity: "NONE", validation_rules: ["VR-CON-01"] },
      { field_key: "expiry_date", table_key: null, value_type: "date", required: true, sensitivity: "NONE", validation_rules: ["VR-CON-01"] },
      { field_key: "contract_value", table_key: null, value_type: "money", required: false, sensitivity: "NONE", validation_rules: [] },
      { field_key: "counterparty_name", table_key: null, value_type: "text", required: true, sensitivity: "NONE", validation_rules: [] },
    ],
  },
  {
    doc_type: "EMPLOYEE_LIST",
    field_set_version: "v1.3",
    fields: [
      { field_key: "employee_id", table_key: "employees", value_type: "text", required: true, sensitivity: "PII", validation_rules: [] },
      { field_key: "full_name", table_key: "employees", value_type: "text", required: true, sensitivity: "PII", validation_rules: [] },
      { field_key: "department", table_key: "employees", value_type: "text", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "position", table_key: "employees", value_type: "text", required: false, sensitivity: "NONE", validation_rules: [] },
      { field_key: "base_salary", table_key: "employees", value_type: "money", required: false, sensitivity: "SALARY", validation_rules: [] },
      { field_key: "join_date", table_key: "employees", value_type: "date", required: false, sensitivity: "PII", validation_rules: [] },
    ],
  },
  {
    doc_type: "KPI_OKR",
    field_set_version: "v1.0",
    fields: [
      { field_key: "period", table_key: null, value_type: "text", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "metric_code", table_key: null, value_type: "text", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "actual_value", table_key: null, value_type: "number", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "target_value", table_key: null, value_type: "number", required: false, sensitivity: "NONE", validation_rules: [] },
      { field_key: "unit", table_key: null, value_type: "text", required: false, sensitivity: "NONE", validation_rules: [] },
    ],
  },
  {
    doc_type: "MEETING_MINUTES",
    field_set_version: "v1.0",
    fields: [
      { field_key: "meeting_date", table_key: null, value_type: "date", required: true, sensitivity: "NONE", validation_rules: [] },
      { field_key: "attendees", table_key: "attendees", value_type: "text", required: false, sensitivity: "NONE", validation_rules: [] },
      { field_key: "agenda", table_key: null, value_type: "text", required: false, sensitivity: "NONE", validation_rules: [] },
      { field_key: "decisions", table_key: "decisions", value_type: "text", required: false, sensitivity: "NONE", validation_rules: [] },
      { field_key: "action_items", table_key: "tasks", value_type: "text", required: false, sensitivity: "NONE", validation_rules: [] },
    ],
  },
];
