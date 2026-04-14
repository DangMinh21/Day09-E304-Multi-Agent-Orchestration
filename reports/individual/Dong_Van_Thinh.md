# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đồng Văn Thịnh
**Mã học viên:** 2A202600365 
**Vai trò trong nhóm:** Trace & Docs Owner
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào?

**File chính:** `eval_trace.py`, `artifacts/grading_run.jsonl`, `artifacts/traces/`, docs

Tôi chịu trách nhiệm Sprint 4: eval_trace.py, phân tích và cải thiện chất lượng, 3 doc templates, và group_report

**Kết nối với thành viên khác:** 
- `eval_trace.py`: viết truy xuất kết quả chạy giúp theo dõi, đánh giá đầu ra. Tạo tiền đề cải thiện độ tin cậy cho phù hợp

**Bằng chứng:**  `artifacts/grading_run.jsonl`, `artifacts/traces/`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Tích hợp Simple Heuristic Reranker để "hard-verify" các chunk có score cao.

**Lý do chọn:** Vector Search đôi khi cho score cao dựa trên sự tương đồng ngữ nghĩa chung chung nhưng thiếu từ khóa định danh (P1, Level 3). Nhóm dùng Heuristic Rerank để cộng điểm thưởng (0.05/term) cho các chunk đã có score tốt, giúp tách biệt hẳn nhóm thông tin "chắc chắn đúng" với nhóm "có vẻ liên quan", từ đó tối ưu thời gian xử lý của Synthesis Worker.

**Vấn đề phát sinh và cách xử lý:** Chấp nhận rủi ro "bỏ sót" nếu câu hỏi dùng từ đồng nghĩa không khớp keyword-list, đổi lại là tốc độ xử lý tức thì (local) và độ tin cậy cực cao cho các tài liệu kỹ thuật/chính sách vốn yêu cầu sự chính xác tuyệt đối về thuật ngữ.

**Bằng chứng từ trace/code:**
```python
// Logic: Chỉ thực hiện trên top candidates để tối ưu hiệu năng
reranked_chunks = simple_reranker(query, chunks) # Chạy nội bộ, 0ms latency tăng thêm
return reranked_chunks[:3] # Trả về Top 3 đã được bảo chứng bằng Heuristic

// Trace gq01: Xác nhận hiệu quả verify
"score": 0.77 // Kết quả của việc Vector High Score + Heuristic Bonus
"history": "[retrieval_worker] HIGH CONFIDENCE: retrieved 3 chunks"
```

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** State Overwrite tại Synthesis Worker (Lỗi mất dấu dữ liệu trạng thái).

**Symptom:** Hệ thống truy xuất thành công (Retrieval báo 3 chunks) nhưng Synthesis Worker 
lại trả về câu trả lời rỗng hoặc báo lỗi NoneType" do không nhận được ngữ cảnh. Trace log cho thấy danh sách `retrieved_chunks` bị reset về rỗng ở node cuối.

**Root cause:** Lỗi nằm ở Worker logic. Trong file `synthesis.py`, hàm trả về một dictionary mới 
`return {"final_answer": answer}` mà không bao gồm các trường cũ của AgentState. Trong LangGraph, điều này vô tình ghi đè và làm mất các dữ liệu quan trọng đã thu thập từ retrieval_worker trước đó.

**Cách sửa:** chuẩn hóa cấu trúc trả về bằng cách sử dụng toán tử cập nhật thay vì khởi tạo lại. Cụ thể, sử dụng `Annotated[list, operator.add]` trong định nghĩa Schema cho các trường danh sách (như history, sources) để đảm bảo dữ liệu luôn được nối thêm (append) chứ không bị thay thế.

```python
# Sau khi sửa:
// TRƯỚC KHI SỬA (Trace gq01 fail):
"retrieved_chunks": [],  
"final_answer": null,
"history": ["[synthesis_worker] Error: Context missing"]

// SAU KHI SỬA (Trace gq01 success):
"retrieved_chunks": [{"text": "Ticket P1...", "score": 0.868}, ...],
"final_answer": "SLA xử lý ticket P1 là...",
"history": [
    "[supervisor] route=retrieval_worker",
    "[retrieval_worker] HIGH CONFIDENCE: 3 chunks",
    "[synthesis_worker] answer generated"
]
```

**Bằng chứng sau khi sửa** (commit `7359f7fe` — "improved quality"):
```
"retrieved_chunks": [
    {
      "text": "Ticket P1:\n- Phản hồi ban đầu (first response): 15 phút kể từ khi ticket được tạo.\n- Xử lý và khắc phục (resolution): 4 giờ.\n- Escalation: Tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút.\n- Thông báo stakeholder: Ngay khi nhận ticket, update mỗi 30 phút cho đến khi resolve.\n\nTicket P2:\n- Phản hồi ban đầu: 2 giờ.\n- Xử lý và khắc phục: 1 ngày làm việc.\n- Escalation: Tự động escalate sau 90 phút không có phản hồi.\n\nTicket P3:\n- Phản hồi ban đầu: 1 ngày làm việc.\n- Xử lý và khắc phục: 5 ngày làm việc.\n\nTicket P4:\n- Phản hồi ban đầu: 3 ngày làm việc.\n- Xử lý và khắc phục: Theo sprint cycle (thông thường 2-4 tuần).",
      "source": "support/sla-p1-2026.pdf",
      "score": 0.8681,
      "metadata": {
        "department": "IT",
        "source": "support/sla-p1-2026.pdf",
        "effective_date": "2026-01-15",
        "access": "internal",
        "section": "Phần 2: SLA theo mức độ ưu tiên"
      }
    },
    ....
```

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**

**Evaluation và Phân tích Trace** : thiết kế hệ thống scorecard giúp đo lường chính xác các chỉ số Confidence và Latency giữa Day 08 và Day 09. Nhờ đó phát hiện ra sự sụt giảm hiệu năng ở các câu hỏi đơn giản để kịp thời điều chỉnh logic routing.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

**tối ưu hóa kích thước Chunking** : Trong quá trình test, nhiều đoạn văn bản bị cắt ngang (overlap chưa hợp lý), dẫn đến việc Reranker đôi khi "phạt" nhầm các chunk chứa thông tin đúng nhưng bị khuyết từ khóa do lệch index, làm giảm score của những tài liệu quan trọng như gq02.

**Nhóm phụ thuộc vào tôi ở đâu?**

Nhóm phụ thuộc vào tôi ở **Pipeline Kiểm thử và Đối soát**. Nếu tôi không hoàn thành  bộ script đánh giá và trích xuất dữ liệu từ log, nhóm sẽ bị "mù" về mặt số liệu, không thể chứng minh được Multi-agent hiệu quả hơn Single Agent ở điểm nào để viết báo cáo kỹ thuật.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi phụ thuộc vào thành viên phụ trách **MCP Server và Tools**. Tôi cần các API như get_ticket_info và search_kb phải trả về cấu trúc dữ liệu chuẩn để tôi có thể đưa vào bộ Eval mà không gặp lỗi parse JSON.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thử **điều chỉnh chiến lược Chunking (Recursive Character Split)** kết hợp với Dynamic Overlap. Lý do là vì trace của câu **gq02** cho thấy chunk bị lệch khiến thông tin về "chính sách Flash Sale" bị tách làm đôi, làm giảm điểm Rerank xuống còn 0.66. Nếu cải thiện được tính toàn vẹn của chunk, điểm Confidence có thể tăng từ 0.77 lên >0.85 cho các case tra cứu chính sách phức tạp.
