# IDP Extraction Schema

> The document types, extraction field schemas, confidence/STP rules, validation rules, and the
> downstream Action Registry mapping, as **published in the running database** (live snapshot
> 2026-10-26). Source of truth for what the pipeline extracts and where it commits. Companion:
> `Data_Inbox_MVP_Workflow.md`, `IDP_Sample_Data.md`, `IDP_Operations.md`.

## 1. Document types (live)

| Code | Name (VI) | Sensitivity | Classification | Pillars | Published schema | Fields |
|---|---|:--:|---|---|:--:|:--:|
| `INVOICE` | Hóa đơn | 2 | INTERNAL | F | v1 | 8 |
| `HR_ROSTER` | Danh sách nhân sự | 4 | INTERNAL | O | v1 | 17 |
| `PERIOD_REPORT` | Báo cáo kỳ | 2 | INTERNAL | F,O,C,U,S | v1 | 7 |
| `PLAN_KPI_OKR` | Kế hoạch KPI/OKR | 2 | INTERNAL | F,O,C,U,S | v1 | 13 |
| `OTHER` | Khác | 2 | INTERNAL | — | v1 | 1 |

- **Sensitivity 4** (HR_ROSTER) means level-4 data (salary, DOB, national ID, bank account,
  address) is masked for roles without explicit access and is **never sent to a cloud LLM**;
  classification routing applies (Confidential → local LLM, Secret → no LLM).
- Each field in a schema declares `name`, `value_type`, `required`, and `is_critical`.

## 2. Field schemas (live)

Legend: `req` = required · `CRIT` = critical field (always forces human review, never STP).

### INVOICE (8 fields)
| Field | Type | Flags |
|---|---|---|
| invoice_number | text | req |
| issue_date | date | req |
| seller_name | org_name | req |
| seller_tax_code | tax_code | req |
| subtotal | money | req, **CRIT** |
| vat_rate_pct | percent | req |
| vat_amount | money | req, **CRIT** |
| total_amount | money | req, **CRIT** |

### HR_ROSTER (17 fields)
| Field | Type | Flags |
|---|---|---|
| department_code | text | req |
| department_name | text | req |
| team_code | text | |
| team_name | text | |
| title | text | |
| employee_code | text | req |
| full_name | person_name | req |
| manager_code | text | |
| hire_date | date | req |
| status | enum | |
| email | text | |
| phone | phone | |
| salary | money | **CRIT** |
| date_of_birth | date | **CRIT** |
| address | text | **CRIT** |
| national_id | text | **CRIT** |
| bank_account | text | **CRIT** |

### PERIOD_REPORT (7 fields)
| Field | Type | Flags |
|---|---|---|
| kpi_code | text | |
| period_key | period | |
| actual_value | number | |
| kr_ref | text | |
| value | number | |
| confidence | enum | |
| note | text | |

### PLAN_KPI_OKR (13 fields)
| Field | Type | Flags |
|---|---|---|
| period_key | period | req |
| owner_code | text | req |
| unit | text | |
| baseline | number | |
| target | number | |
| objective_title | text | |
| kr_title | text | |
| kpi_code | text | |
| kpi_name | text | |
| kpi_period_target | number | |
| task_title | text | |
| assignee_code | text | |
| task_due_date | date | |

### OTHER (1 field)
| Field | Type | Flags |
|---|---|---|
| title | text | |

## 3. Confidence bands & STP (DEC-133)

| Band | Range |
|---|---|
| HIGH | ≥ 0.90 |
| MEDIUM | 0.60 – < 0.90 |
| LOW | < 0.60 |

**Straight-through processing (AUTO_APPROVED)** requires *all* of:
- document (classification) confidence ≥ 0.95,
- every **required** field confidence ≥ 0.90,
- **no critical field present** in the schema,
- no validation rule failure.

Any critical field, or any gap above, routes the document to `NEEDS_REVIEW`. Because `INVOICE` and
`HR_ROSTER` both contain critical fields, they **always** go to review regardless of confidence.

## 4. Validation rules (live)

Rules are attached to the published schema. `fail` severity blocks STP.

| Doc type | Rule code | Kind | Severity | Meaning |
|---|---|---|---|---|
| INVOICE | VR-INV-02 | field | fail | field-level constraint (e.g. non-negative amount) |
| INVOICE | VR-INV-03 | field | fail | field-level constraint (e.g. date not in the future) |
| INVOICE | VR-INV-05 | cross_field | fail | `total_amount` = `subtotal` + `vat_amount` (tolerance) |
| INVOICE | VR-INV-SUB | field | fail | subtotal present/valid |
| HR_ROSTER | VR-HR-01 | field | fail | roster field-level constraint |

> `PERIOD_REPORT`, `PLAN_KPI_OKR`, and `OTHER` have no published `fail` validation rules in the
> current snapshot; they rely on schema field typing and (for the first two) downstream Action
> Registry constraints at commit.

## 5. Extraction mechanics

- Extraction is **schema-driven**: the schema's field list is sent to the model as a JSON schema;
  the model returns `{ field: { value, raw_text?, confidence } }`. A missing field is `null` /
  confidence `0` — never fabricated (BRD-P05).
- The call goes through the internal **ModelGateway** structured-output path
  (`gateway.extract()`), which parses the model's JSON into `data`. (Calling the plain `chat()`
  path leaves `data=None` for a live provider — the cause of the live-only null-field bug fixed in
  this work; see `Data_Inbox_MVP_Workflow.md` §7.)
- Classification by sensitivity controls routing: SECRET (level ~4 blocked) → no LLM;
  CONFIDENTIAL → local LLM; INTERNAL/PUBLIC → cloud chain. All five current types are INTERNAL,
  except HR_ROSTER data-level masking applies to its level-4 fields.

## 6. Downstream Action Registry mapping (live `action_names`)

Committed values flow to business tables via the chain stored on each schema:

| Doc type | Action chain (ordered) | Module | Per-action permission |
|---|---|---|---|
| INVOICE | `ACT-create_invoice` | finance | `finance:write` |
| HR_ROSTER | `ACT-create_department` → `ACT-create_team` → `ACT-create_position` → `ACT-create_employee` | hr | `hr:admin` (dept/team/position), `hr:write`+`hr:admin` (employee) |
| PLAN_KPI_OKR | `ACT-upsert_objective` → `ACT-upsert_key_result` → `ACT-upsert_kpi` → `ACT-upsert_kpi_target` → `ACT-create_task` | execution | `execution:write` |
| PERIOD_REPORT | `ACT-record_kpi_measurement` → `ACT-record_kr_checkin` | execution | `execution:write` |
| OTHER | *(empty)* | — | — |

All actions for a document run in **one transaction**; the commit emits
`EVT-idp.document_committed` and opens a **7-day undo** window.

## Version

- Draft 0.1 — 2026-10-26. Live DB snapshot. Schema changes must go through `05-DATA-MODEL.md` + a
  DEC; this doc only records the current published state.
