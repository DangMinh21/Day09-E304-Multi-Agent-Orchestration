# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Đặng Văn Minh  
**Mã học viên:** 2A202600027  
**Vai trò trong nhóm:** M1 — Supervisor Owner (Lead)  
**Ngày nộp:** 14/04/2026

---

## 1. Tôi phụ trách phần nào?

**File chính:** `graph.py`

**Functions tôi implement:**
- `supervisor_node()` — routing logic với 3 nhóm keyword, risk detection, HITL override
- `route_decision()` — conditional edge của LangGraph, trả về tên worker tiếp theo
- `human_review_node()` — HITL placeholder với auto-approve trong lab mode
- `build_graph()` — kết nối toàn bộ graph bằng LangGraph `StateGraph`, compile thành `run_wrapper`
- `make_initial_state()`, `run_graph()`, `save_trace()` — public API cho `main.py` và `eval_trace.py`

Ngoài ra, tôi chịu trách nhiệm phân công task từ đầu (commit `6b10e47` — "add plan for team, phân chia task"), viết `plans/M1_guide.md` đến `M4_guide.md` và `plans/PLAN.md` để các thành viên có hướng dẫn chi tiết từng sprint. Sprint 4 tôi chạy `eval_trace.py` và push 15 traces vào `artifacts/` (commit `7d5af49`).

**Kết nối với thành viên khác:** `graph.py` là điểm giao giữa tất cả. M2 (Worker Owner) implement `workers/*.py` với hàm `run(state)`; tôi import và wrap chúng thành `retrieval_worker_node`, `policy_tool_worker_node`, `synthesis_worker_node`. Nếu `supervisor_node()` chưa xong, M2 không thể test workers trong pipeline; nếu `AgentState` schema chưa đúng, toàn bộ `worker_io_log` của M3 cũng bị sai.

**Bằng chứng:** Commit `dc7276e` ("Hoàn thiện kiến trúc lớp Orchestrator trong file graph.py", 14/04 14:40), Merge PR #4 từ nhánh `feature/supervisor-router` lúc 14:53.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** Đặt bước kiểm tra `risk_high` trước routing chính, và dùng `elif` thay vì hai `if` độc lập để tạo thứ tự ưu tiên cứng cho routing.

**Bối cảnh:** Skeleton ban đầu trong `graph.py` có đoạn:

```python
# Skeleton cũ (trước commit dc7276e):
if any(kw in task for kw in policy_keywords):
    route = "policy_tool_worker"
if any(kw in task for kw in risk_keywords):
    risk_high = True
    route_reason += " | risk_high flagged"
if risk_high and "err-" in task:
    route = "human_review"
```

Vấn đề: Risk check nằm sau policy check, không tách biệt. Với câu hỏi chứa cả policy keyword lẫn mã lỗi (VD: "Flash sale ERR-403"), hệ thống route về `policy_tool_worker` trước, sau đó mới check risk — nhưng HITL override lúc này đã xác nhận `route=policy_tool_worker` nên override không có tác dụng đúng lúc.

**Các lựa chọn thay thế:**
- Giữ nguyên 3 `if` độc lập: đơn giản nhưng risk check đến sau, thứ tự ưu tiên không rõ ràng
- Dùng LLM classifier để routing: chính xác nhất nhưng thêm 1 API call (~800ms) mỗi câu, tốn chi phí không cần thiết cho lab

**Phương án đã chọn:** Tôi tách thành 4 bước có thứ tự rõ ràng:
1. Set risk_high trước (step 2 trong code)
2. Route policy vs retrieval (step 3 — elif, không phải 2 if)
3. HITL override nếu risk_high + err- (step 4 — override mọi route trước đó)

**Trade-off đã chấp nhận:** Dùng `elif` giữa policy và retrieval có nghĩa là câu chứa cả hai từ khóa luôn đi về policy — ví dụ "access control cho ticket P1" đi về `policy_tool_worker` dù "p1" và "ticket" là retrieval keywords. Tôi chấp nhận điều này vì policy decision quan trọng hơn retrieval đơn thuần.

**Bằng chứng từ trace:**
```
# q09 — ERR-403-AUTH (trace run_20260414_172211_232827.json):
"risk_high": true,
"supervisor_route": "human_review",
"route_reason": "ép buộc human_review: rủi ro cao + mã lỗi không xác định (err-) | risk_flag: High"

# q13 — "Contractor Level 3 + P1 active" (trace run_20260414_172224_344366.json):
# Contains "p1" (retrieval) AND "level 3", "access" (policy) → elif: policy wins
"supervisor_route": "policy_tool_worker",
"confidence": 0.89  ← correct answer, route đúng
```

Nếu dùng 2 `if` riêng, q09 có thể đã đi về `policy_tool_worker` (vì "err-" không match policy keywords nhưng route_reason chưa ghi risk đúng lúc). Kết quả: routing accuracy 13-14/15 câu đúng.

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** `graph.py` dùng `StateGraph` của LangGraph nhưng build thành công mà không invoke được — `app.invoke(state)` trả về state thiếu nhiều fields.

**Symptom:** Trong lần test đầu (commit `dc7276e` context), `run_graph("SLA ticket P1")` trả về state có `final_answer=""` và `confidence=0.0`, dù không có exception nào:

```
# Output ban đầu (test manual trước khi fix):
Route: retrieval_worker
Workers: ['retrieval_worker', 'synthesis_worker']
Answer: ""
Confidence: 0.0
```

**Root cause:** LangGraph `StateGraph` với `TypedDict` yêu cầu `set_entry_point()` được gọi đúng sau khi thêm tất cả nodes. Trong lần đầu, tôi gọi `set_entry_point("supervisor")` trước `add_node()` cho `human_review`. LangGraph compile thành công nhưng khi invoke, graph không biết `human_review` là node hợp lệ trong conditional edges — silently trả về state rỗng thay vì raise error.

**Cách sửa:** Đảm bảo `set_entry_point()` được gọi sau tất cả `add_node()`, và kiểm tra `add_conditional_edges` dict có đủ 3 keys khớp với giá trị `route_decision()` có thể trả về:

```python
# Thứ tự đúng trong build_graph():
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("human_review", human_review_node)      # phải có trước set_entry_point
workflow.add_node("retrieval_worker", retrieval_worker_node)
workflow.add_node("policy_tool_worker", policy_tool_worker_node)
workflow.add_node("synthesis_worker", synthesis_worker_node)
workflow.set_entry_point("supervisor")                     # sau tất cả add_node
workflow.add_conditional_edges(
    "supervisor",
    route_decision,
    {"human_review": "human_review",         # key khớp với return value
     "policy_tool_worker": "policy_tool_worker",
     "retrieval_worker": "retrieval_worker"}
)
```

**Bằng chứng sau khi sửa:** Trace `run_20260414_143443.json` (committed trong `dc7276e`) ghi đầy đủ `history`, `workers_called`, `final_answer` khác rỗng — xác nhận graph invoke đúng.

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**  
Thiết kế `AgentState` schema với `history` array — mỗi worker append log theo format `"[worker_name] action"`. Quyết định này cho phép M4 debug bằng cách đọc `history` thay vì đọc code. Bằng chứng: q09 có `history` 6 bước rõ ràng từ supervisor → HITL → retrieval → synthesis, đủ để kết luận pipeline không có bug mà chỉ là honest abstain (confidence 0.30).

Cũng làm tốt vai trò phân công — viết `plans/M*_guide.md` với timeline cụ thể từng 30 phút giúp nhóm song song được Sprint 1 (tôi) và Sprint 2 (M2) mà không block nhau.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**  
Routing dùng keyword matching đơn giản — "access" xuất hiện trong nhiều câu không liên quan đến access control (VD: "access vào hệ thống ticket") vẫn route về policy_tool_worker. Nên dùng LLM classifier hoặc regex pattern chính xác hơn.

**Nhóm phụ thuộc vào tôi ở đâu?**  
`AgentState` schema là interface chung — M2, M3 phải biết field names trước khi code. Nếu tôi đổi tên field (VD: `retrieved_chunks` → `chunks`), tất cả worker code của M2 và trace của M4 phải update. Trong thực tế tôi freeze schema sớm (commit `6b10e47`) để block M2 sớm nhất có thể.

**Phần tôi phụ thuộc vào thành viên khác:**  
Phụ thuộc M2 để `workers/*.py` có hàm `run(state)` đúng signature trước khi tôi test end-to-end trong `build_graph()`.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thay keyword-based routing bằng **LLM classifier nhỏ** (gpt-4o-mini, 1 call, prompt ngắn) để phân loại intent. Trace q03 (`run_20260414_172154_820022.json`) cho thấy câu "xin nghỉ phép 3 ngày" route về `policy_tool_worker` đúng nhưng với route_reason chung chung `"chứa keyword về policy/quyền hạn"` — keyword match là "access" xuất hiện trong chunk context chứ không phải trong câu hỏi. Với LLM classifier, intent "leave policy" sẽ có route_reason cụ thể hơn (`"intent=leave_policy"`) và không bị false positive từ keyword overlap. Confidence của q03 là 0.78 — có thể tăng lên nếu routing rõ hơn.
