# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** E304  
**Ngày:** 2026-04-14

> Số liệu Day 08 lấy từ `eval_report.json` (field `day08_single_agent`).  
> Số liệu Day 09 lấy từ 15 trace files trong `artifacts/traces/` + `eval_report.json`.

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.75 | 0.768 | **+1.8%** | Day 09 tính từ 15 traces thực tế |
| Avg latency (ms) | 800 | 3655 | **+2855ms** | Overhead routing + LLM calls nhiều hơn |
| Abstain rate | 20% | ~7% (1/15) | **-13%** | Day 09 chỉ abstain q09 (ERR-403) |
| Multi-hop accuracy | ~30% | ~47% (7/15 dùng MCP enrich) | **+17%** | Ước tính từ MCP usage rate |
| Routing visibility | None | 100% có route_reason | N/A | Mỗi trace đều có keyword trigger |
| Min confidence | ~0.4 (Day 08 abstain) | 0.30 (q09 HITL case) | -0.10 | Day 09 honest về "không biết" hơn |
| Max confidence | ~0.85 | 0.92 (q12 — access control) | +0.07 | MCP enrich giúp hit score cao hơn |
| MCP tool usage | 0 | 46% (7/15 câu) | N/A | Chỉ Day 09 có MCP capability |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document, không cần policy)

**Ví dụ thực tế:** q01 (SLA P1), q04 (escalation P2), q05 (helpdesk FAQ)

| Metric | Day 08 | Day 09 |
|--------|--------|--------|
| Avg latency | ~800ms | ~2000ms |
| Avg confidence | ~0.75 | ~0.80 (q04=0.76, q05=0.84, q06=0.86) |
| Routing visible | No | Yes |

**Kết luận:** Multi-agent **không cải thiện** accuracy cho câu đơn giản, nhưng tăng ~2x latency do overhead LangGraph routing. Trade-off không có lợi cho simple queries. Với Day 08, câu hỏi SLA đơn giản trả lời được tốt trong 800ms. Day 09 mất 1939–5600ms cho cùng loại câu.

**Dẫn chứng từ trace q04:**
```
latency_ms: 1939
workers_called: ["retrieval_worker", "synthesis_worker"]
mcp_tools_used: []   ← không cần MCP
confidence: 0.76
```

### 2.2 Câu hỏi multi-hop (cross-document, cần policy + context)

**Ví dụ thực tế:** q13 (Contractor + Level 3 + P1 active), q15 (hoàn tiền + ngày cụ thể)

| Metric | Day 08 | Day 09 |
|--------|--------|--------|
| Accuracy (multi-hop) | ~30% | Cao hơn (q13=0.89, q15=0.88) |
| Routing visible | No | Yes — 3 MCP calls traceable |
| Context enrich | No | Yes — MCP merges thêm chunks |

**Kết luận:** Multi-agent **cải thiện rõ rệt** với câu multi-hop. Day 08 single agent không thể kết hợp thông tin từ nhiều nguồn (access policy + ticket status + SLA). Day 09 với MCP orchestration 3 bước (search_kb → get_ticket_info → check_access_permission) cho confidence 0.89 cho q13.

**Dẫn chứng từ trace q13:**
```
task: "Contractor cần Admin Access Level 3 để khắc phục P1 đang active"
MCP calls: search_kb + get_ticket_info + check_access_permission
confidence: 0.89
final_answer: "Level 3 yêu cầu 3 approvers. Không có emergency bypass cho Level 3."
```

### 2.3 Câu hỏi cần abstain (unknown / no document)

**Ví dụ thực tế:** q09 (ERR-403-AUTH — không có doc trong KB)

| Metric | Day 08 | Day 09 |
|--------|--------|--------|
| Abstain rate | 20% (3/15 câu) | ~7% (1/15) |
| Hallucination cases | Không đo được | 0 — HITL route nếu unknown |
| Confidence khi abstain | ~0.4 | 0.30 (honest lower) |

**Kết luận:** Day 09 abstain ít hơn nhờ MCP enrich context. Khi thật sự không có thông tin (ERR-403-AUTH không có trong KB), Day 09 trigger HITL và trả confidence 0.30 thay vì hallucinate — honest hơn Day 08.

**Dẫn chứng từ trace q09:**
```
hitl_triggered: True
confidence: 0.30   ← thấp nhất 15 câu, nhưng là honest abstain
history: "[human_review] HITL triggered — awaiting human input"
```

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow

```
Khi answer sai:
  → Đọc toàn bộ RAG pipeline code
  → Không có trace → không biết lỗi ở retrieval hay generation
  → Thời gian ước tính: 15–20 phút để isolate bug
```

### Day 09 — Debug workflow

```
Khi answer sai:
  1. Mở trace file → xem history array (4–6 steps rõ ràng)
  2. Check supervisor_route + route_reason → routing đúng chưa?
  3. Check retrieved_chunks scores → retrieval chất lượng chưa?
  4. Check policy_result.exceptions_found → policy logic đúng chưa?
  5. Check mcp_tools_used → MCP call thành công chưa?
  → Test worker độc lập: python workers/retrieval.py
  → Thời gian ước tính: 3–5 phút để isolate bug
```

**Case debug thực tế trong lab:**  
q09 (ERR-403-AUTH) có confidence 0.30 → mở trace → thấy ngay `history[1] = "[human_review] HITL triggered"` → biết hệ thống không có doc về lỗi này → không phải bug mà là "honest unknown". Không cần đọc code, trace đủ thông tin.

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Sửa toàn prompt + logic | Thêm function vào mcp_server.py + 1 route rule |
| Thêm 1 domain mới | Re-prompt toàn hệ thống | Thêm worker mới + route condition |
| Thay đổi retrieval strategy | Sửa trong pipeline, risk break | Sửa workers/retrieval.py, test độc lập |
| A/B test một phần | Phải clone toàn pipeline | Swap worker, giữ nguyên phần còn lại |

**Dẫn chứng từ lab:** `get_leave_process` và `get_late_penalty` được thêm vào `mcp_server.py` mà không sửa `graph.py` hay `synthesis.py`. Chỉ thêm tool function + 2 route conditions trong policy_tool.py (line 388–431). Total: ~40 lines thêm, zero regression.

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 LLM calls | Day 09 LLM calls | Ghi chú |
|---------|-----------------|-----------------|---------|
| Simple query (q01 SLA) | 1 (generation) | 2 (embed + generation) | +1 embedding call |
| Policy query (q02 refund) | 1 | 3 (embed + policy LLM + synthesis) | +2 calls |
| Complex query (q13, 3 MCP) | 1 | 5 (embed + 3 MCP + synthesis) | +4 calls |

**Latency thực tế theo số MCP calls:**

| MCP calls | Avg latency | Examples |
|-----------|-------------|---------|
| 0 | ~2283ms | q04, q05, q06, q08, q11, q14 |
| 1 | ~4283ms | q02, q07, q10 |
| 2 | ~3625ms | q03, q12 |
| 3 | ~5833ms | q13, q15 |

**Nhận xét về cost-benefit:** Latency tăng gần tuyến tính theo số MCP calls. Với simple queries không cần MCP, overhead Day 09 so với Day 08 chỉ khoảng ~1.5–2x (routing + embedding). Với complex queries, Day 09 tốn 4–6x nhiều hơn nhưng trả lời chính xác hơn đáng kể.

---

## 6. Kết luận

**Multi-agent tốt hơn single agent ở:**

1. **Complex / multi-hop queries** — MCP orchestration kết hợp nhiều nguồn thông tin (policy + ticket + permission) mà single agent không làm được. Confidence q13=0.89 vs Day 08 multi-hop ~30%.
2. **Debuggability** — Trace có history đầy đủ, có thể test từng worker độc lập. Thay vì 15–20 phút debug, chỉ cần 3–5 phút đọc trace.
3. **Extensibility** — Thêm MCP tool hoặc worker không ảnh hưởng phần còn lại. Đã validate bằng việc thêm leave/penalty tools mà không break existing tests.
4. **Honest abstain** — HITL + confidence scoring giúp hệ thống trung thực hơn khi không biết (q09: 0.30 thay vì hallucinate).

**Multi-agent kém hơn hoặc không khác biệt ở:**

1. **Simple queries** — Overhead routing tăng latency từ 800ms lên 1400–5600ms không có lợi ích tương ứng. q01 (SLA P1 đơn giản) mất 5600ms — 7x chậm hơn Day 08.

**Khi nào KHÔNG nên dùng multi-agent:**

- Queries đơn giản, single-document, không cần policy check — single RAG pipeline đủ và nhanh hơn nhiều.
- Khi latency là constraint cứng (< 1s) — multi-agent với LLM routing không đáp ứng được.
- Prototype/MVP stage — complexity overhead không xứng với benefit khi chưa có nhiều domain.

**Nếu tiếp tục phát triển:**

- Thay keyword-based routing bằng LLM classifier — giảm mismatch với câu multi-domain.
- Implement HITL thật bằng LangGraph `interrupt_before` thay vì auto-approve.
- Cache MCP search_kb results khi retrieval_worker đã lấy chunks — tránh duplicate retrieval (q02, q07 hiện đang call ChromaDB 2 lần).
