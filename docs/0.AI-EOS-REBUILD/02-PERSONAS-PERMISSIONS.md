# 02 — Personas & Permissions (AI-EOS, nhánh `ai-eos`)

> **Nguồn chuẩn:** `_reference/SOURCE-BRD-v1.1.md` §3 (vai trò, RACI), §5.2 (D02 Admin & Security), §11.6 (Autonomy), §17 (governance, Approval Matrix, audit); `SOURCE-UIUX.md` §2 (persona).
> **Phụ thuộc:** 00, 01, `TRACEABILITY-SKELETON.md` §5. **Trạng thái:** 🟡 draft (Phase R1). **Ngày:** 2026-10-22 · **Maintainer:** @CyEyes

---

## 1. Stakeholder (BRD §3.1)

CEO · HĐQT/Ban điều hành · COO · CFO/Kế toán trưởng · CHRO/HR · CRO/GĐ kinh doanh · CMO · CTO/CPO · CISO/DPO · Trưởng phòng/Manager · Nhân viên · Reviewer dữ liệu · Admin hệ thống · **AI Agent** (actor thực thi).

## 2. 7 vai trò chuẩn + AI Agent (BRD §3.2)

| ID | Vai trò | Phạm vi dữ liệu | Quyền chính | AI Assistant |
|---|---|---|---|---|
| ROLE-CEO | CEO | Toàn doanh nghiệp | Chiến lược, tài chính, nhân sự, rủi ro, KPI/OKR, phê duyệt cấp cao, báo cáo điều hành | CEO Assistant |
| ROLE-DIR | Executive / Director | Khối hoặc phòng ban phụ trách | Ngân sách, nhân sự, dự án, KPI/OKR, rủi ro của khối | Department Copilot |
| ROLE-MGR | Manager | Team | Task, workload, KPI/OKR, check-in, đánh giá, duyệt dữ liệu của team | Team Copilot |
| ROLE-EMP | Employee | Cá nhân & việc được giao | Hồ sơ, task, mục tiêu, lịch, nhập liệu, tải tài liệu | Personal Assistant |
| ROLE-REV | Reviewer | Hàng chờ được phân | Xem tài liệu gốc, sửa, duyệt, từ chối bản trích xuất | Review Assistant |
| ROLE-ADM | Admin | Cấu hình nền tảng (không mặc định xem nghiệp vụ) | Tổ chức, người dùng, vai trò, quyền, tích hợp, agent, tool, policy, schema tài liệu | Admin Assistant |
| ROLE-AI | AI Agent | **Giao quyền agent ∩ người được phục vụ** | Tool được cấp, theo Autonomy Level + approval rule | — |

- **Doanh nghiệp tạo thêm vai trò tùy biến** (BRD §3).
- **AI Agent** có đủ: Identity, Role, Permission, Scope, Tools, Policies, Approval rules, Budget, Audit trail (BRD §3.2).

### 2.1. Ánh xạ sang 10 role F.O.C.U.S của `main`

CEO→ROLE-CEO · CFO/VP_SALES/HR_MANAGER/CPO/RISK_MANAGER → **ROLE-DIR** (phân biệt bằng data scope + Department Copilot theo khối) · MANAGER→ROLE-MGR · EMPLOYEE→ROLE-EMP · REVIEWER→ROLE-REV · ADMIN→ROLE-ADM · **ROLE-AI = mới** (AI Agent chưa là actor độc lập ở `main`).

## 3. RACI quy trình cốt lõi (BRD §3.3)

| Quy trình | CEO | Director | Manager | Employee | Admin | AI Agent |
|---|---|---|---|---|---|---|
| Đặt chiến lược & OKR công ty | A/R | C | I | I | — | C |
| Đặt KPI/OKR phòng ban | A | R | C | I | — | C |
| Check-in KPI/OKR | I | A | R | R | — | R (nhắc, tổng hợp) |
| Nhập & duyệt dữ liệu từ tài liệu | I | A | R (duyệt) | R (tải) | C | R (trích xuất) |
| Giao việc & cân bằng workload | I | A | R | C | — | C (đề xuất) |
| Phát hiện & xử lý rủi ro | A | R | R | I | — | R (phát hiện) |
| Cấu hình quyền & policy AI | A | C | I | — | R | — |

**AI Agent không bao giờ là A** (chịu trách nhiệm cuối cùng).

## 4. Mô hình phân quyền (BRD §5.2 D02, NFR-SEC-02)

- **FR-ADM-02: RBAC + ABAC + field-level security.** RBAC theo vai trò; ABAC theo thuộc tính (phòng ban, team, chủ sở hữu, mức phân loại); field-level cho trường nhạy cảm (lương, sức khỏe, CCCD).
- **Data scope:** công ty → phòng ban → team → cá nhân.
- **FR-ADM-03: AI access scope** cấu hình theo phòng ban × vai trò × agent × tool.
- **FR-ADM-01:** Admin quản lý Users/Roles/Permissions/Departments/Data policies/AI agents/AI tools/Integrations/Notification rules/Workflows/Approval policies/Document types/Extraction schemas.
- **Default deny**; quyền kiểm tra ở **mọi** tool call của AI (AI-R08).

## 5. Phân loại dữ liệu 4 mức (FR-ADM-05)

| Mức | Model AI được phép |
|---|---|
| Công khai | Cloud + local |
| Nội bộ | Cloud + local |
| Mật | **Chỉ model local/on-prem** (không ra cloud quốc tế) |
| Tuyệt mật | **Không đưa vào model** |

Mức phân loại quyết định model được phép xử lý (gắn với FR-AIQ + NFR-SEC-03). Trường nhạy cảm (lương, MST, tài khoản, CCCD, sức khỏe) → field-level mask kể cả trong audit, event payload, prompt.

## 6. Autonomy Levels L0–L4 (BRD §11.6)

| Level | Tên | AI được làm gì | Mặc định cho |
|---|---|---|---|
| L0 | Inform | Chỉ đọc & trả lời | Mọi tool READ |
| L1 | Suggest | Đề xuất, người tự làm | Phân bổ nguồn lực, nhân sự |
| L2 | Draft & Confirm | AI soạn sẵn, người bấm xác nhận | Ghi dữ liệu tài chính, giao tiếp ngoài |
| L3 | Act & Notify | AI tự làm trong policy, báo lại, **hoàn tác ≥ 24h** | Task, lịch, nhắc việc nội bộ |
| L4 | Autonomous | AI tự làm, chỉ audit + báo cáo định kỳ | **Không bật MVP** (mở ở phase 5) |

- Level cấu hình theo **tool × vai trò × ngưỡng giá trị**.
- Nâng level 1 tool cần số liệu Evaluation Engine + duyệt Admin + chủ domain.
- **Kill switch (FR-ADM-07):** Admin tắt toàn bộ WRITE/EXECUTION của AI hoặc của một agent trong 1 thao tác; kill switch bật → L3 hạ L2.

## 7. Approval Matrix (BRD §17.3)

| Hành động | Autonomy mặc định | Phê duyệt |
|---|---|---|
| Đọc KPI/OKR/task/lịch | L0 | Không |
| Đọc tài chính/nhân sự | L0 theo quyền | Không |
| Trích xuất từ tài liệu | L0 | Không |
| Ghi dữ liệu không trọng yếu (task, biên bản, KPI nguồn tin cậy) | L2 → L3 khi đạt ngưỡng | Theo policy |
| Ghi dữ liệu trọng yếu (tiền, MST, tài khoản, lương) | L2 | **Bắt buộc người duyệt** |
| Tạo/giao task nội bộ | L3 | Có thể, theo policy |
| Tạo sự kiện lịch nội bộ | L3 | Không |
| Chuyển task giữa người | L1 | Manager |
| Gửi email/tin nhắn ra ngoài | L2 | Người gửi xác nhận |
| Phê duyệt ngân sách | Không cho phép | CEO/CFO |
| Tuyển/đổi lương/đánh giá nhân sự | Không cho phép | HR/CEO/ủy quyền |
| Xóa dữ liệu quan trọng | Không cho phép | **Hai người** |
| Đổi quyền / policy AI | Không cho phép | Admin + chủ domain |

**Nguyên tắc cứng (BRD §17.1 #12):** AI **không tự quyết định về con người** (tuyển, sa thải, lương, điểm đánh giá).

## 8. Xác thực & phiên (BRD §5.2, NFR-SEC)

- **FR-ADM-04:** SSO (Google/Microsoft/SAML/OIDC); **MFA bắt buộc** với Admin, CEO, Finance; quản lý phiên.
- **FR-ADM-06:** Tenant isolation hoàn toàn (dữ liệu, vector index, bộ nhớ AI, file) — NFR-SEC-04.
- **FR-ADM-08:** "Xem như người dùng" để kiểm tra quyền, có audit.
- Mã hóa TLS 1.2+ / AES-256; KMS, tùy chọn khóa khách hàng quản lý (P1) — NFR-SEC-03.

## 9. Audit & governance AI (BRD §17.1, §17.4)

- 12 nguyên tắc governance: least privilege · human approval theo Autonomy · data minimization · auditability · explainability · traceability · model governance · prompt security · tool security · bảo vệ dữ liệu nhạy cảm · không train model chung bằng dữ liệu khách khi chưa có đồng ý · **AI không tự quyết về con người**.
- **Audit nghiệp vụ:** Who/What/When/Why/Source/Data/Action/Result/Approval/Source document.
- **Audit AI thêm:** Model+version, Agent, Prompt version, Autonomy Level, Tool, Tool input/output, Decision, Confidence, Chi phí, Người được phục vụ.
- Log **bất biến**, chỉ Admin/CISO/kiểm toán xem toàn bộ; user xem lịch sử AI trên dữ liệu của mình. Báo cáo governance hằng tháng (số hành động/level, tỷ lệ từ chối/hoàn tác, sự cố, chi phí).

## 10. Open questions
- OQ-02-01: ROLE-DIR gộp 5 C-level — có cần tách lại theo khối (Finance/Sales/HR/Product/Risk) như `main` để demo rõ? (Q4)
- OQ-02-02: Ngưỡng giá trị mặc định cho L3 (BRD §21.1) — chờ CEO.
- OQ-02-03: Chính sách AI cloud cho mức "Mật" (local-only) vs cho phép cloud VN — chờ CEO (Q3-liên quan).

## Version
- **Version:** 0.1.0 (draft, Phase R1)
- **Last updated:** 2026-10-22
- **Maintainer:** @CyEyes
- **Change 0.1.0:** Viết lại 02 theo AI-EOS — 7 role + AI Agent actor + ánh xạ `main`, RACI, RBAC+ABAC+field-level, 4 mức phân loại dữ liệu → model, Autonomy L0–L4 + kill switch, Approval Matrix đầy đủ, xác thực/tenant isolation, audit & 12 nguyên tắc governance.
