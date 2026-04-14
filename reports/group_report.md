# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** E304

| Tên | MSHV | Vai trò |
|-----|------|---------|
| Đặng Văn Minh | 2A202600027 | M1 — Tech Lead, Supervisor Owner |
| Nguyễn Quang Tùng | 2A202600197 | M2 — Worker Owner |
| Nguyễn Thị Quỳnh Trang | 2A202600406 | M3 — MCP Owner |
| Đồng Văn Thịnh | 2A20260036 | M4 — Trace & Docs Owner |

**Ngày nộp:** 14/04/2026  
**Repo:** https://github.com/DangMinh21/Day09-E304-Multi-Agent-Orchestration

---

## 1. Kiến trúc nhóm đã xây dựng

**Hệ thống tổng quan:**  
Hệ thống gồm 1 Supervisor và 4 nodes trong LangGraph `StateGraph`: `retrieval_worker`, `policy_tool_worker`, `human_review`, và `synthesis_worker`. Supervisor đọc task, quyết định route, rồi workers xử lý và trả kết quả về state chung `AgentState`. Tất cả 15 test questions và 10 grading questions đã chạy end-to-end không crash.

**Routing logic cốt lõi:**  
Keyword-based với 3 nhóm theo độ ưu tiên:

```
1. risk_keywords: ["emergency", "khẩn cấp", "2am", "err-"] → set risk_high=True
2. policy_keywords: ["hoàn tiền", "refund", "flash sale", "access", "level 3"] → policy_tool_worker
3. retrieval_keywords: ["p1", "sla", "ticket", "escalation"] → retrieval_worker (elif)
4. risk_high + "err-" → human_review (override mọi route trên)
```

Thứ tự `elif` đảm bảo policy_keywords luôn được check trước retrieval — câu multi-domain (có cả "P1" lẫn "access") đi về `policy_tool_worker`.

**MCP tools đã tích hợp:**

- `search_kb(query, top_k)`: semantic search ChromaDB — gọi trong 7/10 grading questions qua `policy_tool_worker`
- `get_ticket_info(ticket_id)`: tra ticket mock (P1-LATEST, IT-1234) — gọi trong gq03, gq09
- `check_access_permission(level, role, is_emergency)`: kiểm tra quyền theo level 1–3 — gọi trong gq03, gq09
- `get_leave_process`, `get_late_penalty`: HR tools bổ sung

**Ví dụ trace gq09 (3 MCP calls):**
```
[policy_tool_worker] called MCP search_kb
[policy_tool_worker] called MCP get_ticket_info
[policy_tool_worker] called MCP check_access_permission
workers_called: ["policy_tool_worker", "synthesis_worker"]
confidence: 0.92
```

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:** Dùng LLM + rule-based fallback trong `analyze_policy()` thay vì chỉ rule-based.

**Bối cảnh vấn đề:**  
`policy_tool_worker` cần phán xét các ngoại lệ (Flash Sale, kỹ thuật số, đã kích hoạt) và tính ngày theo nghiệp vụ. Rule-based đơn thuần check keyword không đủ: gq02 yêu cầu đếm đúng "7 ngày làm việc" (31/01 là Thứ 7 → ngày làm việc đầu tiên là 02/02, đến 07/02 chỉ là 5 ngày làm việc, tức trong hạn). Rule `if "hoàn tiền" in task` không thể xử lý logic temporal này.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Rule-based thuần (keyword) | Nhanh, không tốn API call | Không xử lý được temporal logic, đếm ngày làm việc |
| LLM-only | Linh hoạt, hiểu ngữ nghĩa sâu | Tốn API call, không ổn định nếu API fail |
| LLM + rule-based fallback (đã chọn) | Chính xác với edge cases, vẫn chạy khi API fail | Phức tạp hơn một chút |

**Phương án đã chọn:** LLM primary (`gpt-4o-mini`, `json_object` mode, `temperature=0`) với system prompt hướng dẫn đếm ngày làm việc, rule-based làm fallback khi LLM thất bại.

**Bằng chứng từ trace gq02:**
```json
"policy_result": {
  "policy_applies": true,
  "policy_name": "refund_policy_v4",
  "explanation": "Khách hàng có thể yêu cầu hoàn tiền trong vòng 7 ngày làm việc kể từ thời điểm
                  xác nhận đơn hàng. Không có ngoại lệ nào được áp dụng trong trường hợp này."
}
```

LLM phân tích đúng "7 ngày làm việc" và không áp dụng ngoại lệ Flash Sale — kết quả chính xác hơn so với rule-based đơn thuần sẽ trigger `flash_sale_exception` sai.

---

## 3. Kết quả grading questions

**Routing phân bố grading run:** retrieval_worker 5/10, policy_tool_worker 5/10

| ID | Confidence | Route | Nhận xét |
|----|-----------|-------|---------|
| gq01 | 0.91 | retrieval | Correct — SLA notification đầy đủ (Slack, email, 10 min) |
| gq02 | 0.92 | policy | Partial — kết luận sai (nói không hoàn tiền, đúng phải hoàn tiền vì 31/01 là Thứ 7) |
| gq03 | 0.88 | policy | Correct — 3 approvers, IT Security là cuối |
| gq04 | 0.85 | policy | Correct — 110% store credit |
| gq05 | 0.92 | retrieval | Correct — escalate lên Senior Engineer sau 10 phút |
| gq06 | 0.92 | retrieval | Correct — probation không được remote |
| gq07 | 0.30 | retrieval | **Full abstain** — "Không đủ thông tin trong tài liệu nội bộ" |
| gq08 | 0.91 | retrieval | Correct — 90 ngày, cảnh báo 7 ngày |
| gq09 | 0.92 | policy | Correct — cả 2 phần SLA + Level 2 emergency, 3 MCP calls |
| gq10 | 0.92 | policy | Correct — Flash Sale → không hoàn tiền dù lỗi nhà SX |

**Tổng điểm raw ước tính:** ~86/96 (nếu gq02 partial 5/10) → **≈26.9/30 điểm nhóm**

**Câu pipeline xử lý tốt nhất:**
- **gq07** (abstain) — confidence 0.30, trả lời đúng "Không đủ thông tin" thay vì hallucinate mức phạt. Đây là câu thiết kế bẫy, pipeline không bị penalty.
- **gq09** (multi-hop khó nhất, 16 điểm) — 3 MCP tools phối hợp, 2 workers được gọi, trả lời đầy đủ cả quy trình SLA lẫn điều kiện Level 2 emergency access. Trace ghi rõ cả hai workers → đủ điều kiện trace bonus +1.

**Câu pipeline fail:**
- **gq02** — Root cause: LLM system prompt có hướng dẫn đếm ngày làm việc nhưng synthesis worker nhận `policy_version_exception` từ rule-based (31/01 trigger `policy_version_note`), khiến synthesis kết luận "không được hoàn tiền". Conflict giữa LLM explanation (đúng) và rule-based exception (sai) — synthesis ưu tiên exception.

**gq07 (abstain):** Hệ thống trả về "Không đủ thông tin trong tài liệu nội bộ về mức phạt tài chính" — synthesis_worker nhận chunks từ SLA docs nhưng không tìm được thông tin về financial penalty, tự abstain theo system prompt "Nếu context không đủ → nói rõ". Không có hallucination.

**gq09 (multi-hop):** Trace ghi đúng `"workers_called": ["policy_tool_worker", "synthesis_worker"]` và 3 MCP calls. Đạt điều kiện full marks.

---

## 4. So sánh Day 08 vs Day 09

**Metric thay đổi rõ nhất (số liệu từ `eval_report.json`):**

| Metric | Day 08 | Day 09 | Delta |
|--------|--------|--------|-------|
| Avg confidence | 0.75 | 0.768 (test) / 0.887 (grading) | +1.8% / +18.3% |
| Avg latency (ms) | 800 | 3655 | +2855ms |
| Abstain rate | 20% | 7% (1/15 test), 10% (1/10 grading) | -13% |
| Multi-hop accuracy | ~30% | gq09=0.92, gq03=0.88 | Cải thiện rõ rệt |

**Điều nhóm bất ngờ nhất:**  
Grading confidence (avg 0.887) cao hơn hẳn test confidence (avg 0.768). Nguyên nhân: grading questions cụ thể hơn, tài liệu KB khớp rất tốt — top chunk score gq02 đạt 0.955, gq05 và gq06 đạt 0.92. Reranking của `retrieval_worker` hoạt động hiệu quả hơn với câu hỏi rõ ràng.

**Trường hợp multi-agent không giúp ích:**  
Câu đơn giản 1 document (gq08, gq05) — Day 09 mất ~1800–2700ms so với Day 08 ~800ms mà confidence tương đương (~0.91–0.92). LangGraph routing overhead không có benefit rõ ràng cho single-document queries.

---

## 5. Phân công và đánh giá nhóm

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Đặng Văn Minh | `graph.py`: supervisor_node, route_decision, build_graph (LangGraph), AgentState, phân công nhóm | 1 + 4 |
| Nguyễn Quang Tùng | `workers/retrieval.py`, `policy_tool.py`, `synthesis.py`, `contracts/worker_contracts.yaml` | 2 |
| Nguyễn Thị Quỳnh Trang | `mcp_server.py`: 6 tools, MCP integration trong policy_tool | 3 |
| Đồng Văn Thịnh | `eval_trace.py`, `artifacts/grading_run.jsonl`, `artifacts/traces/`, docs | 4 |

**Điều nhóm làm tốt:**  
Phân công sớm và rõ interface — M1 freeze `AgentState` schema trong commit `6b10e47` (11:17) trước khi M2 bắt đầu code workers. `contracts/worker_contracts.yaml` cập nhật `status: "done"` realtime nên M4 biết khi nào có thể chạy eval. Không có blocking dependency ngoài ý muốn.

**Điều nhóm làm chưa tốt:**  
Merge conflict xảy ra 2 lần (`038de6d`, `237e5a9`) khi M2 và M3 cùng sửa `workers/policy_tool.py`. Bug `mcp_search` vs `mcp_result` (variable name conflict) âm thầm gây confidence=0.10 cho 7 câu policy mà không crash, mất thời gian debug. Nên có unit test cho từng worker để phát hiện sớm.

**Nếu làm lại:**  
Tách `workers/policy_tool.py` thành 2 file riêng biệt ngay từ đầu: `workers/policy_analysis.py` (M2) và `workers/mcp_client.py` (M3) để tránh conflict. Giao diện giữa hai phần chỉ là 1 function call — đơn giản để merge.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

**Cải tiến 1:** Sửa gq02 — thêm logic đếm ngày làm việc chính xác vào `analyze_policy()`. Trace gq02 cho thấy rule-based trigger `policy_version_exception` sai (31/01 → 02/02 là đầu tuần mới, chỉ 5 ngày làm việc đến 07/02). LLM explanation đã đúng nhưng bị override. Fix: ưu tiên LLM `policy_applies` hơn rule-based exception khi có conflict — 1 dòng code thay đổi trong `policy_tool.py` line 271.

**Cải tiến 2:** Thay keyword routing bằng LLM classifier nhỏ (gpt-4o-mini, 1 call, ~200ms). gq06 hiện route về `default route` vì không có keyword match, nhưng vẫn trả lời đúng nhờ dense retrieval. Với LLM classifier, route_reason sẽ semantically chính xác hơn — quan trọng cho debuggability khi scale lên nhiều domain hơn.

---

*File: `reports/group_report.md`*
