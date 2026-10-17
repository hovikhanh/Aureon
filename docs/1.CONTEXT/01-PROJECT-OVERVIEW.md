# 01 — PROJECT OVERVIEW

> Tầm nhìn, phạm vi, KPI của Aureon Demo.
> File này là "hợp đồng phạm vi" — mọi thứ ngoài đây là ngoài scope.

---

## 1. Vấn đề

Doanh nghiệp Việt Nam vận hành bằng **giấy tờ, PDF, Word, Excel và ảnh chụp**. Dữ liệu nằm rải rác ở:
- File Excel của từng phòng ban
- PDF hóa đơn, hợp đồng trong email
- Ảnh chụp biên bản họp trên Zalo
- Báo cáo giấy chưa số hóa

**Hệ quả:**
- CEO không có bức tranh tổng thể — mỗi phòng báo một kiểu
- AI/BI không có gì để phân tích — dữ liệu rỗng hoặc sai
- Quyết định dựa trên cảm tính, không có nguồn
- Nhập liệu thủ công lặp lại, tốn thời gian, dễ sai

**Khoảng trống thị trường:** Các sản phẩm hiện có hoặc là ERP (nặng, đắt, cứng), hoặc là BI (chỉ đọc dữ liệu đã có sẵn), hoặc là IDP thuần (chỉ đọc tài liệu, không ra quyết định). Không có sản phẩm nào **đi từ tài liệu giấy → quyết định CEO** trong một luồng.

---

## 2. Giải pháp — Aureon

Aureon là nền tảng quản trị doanh nghiệp lấy AI làm trung tâm, gồm 3 khối:

### 2.1. Dashboard CEO (4 trụ sức khỏe)

Bảng điều khiển theo vai trò, hiển thị 4 trụ:

| Trụ | Số chỉ số | Ví dụ |
|---|---|---|
| **Tài chính** | 6 | Doanh thu, biên LN gộp, cash runway, DSO, công nợ quá hạn, chênh ngân sách |
| **Khách hàng** | 5 | Pipeline coverage, tỷ lệ chuyển đổi, NRR, tập trung doanh thu, NPS |
| **Vận hành** | 4 | Task đúng hạn, dự án trễ, thực thi quyết định, workload |
| **Con người** | 3 | Doanh thu/nhân sự, tỷ lệ nghỉ việc, quá tải |

Mỗi chỉ số có:
- Biểu đồ trực quan (bar/line/gauge/sparkline)
- Ngưỡng cảnh báo (vàng/đỏ)
- **Drill-down**: từ số → chi tiết → tài liệu gốc

### 2.2. IDP Feature (tính năng trọng tâm)

Pipeline nhập liệu thông minh:

```
Upload/chụp/nhập tay
        ↓
   AI phân loại tài liệu
        ↓
   AI trích xuất trường
        ↓
   Kiểm tra + đối chiếu
        ↓
   Người duyệt
        ↓
   Ghi vào metric/entity → dashboard tự cập nhật
```

**Kênh nhập liệu (MVP):**
- C1: Nhập thủ công qua form
- C2: Nhập bằng ngôn ngữ tự nhiên (text/voice)
- C3: Tải file lên (PDF, Word, ảnh, Excel/CSV)
- C4: Chụp ảnh trên mobile
- C5: Import Excel/CSV hàng loạt

**Loại tài liệu hỗ trợ (MVP):**
- Báo cáo tài chính
- Hóa đơn
- Báo cáo sales
- Hợp đồng
- Biên bản họp
- Danh sách nhân sự
- Bảng KPI/OKR

### 2.3. Role-based Access

5 vai trò với dashboard và quyền khác nhau. Chi tiết ở `02-PERSONAS-PERMISSIONS.md`.

---

## 3. Phạm vi MVP

### ✅ Trong phạm vi (IN)

- Dashboard 4 trụ với 18 metric + 18 alert
- IDP với 5 kênh nhập liệu (C1–C5)
- 7 loại tài liệu mẫu
- 5 vai trò (CEO, CFO, Sales Director, HR Manager, Reviewer)
- Chuyển vai trò để demo
- Drill-down từ metric → tài liệu gốc
- Doanh nghiệp giả định ABC (seed data)
- Luồng "Nạp doanh nghiệp từ tập tài liệu" (UC-07)

### ❌ Ngoài phạm vi (OUT)

- 21 domain khác của hệ sinh thái Aureon đầy đủ (Procurement, Workflow Engine, Contract Lifecycle…)
- Mobile native app (chỉ responsive web/PWA)
- Integration thật: MISA, Zalo, email forwarding, ngân hàng, hóa đơn XML
- Multi-tenant
- Billing / subscription
- Chữ ký số
- AI Autonomy Level L4 (chỉ L0–L3)
- Email forwarding (C6), Chat integration (C7), XML hóa đơn (C8), Drive sync (C9), API/Webhook (C10)

**Nếu agent thấy yêu cầu nằm ngoài danh sách IN → raise decision, không tự build.**

---

## 4. KPI Demo

Đo lường thành công của demo:

| KPI | Ngưỡng | Cách đo |
|---|---|---|
| Thời gian onboarding từ tập tài liệu | ≤ 15 phút | Usability test |
| Drill-down từ số → tài liệu gốc | ≤ 3 click | Log UI |
| Review 1 tài liệu (6 trường) | ≤ 60 giây | Log màn Review |
| Chuyển vai trò dashboard | ≤ 2 giây | Log UI |
| Field accuracy (trích xuất) | ≥ 90% chung; ≥ 95% với PDF có text layer | Đối chiếu ground truth |
| Straight-through rate | ≥ 50% sau 3 tháng | Log pipeline |
| Thời gian đến insight đầu tiên (CEO) | ≤ 10 giây | Usability test |
| SUS score | ≥ 75 | Khảo sát sau 30 ngày |

---

## 5. Personas

5 vai trò, tóm tắt:

| Role | ID | Mục tiêu | Dashboard chính |
|---|---|---|---|
| **CEO** | ROLE-01 | Biết ngay, quyết nhanh | Toàn bộ 4 trụ |
| **CFO** | ROLE-02 | Kiểm soát tài chính | Tài chính + Vận hành |
| **Sales Director** | ROLE-03 | Giữ pipeline, doanh thu | Khách hàng + doanh thu |
| **HR Manager** | ROLE-04 | Giữ người, đo năng suất | Con người |
| **Reviewer** | ROLE-05 | Duyệt nhanh, không sai | Hàng chờ IDP |

Chi tiết đầy đủ + ma trận quyền ở `02-PERSONAS-PERMISSIONS.md`.

---

## 6. Nguyên tắc thiết kế

Bốn nguyên tắc **không được vi phạm**:

### P01 — Every number traceable
Mọi con số trên UI đều click được. Mở ra phải thấy:
- Công thức tính
- Nguồn dữ liệu
- Thời điểm cập nhật
- Bản ghi gốc
- Tài liệu gốc (nếu có)

**Kiểm tra:** Không có con số "mồ côi".

### P02 — AI shows state
AI luôn nói rõ đang ở trạng thái nào:
- **AI gợi ý** (L1) — chưa làm gì
- **AI soạn · chờ xác nhận** (L2) — đã chuẩn bị, chờ bấm
- **AI đã làm** (L3) — đã thực hiện, có thể hoàn tác

**Kiểm tra:** Người dùng luôn trả lời được "AI vừa làm gì?"

### P03 — Capture once, use everywhere
Một dữ liệu chỉ nhập một lần. Mọi domain dùng chung. Không có "nhập lại ở module khác".

**Kiểm tra:** Không có màn hình nào yêu cầu nhập lại dữ liệu đã có.

### P04 — Vietnamese-first
Ngày, số, địa chỉ, xưng hô theo chuẩn Việt Nam:
- Ngày: `05/10/2026`
- Tiền: `1.250.000 đ` hoặc `1,2 tỷ`
- Phần trăm: `12,5%`
- Địa chỉ theo đơn vị hành chính mới
- MST 10 hoặc 13 số
- AI xưng hô "anh/chị" theo hồ sơ

**Kiểm tra:** Không có nhãn dịch máy gượng gạo.

---

## 7. Ràng buộc

### Kỹ thuật
- Frontend: Next.js 14+ / React 18+
- Backend: Python + FastAPI
- Không mobile native (chỉ PWA/responsive)
- Chạy được offline ở mức demo

### Vận hành
- Build bằng AI Agent (Claude, Codex, free models qua OmniRoute)
- Harness: DeepSeek + VS Code
- Thời gian: 8 tuần (4 sprint)
- Không cần production-grade

### Pháp lý
- Tuân thủ NĐ 13/2023/NĐ-CP (bảo vệ dữ liệu cá nhân)
- Hóa đơn điện tử theo NĐ 123/2020 (khi làm Phase 2)
- Lưu trữ chứng từ theo Luật Kế toán (khi làm Phase 2)

Chi tiết ở `07-TECH-ARCHITECTURE.md`.

---

## 8. Doanh nghiệp giả định

**Công ty TNHH Thương mại & Dịch vụ ABC**

| Thuộc tính | Giá trị |
|---|---|
| Ngành | Phân phối thiết bị văn phòng |
| Quy mô | 45 nhân sự |
| Doanh thu | ~100 tỷ VNĐ/năm |
| Trụ sở | TP.HCM |
| Có đủ 4 trụ dữ liệu | ✅ Tài chính, Khách hàng, Vận hành, Con người |

**7 loại tài liệu mẫu** (chi tiết ở `08-DEMO-DATA-SPEC.md`):

| # | Tài liệu | Định dạng | Trụ đích |
|---|---|---|---|
| 1 | Báo cáo tài chính Q3 | PDF scan | Tài chính |
| 2 | Danh sách hóa đơn T9 | Excel (47 dòng) | Tài chính |
| 3 | Báo cáo sales T9 | PDF | Khách hàng |
| 4 | Hợp đồng mẫu (2 file) | PDF scan | Khách hàng |
| 5 | Biên bản họp giao ban (3 file) | Word | Vận hành |
| 6 | Danh sách nhân sự | Excel | Con người |
| 7 | Bảng KPI/OKR Q4 | Word/Excel | Cả 4 trụ |

**Yêu cầu nhất quán:** Doanh thu trong tài liệu #1 phải khớp SUM(#2); tên khách trong #2 khớp #3, #4; người trong #5 khớp #6.

---

## 9. Tech stack tóm tắt

| Layer | Công nghệ |
|---|---|
| Frontend | Next.js 14+ / React 18+ |
| UI | Tailwind + shadcn/ui + Radix |
| Backend | Python 3.12 + FastAPI |
| ORM | SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL 16 + pgvector |
| Queue | Redis + Celery (hoặc ARQ) |
| Storage | MinIO (dev) / S3 (prod) |
| OCR | PaddleOCR (self-host) hoặc Google Vision |
| LLM | Claude + GPT qua OmniRoute |
| Container | Docker Compose |

Chi tiết đầy đủ ở `07-TECH-ARCHITECTURE.md`.

---

## 10. Kế hoạch build — 4 sprint

| Sprint | Tuần | Mục tiêu | Output |
|---|---|---|---|
| **S0** | 0 | Setup | Monorepo, hạ tầng, Model Gateway |
| **S1** | 1–2 | Auth + Role + Dashboard tĩnh | 4 dashboard với mock data |
| **S2** | 3–4 | IDP core | Upload → Extract → Review → Commit |
| **S3** | 5–6 | Dashboard động + drill-down | Metric thật + lineage |
| **S4** | 7–8 | Demo data + polish | Tài liệu mẫu + kịch bản 15 phút |

Chi tiết task list (~40 task) ở `09-BUILD-PLAN-TASKS.md`.

---

## 11. Câu chuyện demo (15 phút)

Kịch bản chính khi trình diễn:

1. **(2') CEO mở app buổi sáng** → thấy 2 việc cần quyết, 1 rủi ro mới
2. **(2') Click vào cảnh báo doanh thu** → xem nguyên nhân + nguồn
3. **(2') Chuyển vai CFO** → dashboard đổi → xem chi tiết ngân sách
4. **(5') Vào "Nạp doanh nghiệp"** → upload 7 tài liệu mẫu → AI xử lý
5. **(2') Vào Review** → duyệt 1 tài liệu → thấy dữ liệu vào hệ thống
6. **(2') Quay lại CEO dashboard** → thấy dữ liệu mới + drill-down đến tài liệu gốc

Chi tiết đầy đủ ở `09-BUILD-PLAN-TASKS.md`.

---

## 12. Thuật ngữ

| Thuật ngữ | Định nghĩa |
|---|---|
| **Aureon** | Tên sản phẩm |
| **IDP** | Intelligent Document Processing — xử lý tài liệu thông minh |
| **Extraction** | Trích xuất trường từ tài liệu |
| **Metric** | Chỉ số hiển thị trên dashboard |
| **Alert** | Cảnh báo sinh từ ngưỡng metric |
| **Drill-down** | Đi từ số → chi tiết → nguồn |
| **Autonomy Level** | Mức tự chủ của AI (L0–L4) |
| **Ground truth** | Dữ liệu đúng để đối chiếu AI |
| **Straight-through** | Tài liệu được ghi tự động không cần review |
| **Extraction Schema** | Cấu hình trường cần trích cho từng loại tài liệu |
| **Lineage** | Truy vết nguồn gốc dữ liệu |
| **Reviewer** | Người duyệt kết quả AI trích xuất |

---

## 13. Liên kết

| Chủ đề | File |
|---|---|
| Personas & quyền | `02-PERSONAS-PERMISSIONS.md` |
| Dashboard spec | `03-DASHBOARD-SPEC.md` |
| IDP feature | `04-IDP-FEATURE-SPEC.md` |
| Data model | `05-DATA-MODEL.md` |
| UI/UX | `06-UI-UX-SPEC.md` |
| Kiến trúc kỹ thuật | `07-TECH-ARCHITECTURE.md` |
| Demo data | `08-DEMO-DATA-SPEC.md` |
| Build plan | `09-BUILD-PLAN-TASKS.md` |
| API contract | `10-API-SPECIFICATION.md` |
| Agent workflow | `11-AGENT-WORKFLOW.md` |
| Governance | `12`, `13`, `14` |

---

## 14. Version

- **Version:** 1.0.0
- **Last updated:** 2026-10-16
- **Applies to:** Aureon Demo v1.0
- **Maintainer:** @CyEyes