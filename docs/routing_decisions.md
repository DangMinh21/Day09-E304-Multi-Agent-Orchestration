# Routing Decisions Log — Lab Day 09

**Nhóm:** E304  
**Ngày:** 2026-04-14

> Tất cả quyết định routing dưới đây lấy trực tiếp từ `artifacts/traces/` — không ước đoán.

---

## Routing Decision #1 — Standard Retrieval

**Task:** `SLA xử lý ticket P1 là bao lâu?`  
**Trace:** `run_20260414_172143_656641.json` (q01)

**Worker được chọn:** `retrieval_worker`  
**Route reason:** `route to retrieval_worker: chứa keyword ticket/chuẩn SLA cơ bản | risk_flag: Normal`  
**MCP tools được gọi:** none  
**Workers called sequence:** `retrieval_worker → synthesis_worker`

**Kết quả thực tế:**

- final_answer: "SLA xử lý ticket P1: Phản hồi ban đầu 15 phút, xử lý 4 giờ, escalate nếu không phản hồi trong 10 phút [1]."
- confidence: **0.77** | latency: **5600ms**
- Top chunk score: **0.868** (support/sla-p1-2026.pdf, Phần 2: SLA theo mức độ ưu tiên)
- Correct routing? **Yes**

**Nhận xét:** Routing chuẩn. Keyword "ticket" + "P1" khớp `retrieval_keywords`, không cần policy check. Chunk đầu tiên có score 0.868 — cao nhất trong tất cả 15 câu. Câu hỏi đơn giản, single-document, confidence 0.77 hợp lý.

---

## Routing Decision #2 — Policy Tool + MCP

**Task:** `Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?`  
**Trace:** `run_20260414_172149_258806.json` (q02)

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `route to policy_tool_worker: chứa keyword về policy/quyền hạn | risk_flag: Normal`  
**MCP tools được gọi:** `search_kb` (1 call)  
**Workers called sequence:** `policy_tool_worker → synthesis_worker`

**Kết quả thực tế:**

- final_answer: "7 ngày làm việc kể từ xác nhận đơn. Ngoại lệ không được hoàn tiền: digital product, Flash Sale, đã kích hoạt [1][3]."
- confidence: **0.80** | latency: **5559ms**
- policy_applies: **True**, exceptions_found: **1** (flash_sale_exception từ rule-based)
- MCP search_kb → 3 chunks từ policy/refund-v4.pdf, score top: **0.955**
- Correct routing? **Yes**

**Nhận xét:** Keyword "hoàn tiền" trigger policy_tool_worker đúng. MCP `search_kb` trả về chunk có score 0.955 — cao nhất trong experiment này. Lưu ý: policy worker phát hiện `flash_sale_exception` dù câu hỏi không mention Flash Sale — đây là rule-based over-trigger (context có text nhắc Flash Sale). LLM explanation override: "Không có ngoại lệ nào được áp dụng trong trường hợp này" — kết quả cuối vẫn đúng vì synthesis dùng LLM explanation.

---

## Routing Decision #3 — HITL Triggered

**Task:** `ERR-403-AUTH là lỗi gì và cách xử lý?`  
**Trace:** `run_20260414_172211_232827.json` (q09)

**Worker được chọn:** `human_review` → `retrieval_worker`  
**Route reason:** `ép buộc human_review: rủi ro cao + mã lỗi không xác định (err-) | risk_flag: High`  
**MCP tools được gọi:** none  
**Workers called sequence:** `human_review → retrieval_worker → synthesis_worker`

**Kết quả thực tế:**

- final_answer: "[synthesis tổng hợp từ SLA/FAQ docs — không có doc về ERR-403-AUTH]"
- confidence: **0.30** (thấp nhất trong 15 câu) | latency: **1421ms**
- hitl_triggered: **True**
- Correct routing? **Yes** (HITL đúng), nhưng answer quality thấp do không có doc về lỗi cụ thể

**Nhận xét:** Đây là trường hợp routing logic hoạt động đúng nhất về mặt thiết kế. Supervisor phát hiện 2 tín hiệu: (1) `risk_high=True` từ keyword "err-", (2) không có context về ERR-403-AUTH trong KB. Kết quả confidence 0.30 là honest abstain — hệ thống không hallucinate lỗi. Latency 1421ms nhanh nhất vì không có LLM policy call.

**Full history từ trace:**
```
[supervisor] route=human_review reason=ép buộc human_review: rủi ro cao + mã lỗi không xác định (err-)
[human_review] HITL triggered — awaiting human input
[retrieval_worker] HIGH CONFIDENCE: retrieved 3 chunks
[synthesis_worker] answer generated, confidence=0.3
[graph] completed in 1421ms
```

---

## Routing Decision #4 — Multi-MCP Complex Case

**Task:** `Contractor cần Admin Access (Level 3) để khắc phục sự cố P1 đang active. Quy trình cấp quyền tạm thời như thế nào?`  
**Trace:** `run_20260414_172224_344366.json` (q13)

**Worker được chọn:** `policy_tool_worker`  
**Route reason:** `route to policy_tool_worker: chứa keyword về policy/quyền hạn | risk_flag: Normal`  
**MCP tools được gọi:** `search_kb`, `get_ticket_info`, `check_access_permission` (3 calls)  
**Workers called sequence:** `policy_tool_worker → synthesis_worker`

**Kết quả thực tế:**

- final_answer: "Level 3 yêu cầu phê duyệt từ Line Manager + IT Admin + IT Security. Không có emergency bypass cho Level 3. Phải follow quy trình chuẩn dù P1 đang active."
- confidence: **0.89** | latency: **6248ms** (chậm nhất trong 15 câu — 3 MCP calls)
- policy_applies: **False** (contractor không có quyền bypass)
- Correct routing? **Yes**

**Nhận xét — Đây là trường hợp routing khó nhất:** Task chứa cả "P1" (retrieval keyword) lẫn "access Level 3" (policy keyword). Supervisor ưu tiên policy_keyword vì check trước retrieval_keyword trong logic (line 110 graph.py). Kết quả đúng — nếu route về retrieval thì chỉ trả SLA docs, không check được quyền hạn contractor. MCP orchestration 3 bước: search context → lấy ticket status thật → check permission rule → synthesis tổng hợp thành câu trả lời nhất quán.

---

## Tổng kết

### Routing Distribution (15 câu thực tế)

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 8 | 53% |
| policy_tool_worker | 7 | 47% |
| human_review | 1 | 6% (q09, sau đó chuyển về retrieval) |

### Routing Accuracy

- Câu route đúng: **13 / 15** (ước tính — dựa trên confidence và answer quality)
- Câu có thể mismatch: ~2 (policy keyword overlap với retrieval cases)
- Câu trigger HITL: **1** (q09 — ERR-403-AUTH)
- Không có câu nào route về default sai hoàn toàn

### MCP Usage

| MCP Calls per Request | Số câu |
|-----------------------|--------|
| 0 (retrieval path) | 8 |
| 1 | 3 (q02, q07, q10) |
| 2 | 2 (q03, q12) |
| 3 | 2 (q13, q15) |

### Lesson Learned về Routing

1. **Keyword priority order quan trọng** — policy_keywords được check trước retrieval_keywords trong `supervisor_node` (line 110–118 graph.py). Câu multi-domain (có cả SLA lẫn access) sẽ luôn đi về policy_tool_worker. Đây là thiết kế có chủ đích, không phải bug.

2. **risk_high + "err-" là bộ lọc conservative** — chỉ 1/15 câu trigger HITL (q09). Ngưỡng này tốt: không quá aggressive (không block câu P1 bình thường), nhưng đủ để catch unknown error codes. Confidence output 0.30 của q09 xác nhận đây là câu "không biết" thật sự.

### Route Reason Quality

Mỗi `route_reason` trong trace đều có format `[route decision]: [keyword trigger] | risk_flag: [Normal/High]`. Đủ thông tin để debug. Điểm cải thiện: nên thêm keyword nào cụ thể trigger (e.g., `keyword_matched=["access", "level"]`) để trace machine-readable hơn.
