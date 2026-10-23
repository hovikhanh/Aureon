# 02 — Personas & Permissions (Aureon v3 — AI-EOS)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §3 (stakeholder, 7 role + AI Agent, RACI), §5.2 (D02 Admin & Security — FR-ADM-01..08), §11.3 (phân loại tool), §11.5–11.6 (luồng quyền + Autonomy L0–L4), §14.2 (ví dụ audit trail), §17 (governance — §17.1 nguyên tắc, §17.2 pháp lý VN, §17.3 Approval Matrix, §17.4 audit); `SOURCE-BRD-v1.1-Bổ sung.md` §4.2 (Autonomy), §4.5 (pháp lý VN); `SOURCE-UIUX.md` §2 (persona).
> **Phụ thuộc:** 00, 01, `TRACEABILITY-SKELETON.md` §4 (D02), §5 (role), §9 (AI Platform). **Trạng thái:** ✅ current — Aureon v3 (AI-EOS) CHÍNH THỨC. **Ngày:** 2026-10-23 · **Maintainer:** @CyEyes
> **Phạm vi vòng này:** nâng từ outline lên spec-level P0 — mô tả hành vi + ràng buộc cho từng FR-ADM, chi tiết 4 mức phân loại → chính sách model/cloud, Approval Matrix đủ ngưỡng, định nghĩa từng Autonomy level + ví dụ, 12 nguyên tắc governance §17.1, tuân thủ VN (NĐ 13, hóa đơn ĐT). **Không** field-level DB, không task T-*, không TC-* chi tiết (hoãn sang đợt code — R-DEC-09).

---

## 1. Stakeholder (BRD §3.1)

Hệ thống phục vụ một tập stakeholder rộng nhưng P0 chỉ hiện thực hóa 7 vai trò chuẩn + AI Agent (§2). Các stakeholder cấp cao ánh xạ về ROLE-CEO / ROLE-DIR theo data scope.

| Stakeholder | Quan tâm chính | Ánh xạ role P0 |
|---|---|---|
| CEO | Tình trạng công ty, ngoại lệ, quyết định cần mình | ROLE-CEO |
| HĐQT / Ban điều hành | Báo cáo HĐQT, rủi ro, tuân thủ | ROLE-CEO (scope toàn DN, read) |
| COO | Tiến độ, nguồn lực, quy trình | ROLE-DIR (khối vận hành) |
| CFO / Kế toán trưởng | Dòng tiền, ngân sách, công nợ, chứng từ | ROLE-DIR (khối tài chính) |
| CHRO / HR | Vòng đời nhân sự, hiệu suất, giữ chân | ROLE-DIR (khối nhân sự) |
| CRO / Giám đốc kinh doanh | Pipeline, dự báo, khách hàng | ROLE-DIR (khối kinh doanh) |
| CMO | Lead, chiến dịch, CAC | ROLE-DIR (khối marketing) |
| CTO / CPO | Roadmap, delivery, technical debt | ROLE-DIR (khối sản phẩm/kỹ thuật) |
| CISO / DPO | Quyền truy cập, audit, tuân thủ NĐ 13/2023 | ROLE-ADM (+ quyền xem audit toàn phần) |
| Trưởng phòng / Manager | KPI/OKR, workload, phê duyệt | ROLE-MGR |
| Nhân viên | Việc của mình, mục tiêu, nhập liệu nhanh | ROLE-EMP |
| Reviewer dữ liệu | Hàng chờ review, độ chính xác | ROLE-REV |
| Admin hệ thống | Người dùng, quyền, tích hợp, AI policy | ROLE-ADM |
| **AI Agent** | Tool, phạm vi, phê duyệt | **ROLE-AI** (actor thực thi) |

## 2. 7 vai trò chuẩn + AI Agent (BRD §3.2)

| ID | Vai trò | Phạm vi dữ liệu | Quyền chính | AI Assistant |
|---|---|---|---|---|
| ROLE-CEO | CEO | Toàn doanh nghiệp | Chiến lược, tài chính, nhân sự, rủi ro, KPI/OKR, phê duyệt cấp cao, báo cáo điều hành | CEO Assistant |
| ROLE-DIR | Executive / Director | Khối hoặc phòng ban phụ trách | Ngân sách, nhân sự, dự án, KPI/OKR, rủi ro của khối | Department Copilot |
| ROLE-MGR | Manager | Team | Task, workload, KPI/OKR, check-in, đánh giá, duyệt dữ liệu của team | Team Copilot |
| ROLE-EMP | Employee | Cá nhân & việc được giao | Hồ sơ, task, mục tiêu, lịch, nhập liệu, tải tài liệu | Personal Assistant |
| ROLE-REV | Reviewer | Hàng chờ được phân | Xem tài liệu gốc, sửa, duyệt, từ chối bản trích xuất | Review Assistant |
| ROLE-ADM | Admin | Cấu hình nền tảng (không mặc định xem bản ghi nghiệp vụ) | Tổ chức, người dùng, vai trò, quyền, tích hợp, agent, tool, policy, schema tài liệu | Admin Assistant |
| ROLE-AI | AI Agent | **Giao quyền agent ∩ người được phục vụ** | Tool được cấp, theo Autonomy Level + approval rule | — |

- **Doanh nghiệp tạo thêm vai trò tùy biến** (BRD §3): vai trò mới kế thừa cơ chế RBAC+ABAC, không được vượt quyền mẫu ROLE-CEO.
- **AI Agent** có đủ 9 thuộc tính identity (BRD §3.2): Identity, Role, Permission, Scope, Tools, Policies, Approval rules, Budget, Audit trail. Chi tiết entity `ENT-AIAgent` chốt ở 05 (R-DEC-09).
- **ROLE-ADM không mặc định đọc bản ghi nghiệp vụ** (tài chính, nhân sự, sales) — chỉ cấu hình nền tảng; muốn xem phải dùng "Xem như người dùng" (FR-ADM-08) có audit, hoặc được cấp quyền tường minh.
- **Cơ cấu tổ chức (R-DEC-30, M1.2):** ghi tổ chức/phòng ban/team/chức danh/phân công = permission `hr:admin`, cấp cho ROLE-CEO, ROLE-ADM và ROLE-DIR khối O. ROLE-ADM có `hr:read` với scope `s` = **chỉ cơ cấu** (organization, department, team, position, assignment, cây tổ chức); hồ sơ nhân sự, lương, hiring vẫn bị chặn (`403 FORBIDDEN_SCOPE`) — giữ nguyên tắc trên, đáp ứng FR-ADM-01 (Admin quản lý Departments). ROLE-ADM không được tạo/nâng người dùng lên ROLE-CEO (R-DEC-36).

### 2.1. Ánh xạ sang 10 role F.O.C.U.S của `main`

CEO→ROLE-CEO · CFO/VP_SALES/HR_MANAGER/CPO/RISK_MANAGER → **ROLE-DIR** (phân biệt bằng data scope + Department Copilot theo khối) · MANAGER→ROLE-MGR · EMPLOYEE→ROLE-EMP · REVIEWER→ROLE-REV · ADMIN→ROLE-ADM · **ROLE-AI = mới** (AI Agent chưa là actor độc lập ở `main`). Bảng ánh xạ đầy đủ: `TRACEABILITY-SKELETON.md` §12.

## 3. RACI quy trình cốt lõi (BRD §3.3)

| Quy trình | CEO | Director | Manager | Employee | Admin | AI Agent |
|---|---|---|---|---|---|---|
| Đặt chiến lược & OKR công ty | A/R | C | I | I | — | C (gợi ý, phân tích) |
| Đặt KPI/OKR phòng ban | A | R | C | I | — | C |
| Check-in KPI/OKR | I | A | R | R | — | R (nhắc, tổng hợp) |
| Nhập & duyệt dữ liệu từ tài liệu | I | A | R (duyệt) | R (tải) | C | R (trích xuất) |
| Giao việc & cân bằng workload | I | A | R | C | — | C (đề xuất) |
| Phát hiện & xử lý rủi ro | A | R | R | I | — | R (phát hiện) |
| Cấu hình quyền & policy AI | A | C | I | — | R | — |

R = thực hiện · A = chịu trách nhiệm cuối cùng · C = tham vấn · I = được thông báo. **AI Agent không bao giờ là A** (chịu trách nhiệm cuối cùng) — hệ quả trực tiếp của nguyên tắc §9 #12 (AI không tự quyết về con người) và P04 (Human in the Loop).

## 4. Mô hình phân quyền D02 (BRD §5.2, NFR-SEC-02)

Các FR-ADM dưới đây là **spec hành vi P0** của domain D02 Administration & Security; field-level DB (bảng, cột, constraint) hoãn sang đợt code (R-DEC-09).

| FR | Tên | Hành vi + ràng buộc (spec-level) |
|---|---|---|
| **FR-ADM-01** | Quản trị cấu hình nền tảng | Admin quản lý tập đối tượng cấu hình: Users, Roles, Permissions, Departments, Data policies, AI agents, AI tools, Integrations, Notification rules, Workflows, Approval policies, Document types, Extraction schemas. Mọi thay đổi cấu hình là hành động ghi → bắt buộc ghi audit (§9) và không ảnh hưởng bản ghi nghiệp vụ hiện có ngoài phạm vi policy. Admin **không** đọc bản ghi nghiệp vụ qua màn hình cấu hình. |
| **FR-ADM-02** | RBAC + ABAC + field-level security | Phân quyền 3 tầng: **RBAC** theo vai trò (§2); **ABAC** theo thuộc tính (phòng ban, team, chủ sở hữu, mức phân loại dữ liệu); **field-level** cho trường nhạy cảm (lương, dữ liệu sức khỏe, CCCD). Data scope phân cấp **công ty → phòng ban → team → cá nhân**; mặc định mỗi vai trò chỉ thấy scope của mình. Trường nhạy cảm bị mask với vai trò không đủ quyền, kể cả trong audit, event payload và prompt gửi model. |
| **FR-ADM-03** | AI access scope | Phạm vi truy cập của AI cấu hình theo **phòng ban × vai trò × agent × tool**: xác định một agent được dùng tool nào, trên dữ liệu phòng ban/scope nào. Quyền hiệu lực khi AI chạy = **giao của quyền agent và quyền người được phục vụ** (BRD §11.5); AI chạy theo sự kiện/lịch (không có người hỏi) dùng danh tính service của agent với quyền hẹp nhất có thể. |
| **FR-ADM-04** | Xác thực & phiên | **SSO** Google/Microsoft/SAML/OIDC; **MFA bắt buộc** với vai trò quản trị (ROLE-ADM) và tài chính (ROLE-CEO, ROLE-DIR khối tài chính); quản lý phiên đăng nhập (hết hạn, thu hồi, xem phiên đang mở). Chi tiết cơ chế token hoãn sang 07/10 (R-DEC-09). |
| **FR-ADM-05** | Phân loại dữ liệu 4 mức | Mỗi dữ liệu/tài liệu gắn một trong 4 mức (§5); **mức phân loại quyết định model AI được phép xử lý** (gắn FR-AIQ + NFR-SEC-03). Mức mặc định khi chưa phân loại = "Nội bộ"; nâng mức là hành động có audit. |
| **FR-ADM-06** | Tenant isolation | Cô lập hoàn toàn theo tenant: dữ liệu nghiệp vụ, vector index, bộ nhớ AI, file lưu trữ (NFR-SEC-04). Mọi entity nghiệp vụ mang `tenant_id` (R-DEC-07) — single-tenant triển khai nhưng không rò rỉ chéo tenant ở mọi lớp query/retrieval/prompt. |
| **FR-ADM-07** | Kill switch | Admin tắt **toàn bộ** hành động WRITE/EXECUTION của AI — hoặc của **một agent** — trong **một thao tác**. Kill switch bật → mọi tool WRITE/EXECUTION bị chặn; **L3 hạ thành L2** (chỉ soạn, chờ người xác nhận); READ/L0 không bị ảnh hưởng. Bật/tắt kill switch là hành động có audit, hiển thị banner cảnh báo (UI). |
| **FR-ADM-08** | "Xem như người dùng" | Admin/được ủy quyền giả lập phiên của một người dùng để kiểm tra quyền thấy đúng những gì người đó thấy. Phiên giả lập **luôn ghi audit** (ai xem như ai, khi nào, bao lâu), không được dùng để thực hiện hành động ghi thay người bị giả lập. |

- **Default deny** (P08): quyền không được cấp tường minh thì bị từ chối; quyền được kiểm tra ở **mọi** tool call của AI trước khi thực thi (AI-R08).
- Nguồn truy nguyên: FR-ADM-01..08 (BRD §5.2); NFR-SEC-02/03/04.

## 5. Phân loại dữ liệu 4 mức → chính sách model/cloud (FR-ADM-05)

| Mức | Mô tả | Model AI được phép | Cloud / On-prem |
|---|---|---|---|
| **Công khai** | Dữ liệu công bố được, không rủi ro | Cloud + local, mọi provider duyệt | Cloud quốc tế OK |
| **Nội bộ** | Dữ liệu vận hành nội bộ, không PII nhạy cảm | Cloud + local, provider trong danh mục duyệt | Cloud quốc tế OK (trong policy) |
| **Mật** | Tài chính, nhân sự, hợp đồng, PII cơ bản | **Chỉ model local/on-prem** (không ra cloud quốc tế) | On-prem / cloud VN theo policy (OQ-02-03) |
| **Tuyệt mật** | Bí mật kinh doanh, PII nhạy cảm đặc biệt | **Không đưa vào model** (không prompt, không embed) | Không rời hệ thống |

- Quy tắc cứng: **Mật → không fallback sang cloud quốc tế**; **Tuyệt mật → không LLM** dưới mọi hình thức (kể cả tóm tắt). Model Gateway là model-agnostic, hỗ trợ model on-prem cho dữ liệu Mật (BRD Bổ sung §4.4).
- **Trường nhạy cảm** (lương, lịch sử lương, MST, số tài khoản, CCCD, dữ liệu sức khỏe, ngày sinh, địa chỉ) → **field-level mask** kể cả trong audit log, event payload và prompt gửi model; chỉ ROLE-CEO và ROLE-DIR khối nhân sự (và ROLE-REV trong phiên review được phân) thấy giá trị thật.
- Liên kết: FR-AIQ (grounding + chi phí) và NFR-SEC-03 (mã hóa TLS 1.2+/AES-256, KMS). Chính sách cloud cho mức "Mật" còn mở — xem OQ-02-03.

## 6. Autonomy Levels L0–L4 (BRD §11.6, Bổ sung §4.2)

Định nghĩa từng mức, hành vi cho phép và ví dụ. **P0 bật L0–L3**; **L4 không bật trong MVP** (mở ở phase 5 — R-DEC-05).

| Level | Tên | AI được làm gì | Ví dụ hành vi | Mặc định cho |
|---|---|---|---|---|
| **L0** | Inform | **Chỉ đọc & trả lời**, không thay đổi dữ liệu | "Doanh thu tháng này?" → trả số kèm nguồn | Mọi tool READ |
| **L1** | Suggest | **Đề xuất, người tự thực hiện** — AI không tự ghi | "Gợi ý chuyển task từ B sang C" → người tự chuyển | Phân bổ nguồn lực, nhân sự |
| **L2** | Draft & Confirm | **AI soạn sẵn, người bấm xác nhận** mới ghi | Soạn bản ghi từ hóa đơn / email gửi khách → người xác nhận | Ghi dữ liệu tài chính, giao tiếp ra ngoài |
| **L3** | Act & Notify | **AI tự làm trong policy, báo lại**; có nút **hoàn tác ≥ 24h** | Tạo task từ biên bản họp (UC-06); đặt nhắc việc nội bộ | Task, lịch, nhắc việc nội bộ |
| **L4** | Autonomous | AI tự làm, chỉ ghi audit + báo cáo định kỳ | Cập nhật KPI từ nguồn tích hợp đã tin cậy | **Không bật MVP** (phase 5) |

- **Cấu hình theo tool × vai trò × ngưỡng giá trị.** Ví dụ ngưỡng (BRD §11.6): chi phí < 5 triệu → L3; ≥ 5 triệu → L2 + quản lý duyệt. Ngưỡng L3 mặc định cho MVP còn chờ CEO (OQ-02-02).
- **Hoàn tác:** mọi hành động L3 trở lên có nút hoàn tác tối thiểu 24 giờ khi bản chất hành động cho phép (undo không áp dụng cho hành động không thể đảo, VD email đã gửi ra ngoài).
- **Nâng level 1 tool** cần: số liệu chất lượng từ Evaluation Engine + duyệt Admin + chủ domain (BRD §11.6).
- **Nhãn UI** (đồng bộ 06): L1 = "AI gợi ý" · L2 = "AI soạn" · L3 = "AI đã làm".
- **Kill switch (FR-ADM-07):** bật → L3 tự hạ xuống L2; L4 luôn bị khóa ở MVP.
- **Phân loại tool** (BRD §11.3) chi phối Autonomy áp dụng: READ (L0) · WRITE (L2/L3) · APPROVAL (**AI không được tự gọi** — chuyển người duyệt) · EXECUTION (tác động ra ngoài, tối thiểu L2 + xác nhận người gửi).

## 7. Approval Matrix (BRD §17.3)

Ngưỡng và người duyệt theo loại hành động. "Không cho phép" = AI không bao giờ tự thực thi, phải chuyển con người quyết.

| Hành động | Autonomy mặc định | Phê duyệt bắt buộc |
|---|---|---|
| Đọc KPI/OKR/task/lịch | L0 | Không |
| Đọc tài chính/nhân sự | L0 theo quyền người dùng | Không |
| Trích xuất dữ liệu từ tài liệu | L0 | Không |
| Ghi dữ liệu không trọng yếu (task, biên bản, KPI từ nguồn tin cậy) | L2 → L3 khi đạt ngưỡng | Theo policy |
| Ghi dữ liệu **trọng yếu** (tiền, MST, tài khoản, lương) | L2 | **Bắt buộc người duyệt** |
| Tạo / giao task nội bộ | L3 | Có thể, theo policy |
| Tạo sự kiện lịch nội bộ | L3 | Không |
| Chuyển task giữa người (cân bằng workload) | L1 | Manager |
| Gửi email / tin nhắn ra ngoài | L2 | Người gửi xác nhận |
| Phê duyệt ngân sách | **Không cho phép** | CEO / CFO |
| Tuyển dụng / thay đổi lương / đánh giá nhân sự | **Không cho phép** | HR / CEO / người được ủy quyền |
| Xóa dữ liệu quan trọng | **Không cho phép** | **Hai người** |
| Thay đổi quyền / policy AI | **Không cho phép** | Admin + chủ domain |

- **Ngưỡng giá trị** quyết định bước nhảy L2↔L3 (VD chi phí < 5 triệu → L3; ≥ 5 triệu → L2 + duyệt). Ngưỡng cụ thể là cấu hình theo tenant (OQ-02-02, chờ CEO — B5).
- **Trường trọng yếu luôn qua người** — khớp quy tắc IDP: số tiền, số tài khoản, MST, lương, giá trị hợp đồng không bao giờ STP tự động.
- **Nguyên tắc cứng (BRD §17.1 #12):** AI **không tự quyết định về con người** (tuyển, sa thải, lương, điểm đánh giá) — mọi dòng "Tuyển/đổi lương/đánh giá" và "Phê duyệt ngân sách" đều "Không cho phép".

## 8. Xác thực, phiên & tenant isolation (BRD §5.2, NFR-SEC)

- **FR-ADM-04:** SSO (Google/Microsoft/SAML/OIDC); **MFA bắt buộc** với Admin, CEO, Finance; quản lý phiên (hết hạn, thu hồi, danh sách phiên).
- **FR-ADM-06:** Tenant isolation hoàn toàn (dữ liệu, vector index, bộ nhớ AI, file) — NFR-SEC-04; `tenant_id` trên mọi entity nghiệp vụ (R-DEC-07).
- **FR-ADM-08:** "Xem như người dùng" để kiểm tra quyền, luôn có audit; không dùng để ghi thay.
- Mã hóa TLS 1.2+ / AES-256; KMS, tùy chọn khóa do khách hàng quản lý (P1) — NFR-SEC-03.
- Cơ chế token/khóa/kid cụ thể hoãn sang 07/10 (R-DEC-09).

## 9. Audit & governance AI (BRD §17.1, §17.4)

### 9.1. 12 nguyên tắc AI governance (BRD §17.1)

1. **Least privilege** — cấp quyền tối thiểu đủ dùng.
2. **Human approval theo Autonomy Level** — hành động vượt ngưỡng phải có người duyệt (P04).
3. **Data minimization** — chỉ đưa vào model dữ liệu cần cho tác vụ.
4. **Auditability** — mọi hành động quan trọng ghi lại, kiểm tra được.
5. **Explainability** — insight/khuyến nghị giải thích được (cấu trúc 9 phần §11.8 BRD).
6. **Traceability** — mọi con số truy nguyên về nguồn (P06), lineage tới bản ghi/trang tài liệu.
7. **Model governance** — danh mục model được duyệt, đánh giá trước khi đưa vào dùng.
8. **Prompt security** — chống prompt injection từ mọi nguồn nội dung ngoài (FR-AIQ-06).
9. **Tool security** — tool có metadata quyền/rủi ro; AI không tự gọi tool APPROVAL.
10. **Bảo vệ dữ liệu nhạy cảm** — field-level mask, phân loại 4 mức, không rò rỉ ra prompt.
11. **Không train model chung bằng dữ liệu khách khi chưa có đồng ý bằng văn bản.**
12. **AI không tự ra quyết định về con người** (tuyển, sa thải, lương, điểm đánh giá).

### 9.2. Nội dung audit (BRD §17.4)

- **Audit nghiệp vụ** ghi: Who / What / When / Why / Source / Data / Action / Result / Approval / Source document.
- **Audit AI thêm:** Model + phiên bản · Agent · Prompt/Instruction version · Autonomy Level áp dụng · Tool · Tool input · Tool output · Decision · Confidence · Chi phí · Người được phục vụ.
- **Ví dụ audit trail** (BRD §14.2): CEO hỏi "Đánh giá khả năng đạt doanh thu" → CEO Agent gọi `get_sales_pipeline`, `get_financial_forecast`, `get_employee_capacity` → kết quả 72% + khuyến nghị → CEO APPROVED → AI `create_task`/`assign_task`/`create_calendar_event` (L3) → verification task tạo thành công → Decision Log ghi, hẹn đối chiếu 30 ngày.
- Log **bất biến** (append-only), chỉ Admin/CISO/kiểm toán xem toàn bộ; người dùng xem được lịch sử hành động AI trên dữ liệu của mình.
- **Báo cáo governance hằng tháng:** số hành động theo level, tỷ lệ bị từ chối/hoàn tác, sự cố, chi phí.

### 9.3. Tuân thủ pháp lý Việt Nam (BRD §17.2, Bổ sung §4.5)

- **NĐ 13/2023/NĐ-CP & Luật Bảo vệ dữ liệu cá nhân:** quản lý consent (ứng viên, nhân viên, người tham gia họp); phân loại dữ liệu cá nhân cơ bản vs nhạy cảm; quyền truy cập/sửa/xóa của chủ thể dữ liệu; hồ sơ đánh giá tác động xử lý dữ liệu (DPIA); kiểm soát chuyển dữ liệu ra nước ngoài khi dùng AI cloud (gắn với mức phân loại §5); thông báo vi phạm trong thời hạn luật định.
- **Ghi âm cuộc họp:** thông báo rõ cho mọi người, cơ chế từ chối, chính sách lưu & xóa bản ghi.
- **Kế toán & hóa đơn điện tử (NĐ 123/2020 + sửa đổi):** đọc hóa đơn điện tử theo NĐ 123, lưu chứng từ theo Luật Kế toán; **AI-EOS không thay thế phần mềm kế toán** (tích hợp MISA/Fast/Bravo).
- **Chữ ký số** cho phê duyệt có giá trị pháp lý — **P1** (phase 2+).
- **Luật An ninh mạng:** đáp ứng yêu cầu lưu trữ & bảo vệ dữ liệu khi áp dụng.
- Danh mục văn bản cần bộ phận pháp chế xác nhận hiệu lực tại thời điểm triển khai.

## 10. Open questions
- OQ-02-01: ROLE-DIR gộp 5 C-level — ĐÃ CHỐT: R-DEC-08 — giữ 7 role BRD + AI Agent; ROLE-DIR có data scope thay 5 C-level, giữ bảng ánh xạ sang 10 role F.O.C.U.S của `main` (§2.1, skeleton §12).
- OQ-02-02: Ngưỡng giá trị mặc định cho L3 (BRD §21.1) — chờ CEO (B5). Ảnh hưởng §6, §7 (bước nhảy L2↔L3).
- OQ-02-03: Chính sách AI cloud cho mức "Mật" (local-only) vs cho phép cloud VN — chờ CEO (B3). Ảnh hưởng §5 (cột cloud/on-prem).
- OQ-02-04: Entity `ENT-AIAgent`/`ENT-AIAudit` (9 thuộc tính identity, nội dung audit §9.2) chốt field/kiểu/quan hệ ở 05 — hoãn sang đợt code (R-DEC-09).

## Version
- **Version:** 1.0.0 (current)
- **Last updated:** 2026-10-23
- **Maintainer:** @CyEyes
- **Change 1.0.1 (đề xuất — M1.2, human duyệt R-DEC-30/36 2026-10-23):** §2 thêm ghi chú quyền cơ cấu `hr:admin` (CEO/ADM/DIR-O), ADM `hr:read` scope `s` chỉ cơ cấu, ADM không cấp ROLE-CEO.
- **Change 1.0.0 (promote):** Promote tài liệu AI-EOS lên CHÍNH THỨC Aureon v3; di chuyển vào vị trí docs chuẩn; v2.1 archived (docs/_archive/v2.1/).
- **Change 0.3.0:** Mở rộng spec-level P0 bám canonical: §1 bảng stakeholder + ánh xạ role; §4 mô tả hành vi + ràng buộc từng FR-ADM-01..08; §5 4 mức phân loại → chính sách model/cloud + quy tắc fallback + field-level mask; §6 định nghĩa từng Autonomy L0–L4 kèm ví dụ hành vi + phân loại tool READ/WRITE/APPROVAL/EXECUTION + nhãn UI; §7 Approval Matrix đủ ngưỡng theo loại hành động; §9.1 liệt kê 12 nguyên tắc governance §17.1, §9.2 nội dung audit + ví dụ audit trail §14.2, §9.3 tuân thủ VN (NĐ 13, NĐ 123, ghi âm họp, chữ ký số, an ninh mạng); thêm OQ-02-04. Không field-level DB / T-* / TC-* (R-DEC-09).
- **Change 0.2.0:** Chốt Q1–Q6 (R-DEC-05..10) — cập nhật trạng thái quyết định, đóng OQ liên quan; phạm vi docs-first P0.
- **Change 0.1.0:** Viết lại 02 theo AI-EOS — 7 role + AI Agent actor + ánh xạ `main`, RACI, RBAC+ABAC+field-level, 4 mức phân loại dữ liệu → model, Autonomy L0–L4 + kill switch, Approval Matrix đầy đủ, xác thực/tenant isolation, audit & 12 nguyên tắc governance.
