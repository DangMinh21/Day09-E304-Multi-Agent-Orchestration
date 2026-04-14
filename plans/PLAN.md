# Kế Hoạch Thực Hành Lab Day 09: Multi-Agent Orchestration

**Thời gian:** 4 Tiếng (14:00 - 18:00)
**Nhân sự:** Nhóm 4 người (Thành viên M1, M2, M3, M4)
**Mục tiêu:**
- *Học hỏi:* Hiểu rõ cách LangGraph vận hành, cơ chế routing của Supervisor, cách setup Worker và MCP.
- *Điểm số/Report:* Code rõ ràng, trace log minh bạch, có lý luận (route logic) cụ thể để giải thích trong Report.

---

## 1. Phân Chia Vai Trò & Tác Vụ

### M1: Leader / Orchestrator (Supervisor)
- **Nhiệm vụ:** Thiết kế LangGraph / Đóng vai trò Supervisor.
- **Deliverable chính:** Lập trình `supervisor_agent.py` và setup bộ định tuyến (router logic).
- **Trọng điểm cho report:** Đưa ra lưu đồ (flowchart) và giải thích tiêu chí routing (loại câu hỏi nào đi về worker nào).

### M2: Knowledge Engineer (Retrieval & Synthesis Workers)
- **Nhiệm vụ:** Tái sử dụng logic RAG của Lab 08 để xây dựng các Worker chuyên lấy thông tin (Retrieval) và tổng hợp câu trả lời (Synthesis).
- **Deliverable chính:** Các file `worker_retrieval.py`, `worker_synthesis.py`.
- **Trọng điểm cho report:** Contract giữa các vòng RAG từ Day 08 khi được nhúng nguyên khối vào làm một node của hệ thống Day 09.

### M3: Integration Specialist (Policy Worker & MCP)
- **Nhiệm vụ:** Cấu hình chuẩn giao tiếp MCP và xây dựng Policy Worker (Xử lý các luật lệ/nguyên tắc của công ty, cần lấy từ Tool ngoài).
- **Deliverable chính:** `worker_policy.py`, `mcp_config.json`.
- **Trọng điểm cho report:** Bằng chứng agent đã call function qua chuẩn MCP ra sao (chụp snippet code và log).

### M4: QA & Observability / Report Lead
- **Nhiệm vụ:** Setup hệ thống logging, chạy thử các luồng end-to-end, gom nhặt content để viết báo cáo.
- **Deliverable chính:** `trace_log.jsonl`, file báo cáo/Report.
- **Trọng điểm cho report:** Trace log phải thể hiện rõ "câu hỏi -> supervisor suy nghĩ -> route qua worker -> kết quả -> trace lại toàn bộ". 

---

## 2. Lịch Trình Chi Tiết Từng Phase (14:00 - 18:00)

### Phase 1: Kick-off, Setup & Design (14:00 - 14:30)
- **Toàn team:** Đọc nhanh `lecture-09.html` đặc biệt phần "Supervisor-Worker" và "Trace & Observability".
- **M1 + M4:** Phác thảo ra giấy/draw.io thiết kế Node và Edge cho đồ thị (Graph) của kiến trúc Multi-Agent.
- **M2 + M3:** Set up Github Repo, clone code Lab Day 08 cũ làm base và cài đặt các thư viện cần thiết.
- **Mục tiêu:** Tạo được bộ khung, thống nhất về Interface truyền nhận dữ liệu (`State` Object chung của đồ thị là gì).

### Phase 2: Core Development - Tác chiến song song (14:30 - 16:00)
- **M1:** Code `supervisor_agent.py` - chỉ viết mock (Giả lập) các worker để test routing trước.
- **M2:** Code `worker_retrieval.py` bọc RAG cũ vào thành node function. Đảm bảo input và output đúng chuẩn State.
- **M3:** Nháp file `mcp_config.json` để khai báo tool. Xây dựng logic `worker_policy.py` gọi vào MCP tool đó.
- **M4:** Viết khung logging để bắt chuẩn luồng dữ liệu lúc chạy, đồng thời tạo dàn ý (Outline) cho Report. Setup test cases thực tế (VD: 1 câu hỏi IT, 1 câu chính sách HR, 1 câu tổng hợp dài).

### Phase 3: Integration & Testing (16:00 - 17:00)
- **M1, M2, M3:** Lắp ráp tất cả code vào Graph chính (Main app). Thay thế mock worker bằng worker thật!
- **M4:** Bắt đầu ném các test_cases vào hệ thống. Thông báo lỗi (bug) khi test trên LangGraph Studio hoặc console execution.
- **Toàn team:** Debug lỗi dữ liệu giữa các node (thường lỗi nằm ở khâu lưu State hoặc type_hint chưa chuẩn). Mọi người cùng fix luồng luân chuyển.

### Phase 4: Tracing, Report & Cleanup (17:00 - 18:00)
- **M4:** Chạy script để nôn toàn bộ trace ra file `trace_log.jsonl`.
- **M1 + M2:** Đóng góp viết các section giải thích thiết kế kỹ thuật vào Report.
- **M3:** Dọn dẹp code, thêm Document string (docstrings) cho code trong trẻo để ăn điểm Clean code.
- **Toàn team:** Đọc chéo lại Report (Proofreading), đảm bảo mọi yêu cầu của giảng viên trong `README.md` Day 09 được cover. Submit đúng 18:00.

---

## 3. Quy trình làm việc nhóm qua GitHub (Dành cho Fresher)

Để tránh tình trạng "code chạy máy em nhưng không chạy máy bạn" hoặc **conflict** (xung đột code) khiến cả nhóm mất hàng giờ để sửa, hệ thống GitHub sẽ là cứu cánh. Dưới đây là quy trình thao tác chuẩn chỉ từng bước:

### Bước 1: Khởi tạo & Lấy code về máy (Clone)
- **M1 (Leader)** sẽ tạo một repository trên GitHub, upload mã nguồn gốc (thư mục `.vscode/`, `.gitignore`, `requirements.txt`...) lên nhánh `main`.
- **Thành viên khac (M2, M3, M4):** Mở Terminal (hoặc Git Bash), gõ lệnh:
  ```bash
  git clone <link-repo-github>
  cd <tên-thư-mục-repo>
  ```

### Bước 2: Bắt buộc tạo Nhánh (Branch) riêng trước khi code
> **Tuyệt đối không ai được code và push trực tiếp lên nhánh `main`!** Nhánh `main` chỉ chứa code đã hoàn thiện và chạy được.
- Trước khi bắt đầu nhiệm vụ của mình, hãy tạo và chuyển sang một nhánh mới:
  ```bash
  # Cú pháp: git checkout -b feature/<tên-chức-năng>
  git checkout -b feature/retrieval-worker  # (Ví dụ cho M2)
  ```
- Lúc này, bạn đang ở một "vũ trụ song song", mọi thay đổi của bạn sẽ không ảnh hưởng đến code của người khác.

### Bước 3: Code, Lưu (Commit) và Đẩy lên mạng (Push)
- Sau khi code xong 1 phần (ví dụ viết xong file `worker_retrieval.py`), bạn cần lưu lại chặng đường này:
  ```bash
  git add worker_retrieval.py  # (Hoặc git add . để lưu tất cả thay đổi)
  git commit -m "Hoàn thành logic lấy dữ liệu RAG cho retrieval worker"
  ```
  *(Lưu ý: Message commit `-m` phải viết rõ ràng, tiếng Anh hay tiếng Việt đều được nhưng phải dễ hiểu để đồng đội đọc).*
- Đẩy nhánh của bạn lên web GitHub:
  ```bash
  git push origin feature/retrieval-worker
  ```

### Bước 4: Yêu cầu gộp code (Tạo Pull Request - PR)
- Lên trang web GitHub, bạn sẽ thấy nút màu xanh báo **"Compare & pull request"**. Bấm vào đó.
- Viết mô tả ngắn gọn: *Tôi đã thêm hàm X, giải quyết vấn đề Y.*
- **Review chéo:** Bạn không được tự gộp code của mình. Hãy copy link PR gửi vào group chat: *"M1 ơi, vào review code phần Worker giúp tao rồi Approve nhé!"*
- Người review (M1) sẽ vào xem file thay đổi, nếu thấy ổn thì bấm **Approve** và **Merge pull request** để gộp nhánh của bạn vào `main`.

### Bước 5: Cập nhật code mới nhất từ đồng đội (Pull)
- Khi code của M2 đã được gộp vào `main`, các thành viên khác (M3, M4) cần kéo code mới đó về máy của mình để bắt kịp:
  ```bash
  git checkout main         # Trở về nhánh chính
  git pull origin main      # Kéo code mới nhất về
  git checkout feature/abc  # Quay lại nhánh đang làm dở của mình
  git merge main            # Trộn code mới vảo nhánh của mình để tiếp tục code
  ```

---
**📝 Hướng Dẫn Hành Động Từng Người:**
Để dễ dàng theo dõi, tôi đã tạo ra các file hướng dẫn chi tiết (Plan + Action) cho từng thành viên. Vui lòng mở file tương ứng của mình để bắt đầu làm việc:
- 👉 **[M1_guide.md](M1_guide.md)**: Dành cho Leader / Orchestrator
- 👉 **[M2_guide.md](M2_guide.md)**: Dành cho Knowledge Engineer
- 👉 **[M3_guide.md](M3_guide.md)**: Dành cho Integration Specialist
- 👉 **[M4_guide.md](M4_guide.md)**: Dành cho QA & Report Lead

Chúc nhóm chạy deadline 4 tiếng năng suất nhất! Mọi đầu ra đã được mapping hoàn hảo theo yêu cầu môn học.
