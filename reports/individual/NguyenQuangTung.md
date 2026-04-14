# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Quang Tùng  
**Mã học viên:** 2A202600197  
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào?

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/policy_tool.py`, `workers/retrieval.py`, `workers/synthesis.py`
- Functions tôi implement: `analyze_policy()`, `run()` trong cả 3 workers, `_estimate_confidence()` trong synthesis, `_call_mcp_tool()` trong policy_tool
- Contract: `contracts/worker_contracts.yaml` — cập nhật `actual_implementation.status` cho 3 workers

Tôi chịu trách nhiệm toàn bộ Sprint 2: xây dựng 3 workers với input/output khớp contract, đảm bảo mỗi worker test độc lập được. Cụ thể, `policy_tool.py` là phần phức tạp nhất — phải kết hợp rule-based exception detection với LLM call (gpt-4o-mini, `response_format=json_object`) và fallback graceful khi LLM fail.

**Cách công việc của tôi kết nối với phần của thành viên khác:**

`retrieval.py` cung cấp `retrieved_chunks` cho `policy_tool.py` và `synthesis.py`. `policy_tool.py` ghi `policy_result` vào state để `synthesis.py` đọc khi build context. Nếu workers chưa xong, M1 không thể kết nối `graph.py` và pipeline không chạy end-to-end.

**Bằng chứng:** `contracts/worker_contracts.yaml` được cập nhật `status: "done"` cho cả 3 workers vào ngày 14/04/2026.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Dùng LLM (gpt-4o-mini) làm primary analyzer trong `analyze_policy()`, với rule-based keyword detection làm fallback — thay vì chỉ dùng rule-based đơn thuần.

**Các lựa chọn thay thế:**
- Option A: Chỉ rule-based (keyword matching) — nhanh, không tốn API call, nhưng bỏ sót các câu hỏi dùng từ đồng nghĩa hoặc ngữ cảnh phức tạp.
- Option B: Chỉ LLM — chính xác hơn nhưng nếu API fail thì toàn bộ policy check crash.
- Option C (đã chọn): Rule-based chạy trước để detect các exception rõ ràng (flash_sale, digital_product, activated), sau đó LLM override `policy_applies` và bổ sung `explanation`. Nếu LLM fail → `except Exception` giữ nguyên rule-based result.

**Lý do:** Câu q12 (temporal scoping) và q07 (license key) đều cần LLM hiểu ngữ cảnh — rule-based không thể tính ngày làm việc hay phân biệt "license key đã kích hoạt" vs "chưa kích hoạt". Nhưng nếu chỉ dùng LLM, khi API timeout thì confidence = 0.1 và answer rỗng.

**Trade-off đã chấp nhận:** Mỗi policy query tốn thêm ~1 LLM call (~1–2 giây), tăng latency từ ~2s lên ~4–6s. Chấp nhận được vì policy queries chiếm 7/15 câu (46%) và accuracy quan trọng hơn latency trong bài toán này.

**Bằng chứng từ trace:**

```
q07 | route=policy_tool_worker | conf=0.51
workers_called: ['policy_tool_worker', 'synthesis_worker']
mcp_tools: ['search_kb']
answer: "Sản phẩm kỹ thuật số (license key) không được hoàn tiền.
         Điều này được quy định trong chính sách hoàn tiền... [1]"
sources: ['policy/refund-v4.pdf']
latency: 3630ms
```

So sánh: nếu chỉ dùng rule-based, câu "license key có được hoàn tiền không?" sẽ detect đúng nhưng `explanation` sẽ là hardcode string, không có citation từ docs thật.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** `NameError: name 'mcp_search' is not defined` trong `workers/policy_tool.py`

**Symptom:** Tất cả câu route qua `policy_tool_worker` đều có `confidence=0.10` và `retrieved_chunks=0` trong trace, dù MCP `search_kb` được gọi và trả về chunks thật.

```
# Trước khi sửa — output eval_trace.py:
[02/15] q02: conf=0.10, 1338ms
[03/15] q03: conf=0.10, 1480ms
[07/15] q07: conf=0.10, 1275ms
[10/15] q10: conf=0.10, 1361ms
history: "[policy_tool_worker] ERROR: name 'mcp_search' is not defined"
```

**Root cause:** Khi merge code từ nhiều thành viên, đoạn Step 1 dùng tên biến `mcp_result` để gọi MCP, nhưng đoạn merge chunks bên dưới lại dùng `mcp_search` (tên biến từ version trước). Exception bị catch bởi `except Exception as e` nên không crash rõ ràng — chỉ ghi vào history và tiếp tục với chunks rỗng.

**Cách sửa:** Thống nhất tên biến thành `mcp_search` xuyên suốt, đồng thời bỏ điều kiện `if not chunks` (vốn ngăn MCP chạy khi đã có chunks từ retrieval) để MCP luôn được gọi:

```python
# Sau khi sửa:
mcp_search = _call_mcp_tool("search_kb", {"query": task, "top_k": search_top_k})
state["mcp_tools_used"].append(mcp_search)
if mcp_search.get("output") and mcp_search["output"].get("chunks"):
    existing_texts = {c.get("text") for c in chunks}
    for c in mcp_search["output"]["chunks"]:
        if c.get("text") not in existing_texts:
            chunks.append(c)
    state["retrieved_chunks"] = chunks
    state["retrieved_sources"] = list({c.get("source") for c in chunks})
```

**Bằng chứng sau khi sửa:**

```
# Sau khi sửa — output eval_trace.py:
[02/15] q02: conf=0.67, 4811ms  ← từ 0.10 lên 0.67
[03/15] q03: conf=0.69, 3465ms  ← từ 0.10 lên 0.69
[07/15] q07: conf=0.51, 3630ms  ← từ 0.10 lên 0.51
avg_confidence toàn pipeline: 0.659  ← từ 0.519
```

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**

Thiết kế `analyze_policy()` với LLM+fallback pattern — đảm bảo worker không bao giờ crash dù API fail, và xử lý đúng các edge case như temporal scoping (q12: đơn trước 01/02/2026 → abstain vì không có policy v3) và digital product exception (q07). Đây là phần phức tạp nhất trong Sprint 2 và ảnh hưởng trực tiếp đến điểm grading.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Không kiểm tra kỹ tên biến khi merge code với thành viên khác — dẫn đến bug `mcp_search` vs `mcp_result` chỉ phát hiện được khi chạy eval_trace và thấy confidence = 0.10 bất thường. Nên có unit test cho từng worker để catch lỗi này sớm hơn.

**Nhóm phụ thuộc vào tôi ở đâu?**

M1 (graph.py) không thể uncomment `from workers.policy_tool import run` cho đến khi `run(state)` trả về đúng contract. M4 (eval_trace) không có meaningful trace nếu policy worker crash âm thầm — toàn bộ policy queries sẽ có confidence = 0.10 và sources rỗng.

**Phần tôi phụ thuộc vào thành viên khác:**

Phụ thuộc vào M1 để biết `AgentState` schema (các key nào có trong state), và M3 để `mcp_server.dispatch_tool()` hoạt động đúng — nếu MCP server chưa có `search_kb` thì policy worker fallback về chunks rỗng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ implement **top-k dynamic** trong `retrieve_dense()` dựa trên độ phức tạp của câu hỏi. Trace của q15 (multi-hop: SLA + Level 2 access) cho thấy chỉ retrieve 3 chunks nhưng cần cross-reference 2 tài liệu khác nhau (`sla-p1-2026.pdf` và `access-control-sop.md`). Nếu tăng top_k lên 5–6 cho câu multi-hop, synthesis có thêm evidence từ cả hai docs và answer sẽ đầy đủ hơn — đặc biệt quan trọng cho câu q09 (16 điểm) trong grading.
