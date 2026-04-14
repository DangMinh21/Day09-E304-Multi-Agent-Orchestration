# Hướng Dẫn Tác Chiến Của M2: Knowledge Engineer (Retrieval Worker)

Cậu sẽ là "thủ thư" cho hệ thống. Mọi câu hỏi cần tra cứu kiến thức trong tài liệu (RAG của Day 08) sẽ được Supervisor chuyển qua cánh cửa của cậu. 

## 🎯 Mục Tiêu Đạt Được
1. Tái sử dụng thành công luồng Retrieval từ Lab 08.
2. Bọc (Wrap) luồng RAG đó lại thành một Node (Worker) đạt chuẩn LangGraph.
3. Hoàn thiện file `worker_retrieval.py` và `worker_synthesis.py`.

## 🛠 Plan & Action Chi Tiết

### Phase 1: Phân tích RAG cũ & Align Interface (14:00 - 14:30)
- **Hành động 1:** Xem qua Lecture 09, phần "Worker Contract". Lời hứa của cậu là: Nhận vào câu hỏi (string) -> Trả ra ngữ cảnh (context) hoặc Câu trả lời cuối.
- **Hành động 2:** Mở lại code Lab 08. Copy script Vector Store, document loaders, chunking logic... sang thư mục Day 09.
- **Hành động 3:** Bàn với M1 về `State`. Cậu cần chốt với M1: "Khi Supervisor gọi tao, tao sẽ lấy câu hỏi ở key nào trong State (VD: `state['messages'][-1]`)?"

### Phase 2: Đóng gói RAG thành Node (14:30 - 16:00)
- **Hành động 1:** Nhận đường link repo từ M1. Mở Terminal:
  ```bash
  git clone <link>
  cd day09_lab
  git checkout -b feature/retrieval-worker
  ```
- **Hành động 2:** Viết hàm `retrieval_node(state: State)`. Bên trong hàm này dán logic vector search của Day 08 vào.
- **Hành động 3:** Xử lý lỗi. Nếu vector search không ra kết quả nào? Trả về State cập nhật báo lỗi thay vì app bị crash. (Đây là điểm cộng lớn!).
- **Hành động 4:** Viết hàm `synthesis_node` (Tổng hợp). Dùng context vừa lấy được, đẩy cho LLM (Claude/GPT) sinh câu trả lời mượt mà, sau đó nối kết quả vào `state['messages']` và trả lại Supervisor.
- **Hành động 5:** Lưu lại và đẩy lên mạng:
  ```bash
  git add .
  git commit -m "Hoàn thành logic Worker Retrieval và Worker Synthesis"
  git push origin feature/retrieval-worker
  ```
  Lên GitHub bấm tạo Pull Request và chọc M1 vào Review.

### Phase 3: Ráp nối & Sửa lỗi (16:00 - 17:00)
- **Hành động 1:** Sau khi code được gộp, kéo code main mới nhất vảo máy.
- **Hành động 2:** Phối hợp cùng M1 chạy luồng, theo dõi terminal xem Node Retrieval có in ra đúng các tài liệu (docs) cần lấy không. 
- **Hành động 3:** Tinh chỉnh prompt của Synthesis theo test case của M4 để câu trả lời bám sát ngữ cảnh hơn.

### Phase 4: Ghi chép Report (17:00 - 18:00)
- **Hành động 1:** Viết phần "Xây dựng Knowledge Worker từ di sản Day 08".
- **Hành động 2:** Giải thích trong báo cáo làm sao để biến một chain Python thông thường (RAG Day 08) thành một State-based Node cho Day 09. Chụp snippet code đoạn convert này.

Chúc M2 xử lý RAG mượt mà, không bị lạc mất Vector Database nhé!
