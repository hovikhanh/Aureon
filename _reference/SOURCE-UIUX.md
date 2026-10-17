# AI-EOS — Đề xuất UI/UX v1.0

Oct 5, 2026 · @CyEyes

## 1. Tóm tắt

AI-EOS không nên trông như một ERP có thêm chatbot. Giao diện nên được xây quanh ba hành động mà người dùng làm nhiều nhất: **xem ngoại lệ, hỏi AI, và duyệt việc AI đã chuẩn bị**. Module nghiệp vụ (KPI, task, tài chính...) vẫn có đầy đủ nhưng lùi về lớp thứ hai.

Bản đề xuất này dựa trên BRD v1.1 (7 vai trò, 28 domain, khoảng 100 user story) và đưa ra 6 quyết định UX chính:

1. **Trang chủ theo vai trò, lấy ngoại lệ làm trung tâm.** CEO thấy Briefing và "việc chờ tôi quyết", Manager thấy team và hàng chờ duyệt, Employee thấy việc hôm nay. Không dùng một dashboard chung cho mọi người.
2. **Một thanh AI dùng được ở mọi màn hình** (⌘K / Ctrl+K): hỏi, ra lệnh, nhập liệu bằng lời, thả file. AI biết người dùng đang ở đâu và đang xem gì.
3. **Mọi con số đều bấm vào được** để xem nguồn, thời điểm cập nhật và tài liệu gốc. Đây là cơ chế chính để tạo niềm tin vào AI.
4. **Nhập liệu không có "màn hình nhập liệu"**: thả file vào bất kỳ đâu, chụp ảnh trên mobile, hoặc nói; mọi thứ về một Hộp thư dữ liệu và màn hình Review song song.
5. **Mỗi Autonomy Level có một mẫu giao diện cố định** (gợi ý, bản nháp chờ xác nhận, đã làm + hoàn tác) để người dùng luôn biết AI đã làm gì và còn chờ gì.
6. **Mobile chỉ làm 4 việc thật tốt**: đọc Briefing, hỏi AI, chụp/gửi tài liệu, duyệt. Cấu hình và phân tích sâu ở desktop.

## 2. Phân tích người dùng

Năm persona (xây từ BRD và giả định, cần kiểm chứng bằng phỏng vấn) có nhu cầu và bối cảnh dùng rất khác nhau; cảm nhận về sản phẩm sẽ do CEO quyết định, còn việc sản phẩm có được dùng hay không do Employee và Reviewer quyết định.

### 2.1. Persona

| Persona | Mục tiêu khi mở AI-EOS | Bối cảnh và thiết bị | Tần suất | Nỗi đau hiện tại | User story then chốt |
| --- | --- | --- | --- | --- | --- |
| **CEO** — "Biết ngay, quyết nhanh" | Biết công ty có ổn không, cái gì cần mình, giao việc | Mobile buổi sáng và giữa các cuộc họp; desktop khi chuẩn bị họp, HĐQT | Nhiều lần/ngày, mỗi lần 1–5 phút | Phải hỏi từng người, số liệu vênh nhau, không biết việc đã giao đi đến đâu | US-CEO-001…008, US-KPI-007, US-OKR-005, US-STR-003 |
| **Director / Manager** — "Giữ team đúng hướng" | Theo dõi KPI/OKR, workload, duyệt việc, chuẩn bị báo cáo lên trên | Desktop là chính; mobile để duyệt | Hằng ngày, 15–60 phút | Tốn thời gian tổng hợp báo cáo, không thấy ai quá tải | US-TASK-001…004, US-KPI-002…006, US-OKR-007, US-MTG-002 |
| **Employee** — "Làm việc, ít khai báo" | Biết hôm nay làm gì, cập nhật tiến độ nhanh, gửi chứng từ | Mobile và desktop xen kẽ; thời gian ngắn | Hằng ngày, vài phút | Nhập liệu lặp lại, báo cáo nhiều nơi | US-TASK-002, US-OKR-006, US-DC-001…003, US-DC-009 |
| **Reviewer dữ liệu** (kế toán, thư ký, admin phòng ban) — "Duyệt nhanh, không sai" | Xử lý hàng chờ tài liệu AI trích xuất | Desktop màn hình lớn, bàn phím | Nhiều giờ/ngày vào cao điểm | Nhập tay từ giấy, sợ sai số tiền | US-DC-006, US-DC-007, US-DC-010 |
| **Admin** — "Cấu hình an toàn" | Thiết lập tổ chức, quyền, AI policy, schema tài liệu | Desktop | Theo đợt | Sợ AI vượt quyền, khó kiểm tra quyền | US-ORG-002…004, US-AI-004…008, US-DC-008 |

### 2.2. Phân tích user stories theo loại tác vụ

Gộp khoảng 100 user story theo tác vụ giao diện cho thấy 5 mẫu tương tác chiếm gần hết sản phẩm; thiết kế tốt 5 mẫu này là thiết kế được phần lớn hệ thống.

| Mẫu tương tác | Ví dụ user story | Thành phần UI cần có |
| --- | --- | --- |
| **Theo dõi & phát hiện** (xem tình trạng, so sánh, cảnh báo) | US-CEO-002/003, US-KPI-005/007, US-OKR-005, US-TASK-003/006, US-FIN-003 | Briefing, thẻ chỉ số có trạng thái, bảng so sánh, cây alignment, heatmap workload |
| **Hỏi & phân tích** (hỏi tự nhiên, tìm nguyên nhân, dự báo) | US-CEO-001/004, US-KPI-008…010, US-OKR-008/009, US-SAL-004 | Thanh AI, câu trả lời có trích dẫn, Insight card, bước suy luận hiển thị |
| **Nhập & duyệt dữ liệu** | US-DC-001…012, US-ORG-004, US-OKR-006 | Drop zone toàn cục, Hộp thư dữ liệu, Review song song, import grid, form thông minh |
| **Giao việc & thực thi** | US-CEO-005, US-TASK-001/002/004, US-MTG-002 | Action card, danh sách/Kanban, gợi ý phân bổ, biên bản → task |
| **Thiết lập & quản trị** | US-KPI-001…004, US-OKR-001…003, US-PERF-001, US-ORG-002/003, US-AI-004…008 | Wizard có AI soạn sẵn, ma trận quyền, công cụ "xem như người dùng", bảng điều khiển AI |

### 2.3. Phát hiện quan trọng cho thiết kế

- **CEO dùng theo nhịp ngắn.** Phần lớn lượt dùng của CEO dưới 5 phút, nên màn hình đầu tiên phải trả lời "có gì cần tôi?" mà không cần cuộn hay bấm.
- **Niềm tin quyết định mức sử dụng.** Sai một con số trước HĐQT là CEO bỏ dùng. Nguồn, độ mới dữ liệu và độ tin cậy phải luôn hiển thị, nhưng không chiếm chỗ.
- **Employee quyết định chất lượng dữ liệu.** Nếu cập nhật một task hay gửi một chứng từ mất quá 10 giây, dữ liệu sẽ thiếu và cả hệ thống mất giá trị.
- **Reviewer là người dùng "chuyên nghiệp".** Họ cần mật độ cao, phím tắt, xử lý hàng loạt — ngược với CEO cần tối giản.
- **AI làm việc cả khi không ai hỏi.** Giao diện phải có chỗ cho "việc AI đã làm" và "việc AI đề xuất", tách khỏi thông báo thường.

## 3. Nguyên tắc UX

Tám nguyên tắc dưới đây là tiêu chí để duyệt mọi thiết kế; một màn hình vi phạm nguyên tắc nào thì phải nêu lý do.

| # | Nguyên tắc | Ý nghĩa trên giao diện | Kiểm tra nhanh |
| --- | --- | --- | --- |
| U1 | **Ngoại lệ trước, chi tiết sau** | Màn hình đầu tiên chỉ hiện điều lệch kế hoạch, việc cần quyết, rủi ro mới. Mọi thứ "bình thường" gộp thành một dòng | CEO trả lời được "có gì cần tôi?" trong 10 giây |
| U2 | **Hỏi ở bất kỳ đâu** | Thanh AI luôn sẵn (⌘K), hiểu ngữ cảnh màn hình hiện tại ("tại sao KPI này thấp?") | Không cần chuyển trang để hỏi |
| U3 | **Mọi con số có nguồn** | Con số bấm được, mở popover: công thức, nguồn, cập nhật lúc nào, bản ghi và tài liệu gốc | Không có con số "mồ côi" |
| U4 | **AI hiển thị trạng thái thật** | Phân biệt rõ: AI gợi ý / AI soạn chờ duyệt / AI đã làm. Không để AI "âm thầm" thay đổi dữ liệu | Người dùng luôn trả lời được "AI vừa làm gì?" |
| U5 | **Nhập một lần, nhập ở đâu cũng được** | Thả file vào bất kỳ màn hình nào, AI đoán đích đến theo ngữ cảnh; không bắt người dùng chọn module trước | Cập nhật task/tiến độ ≤ 10 giây; gửi chứng từ ≤ 3 chạm trên mobile |
| U6 | **Hành động ngay tại chỗ** | Mỗi insight, cảnh báo có nút hành động (giao việc, hỏi thêm, bỏ qua) ngay trên thẻ | Không có cảnh báo "chỉ để xem" |
| U7 | **Hai mật độ cho hai kiểu người** | Chế độ Thoáng cho lãnh đạo, chế độ Gọn cho Reviewer, Finance, Admin; cùng component | Reviewer xử lý bằng bàn phím hoàn toàn |
| U8 | **Tiếng Việt là mặc định** | Nhãn, số, ngày theo chuẩn Việt Nam (1.250.000 đ; 05/10/2026); thuật ngữ quản trị quen thuộc giữ tiếng Anh (KPI, OKR, pipeline) | Không có nhãn dịch máy gượng gạo |

## 4. Kiến trúc thông tin và điều hướng

Điều hướng tổ chức theo **việc người dùng muốn làm**, không theo 28 domain kỹ thuật: 28 domain được gộp vào 8 mục, còn phần Quản trị nằm riêng.

&#91;embedded content: kiến trúc thông tin · 8 mục điều hướng\]

Thanh trên cùng là nơi người dùng bắt đầu phần lớn tác vụ; thanh trái dùng khi cần vào sâu một module.

### 4.1. Hiển thị theo vai trò

| Mục | CEO | Director / Manager | Employee | Reviewer | Admin |
| --- | --- | --- | --- | --- | --- |
| Trang chủ | Briefing công ty, việc chờ quyết | Briefing đơn vị, hàng chờ duyệt | Việc hôm nay, mục tiêu của tôi | Hàng chờ review, SLA | Tình trạng hệ thống, sự cố AI |
| Hỏi AI | Toàn công ty | Trong đơn vị | Dữ liệu của tôi và team | Tài liệu được phân | Cấu hình, audit |
| Mục tiêu | Toàn bộ | Đơn vị và cấp dưới | Của tôi, xem mục tiêu cha | — | — |
| Công việc | Tổng quan thực thi | Team, workload | Task của tôi | — | — |
| Họp và lịch | Có | Có | Có | — | — |
| Dữ liệu | Xem tài liệu gốc | Duyệt của đơn vị | Gửi lên, theo dõi | Toàn bộ hàng chờ được phân | Schema, ngưỡng |
| Kinh doanh | Toàn bộ | Theo quyền | Theo quyền | Theo quyền | — |
| Tri thức, báo cáo | Có | Có | Tri thức | Tri thức | Audit |

### 4.2. Quy tắc điều hướng

- Mục không có quyền thì ẩn hẳn, không hiện rồi báo lỗi.
- Người có nhiều vai trò (vd. Director kiêm Reviewer) đổi ngữ cảnh ở thanh trên; Trang chủ đổi theo.
- Breadcrumb luôn theo chuỗi nghiệp vụ: Chiến lược › Objective › KR › Dự án › Task, để người dùng thấy việc mình làm đóng góp vào đâu (P06 Traceability).
- Mọi entity có trang chi tiết cùng bố cục: tiêu đề và trạng thái, chỉ số chính, tab (Tổng quan, Liên kết, Lịch sử, Tài liệu gốc, Hoạt động AI), panel AI bên phải.

## 5. Luồng người dùng chính

Năm luồng dưới đây bao phủ các use case MVP; mỗi luồng có mục tiêu số thao tác và thời gian để kiểm thử khả dụng.

### F1. CEO buổi sáng: từ Briefing đến giao việc (UC-01, UC-03) — mục tiêu ≤ 2 phút, ≤ 5 chạm

1. 07:00 nhận thông báo "Briefing sẵn sàng: 2 việc cần anh, 1 rủi ro mới".
2. Mở Trang chủ: thấy 4 chỉ số sức khỏe, khối "Cần anh quyết", khối "Rủi ro".
3. Chạm thẻ "Doanh thu tháng 9 đạt 82% kế hoạch" → panel AI mở ra: nguyên nhân, bằng chứng, nguồn.
4. Chọn "Phương án 1: CEO tham gia 2 deal lớn" → Action card hiện sẵn task, owner, hạn, lịch.
5. Bấm Xác nhận → toast "Đã tạo 3 task, đặt 2 lịch · Hoàn tác"; quyết định vào Decision Log.

### F2. Gửi tài liệu và AI trích xuất (US-DC-003, 006) — gửi ≤ 3 chạm, review ≤ 60 giây

1. Thả file vào bất kỳ màn hình nào (hoặc bấm Chụp trên mobile, hoặc chuyển tiếp email).
2. Ngay lập tức: thẻ tiến trình "Đang đọc 3 file" ở góc màn hình; người dùng làm việc khác bình thường.
3. AI phân loại xong: "2 biên bản họp, 1 báo cáo KPI. 1 cần anh xem lại".
4. Mở Review: tài liệu gốc bên trái, trường trích xuất bên phải; trường vàng/đỏ cần xem; Tab đi qua từng trường.
5. Enter để duyệt → dữ liệu ghi vào domain đích; toast có link "Xem bản ghi" và "Hoàn tác".

### F3. Biên bản họp thành việc (UC-02, UC-06) — mục tiêu ≤ 10 phút kể cả duyệt

1. Người chủ trì tải biên bản hoặc transcript vào cuộc họp trên Lịch.
2. AI trả về bản tóm tắt với 3 khối: Quyết định, Việc cần làm, Vấn đề mở.
3. Bảng action item: tên người đã khớp với danh bạ (avatar), hạn đã quy ra ngày; mục chưa chắc gắn dấu hỏi.
4. Người chủ trì sửa trực tiếp trong bảng, bấm "Giao việc".
5. Mỗi người nhận task kèm trích đoạn biên bản gốc.

### F4. Check-in KPI/OKR của nhân viên (US-OKR-006) — mục tiêu ≤ 30 giây

1. Thứ Sáu, thông báo "Check-in tuần: 2 KR của bạn".
2. Mở thẻ check-in: giá trị AI đã điền sẵn từ dữ liệu tích hợp hoặc task đã xong.
3. Kéo thanh độ tự tin, ghi blocker bằng giọng nói hoặc gõ một câu.
4. Gửi → Manager thấy trong tổng hợp team.

### F5. Manager xử lý cảnh báo quá tải (US-TASK-003/004) — mục tiêu ≤ 1 phút

1. Trang chủ Manager: "B quá tải 130% trong 2 tuần".
2. Mở Workload: heatmap người × tuần.
3. AI gợi ý (L1): "Chuyển 2 task sang C (50%), C đã làm việc tương tự".
4. Manager kéo thả hoặc bấm Áp dụng; B và C nhận thông báo kèm lý do.

## 6. Wireframe màn hình chính

Ba wireframe dưới đây là mức độ trung bình (mid-fi): thể hiện bố cục, thứ tự ưu tiên thông tin và hành động, chưa phải màu sắc hay hình ảnh thương hiệu. Số liệu là ví dụ minh họa.

### 6.1. Trang chủ CEO (desktop)

&#91;embedded content: wireframe 1 · Trang chủ CEO, desktop 1440 px\]

Điểm thiết kế chính:

- **Dòng tóm tắt một câu** ngay dưới lời chào trả lời câu hỏi "có gì cần tôi?" trước khi người dùng đọc bất cứ con số nào (U1).
- **4 ô chỉ số sức khỏe**, mỗi ô có nhãn độ tươi dữ liệu ("06:45 hôm nay", "hôm qua"). Bấm vào ô mở nguồn và công thức (U3). CEO chọn 4 chỉ số này trong phần cài đặt; mặc định là doanh thu, dòng tiền, OKR, task trễ.
- **"Cần anh quyết"** đứng trên rủi ro, vì đó là việc chỉ CEO làm được. Mỗi dòng có tóm tắt của AI và nút hành động tại chỗ (U6).
- **"AI đã làm"** có nền khác để luôn phân biệt được việc của AI với việc của người (U4), kèm lối hoàn tác.
- **Panel AI bên phải** mở theo ngữ cảnh: bấm vào ô doanh thu thì panel giải thích doanh thu. Panel có thể thu gọn; trên màn hình dưới 1280 px nó chuyển thành ngăn kéo trượt ra.

### 6.2. Review tài liệu (desktop, dành cho Reviewer)

&#91;embedded content: wireframe 2 · Review tài liệu, chế độ Gọn\]

Điểm thiết kế chính:

- **Liên kết hai chiều giữa trường và vùng trên bản gốc.** Trường đang xem được tô cùng màu với vùng AI đã đọc trên tài liệu; bấm vào vùng trên tài liệu cũng nhảy tới trường tương ứng. Người duyệt không phải tự dò tìm.
- **Độ tin cậy có ba mức, mã hóa bằng cả màu và hình** (● cao, ◐ trung bình, ○ thấp) để người mù màu vẫn phân biệt được. Ngưỡng mặc định: ≥ 90% cao, 60–89% trung bình, dưới 60% thấp; Admin chỉnh được theo loại tài liệu.
- **Con trỏ tự nhảy vào trường cần xem trước**, không theo thứ tự từ trên xuống. Trường trọng yếu (tiền, MST, số tài khoản) luôn phải được đi qua dù độ tin cậy cao, đúng quy tắc trong BRD.
- **AI nói rõ lý do không chắc** ("ký tự thứ 4 mờ", "ảnh mờ") thay vì chỉ hiện con số phần trăm.
- **Thao tác hoàn toàn bằng bàn phím**; sau khi duyệt, tài liệu tiếp theo mở ngay. Mục tiêu: một hóa đơn 6 trường duyệt trong 60 giây.
- **Mỗi lần sửa của người duyệt được ghi lại** để đo độ chính xác của AI theo từng trường và làm dữ liệu cải tiến.

### 6.3. Mobile (390 px)

&#91;embedded content: wireframe 3 · Mobile 390 px: briefing, chụp chứng từ, duyệt\]

Điểm thiết kế chính:

- **Thanh tab dưới 4 mục và nút + ở giữa.** Nút + mở menu nhập nhanh: chụp chứng từ, ghi âm, cập nhật task, check-in. Mọi thứ khác (cấu hình, báo cáo sâu, quản trị) chỉ có trên desktop.
- **Briefing là một trang cuộn ngắn**, đọc hết trong 30 giây. Có thể hỏi bằng giọng nói ngay từ Trang chủ.
- **Chụp chứng từ chạy nền.** Camera tự nhận cạnh, chụp nhiều trang liền, người dùng đóng app được; AI báo bằng thông báo khi đọc xong hoặc khi cần người xem lại.
- **Thẻ duyệt hiển thị đủ để quyết mà không cần mở thêm:** AI đã soạn gì, nguồn từ đâu, hai nút lớn (vùng chạm ≥ 44 px). Vuốt để duyệt hàng loạt các mục rủi ro thấp; mục tài chính trên ngưỡng phải xác thực sinh trắc học.
- **Chế độ ngoại tuyến:** ảnh chụp và cập nhật task được xếp hàng, gửi lên khi có mạng, có nhãn "chưa đồng bộ".

## 7. Mẫu tương tác AI

Đây là phần khác biệt nhất của AI-EOS so với phần mềm quản trị thông thường. Người dùng chỉ tin AI khi họ luôn biết AI đang ở trạng thái nào, dựa vào đâu, và có thể rút lại được không. Vì vậy mỗi mức tự chủ (Autonomy Level) trong BRD gắn với **một mẫu giao diện cố định**, dùng nhất quán ở mọi module.

### 7.1. Mức tự chủ và mẫu giao diện

| Mức | AI làm gì | Mẫu giao diện | Người dùng phải làm | Ví dụ |
| --- | --- | --- | --- | --- |
| L0 Thông tin | Chỉ hiển thị, tóm tắt | **Insight card**: tiêu đề một câu, con số, nguồn | Không | "Doanh thu T9 đạt 82% KH" |
| L1 Gợi ý | Đưa phương án, chưa soạn gì | **Suggestion chip** dưới insight: 1–3 phương án, mỗi cái một nút | Chọn hoặc bỏ qua | "Chuyển 2 task sang C" |
| L2 Soạn và chờ xác nhận | Soạn sẵn hành động đầy đủ | **Action card** viền nhấn, nhãn "AI soạn · chờ xác nhận", xem trước kết quả, nút Xác nhận và Sửa | Xác nhận, có thể sửa từng dòng | Tạo 3 task từ biên bản họp |
| L3 Làm rồi báo | Tự thực hiện trong ngưỡng | **Undo toast** 10 giây ngay lúc làm, sau đó vào feed "AI đã làm" với nút Hoàn tác trong 24 giờ | Không, trừ khi muốn hoàn tác | Nhắc deadline, nhập hóa đơn đã duyệt |
| L4 Tự chủ | Tự làm, chỉ tổng hợp định kỳ | **Báo cáo hoạt động** tuần trong "AI đã làm", có thể lọc và hoàn tác theo lô | Đọc tổng hợp | Phân loại email, gắn nhãn tài liệu |

Quy tắc: nhãn trạng thái ("AI gợi ý", "AI soạn", "AI đã làm") dùng đúng một từ vựng ở mọi nơi; màu nhấn của AI chỉ dùng cho nội dung do AI tạo, không dùng cho nút thường.

### 7.2. Bộ thành phần AI

- **Thanh AI toàn cục (⌘K)**: vừa là ô tìm kiếm, vừa là ô hỏi, vừa là ô ra lệnh ("giao cho Lan báo cáo tuần"). Gợi ý câu hỏi theo màn hình đang mở.
- **Panel AI theo ngữ cảnh**: mở bên phải, tự nạp ngữ cảnh của entity đang xem; hiển thị "AI đang xem: KPI Doanh thu T9" để người dùng biết AI đang hiểu câu hỏi trong phạm vi nào.
- **Trạng thái đang nghĩ**: hiện các bước thật ("Đọc 3 báo cáo · So sánh với T8 · Kiểm tra pipeline") thay vì vòng quay vô nghĩa; câu trả lời truyền dần (streaming); có nút Dừng.
- **Source chip (trích dẫn)**: mỗi khẳng định có chip nguồn cuối câu; chạm vào mở popover với bản ghi gốc, tài liệu gốc (nhảy tới đúng đoạn), thời điểm cập nhật.
- **Nhãn độ tin cậy**: ba mức Cao, Trung bình, Thấp bằng chữ kèm biểu tượng, không dùng phần trăm trong câu trả lời hội thoại (phần trăm chỉ dùng ở màn Review, nơi Reviewer cần độ chi tiết).
- **Nhãn độ tươi dữ liệu**: "cập nhật 06:45", chuyển sang cảnh báo khi dữ liệu cũ hơn ngưỡng của chỉ số đó.
- **Feed "AI đã làm"**: dòng thời gian mọi hành động L3/L4, lọc theo module, người, mức; mỗi dòng có lý do và nút Hoàn tác.
- **Phản hồi một chạm**: 👍/👎 và "Sai ở đâu?" trên mọi câu trả lời và mọi bản trích xuất; phản hồi đi vào AI Control Center.
- **Công tắc dừng khẩn cấp (kill switch)**: trong AI Control Center cho Admin và CEO; khi bật, mọi thẻ L3/L4 chuyển sang L2 và có băng thông báo trên đầu ứng dụng.

### 7.3. Khi AI sai hoặc không biết

- AI nói "Tôi chưa có dữ liệu về X" kèm gợi ý cách bổ sung (kết nối nguồn, tải tài liệu), không bịa câu trả lời.
- Khi các nguồn mâu thuẫn, hiển thị cả hai giá trị cạnh nhau và hỏi người dùng chọn, ghi vào Data Lineage.
- Lỗi hệ thống AI (timeout, mô hình không phản hồi) không chặn thao tác thủ công: mọi luồng đều có đường làm tay.

## 8. Design system đề xuất

Design system xây theo token ngay từ đầu để hỗ trợ hai mật độ, chế độ sáng/tối và đổi thương hiệu nếu sau này bán dạng SaaS. Màu thương hiệu cụ thể chờ quyết định (xem mục 10).

### 8.1. Token nền tảng

| Nhóm | Đề xuất | Ghi chú |
| --- | --- | --- |
| Font | **Be Vietnam Pro** cho giao diện; **JetBrains Mono** cho mã và số liệu bảng (tùy chọn) | Be Vietnam Pro thiết kế cho dấu tiếng Việt, không chồng dấu ở cỡ nhỏ; dự phòng: Inter |
| Cỡ chữ | 12 · 14 · 16 · 20 · 24 · 32 | 14 là cỡ thân mặc định chế độ Gọn, 16 cho chế độ Thoáng; dòng cao 1,5 vì dấu tiếng Việt cần khoảng trên |
| Số | Chữ số đều rộng (tabular figures) trong bảng và chỉ số | Cột số thẳng hàng, dễ so sánh |
| Khoảng cách | Lưới 4 px: 4 · 8 · 12 · 16 · 24 · 32 · 48 | Chế độ Gọn giảm một bậc khoảng cách, hàng bảng 32 px thay vì 44 px |
| Bo góc | 4 (ô nhập) · 8 (thẻ) · 16 (panel) · tròn (nút, chip) |  |
| Độ sâu | 3 mức bóng: thẻ, menu nổi, hộp thoại | Chế độ tối dùng viền thay bóng |
| Chuyển động | 150 ms (hover) · 250 ms (panel) · tôn trọng "giảm chuyển động" của hệ điều hành |  |

### 8.2. Màu theo ngữ nghĩa

| Token | Ý nghĩa | Dùng cho |
| --- | --- | --- |
| `primary` | Màu thương hiệu | Nút chính, liên kết, mục đang chọn |
| `ai` | Nội dung do AI tạo | Viền action card, nhãn "AI soạn", panel AI. Khác hẳn `primary` để không nhầm AI với nút thường |
| `success` / `warning` / `danger` | Đúng kế hoạch / có nguy cơ / lệch | Trạng thái KPI, OKR, task, độ tin cậy Cao/Trung bình/Thấp |
| `info` | Thông tin trung tính | Thông báo hệ thống |
| `neutral-0…900` | Thang xám 10 bậc | Nền, viền, chữ phụ |
| `stale` | Dữ liệu cũ | Nhãn độ tươi khi quá ngưỡng |

Màu trạng thái không bao giờ đứng một mình: luôn đi kèm chữ hoặc biểu tượng (● ◐ ○, ↑ ↓). Xanh lá và đỏ kiểm tra với các dạng mù màu phổ biến.

### 8.3. Thành phần

| Nhóm | Thành phần |
| --- | --- |
| Cơ bản | Nút, ô nhập, chọn, ngày, tiền tệ VNĐ, tab, menu, hộp thoại, toast, avatar, badge |
| Dữ liệu | Bảng (sắp xếp, lọc, sửa trực tiếp, chọn nhiều), thẻ chỉ số, sparkline, heatmap workload, timeline/Gantt, cây mục tiêu (Chiến lược › OKR › Task) |
| AI | Thanh AI, panel AI, insight card, suggestion chip, action card, undo toast, source chip, nhãn độ tin cậy, nhãn độ tươi, trạng thái đang nghĩ, feed "AI đã làm", nút phản hồi |
| Nhập liệu | Vùng thả file toàn cục, thẻ tiến trình xử lý, trình xem tài liệu có vùng tô, form trường trích xuất, camera chụp chứng từ, ghi âm |
| Điều hướng | Sidebar thu gọn được, breadcrumb nghiệp vụ, thanh tab mobile, đổi vai trò |

Đề xuất xây trên một thư viện sẵn có (ví dụ shadcn/ui trên Radix, đã có sẵn khả năng truy cập) và chỉ tự làm nhóm AI và Nhập liệu. Đây là giả định, cần team kỹ thuật xác nhận stack.

### 8.4. Quy tắc trực quan hóa dữ liệu

- Mỗi biểu đồ có tiêu đề là kết luận ("Doanh thu online giảm 18% từ tháng 7"), không phải tên chỉ số.
- Luôn có đường kế hoạch/mục tiêu để so sánh; màu trạng thái chỉ dùng cho phần lệch.
- Ưu tiên cột và đường; tránh biểu đồ tròn trên 4 phần, tránh 3D.
- Đơn vị rút gọn kiểu Việt: 1,2 tỷ; 450 tr; 12,5%.
- Biểu đồ nào cũng bấm được vào điểm dữ liệu để xem bản ghi gốc và hỏi AI về điểm đó.

## 9. Đa thiết bị, truy cập và bản địa hóa

### 9.1. Điểm ngắt màn hình

| Điểm ngắt | Thiết bị | Bố cục |
| --- | --- | --- |
| ≥ 1440 px | Màn hình lớn | Sidebar mở, nội dung, panel AI cố định bên phải |
| 1280–1439 px | Laptop | Sidebar mở, panel AI trượt ra khi cần |
| 768–1279 px | Tablet, laptop nhỏ | Sidebar thu thành biểu tượng, panel AI phủ lên nội dung |
| < 768 px | Điện thoại | Thanh tab dưới, chỉ 4 việc cốt lõi (mục 6.3); các màn khác hiển thị chế độ chỉ đọc |

Đề xuất MVP làm web responsive và PWA (cài lên màn hình chính, nhận thông báo, dùng camera), chưa làm app native. App native cân nhắc ở giai đoạn sau nếu cần sinh trắc học hoặc ngoại tuyến sâu.

### 9.2. Khả năng truy cập (WCAG 2.1 AA)

- Độ tương phản chữ ≥ 4,5:1, thành phần giao diện ≥ 3:1, kiểm tra cả chế độ sáng và tối.
- Toàn bộ thao tác dùng được bằng bàn phím; vòng focus rõ ràng; phím tắt có trang tra cứu (phím ?).
- Câu trả lời AI đang truyền dần được thông báo cho trình đọc màn hình khi hoàn tất, không đọc từng từ.
- Biểu đồ có bảng dữ liệu thay thế và mô tả một câu.
- Vùng chạm ≥ 44 × 44 px trên mobile; không dựa vào thao tác vuốt làm cách duy nhất.
- Undo toast đủ lâu (10 giây) và tạm dừng khi di chuột hoặc focus vào.

### 9.3. Ngôn ngữ và định dạng

| Loại | Tiếng Việt (mặc định) | Tiếng Anh |
| --- | --- | --- |
| Tiền | 1.250.000 đ · 1,2 tỷ | VND 1,250,000 · VND 1.2B |
| Ngày | 05/10/2026 · Thứ Hai | Oct 5, 2026 · Mon |
| Phần trăm | 12,5% | 12.5% |
| Xưng hô của AI | "anh/chị" theo hồ sơ, mặc định "bạn" | you |

- Người dùng hỏi bằng ngôn ngữ nào, AI trả lời bằng ngôn ngữ đó; giao diện theo cài đặt tài khoản.
- Nhãn tiếng Việt thường dài hơn tiếng Anh 20–30%: nút và cột bảng thiết kế theo bản tiếng Việt.
- Cách AI xưng hô (anh/chị hay bạn) là quyết định văn hóa doanh nghiệp, Admin cấu hình được; wireframe trong tài liệu này dùng "anh" ví dụ cho CEO.

## 10. Đo lường UX, lộ trình thiết kế và câu hỏi mở

### 10.1. Chỉ số UX

| Chỉ số | Mục tiêu MVP | Cách đo |
| --- | --- | --- |
| Thời gian đến insight đầu tiên (CEO mở app → biết việc cần làm) | ≤ 10 giây | Usability test, phân tích phiên |
| Thời gian review một hóa đơn 6 trường | ≤ 60 giây | Log màn Review |
| Tỷ lệ hoàn thành 5 luồng chính (F1–F5) không cần hỗ trợ | ≥ 90% | Usability test |
| Điểm SUS | ≥ 75 | Khảo sát sau 30 ngày |
| Tỷ lệ quản lý dùng hàng tuần | ≥ 80% | Analytics |
| Tỷ lệ action card L2 được xác nhận không sửa | ≥ 60% và tăng dần | Log AI |
| Tỷ lệ hoàn tác hành động L3 | ≤ 5% | Feed "AI đã làm" |
| Tỷ lệ câu trả lời AI được người dùng mở nguồn | Theo dõi, không đặt ngưỡng | Cho biết mức độ kiểm chứng của người dùng |

Hai chỉ số L2 và L3 cũng là căn cứ để nâng hoặc hạ mức tự chủ của từng loại hành động.

### 10.2. Lộ trình thiết kế khớp MVP 90 ngày

| Giai đoạn | Tuần | Việc | Đầu ra |
| --- | --- | --- | --- |
| Khám phá | 1–2 | Phỏng vấn 8–10 người (2 mỗi persona), quan sát cách làm hiện tại (Excel, Zalo, email), kiểm chứng persona | Persona đã xác thực, bản đồ hành trình |
| Wireframe | 2–4 | Wireframe toàn bộ màn MVP; test giấy/click với 5 người | Wireframe đã test, IA chốt |
| Design system và hi-fi | 4–7 | Chốt thương hiệu, token, thư viện thành phần trên Figma; hi-fi các màn P0 | File Figma, thư viện thành phần |
| Prototype và test | 6–8 | Prototype tương tác F1–F5; usability test 2 vòng | Báo cáo test, danh sách sửa |
| Đồng hành build | 6–12 | Designer ngồi cùng team dev, review từng màn, QA giao diện | Màn hình đúng thiết kế |
| Pilot | 11–13 | Đo các chỉ số 10.1 với nhóm pilot, SUS lần 1 | Báo cáo UX pilot, backlog giai đoạn 2 |

### 10.3. Câu hỏi cần anh quyết

1. **Thương hiệu**: đã có bộ nhận diện (logo, màu) cho AI-EOS chưa, hay để team thiết kế đề xuất?
2. **Nền tảng**: MVP làm web và PWA như đề xuất, hay cần app native ngay?
3. **Người dùng thử**: ai trong công ty sẽ tham gia phỏng vấn và test (cần ít nhất 2 người mỗi persona)?
4. **Kênh nhắn tin**: briefing và duyệt có cần đẩy qua Zalo/Slack/Teams không (ảnh hưởng thiết kế thông báo)?
5. **Cách AI xưng hô** với nhân viên: "anh/chị" hay "bạn"?

Bước tiếp theo đề xuất: dựng prototype HTML bấm được cho luồng F1 và F2 để dùng ngay trong các buổi phỏng vấn tuần 1–2.
