# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Quang Tùng  
**Mã học viên:** 2A202600197  
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào?

**File chính:** `workers/policy_tool.py`, `workers/retrieval.py`, `workers/synthesis.py`

**Functions tôi implement:**
- `analyze_policy()` — phân tích policy với LLM primary + rule-based fallback
- `_estimate_confidence()` — tính confidence từ embedding score với normalize
- `run()` trong cả 3 workers — đảm bảo input/output khớp contract
- `_call_mcp_tool()` — gọi MCP tools từ policy worker

Tôi chịu trách nhiệm Sprint 2: xây dựng 3 workers độc lập, test được từng file, và cập nhật `contracts/worker_contracts.yaml` với `status: "done"` cho cả 3 workers.

**Kết nối với thành viên khác:** `retrieval.py` cung cấp `retrieved_chunks` cho `policy_tool.py` và `synthesis.py`. `policy_tool.py` ghi `policy_result` vào state để `synthesis.py` build context. M1 không thể kết nối `graph.py` cho đến khi 3 workers có `run(state)` trả về đúng contract.

**Bằng chứng:** `contracts/worker_contracts.yaml` — `status: "done"` cho cả 3 workers ngày 14/04/2026. Commit của tôi: `38fa5b0` (sprint 2.1–2.2), `472d18b` (sprint 2.3), `248b3e3` (sprint 2.4 done), `73f851b` (fix bug policy worker).

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Implement `_estimate_confidence()` dựa trên embedding score từ ChromaDB thay vì hardcode hoặc dùng LLM-as-Judge.

**Các lựa chọn thay thế:**
- Hardcode confidence = 0.8 cho mọi câu — đơn giản nhưng không phản ánh thực tế, không đạt bonus +1 theo SCORING
- LLM-as-Judge — chính xác nhất nhưng tốn thêm 1 API call mỗi câu (~1–2 giây latency)
- Dùng embedding score (đã chọn) — không tốn thêm API call, score đã có sẵn từ ChromaDB

**Lý do chọn:** Embedding score phản ánh mức độ khớp giữa câu hỏi và evidence — câu hỏi có evidence rõ ràng thì score cao, câu hỏi mơ hồ thì score thấp. Đây là proxy hợp lý cho confidence mà không tốn thêm chi phí.

**Vấn đề phát sinh và cách xử lý:** ChromaDB với `text-embedding-3-small` tiếng Việt trả về score thực tế chỉ ~0.5–0.7, không phải 0–1. Nếu dùng raw score thì confidence luôn thấp dù answer đúng. Tôi thêm normalize để map `[0.3, 1.0] → [0.5, 0.92]`:

```python
low, high = 0.3, 1.0
normalized = (avg_score - low) / (high - low)
scaled = 0.5 + normalized * 0.42   # map về [0.5, 0.92]
exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))
confidence = min(0.92, scaled - exception_penalty)
```

**Bằng chứng từ grading run** (`artifacts/grading_run.jsonl`):
```
gq01 (SLA đơn giản)      → conf=0.91
gq04 (store credit)      → conf=0.85
gq07 (abstain)           → conf=0.30  ← đúng, không có evidence
gq10 (Flash Sale)        → conf=0.92
avg grading confidence   → 0.85
```

Confidence phân tán tự nhiên theo độ khó câu hỏi, không bị cap ở một giá trị cố định.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** `NameError: name 'mcp_search' is not defined` trong `workers/policy_tool.py`

**Symptom:** Tất cả câu route qua `policy_tool_worker` đều có `confidence=0.10` và `retrieved_chunks=0`, dù pipeline không crash:

```
# Output eval_trace.py trước khi sửa:
[02/15] q02: conf=0.10, 1338ms
[03/15] q03: conf=0.10, 1480ms
[07/15] q07: conf=0.10, 1275ms
history: "[policy_tool_worker] ERROR: name 'mcp_search' is not defined"
```

**Root cause:** Khi merge code từ nhiều thành viên, Step 1 gọi MCP dùng tên biến `mcp_result`, nhưng đoạn merge chunks bên dưới dùng `mcp_search` (tên từ version trước). Exception bị catch bởi `except Exception as e` nên không crash rõ ràng — worker âm thầm trả về chunks rỗng, synthesis thấy không có evidence → confidence = 0.1.

**Cách sửa:** Thống nhất tên biến thành `mcp_search` xuyên suốt, bỏ điều kiện `if not chunks` vốn ngăn MCP chạy khi đã có chunks:

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

**Bằng chứng sau khi sửa** (commit `73f851b` — "solve conflict at policy"):
```
# Sau khi sửa:
[02/15] q02: conf=0.67  ← từ 0.10
[03/15] q03: conf=0.69  ← từ 0.10
avg_confidence: 0.659   ← từ 0.519
mcp_usage_rate: 7/15    ← từ 0/15
```

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**

Thiết kế `analyze_policy()` với LLM+fallback pattern — worker không bao giờ crash dù API fail, và xử lý đúng edge case temporal scoping (gq02: đơn 31/01 → abstain vì không có policy v3) và exception detection (gq10: Flash Sale → từ chối hoàn tiền). Hai câu này chiếm 20/96 điểm grading.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Không kiểm tra kỹ tên biến khi merge code — bug `mcp_search` vs `mcp_result` chỉ phát hiện được khi thấy confidence = 0.10 bất thường trong eval_trace. Nên có unit test cho từng worker để catch lỗi này sớm hơn thay vì phải debug từ output.

**Nhóm phụ thuộc vào tôi ở đâu?**

M1 không thể kết nối `graph.py` cho đến khi `run(state)` của 3 workers trả về đúng contract. M4 không có meaningful trace nếu policy worker crash âm thầm — toàn bộ 7 policy queries sẽ có confidence = 0.10 và sources rỗng, ảnh hưởng trực tiếp đến `grading_run.jsonl`.

**Phần tôi phụ thuộc vào thành viên khác:**

Phụ thuộc M1 để biết `AgentState` schema, và M3 để `mcp_server.dispatch_tool()` có đủ tools — nếu `search_kb` chưa implement thì policy worker fallback về chunks rỗng.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ implement **LLM-as-Judge** để tính confidence chính xác hơn. Hiện tại `_estimate_confidence()` trong `workers/synthesis.py` dùng embedding score từ ChromaDB làm proxy — đây là đo chất lượng retrieval, không phải chất lượng answer. Trace gq07 cho thấy vấn đề rõ nhất: pipeline abstain đúng (conf=0.30) nhưng không có cách nào biết câu trả lời có đúng hay không nếu không có ground truth. Với LLM-as-Judge, sau khi có answer, gọi thêm 1 LLM call để tự chấm điểm dựa trên context — confidence lúc đó phản ánh thật sự chất lượng answer thay vì chỉ phản ánh độ khớp của embedding.
