# System Architecture — Lab Day 09

**Nhóm:** E304  
**Ngày:** 2026-04-14  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

**Pattern đã chọn:** Supervisor-Worker (LangGraph `StateGraph`)

**Lý do chọn pattern này:**  
Day 08 là một RAG pipeline đơn — một hàm vừa retrieve, vừa kiểm tra policy, vừa generate. Khi pipeline trả lời sai không rõ lỗi nằm ở bước nào. Day 09 tách mỗi trách nhiệm thành một worker riêng, Supervisor điều phối luồng qua `AgentState` dùng chung. Mỗi worker có thể test độc lập và thay thế mà không ảnh hưởng toàn hệ.

---

## 2. Sơ đồ Pipeline

```
User Query (task)
       │
       ▼
┌──────────────────────┐
│     Supervisor       │  → ghi: supervisor_route, route_reason, risk_high, needs_tool
│     (graph.py)       │
└──────────┬───────────┘
           │
     [route_decision()]   ← conditional edge của LangGraph
           │
  ┌────────┼────────────────────┐
  │        │                   │
  ▼        ▼                   ▼
human_  retrieval_         policy_tool_
review  worker             worker
  │     (ChromaDB          (policy check
  │      + rerank)          + MCP tools)
  │         │                   │
  └────►    ▼                   ▼
      ┌────────────────────────────┐
      │      synthesis_worker      │  → ghi: final_answer, sources, confidence
      │   (gpt-4o-mini, T=0.1)    │
      └────────────┬───────────────┘
                   │
                   ▼
               [END] → AgentState với full trace
```

**Lưu ý luồng HITL (q09 — trace thực tế):**
```
ERR-403-AUTH → supervisor detects "err-" + risk_high=True
→ human_review (HITL triggered, auto-approve in lab mode)
→ retrieval_worker → synthesis_worker
History: 6 bước thay vì 4 bước thông thường
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích task bằng keyword matching, quyết định route và risk |
| **Input** | `task` (string) |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool` |
| **Routing logic** | policy_keywords → policy_tool_worker; retrieval_keywords → retrieval_worker; "err-" + risk → human_review |
| **HITL condition** | `risk_high=True AND "err-" in task` → ép route về human_review |

**Routing phân bố thực tế (15 câu, từ traces):**

| Worker | Số câu | % |
|--------|--------|---|
| retrieval_worker | 8 | 53% |
| policy_tool_worker | 7 | 47% |
| human_review | 1 | 6% (q09, sau đó về retrieval) |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Dense vector search trên ChromaDB, rerank kết quả |
| **Embedding model** | OpenAI `text-embedding-3-small` |
| **Top-k** | 5 (lấy từ ChromaDB), rerank → trả về 3 tốt nhất |
| **Reranking** | Keyword bonus: `+0.05` mỗi term match từ query trong chunk text |
| **Stateless?** | Yes — không đọc/ghi gì ngoài contract |
| **Low-confidence flag** | Nếu bất kỳ chunk nào score < 0.35, ghi "LOW CONFIDENCE" vào history |

**Ví dụ từ trace q01 (SLA P1):**
```
Retrieved 3 chunks, scores: [0.868, 0.735, 0.668]
Source top: support/sla-p1-2026.pdf (score 0.868)
History: "[retrieval_worker] HIGH CONFIDENCE: retrieved 3 chunks"
```

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Kiểm tra policy exceptions + gọi MCP tools để enrich context |
| **MCP tools gọi** | `search_kb`, `get_ticket_info`, `check_access_permission`, `get_leave_process`, `get_late_penalty` |
| **Exception cases** | flash_sale, digital_product, activated_product, policy_version (v3 vs v4) |
| **LLM call** | gpt-4o-mini, `json_object` mode, temperature=0 — primary analysis |
| **Fallback** | Rule-based nếu LLM call thất bại |

**Ví dụ MCP call sequence từ trace q13 (3 MCP tools):**
```
Task: "Contractor cần Admin Access (Level 3) để khắc phục sự cố P1"
MCP calls:
  1. search_kb → 3 chunks từ it/access-control-sop.md
  2. get_ticket_info → ticket IT-9847, status: in_progress
  3. check_access_permission(level=3, role=contractor, emergency=False)
     → can_grant=True, required_approvers=[Line Manager, IT Admin, IT Security]
```

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | gpt-4o-mini (fallback: Gemini 1.5 Flash) |
| **Temperature** | 0.1 |
| **Grounding strategy** | System prompt: "CHỈ dùng context được cung cấp, KHÔNG dùng kiến thức ngoài" |
| **Abstain condition** | Nếu retrieved_chunks=[] → trả về "Không đủ thông tin trong tài liệu nội bộ" |
| **Confidence formula** | `avg_score` mapped [0.3, 1.0] → [0.5, 0.92], trừ `0.05 × exceptions_count` |
| **Citation format** | `[1]` hoặc `[source_name]` sau mỗi câu quan trọng |

**Confidence thực tế 15 traces:** min=0.3 (q09 — ERR-403), max=0.92 (q12), avg=0.768

### MCP Server (`mcp_server.py`)

| Tool | Input | Output | Ghi chú |
|------|-------|--------|---------|
| `search_kb` | query, top_k | chunks, sources, total_found | Delegate về retrieval_worker |
| `get_ticket_info` | ticket_id | ticket details, notifications | Mock data (P1-LATEST, IT-1234) |
| `check_access_permission` | access_level, requester_role, is_emergency | can_grant, required_approvers | Rules: Level 1/2/3 |
| `create_ticket` | priority, title, description | ticket_id, url | MOCK — không tạo thật |
| `get_leave_process` | leave_days, leave_type, is_emergency | submission_channel, notice_days | HR policy |
| `get_late_penalty` | minutes_late, late_count | level (L0/L1/L2), action | Attendance mock |

**MCP usage rate từ traces:** 7/15 câu gọi MCP (46%) — tất cả qua policy_tool_worker.  
Số MCP calls per request: 1 (simple policy) đến 3 (complex: q13, q15).

---

## 4. Shared State Schema (`AgentState`)

| Field | Type | Mô tả | Ai ghi | Ai đọc |
|-------|------|-------|--------|--------|
| `task` | str | Câu hỏi đầu vào | main.py | supervisor, tất cả workers |
| `supervisor_route` | str | Worker được chọn | supervisor | route_decision() |
| `route_reason` | str | Lý do route (có risk_flag suffix) | supervisor | trace/debug |
| `risk_high` | bool | True nếu task có risk keywords | supervisor | human_review check |
| `needs_tool` | bool | True → policy worker được gọi MCP | supervisor | policy_tool_worker |
| `hitl_triggered` | bool | True nếu HITL đã kích hoạt | human_review | synthesis (biết đây là case đặc biệt) |
| `retrieved_chunks` | list | Chunks có text, source, score, metadata | retrieval/policy | synthesis |
| `retrieved_sources` | list | Unique sources | retrieval/policy | synthesis, trace |
| `policy_result` | dict | policy_applies, exceptions_found, explanation | policy_tool | synthesis |
| `mcp_tools_used` | list | Danh sách MCP calls với timestamp | policy_tool | trace/eval |
| `final_answer` | str | Câu trả lời cuối có citation | synthesis | output |
| `confidence` | float | 0.0–1.0 | synthesis | eval, HITL decision |
| `history` | list | Log từng bước "[worker] action" | mọi worker | debug/trace |
| `workers_called` | list | Thứ tự workers đã qua | mọi worker | eval |
| `latency_ms` | int | Tổng thời gian (ms) | graph wrapper | eval |
| `run_id` | str | ID duy nhất mỗi run | make_initial_state | trace file name |

---

## 5. So sánh Supervisor-Worker với Single Agent

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Không có trace → đọc toàn code | Xem history → biết ngay bước sai |
| Test một phần | Không thể | `python workers/retrieval.py` độc lập |
| Thêm capability mới | Sửa toàn prompt | Thêm MCP tool + 1 route rule |
| Routing visibility | Không có | `route_reason` trong mỗi trace |
| Multi-hop accuracy | ~30% (Day 08 baseline) | ~76.8% avg confidence (có MCP enrich) |
| Latency | ~800ms | ~3655ms (+2855ms overhead routing) |

---

## 6. Giới hạn và điểm cần cải tiến

1. **Routing dùng keyword matching** — "access" trong câu hỏi về SLA vẫn route về policy_tool_worker. Nên dùng LLM classifier để routing chính xác hơn (hiện tại routing accuracy ~87%, 2/15 câu có thể mismatch).

2. **HITL là placeholder** — `human_review_node` auto-approve trong lab mode. Câu q09 (ERR-403-AUTH) trigger HITL nhưng không có human answer thật → confidence chỉ 0.3. Production cần interrupt_before thật với LangGraph breakpoint.

3. **Policy worker luôn gọi MCP search_kb** khi `needs_tool=True`, dù retrieval_worker đã lấy chunks rồi. Gây duplicate retrieval + tăng latency. Nên check `len(retrieved_chunks) > 0` trước khi gọi.

4. **Không có retry logic** — nếu LLM call timeout, synthesis trả về lỗi thay vì retry. Nên thêm exponential backoff cho production.
