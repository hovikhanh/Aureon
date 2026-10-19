# 01 — PROJECT OVERVIEW

> Tầm nhìn, phạm vi, KPI và lộ trình của **Aureon v2**.
> File này là "hợp đồng phạm vi" — mọi thứ ngoài đây là ngoài scope.
> Nguồn hợp nhất (DEC-124): A-EMS (`SOURCE-BRD-v1.0`, "Digital Chief of Staff", 5 trụ F.O.C.U.S), AI-EOS (`SOURCE-BRD-v1.1`, Domain 22 Data Capture & IDP, Data Foundation, Autonomy L0–L4) và đề xuất UI/UX AI-EOS. Quyết định kiến trúc: DEC-125 → DEC-137.

---

## 1. Vấn đề

Doanh nghiệp Việt Nam vận hành bằng **giấy tờ, PDF, Word, Excel, ảnh chụp và Zalo**. Hệ quả:

- CEO không có bức tranh tổng thể — mỗi phòng báo một kiểu, số liệu vênh nhau.
- AI/BI không có gì để phân tích — dữ liệu rỗng hoặc sai ("vòng lặp Data → Intelligence → Action gãy ngay từ mắt xích đầu tiên", AI-EOS §1).
- Quyết định dựa trên cảm tính; rủi ro chỉ phát hiện khi đã muộn.
- Quyết định đã giao không biết đi đến đâu.

**Khoảng trống thị trường:** ERP (nặng, cứng), BI (chỉ đọc dữ liệu có sẵn), IDP thuần (đọc tài liệu, không ra quyết định), chatbot (không có dữ liệu thật, không có nguồn). Không sản phẩm nào đi **từ tài liệu giấy → dữ liệu có cấu trúc → insight có nguồn → quyết định → giao việc** trong một luồng.

---

## 2. Giải pháp — Aureon v2 "Digital Chief of Staff"

**Lời hứa duy nhất (AI-EOS §6):** *"CEO biết công ty đang đạt mục tiêu đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file."*

Aureon v2 gồm 5 khối:

| # | Khối | Mô tả | Spec |
|---|---|---|---|
| 1 | **Executive Dashboard F.O.C.U.S** | 5 trụ — **F** Finance, **O** Operations & People, **C** Customer & Growth, **U** Product & Innovation, **S** Strategy & Risk; 31 metric, 31 alert, trạng thái trụ ok/warning/critical, drill-down ≤ 3 click đến tài liệu gốc | 03 |
| 2 | **Domain modules** | Finance, Sales, HR, Product, Risk, Execution (họp, quyết định, task, OKR/KPI) — CRUD, quy tắc nghiệp vụ, event | 03, 05, 10 |
| 3 | **Data Capture & IDP (Domain 22)** | 5 kênh C1–C5, AI phân loại → trích xuất → kiểm tra → review song song → ghi qua Action Registry; lineage đến trang tài liệu | 04 |
| 4 | **AI Core — Trợ lý AI** | Thanh ⌘K + Panel ngữ cảnh + Chat streaming; tool calling lọc theo quyền; mọi con số có nguồn; insight chủ động; Autonomy L0–L3 + kill switch; feed "AI đã làm" | 03, 06, 07, 10 |
| 5 | **Data Foundation & Governance** | Master data, data quality score, freshness, lineage, metric store, audit, RBAC 10 vai trò | 02, 05, 07 |

### 2.1. Kiến trúc tóm tắt (DEC-125, DEC-126)

**Modular Monolith** — một ứng dụng FastAPI, chia module theo bounded context, mỗi module một schema PostgreSQL riêng; giao tiếp liên module qua service interface (đồng bộ) hoặc **domain event qua Transactional Outbox + Celery/Redis** (bất đồng bộ). Không có 17 container như A-EMS. Chi tiết ở `07-TECH-ARCHITECTURE.md`.

### 2.2. Pipeline dữ liệu end-to-end

```
Nhập tay / nói / thả file / chụp / import Excel   (C1–C5)
        ↓
IDP: phân loại → trích xuất → chuẩn hóa VN → kiểm tra nghiệp vụ
        ↓
Review song song (bắt buộc với trường trọng yếu / confidence thấp)
        ↓
Action Registry → ghi vào module domain (finance, sales, hr, product, risk, execution)
        ↓
Outbox → domain event → Risk tự sinh rủi ro · Metric store tính lại · AI làm mới insight
        ↓
Dashboard F.O.C.U.S + Briefing + Trợ lý AI (mọi con số có nguồn, truy về trang tài liệu)
```

---

## 3. Phạm vi v2

### ✅ Trong phạm vi (IN)

- Dashboard F.O.C.U.S: 5 trụ, 31 metric, 31 alert, trạng thái trụ, insight panel, briefing CEO, bộ lọc kỳ, cô lập lỗi theo widget.
- Module domain: Finance (doanh thu, chi phí, ngân sách, tiền mặt, dự báo 3 kịch bản, hóa đơn), Sales (khách hàng, deal, pipeline, mục tiêu, hợp đồng), HR (phòng ban, nhân viên, lịch sử lương, kế hoạch tuyển dụng), Product (sản phẩm, tính năng, roadmap, release, chỉ số), Risk (sổ rủi ro, chấm điểm, rủi ro tự sinh, mitigation, what-if), Execution (họp, quyết định, task, dự án, OKR, KPI, check-in).
- IDP 5 kênh C1–C5, 9 loại tài liệu MVP (§8), review song song, import Excel có map cột, UC-06, UC-07, UC-08 (bản demo).
- Trợ lý AI: chat + SSE, tool calling theo quyền, source chip, insight chủ động, what-if runway, feedback, lọc PII trước khi gửi LLM.
- AI Autonomy L0–L3 cấu hình theo tool × role × ngưỡng giá trị; hoàn tác; kill switch.
- 10 vai trò (DEC-128), RBAC `<domain>:<action>`, data scoping, chuyển vai trò demo.
- ModelGateway đa provider (OmniRoute, OpenRouter, 9router, DeepSeek, OpenAI, Anthropic) với fallback (DEC-131).
- Giao diện tiếng Việt mặc định + tiếng Anh (DEC-135); web responsive + PWA mobile (4 việc).
- Doanh nghiệp giả định ABC ~150 nhân sự, dữ liệu đủ 5 trụ (DEC-136).

### ❌ Ngoài phạm vi (OUT)

- Microservice tách deployable, database-per-service vật lý, RabbitMQ, API Gateway riêng (DEC-125/126).
- Kênh C6–C10 (email forwarding, Zalo/Slack/Teams bot, hóa đơn XML NĐ 123, Drive sync, API/Webhook) — Phase 2.
- Integration thật: MISA, Fast, Bravo, ngân hàng, cổng hóa đơn điện tử, Google Meet bot.
- Procurement/Vendor, Workflow Engine tổng quát, chữ ký số, Performance Cycle đầy đủ.
- Autonomy L4; huấn luyện/fine-tune model riêng.
- Multi-tenant, đa pháp nhân, billing; SSO/LDAP/MFA; self-register (DEC-137).
- Mobile native app (chỉ PWA).

**Nếu agent thấy yêu cầu nằm ngoài danh sách IN → raise decision, không tự build.**

---

## 4. KPI v2

| Nhóm | KPI | Ngưỡng | Cách đo |
|---|---|---|---|
| CEO | Thời gian đến insight đầu tiên | ≤ 10 giây | Usability test |
| CEO | F1 Briefing → giao việc | ≤ 2 phút, ≤ 5 chạm | Usability test |
| Trust | Drill-down từ số → tài liệu gốc | ≤ 3 click | Log UI |
| Trust | Câu trả lời AI có số liệu kèm nguồn | 100% | Log AI |
| IDP | Field accuracy | ≥ 90% chung; ≥ 95% tài liệu có text layer | Đối chiếu ground truth |
| IDP | Straight-through rate | ≥ 50% sau 3 tháng | Log pipeline |
| IDP | Review 1 hóa đơn 6 trường | ≤ 60 giây | Log SCR-10 |
| IDP | Error leakage trường trọng yếu | < 0,5% | Hậu kiểm |
| IDP | Time to data (≤ 5 trang) | p50 ≤ 5 phút; p95 trích xuất ≤ 60 giây | Log pipeline |
| Onboarding | UC-07 từ tập tài liệu đến dashboard đầu tiên | ≤ 15 phút (demo) | Usability test |
| Hiệu năng | Endpoint dashboard p95 | < 800 ms; 5 trụ < 3 giây | Load test |
| Hiệu năng | AI chat token đầu tiên / p95 | ≤ 5 giây / ≤ 30 giây | Log AI |
| UX | SUS | ≥ 75 | Khảo sát |
| UX | Hoàn thành F1–F5 không cần hỗ trợ | ≥ 90% | Usability test |
| AI | Action card L2 xác nhận không sửa / hoàn tác L3 | ≥ 60% / ≤ 5% | Log AI |
| Adoption | WAU / tổng user | ≥ 70% | Analytics |

---

## 5. Personas (10 vai trò — DEC-128)

| ID | Role | Mục tiêu | Trang chủ |
|---|---|---|---|
| ROLE-01 | **CEO** | Biết ngay, quyết nhanh | Briefing công ty, 5 trụ, "Cần anh quyết", rủi ro |
| ROLE-02 | **CFO** | Đủ tiền, chi tiêu hiệu quả | Trụ F + S, ngân sách, dự báo |
| ROLE-03 | **VP_SALES** | Giữ pipeline, doanh thu | Trụ C |
| ROLE-04 | **HR_MANAGER** | Đủ người, giữ người | Trụ O (con người) |
| ROLE-05 | **REVIEWER** | Duyệt nhanh, không sai | Hàng chờ review + SLA |
| ROLE-06 | **CPO** | Sản phẩm được dùng thật | Trụ U |
| ROLE-07 | **RISK_MANAGER** | Không bỏ sót rủi ro | Trụ S, sổ rủi ro |
| ROLE-08 | **MANAGER** | Giữ team đúng hướng | Briefing đơn vị, hàng chờ duyệt, workload |
| ROLE-09 | **EMPLOYEE** | Làm việc, ít khai báo | Việc hôm nay, mục tiêu của tôi, gửi chứng từ |
| ROLE-10 | **ADMIN** | Cấu hình an toàn | Tình trạng hệ thống, AI Control Center |

Chi tiết + user stories + ma trận quyền ở `02-PERSONAS-PERMISSIONS.md`.

---

## 6. Nguyên tắc thiết kế (bất biến)

| # | Nguyên tắc | Kiểm tra |
|---|---|---|
| **P01** | **Every number traceable** — mọi con số click được: công thức, nguồn, thời điểm cập nhật, bản ghi gốc, tài liệu gốc (trang/vùng) | Không có con số "mồ côi" |
| **P02** | **AI shows state** — AI gợi ý (L1) / AI soạn · chờ xác nhận (L2) / AI đã làm (L3, hoàn tác được) | Người dùng luôn trả lời được "AI vừa làm gì?" |
| **P03** | **Capture once, use everywhere** — dữ liệu nhập một lần, mọi module dùng chung qua event | Không màn hình nào yêu cầu nhập lại |
| **P04** | **Vietnamese-first** — `05/10/2026`, `1.250.000 đ`, `1,2 tỷ`, `12,5%`, MST 10/13 số, địa chỉ hành chính mới | Không nhãn dịch máy gượng gạo |
| **P05** | **AI never fabricates numbers** — mọi số trong câu trả lời AI đến từ tool call hoặc tài liệu có trích dẫn; thiếu dữ liệu thì nói thiếu | Không có số ngoài `sources` |
| **P06** | **AI within user's permission** — AI gọi tool bằng chính JWT/quyền người hỏi; danh sách tool lọc theo role trước khi gửi model | AI không trả dữ liệu vượt quyền |
| **P07** | **Exceptions first** — màn hình đầu tiên chỉ hiện điều lệch kế hoạch, việc cần quyết, rủi ro mới | CEO trả lời "có gì cần tôi?" trong 10 giây |
| **P08** | **Graceful degradation** — AI hoặc một module lỗi chỉ widget đó báo lỗi; nhập tay luôn hoạt động | Dashboard vẫn dùng được khi AI lỗi |
| **P09** | **Event-driven, vendor-agnostic** — thay đổi nghiệp vụ quan trọng phát event; không khóa vào một nhà cung cấp LLM | Đổi provider chỉ cần đổi env |

---

## 7. Ràng buộc

### Kỹ thuật
- Frontend Next.js 14+ App Router / React 18+; Backend Python 3.12 + FastAPI; PostgreSQL 16 + pgvector; Celery + Redis; MinIO/S3.
- Modular Monolith (DEC-125); JWT RS256 (DEC-129); mọi LLM call qua ModelGateway (DEC-131).
- Không mobile native (PWA); chạy được offline ở mức demo (fixture mode của ModelGateway).

### Vận hành
- Build bằng AI Agent qua DeepSeek Harness + OmniRoute (11 §9).
- 6 mốc S0–S5, mỗi mốc ~2 tuần (09).
- Mức "demo-grade+": đủ chặt về bảo mật dữ liệu và quyền, chưa yêu cầu HA production.

### Pháp lý
- NĐ 13/2023/NĐ-CP & Luật Bảo vệ dữ liệu cá nhân: consent, phân loại dữ liệu nhạy cảm, không gửi PII/lương cá nhân tới LLM bên ngoài, kiểm soát chuyển dữ liệu ra nước ngoài.
- Hóa đơn điện tử NĐ 123/2020 (Phase 2 cho XML); lưu chứng từ kế toán ≥ 10 năm (Luật Kế toán) — cấu hình retention theo doc type.
- Aureon là lớp quản trị, **không** thay phần mềm kế toán.

---

## 8. Doanh nghiệp giả định (DEC-136)

**Công ty TNHH Thương mại & Dịch vụ ABC** — phân phối thiết bị văn phòng + dịch vụ bảo trì + nền tảng đặt hàng trực tuyến "ABC Order".

| Thuộc tính | Giá trị |
|---|---|
| Quy mô | ~150 nhân sự, 7 phòng ban |
| Doanh thu | ~300 tỷ VNĐ/năm |
| Trụ sở | TP.HCM; chi nhánh Hà Nội |
| Sản phẩm/dịch vụ (trụ U) | ABC Order (B2B portal), ABC Care (gói bảo trì), ABC Supply (phân phối) |
| Kỳ demo | Tháng 9 / Q3 2026; `DEMO_REFERENCE_DATE = 2026-10-20` |

**9 loại tài liệu MVP** (chi tiết `08-DEMO-DATA-SPEC.md`, schema `04-IDP-FEATURE-SPEC.md` §5):

| # | Doc type | Trụ đích chính |
|---|---|---|
| 1 | `FINANCIAL_REPORT` — Báo cáo tài chính quý | F |
| 2 | `INVOICE` — Hóa đơn / danh sách hóa đơn | F, C |
| 3 | `SALES_REPORT` — Báo cáo sales tháng | C |
| 4 | `CONTRACT` — Hợp đồng khách hàng | C, F |
| 5 | `MEETING_MINUTES` — Biên bản họp | O, S |
| 6 | `EMPLOYEE_LIST` — Danh sách nhân sự / sơ đồ tổ chức | O |
| 7 | `KPI_OKR` — Kế hoạch KPI/OKR | O, cả 5 trụ |
| 8 | `PRODUCT_REPORT` — Báo cáo chỉ số sản phẩm tháng | U |
| 9 | `RISK_REGISTER` — Sổ/biên bản đánh giá rủi ro | S |

**Yêu cầu nhất quán:** doanh thu T9 trong #1 khớp SUM(subtotal #2, T9) ±0,5% (DEC-030); tên khách trong #2 khớp #3, #4; người trong #5, #7 khớp #6; sản phẩm trong #8 khớp danh mục; rủi ro trong #9 gắn với entity tồn tại.

---

## 9. Tech stack tóm tắt

| Layer | Công nghệ |
|---|---|
| Frontend | Next.js 14+ App Router, TypeScript strict, TanStack Query, react-hook-form + zod, next-intl, Recharts |
| UI | Tailwind + shadcn/ui + Radix; font Be Vietnam Pro |
| Backend | Python 3.12 + FastAPI (Modular Monolith), Pydantic v2 |
| ORM | SQLAlchemy 2.0 async + Alembic (schema per module) |
| Database | PostgreSQL 16 + pgvector |
| Async / Event | Celery + Redis; Transactional Outbox; DLQ |
| Storage | MinIO (dev) / S3 (prod) |
| Auth | NextAuth + JWT RS256 (PyJWT + cryptography) |
| OCR | PaddleOCR in-process |
| LLM | ModelGateway — OmniRoute / OpenRouter / 9router / DeepSeek / OpenAI / Anthropic |
| RAG | LlamaIndex + pgvector (tri thức SOP/chính sách) |
| Container | Docker Compose |

Chi tiết ở `07-TECH-ARCHITECTURE.md`.

---

## 10. Lộ trình build — 6 mốc

| Mốc | Tuần | Mục tiêu | Output |
|---|---|---|---|
| **S0** | 1–2 | Nền tảng v2 | Module skeleton, schema per module, RS256 + 10 role, outbox/event bus, ModelGateway đa provider, envelope/phân trang mới |
| **S1** | 3–4 | Domain F, C, O | Finance, Sales, HR, Execution CRUD + quy tắc + event |
| **S2** | 5–6 | Domain U, S + Dashboard F.O.C.U.S | Product, Risk, metric store, 5 dashboard, alert, drill-down |
| **S3** | 7–8 | Trợ lý AI + Autonomy | Tool Registry, chat SSE, insight, AI actions + undo, kill switch, ⌘K |
| **S4** | 9–10 | IDP v2 | 5 kênh, 9 doc type, review song song, import grid, UC-06/07/08, lineage |
| **S5** | 11–12 | UX, mobile, demo | Design system v2, trang chủ theo role, PWA, demo data ABC, E2E F1–F5, đo NFR |

Checklist task chi tiết ở `09-BUILD-PLAN-TASKS.md`.

---

## 11. Câu chuyện demo (20 phút)

1. **(2') CEO mở app buổi sáng** (F1) → dòng tóm tắt "2 việc cần anh, 1 rủi ro mới"; 5 thẻ trụ, trụ S đỏ.
2. **(3') Bấm thẻ "Doanh thu T9 đạt 82% KH"** → Panel AI giải thích nguyên nhân có source chip → drill-down tới hóa đơn và trang PDF gốc.
3. **(2') Hỏi AI** "Rủi ro tuyển dụng chậm ảnh hưởng thế nào đến dự báo tài chính?" → trả lời liên miền có nguồn; "Runway nếu tháng sau không có doanh thu mới?".
4. **(2') Chọn phương án** → Action card L2 → xác nhận → 3 task được tạo, toast hoàn tác, Decision log cập nhật.
5. **(2') Chuyển vai CFO / Risk Manager** → dashboard đổi; chạy what-if rủi ro.
6. **(5') Nạp doanh nghiệp (UC-07)** → thả 9 tài liệu mẫu → AI phân loại, trích xuất.
7. **(2') Review song song** (F2) → duyệt hóa đơn ≤ 60 giây → dữ liệu vào module Finance.
8. **(2') Quay lại CEO** → metric cập nhật, insight mới, lineage tới tài liệu vừa duyệt.

---

## 12. Thuật ngữ

| Thuật ngữ | Định nghĩa |
|---|---|
| **F.O.C.U.S** | 5 trụ: Finance, Operations & People, Customer & Growth, Product (U = Usage/Innovation), Strategy & Risk |
| **Modular Monolith** | Một deployable, nhiều module có ranh giới rõ (schema riêng, interface riêng) |
| **Outbox** | Bảng ghi event trong cùng transaction nghiệp vụ, relay publish sau commit |
| **IDP** | Intelligent Document Processing — Domain 22 |
| **Action Registry** | Danh mục hành động ghi dữ liệu có idempotency, audit, undo — cửa duy nhất để IDP/AI ghi |
| **Tool Registry** | Danh mục tool AI được gọi (đọc/ghi), có `risk_level`, quyền, autonomy |
| **Autonomy Level** | L0 Inform · L1 Suggest · L2 Draft & Confirm · L3 Act & Notify · L4 Autonomous (ngoài scope) |
| **Kill switch** | Một thao tác tắt mọi hành động WRITE của AI; L3 → L2 |
| **Briefing** | Tóm tắt ngoại lệ hằng ngày theo vai trò |
| **Lineage** | Truy vết metric → bản ghi → field trích xuất → trang tài liệu |
| **Straight-through (STP)** | Tài liệu ghi tự động không cần review |
| **Trường trọng yếu** | Số tiền, số tài khoản, MST, lương, giá trị hợp đồng — luôn qua người |

---

## 13. Liên kết

| Chủ đề | File |
|---|---|
| Personas & quyền | `02-PERSONAS-PERMISSIONS.md` |
| Dashboard F.O.C.U.S & domain | `03-DASHBOARD-SPEC.md` |
| IDP | `04-IDP-FEATURE-SPEC.md` |
| Data model | `05-DATA-MODEL.md` |
| UI/UX | `06-UI-UX-SPEC.md` |
| Kiến trúc | `07-TECH-ARCHITECTURE.md` |
| Demo data | `08-DEMO-DATA-SPEC.md` |
| Build plan | `09-BUILD-PLAN-TASKS.md` |
| API contract | `10-API-SPECIFICATION.md` |
| Agent workflow | `11-AGENT-WORKFLOW.md` |
| Governance | `12`, `13`, `14` |

---

## 14. Version

- **Version:** 2.0.0
- **Last updated:** 2026-10-19
- **Applies to:** Aureon v2
- **Maintainer:** @CyEyes
- **Change:** Viết lại toàn bộ theo DEC-124..137 (v1.0.0 lưu ở nhánh `v1`).
