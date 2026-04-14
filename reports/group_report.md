# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Nhóm 9 - E403 
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Đặng Văn Minh | Supervisor Owner | minhdv0201@gmail.com |
| Nguyễn Quang Tùng | Worker Owner | quangtungnguyen613@gmail.com |
| Nguyễn Thị Quỳnh Trang | MCP Owner | quynhtrang1225@gmail.com |
| Đồng Văn Thịnh | Trace & Docs Owner | dvttvdthanhan@gmail.com |

**Ngày nộp:** 14/04/2026 

**Repo:** https://github.com/DangMinh21/Day09-E304-Multi-Agent-Orchestration

**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng

**Hệ thống tổng quan:**
Nhóm triển khai hệ thống theo mô hình **Supervisor-Worker** dựa trên LangGraph `StateGraph`. Thay vì một pipeline đơn lẻ, nhóm tách biệt các trách nhiệm thành các Worker chuyên biệt: **Retrieval** (truy xuất), **Policy Tool** (phân tích chính sách) và **Synthesis** (tổng hợp). Toàn bộ dữ liệu được đồng bộ qua `AgentState` tập trung, giúp hệ thống đạt độ chính xác trung bình **~76.8%** (tăng mạnh so với baseline Day 08) nhờ khả năng kiểm soát độc lập và tích hợp con người vào luồng xử lý (**Human-in-the-loop**) khi phát hiện rủi ro cao.

**Routing logic cốt lõi:**
Supervisor điều phối luồng dựa trên cơ chế **Keyword Matching kết hợp Risk Detection**:
- **Điều hướng Worker:** Phân loại dựa trên tập từ khóa (ví dụ: "SLA", "hoàn tiền" -> Policy; tra cứu chung -> Retrieval).
- **Xử lý rủi ro:** Nếu task chứa tiền tố lỗi hệ thống (`err-`) và nhãn `risk_high=True`, Supervisor ép route qua node `human_review`.
- **Quyết định Tool:** Sử dụng cờ `needs_tool` để kích hoạt khả năng gọi MCP Tools khi câu hỏi yêu cầu dữ liệu động hoặc thực thi nghiệp vụ (latency trung bình ~3.6s).

**MCP tools đã tích hợp:**
Nhóm tích hợp 05 công cụ chính qua giao thức MCP để làm giàu ngữ cảnh:
* `search_kb`: Truy xuất bổ sung dữ liệu để làm rõ các điều khoản chính sách.
* `get_ticket_info`: Lấy thông tin thực tế từ hệ thống Ticket (ví dụ: IT-9847).
* `check_access_permission`: Thực thi quy tắc phân quyền Level 1/2/3 dựa trên Role.
* `get_leave_process` & `get_late_penalty`: Tra cứu quy trình nhân sự và mức phạt chuyên biệt.

**Ví dụ Trace thực tế (Case q13):**
* **Supervisor:** Nhận diện task "Admin Access" -> Route: `policy_tool_worker`, `needs_tool=True`.
* **Policy Tool:** Gọi đồng thời `search_kb` (lấy SOP) và `check_access_permission`.
* **MCP Output:** Xác định Contractor cần 3 cấp phê duyệt (Line Manager, IT Admin, IT Security).
* **Synthesis:** Tổng hợp câu trả lời có trích dẫn nguồn từ file `it/access-control-sop.md`.
---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** Tích hợp bộ lọc Simple Keyword-based Reranker sau bước Vector Search
**Bối cảnh vấn đề:**

Trong quá trình thử nghiệm Day 08, nhóm nhận thấy tìm kiếm bằng Vector (Dense Retrieval) 
tuy hiểu ngữ nghĩa nhưng thường xuyên bỏ lỡ các thực thể quan trọng có tên riêng cụ thể 
như "P1", "Level 3", hay "SLA". Hệ thống trả về các đoạn văn bản có độ tương đồng 
vector cao nhưng không chứa đúng từ khóa then chốt mà người dùng hỏi, dẫn đến 
synthesis_worker bị thiếu dữ liệu chính xác để khẳng định câu trả lời.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Chỉ dùng Vector Search (Baseline) | Tốc độ nhanh, không cần thêm code xử lý. | Độ chính xác với từ khóa đặc hiệu (Hard Keywords) thấp. |
| Dùng Cross-Encoder Model chuyên dụng | Độ chính xác cực cao trong việc xếp hạng lại. | Tăng đáng kể Latency (~1-2s) và chi phí API/tài nguyên tính toán. |

**Phương án đã chọn và lý do:**
`Reranker`
   - Ưu điểm: Cải thiện rõ rệt độ tin cậy bằng cách ưu tiên Keyword mà vẫn giữ Latency thấp.
   - Nhược điểm: Cần tinh chỉnh thủ công hệ số Bonus (0.05) dựa trên thực tế dữ liệu.

**Bằng chứng từ trace/code:**
> Dẫn chứng cụ thể (VD: route_reason trong trace, đoạn code, v.v.)

1. SUPERVISOR ROUTING:
- Kết quả: retrieval_worker.
- Lý do: "chứa keyword ticket/chuẩn SLA cơ bản".
- Risk: Normal (Không kích hoạt human_review).

2. RETRIEVAL & RERANKING:
- Chunk top 1: support/sla-p1-2026.pdf
- Score cuối: 0.868 (Đã cộng bonus +0.15 nhờ match "SLA", "ticket", "P1").
- Trạng thái: [HIGH CONFIDENCE].

3. SYNTHESIS:
- Confidence: 0.77.
- Nội dung: Trích xuất chính xác mốc 15 phút (phản hồi) và 4 giờ (xử lý).
- Nguồn trích dẫn: support/sla-p1-2026.pdf.

4. HIỆU SUẤT:
- Tổng thời gian (Latency): 5600ms.
- Số bước thực hiện: 2 (retrieval -> synthesis).

```
[NHÓM ĐIỀN VÀO ĐÂY — ví dụ trace hoặc code snippet]
```

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** 90 / 96

**Câu pipeline xử lý tốt nhất:**
- ID: gq01 (SLA P1)
- Lý do tốt: Nhờ logic Reranker ưu tiên từ khóa "P1", hệ thống truy xuất chính xác 
  tuyệt đối các mốc thời gian (15 phút phản hồi, 4 giờ xử lý). Confidence đạt 
  mức tối đa 0.91 - 0.92 với latency rất thấp (~2.7s).

**Câu pipeline fail hoặc partial:**
- ID: gq02 (Chính sách hoàn tiền đơn hàng 31/01)
- Fail ở đâu: Phần giải thích về Policy v3 bị mơ hồ.
- Root cause: Do hệ thống chỉ có tài liệu refund-v4.pdf. Dù đã kích hoạt 
  policy_tool_worker để gọi search_kb, nhưng vì thiếu data v3 nên LLM phải 
  dựa trên suy luận logic thời gian thay vì bằng chứng văn bản cụ thể.

**Câu gq07 (abstain):** Nhóm xử lý thế nào? 
Nhóm xử lý thành công bằng cơ chế "Abstain condition". 
- Trace ghi nhận: Hệ thống trả về "Không đủ thông tin trong tài liệu nội bộ".
- Chỉ số Confidence: Giảm xuống 0.3 (thấp nhất trong bộ test), đúng với kỳ vọng rằng hệ thống không được phép "bịa" ra mức phạt tài chính khi tài liệu SLA chỉ ghi quy trình kỹ thuật.


**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?
- Trace ghi nhận: 2 workers (policy_tool_worker -> synthesis_worker).
- Kết quả: Xử lý xuất sắc. Mặc dù là câu hỏi phức tạp kết hợp cả SLA P1 và 
  Emergency Access, policy_tool_worker đã thực hiện chuỗi 3 MCP calls liên tiếp:
  1. search_kb (lấy SOP)
  2. get_ticket_info (xác nhận sự cố)
  3. check_access_permission (kiểm tra điều kiện cho contractor).
- Kết quả cuối đạt Confidence 0.92, trả lời đầy đủ cả 2 vế của câu hỏi.


---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**

- Multi-hop Accuracy: Tăng từ ~30% lên 47%. Nhờ MCP orchestration 3 bước (search_kb 
  -> get_ticket_info -> check_access_permission), các câu phức hợp như q13 đạt 
  Confidence 0.89, điều mà Single Agent hoàn toàn thất bại.
- Latency: Tăng vọt từ 800ms lên trung bình 3655ms (Delta +2855ms). Độ trễ tỷ lệ 
  thuận với số lượng MCP calls, đạt đỉnh ~5.8s cho các câu hỏi cần 3 công cụ.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**

Đó là khả năng "Debuggability" vượt trội. Thay vì mất nhiều thời gian để đọc lại toàn bộ pipeline code như Day 08, nhóm chỉ mất vài phút phút để isolate bug bằng cách đọc `history` và `route_reason` trong trace file. Việc tách biệt các Worker giúp nhóm xác định ngay lỗi nằm ở bước Retrieval (score thấp) hay do Supervisor định tuyến sai mà không cần can thiệp vào logic của các Worker khác.
**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**

Với các câu hỏi đơn giản (Single-document) như q01 hay q08, Multi-agent gây ra sự lãng phí tài nguyên rõ rệt. Overhead của LangGraph routing đẩy Latency lên gấp 2-7 lần (q01 mất 5600ms so với 800ms của Day 08) mà không cải thiện thêm về chất lượng câu trả lời. Ngoài ra, việc gọi trùng lặp ChromaDB giữa retrieval_worker và MCP search_kb là một điểm yếu gây dư thừa tài nguyên cần tối ưu hóa trong tương lai.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Đặng Văn Minh | graph.py, routing logic, state management | 1 |
| Nguyễn Quang Tùng | retrieval.py, policy_tool.py, synthesis.py, contracts | 2 |
| Nguyễn Thị Quỳnh Trang | mcp_server.py, MCP integration trong policy_tool | 3 |
| Đồng Văn Thịnh | eval_trace.py, 3 doc templates, group_report | 4 |

**Điều nhóm làm tốt:**

triển khai thành công kiến trúc Supervisor-Worker linh hoạt, giúp giải quyết triệt để các câu hỏi Multi-hop phức tạp (Confidence tăng lên 0.92). Việc xây dựng thành công bộ lọc Simple Reranker thủ công là một điểm sáng, giúp hệ thống không 
chỉ dựa vào vector mà còn bám sát các thực thể quan trọng (P1, SLA, Level 3). Đặc biệt, nhóm đã quản lý Trace log rất tốt, giúp việc debug và đánh giá hệ thống trở nên minh bạch và có cơ sở dữ liệu rõ ràng.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**

Nhóm gặp khó khăn trong việc thống nhất cấu trúc dữ liệu (Interface) giữa các Worker dẫn đến lỗi tích hợp, đồng thời chưa tối ưu được độ trễ cho các câu hỏi đơn giản do quy trình xử lý còn chồng chéo.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**

Nhóm sẽ thiết kế chuẩn hóa Schema ngay từ đầu để đồng bộ dữ liệu tuyệt đối, đồng thời triển khai bộ định tuyến nhanh (Fast-track Router) để xử lý các tác vụ cơ bản nhằm tối ưu hóa tốc độ hệ thống.

---

## 6. NẾU CÓ THÊM 1 NGÀY, NHÓM SẼ LÀM GÌ?

Nhóm sẽ tập trung vào hai cải tiến: 
1. Triển khai Semantic Router bằng một LLM Classifier siêu nhỏ thay vì Keyword Matching để sửa lỗi "chọn nhầm worker" khi từ khóa bị trùng (như câu gq02). 
2. Xây dựng cơ chế Shared Context Cache để policy_worker có thể tái sử dụng dữ liệu từ retrieval_worker, loại bỏ tình trạng Duplicate Retrieval giúp giảm latency trung bình từ 3.6s xuống dưới 2s (dựa trên bằng chứng overhead 2855ms trong scorecard).

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
