# Hướng Dẫn Tác Chiến Của M1: Leader & Orchestrator (Supervisor)

Cậu là hạt nhân của toàn bộ hệ thống Multi-Agent ngày hôm nay. Trách nhiệm của cậu là xây dựng bộ định tuyến (Router), quyết định xem câu hỏi của người dùng sẽ đi vào Node nào (Worker nào) để xử lý.

## 🎯 Mục Tiêu Đạt Được
1. Hiểu được đồ thị trạng thái Graph (LangGraph) hoạt động thế nào.
2. Hoàn thiện file `supervisor_agent.py`.
3. Có đủ tài liệu (Draw.io/Ảnh chụp codebase) để giải thích cơ chế Routing.

## 🛠 Plan & Action Chi Tiết

### Phase 1: Setup & Thiết kế mạng lưới (14:00 - 14:30)
- **Hành động 1:** Đọc tài liệu Lecture 09 phần "Supervisor-Worker". Chú ý hình vẽ luồng đi của dữ liệu.
- **Hành động 2:** Khởi tạo GitHub repo! 
  - Tạo một folder `day09_lab`.
  - Copy `.gitignore`.
  - Khởi tạo git: `git init`.
  - Thêm file `.env` chứa biến môi trường (LƯU Ý: Không được push file này lên github!).
  - Push code base skeleton lên nhánh `main`.
- **Hành động 3:** Viết cấu trúc dữ liệu `State`. Cậu thảo luận cùng M2 và M3 xem 1 State truyền qua lại giữa các Node sẽ có các trường (fields) gì. Ví dụ: `messages` (list), `current_worker` (str), `error` (bool)... Khai báo Class State này vào 1 file `state.py` và yêu cầu mọi người import.

### Phase 2: Viết khung sườn Supervisor (14:30 - 16:00)
- **Hành động 1:** Tạo nhánh mới: `git checkout -b feature/supervisor-router`
- **Hành động 2:** Bắt tay vào viết `supervisor_agent.py`. 
- **Hành động 3:** Viết logic Routing Function. 
  - Prompt chỉ đạo: "Bạn là trưởng nhóm điều phối..."
  - Cần yêu cầu LLM có khả năng trả về JSON cấu trúc cứng (VD: Output phải là thẻ `<route>worker_name</route>` hoặc dùng Structured Output/Function Calling).
- **Hành động 4:** Tạo Mock Workers. Khoan hẳn ráp code của M2, M3. Cậu hãy tự define 2 function giả (return chuỗi cứng) để test đường nối Graph từ Supervisor sang Worker trước.

### Phase 3: Ráp code & Chạy thử (16:00 - 17:00)
- **Hành động 1:** Khi M2 và M3 đã push code và cậu đã duyệt PR của họ, hãy chạy lệnh `git pull origin main` để cập nhật các file `worker_*.py`.
- **Hành động 2:** Đưa file của M2, M3 vào LangGraph. Xoá Mock code đi. 
- **Hành động 3:** Cùng M4 chạy thử qua màn hình Console. Phối hợp fix lỗi nếu xảy ra kẹt luồng (Dữ liệu không truyền đúng State).

### Phase 4: Tổng hợp Report (17:00 - 18:00)
- **Hành động 1:** Chụp màn hình sơ đồ LangGraph chạy thành công (có thể dùng visualize Graph bằng code).
- **Hành động 2:** Viết section "Kiến trúc hệ thống và Routing Logic" vào báo cáo. Giải thích rõ vì sao cậu chọn prompt đó để phân luồng.
- **Hành động 3:** Đóng gói source code và nộp bài.

Chúc M1 điều phối thành công! Mọi lỗi luân chuyển dữ liệu cậu là người gánh vác lớn nhất đấy!
