# Hướng Dẫn Tác Chiến Của M3: Integration Specialist (Policy Worker & MCP)

Cậu đảm nhiệm phần mới nhất và "ngầu" nhất của kiến trúc: Giao tiếp với công cụ bên ngoài bằng Model Context Protocol (MCP). Cậu sẽ làm bộ phần xử lý các câu hỏi liên quan đến Chính Sách/Nội Quy công ty.

## 🎯 Mục Tiêu Đạt Được
1. Hiểu được khái niệm MCP khác gì với Prompt Function Calling thông thường.
2. Hoàn thiện `mcp_config.json` khai báo tool ngoài.
3. Hoàn thiện `worker_policy.py`.

## 🛠 Plan & Action Chi Tiết

### Phase 1: Học khái niệm MCP (14:00 - 14:30)
- **Hành động 1:** Đọc ngay Lecture 09 phần "A2A vs MCP". Nắm rõ phân biệt: Giao việc cho agent (A2A) vs Gọi tool (MCP).
- **Hành động 2:** Bàn bạc `State` chung với M1. 

### Phase 2: Khai báo MCP và Viết Worker (14:30 - 16:00)
- **Hành động 1:** Lấy code và chuyển nhánh:
  ```bash
  git clone <link-từ-M1>
  cd day09_lab
  git checkout -b feature/policy-mcp
  ```
- **Hành động 2:** Tạo file `mcp_config.json`. Hãy giả lập việc setup một MCP server nội bộ. (Ví dụ: tool tra cứu ngày nghỉ phép, tool tra cứu mức phạt đi muộn...).
- **Hành động 3:** Viết `worker_policy.py`. 
  - Khởi tạo LLM và mix (bind) nó với function MCP cậu vừa khai báo.
  - Xây dựng Node này: Khi nhận input từ Supervisor -> Dùng Tool tìm kiếm thông tin policy -> Sinh câu trả lời -> Xoay vòng trả về State.
- **Hành động 4:** Vứt lên kho chung:
  ```bash
  git add .
  git commit -m "Thêm config MCP và Policy Worker"
  git push origin feature/policy-mcp
  ```
  Kêu M1 vào tạo PR và Approve.

### Phase 3: Ráp nối và Thử nghiệm (16:00 - 17:00)
- **Hành động 1:** Hỗ trợ M1 lắp Node Policy vào LangGraph.
- **Hành động 2:** Chạy test. Hãy bảo M4 đặt câu hỏi "Xin nghỉ phép 3 ngày thì quy trình thế nào?". Cậu phải dán mắt vào Terminal để xem Agent có thực sự trigger MCP tool đã thiết lập hay bị "hallucinate" (bịa ra câu trả lời).

### Phase 4: Trưng bài cho Report (17:00 - 18:00)
- **Hành động 1:** Chụp choẹt cấu trúc file JSON của MCP và log trả về lúc thực thi thành công. Đây là điểm mấu chốt giảng viên muốn xem!
- **Hành động 2:** Viết section "Tích hợp công cụ bằng kiến trúc MCP". Nêu ra lý do vì sao dùng MCP lại chuẩn hoá và xịn hơn tự viết API Python bình thường gọi thẳng.
- **Hành động 3:** Review lại toàn bộ code của bản thân, đóng chú thích docstring cẩn thận.

MCP là trend công nghệ mới, hãy làm thật tỉ mỉ nhé M3!
