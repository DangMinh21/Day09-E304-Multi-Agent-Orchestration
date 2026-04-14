# Hướng Dẫn Tác Chiến Của M4: QA, Observability & Report Lead

Cậu là "chiếc camera chạy bằng cơm" kiêm tổng đạo diễn cuối cùng. Hệ thống có mạnh tới mấy mà không debug, không ghi log được, không có report chỉn chu thì coi như vứt.

## 🎯 Mục Tiêu Đạt Được
1. Tổ chức hệ thống Trace Log ghi lại mọi hoạt động trong Graph. Xoá bỏ màn hình Terminal mù mờ.
2. Thiết kế Test Cases cover hết mọi nẻo đường (Routing).
3. Gom nhặt ý tưởng, chịu trách nhiệm chính về Document/Báo cáo.

## 🛠 Plan & Action Chi Tiết

### Phase 1: Outline Report và Setup Testcase (14:00 - 14:30)
- **Hành động 1:** Mở Lecture 09, đọc phần "Trace & Observability".
- **Hành động 2:** Cấu trúc lại file Word / Docs Outline của Báo cáo. Chia thành các mục (Design Graph, RAG Node, MCP Node, Trace analysis...). Chỉ định ai phải viết phần nào.
- **Hành động 3:** Chuẩn bị 5 Test cases:
  - TC1: Câu hỏi chitchat vô thưởng vô phạt (Nối thẳng ra END? hay Router chặn?).
  - TC2: Câu hỏi kỹ thuật phần mềm cần tài liệu (Trúng RAG M2).
  - TC3: Câu hỏi nội quy hóc búa (Trúng MCP M3).
  - TC4: Câu cực kỳ phức tạp cần phối hợp.
  - TC5: Câu hỏi nằm ngoài vùng phủ sóng.

### Phase 2: Code bộ khung Observability (Logging) (14:30 - 16:00)
- **Hành động 1:** Nhận repo và tạo nhánh: `git checkout -b feature/tracing-QA`
- **Hành động 2:** Viết một script/một class `Logger` hoặc setup LangSmith (nếu nhóm cho phép). Yêu cầu M1, M2, M3 ở mỗi Node phải import file log này và gọi lệnh `log_step(worker="...", action="..." , state=...)`.
- **Hành động 3:** Hàm lưu trữ: Dữ liệu log phải được in xuống file `trace_log.jsonl` vì giảng viên yêu cầu nộp file format này! Mỗi log là 1 dòng JSON đính kèm timestamp.
- **Hành động 4:** Push đồ nghề của cậu lên cho M1 lấy về nhét vào Router. 

### Phase 3: Bắn Test và Bắt Lỗi (16:00 - 17:00)
- **Hành động 1:** Ép cả nhóm ngồi lại. Cậu cầm quyền gõ Testcase TC1 -> TC5.
- **Hành động 2:** Khi một câu hỏi chạy, cậu sẽ soi trực tiếp vào file `trace_log.jsonl` xem luồng có hiển thị đẹp không. Nếu thấy "Worker RAG mất thời gian quá" hay "Supervisor đi lạc Router", cậu là người gióng hồi chuông cảnh báo bắt team fix bug.

### Phase 4: Hoàn thành Report & Proofreading Tối Thượng (17:00 - 18:00)
- **Hành động 1:** Trích xuất vài dòng log JSON đẹp nhất trong `trace_log.jsonl` đem vào báo cáo. Giảng giải: *"Từ log này, ta có thể thấy rõ Agent suy nghĩ trong 2 giây rồi rẽ nhánh đúng..."*.
- **Hành động 2:** Lắp ráp nội dung M1, M2, M3 đã viết ở các Phase trước. Bôi đậm (Highlight), căn chỉnh format thật chuyên nghiệp.
- **Hành động 3:** Xin ý kiến chốt hạ của team, đóng PDF, đính kèm ZIP code, bấm nộp đúng deadline!

Không có cậu, dự án này chỉ là một mớ code hỗn độn. M4 cố lên, quyết định điểm số cả nhóm nằm ở bản Report này!
