"""
graph.py — Supervisor Orchestrator
Sprint 1: Implement AgentState, supervisor_node, route_decision và kết nối graph.

Kiến trúc:
    Input → Supervisor → [retrieval_worker | policy_tool_worker | human_review] → synthesis → Output

Chạy thử:
    python graph.py
"""

import json
import os
from datetime import datetime
from typing import TypedDict, Literal, Optional

# Đã uncomment để dùng LangGraph:
from langgraph.graph import StateGraph, END

# ─────────────────────────────────────────────
# 1. Shared State — dữ liệu đi xuyên toàn graph
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    # Input
    task: str                           # Câu hỏi đầu vào từ user

    # Supervisor decisions
    route_reason: str                   # Lý do route sang worker nào
    risk_high: bool                     # True → cần HITL hoặc human_review
    needs_tool: bool                    # True → cần gọi external tool qua MCP
    hitl_triggered: bool                # True → đã pause cho human review

    # Worker outputs
    retrieved_chunks: list              # Output từ retrieval_worker
    retrieved_sources: list             # Danh sách nguồn tài liệu
    policy_result: dict                 # Output từ policy_tool_worker
    mcp_tools_used: list                # Danh sách MCP tools đã gọi

    # Final output
    final_answer: str                   # Câu trả lời tổng hợp
    sources: list                       # Sources được cite
    confidence: float                   # Mức độ tin cậy (0.0 - 1.0)

    # Trace & history
    history: list                       # Lịch sử các bước đã qua
    workers_called: list                # Danh sách workers đã được gọi
    supervisor_route: str               # Worker được chọn bởi supervisor
    latency_ms: Optional[int]           # Thời gian xử lý (ms)
    run_id: str                         # ID của run này


def make_initial_state(task: str) -> AgentState:
    """Khởi tạo state cho một run mới."""
    return {
        "task": task,
        "route_reason": "",
        "risk_high": False,
        "needs_tool": False,
        "hitl_triggered": False,
        "retrieved_chunks": [],
        "retrieved_sources": [],
        "policy_result": {},
        "mcp_tools_used": [],
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "history": [],
        "workers_called": [],
        "supervisor_route": "",
        "latency_ms": None,
        "run_id": f"run_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
    }


# ─────────────────────────────────────────────
# 2. Supervisor Node — quyết định route
# ─────────────────────────────────────────────

def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor phân tích task và quyết định:
    1. Route sang worker nào
    2. Có cần MCP tool không
    3. Có risk cao cần HITL không
    """
    task = state["task"].lower()
    state["history"].append(f"[supervisor] received task: {state['task'][:80]}")

    # Giá trị mặc định: ban đầu coi như một câu hỏi thông thường, tìm kiếm tài liệu định dạng chuỗi văn bản
    route = "retrieval_worker"
    route_reason = "default route - không có từ khóa đặc biệt, dùng truy xuất tài liệu mặc định"
    needs_tool = False
    risk_high = False

    # 1. Định nghĩa các nhóm từ khóa (Keywords Mapping)
    # Nhóm dành cho policy / cấp quyền → Yêu cầu xử lý logic phức tạp, gọi tool bên ngoài -> Gọi policy_tool_worker
    policy_keywords = ["hoàn tiền", "refund", "flash sale", "license", "cấp quyền", "access", "level 3"]
    # Nhóm truy xuất thông thường hoặc leo thang (escalation) → Trực tiếp đi tìm tài liệu SLA/quy trình trong DB
    retrieval_keywords = ["p1", "escalation", "sla", "ticket"]
    # Nhóm rủi ro cao / khẩn cấp → Đánh dấu cờ (flag) có thể cần người phê duyệt hoặc cẩn thận (HITL)
    risk_keywords = ["emergency", "khẩn cấp", "2am", "không rõ", "err-"]

    # 2. Xử lý logic Risk / Rủi ro trước
    # Nếu trong câu hỏi có dấu hiệu khẩn cấp hoặc mã lỗi, đánh dấu hệ thống cẩn thận
    if any(kw in task for kw in risk_keywords):
        risk_high = True

    # 3. Phân luồng điều phối chính (Routing Logic) dựa theo mức độ ưu tiên
    if any(kw in task for kw in policy_keywords):
        # Ưu tiên cao: Nếu liên quan tới tiền / cấp quyền -> Cần Policy Worker phán xử
        route = "policy_tool_worker"
        route_reason = f"route to policy_tool_worker: chứa keyword về policy/quyền hạn"
        needs_tool = True
    elif any(kw in task for kw in retrieval_keywords):
        # Ưu tiên vừa: Các từ liên quan đến sự cố SLA, p1 -> Gọi Retrieval Worker ngay
        route = "retrieval_worker"
        route_reason = f"route to retrieval_worker: chứa keyword ticket/chuẩn SLA cơ bản"

    # 4. Ngoại lệ ưu tiên cao nhất (Human review override)
    # Khi rủi ro cao VÀ có dấu hiệu sự cố mà hệ thống không biết (VD: "err-") thì ép buộc đi luồng Human Review
    if risk_high and "err-" in task:
        route = "human_review"
        route_reason = "ép buộc human_review: rủi ro cao + mã lỗi không xác định (err-)"
        needs_tool = False

    # Cuối cùng, tổng hợp lý do để ghi vào Log State giúp dễ debug (Trace)
    final_reason = f"{route_reason} | risk_flag: {'High' if risk_high else 'Normal'}"
    
    # 5. Lưu kết luận trở lại State của hệ thống
    state["supervisor_route"] = route
    state["route_reason"] = final_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high
    state["history"].append(f"[supervisor] route={route} reason={final_reason}")

    return state


# ─────────────────────────────────────────────
# 3. Route Decision — conditional edge
# ─────────────────────────────────────────────

def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
    """
    Trả về tên worker tiếp theo dựa vào supervisor_route trong state.
    Đây là conditional edge của graph.
    """
    route = state.get("supervisor_route", "retrieval_worker")
    return route  # type: ignore


# ─────────────────────────────────────────────
# 4. Human Review Node — HITL placeholder
# ─────────────────────────────────────────────

def human_review_node(state: AgentState) -> AgentState:
    """
    HITL node: pause và chờ human approval.
    Trong lab này, implement dưới dạng placeholder (in ra warning).

    TODO Sprint 3 (optional): Implement actual HITL với interrupt_before hoặc
    breakpoint nếu dùng LangGraph.
    """
    state["hitl_triggered"] = True
    state["history"].append("[human_review] HITL triggered — awaiting human input")
    state["workers_called"].append("human_review")

    # Placeholder: tự động approve để pipeline tiếp tục
    print(f"\n⚠️  HITL TRIGGERED")
    print(f"   Task: {state['task']}")
    print(f"   Reason: {state['route_reason']}")
    print(f"   Action: Auto-approving in lab mode (set hitl_triggered=True)\n")

    # Sau khi human approve, route về retrieval để lấy evidence
    state["supervisor_route"] = "retrieval_worker"
    state["route_reason"] += " | human approved → retrieval"

    return state


# ─────────────────────────────────────────────
# 5. Import Workers
# ─────────────────────────────────────────────

from workers.retrieval import run as retrieval_run
from workers.policy_tool import run as policy_tool_run
from workers.synthesis import run as synthesis_run


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi retrieval worker."""
    return retrieval_run(state)


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker."""
    return policy_tool_run(state)


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    return synthesis_run(state)


# ─────────────────────────────────────────────
# 6. Build Graph
# ─────────────────────────────────────────────

def build_graph():
    """
    Xây dựng graph với supervisor-worker pattern.
    Option B (Nâng cao): Áp dụng LangGraph `StateGraph` để nối edges có điều kiện,
    dễ debug flow thông qua library xịn.
    """
    # 1. Khởi tạo đồ thị State chứa AgentState template
    workflow = StateGraph(AgentState)

    # 2. Thêm các Node worker (tương đương quy định các phòng ban công việc)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("retrieval_worker", retrieval_worker_node)
    workflow.add_node("policy_tool_worker", policy_tool_worker_node)
    workflow.add_node("synthesis_worker", synthesis_worker_node)

    # 3. Quy định cổng vào mặc định của chương trình: Supervisor
    workflow.set_entry_point("supervisor")

    # 4. Supervisor phân luồng bằng một conditional_edges (Cạnh rẽ nhánh có điều kiện)
    # Hàm route_decision sẽ trả về "chuỗi" là tên Node tiếp theo.
    workflow.add_conditional_edges(
        "supervisor",              # Node nguồn (đứng đây rẽ nhánh)
        route_decision,            # Hàm phán đoán đường đi (trả về giá trị A,B,C...)
        {
            "human_review": "human_review",
            "policy_tool_worker": "policy_tool_worker",
            "retrieval_worker": "retrieval_worker"
        }
    )

    # 5. Khai báo các đường đi bình thường sau khi vào nhánh (Edges tĩnh)
    
    # - Nếu đi qua human review xong -> bắt buộc phải trả về retrieval lấy tài liệu.
    workflow.add_edge("human_review", "retrieval_worker")
    
    # - Nếu đi qua policy tool -> trả về synthesis worker để chuẩn bị xuất câu trả lời
    workflow.add_edge("policy_tool_worker", "synthesis_worker")

    # - Nếu lấy retrieval xong -> đương nhiên là sang synthesis để gộp kết quả
    workflow.add_edge("retrieval_worker", "synthesis_worker")

    # 6. Mọi đường nối đến synthesis đều là bước cuối nên móc vào END
    workflow.add_edge("synthesis_worker", END)

    # 7. Compile (đóng gói) đồ thị thành một ứng dụng hoàn thiện (Graph App)
    app = workflow.compile()

    # Tạo một hàm bọc (wrapper) để API run_graph tương thích như thiết kế bên option A ban đầu.
    # Trong thực tế có thể gọi thẳng app.invoke()
    def run_wrapper(state: AgentState) -> AgentState:
        import time
        start = time.time()
        
        # Invoke (kích hoạt) toàn bộ langgraph chạy tự động
        result = app.invoke(state)
        
        # Log latency
        result["latency_ms"] = int((time.time() - start) * 1000)
        result["history"].append(f"[graph] completed in {result['latency_ms']}ms - Powered by LangGraph!")
        return result

    return run_wrapper


# ─────────────────────────────────────────────
# 7. Public API
# ─────────────────────────────────────────────

_graph = build_graph()


def run_graph(task: str) -> AgentState:
    """
    Entry point: nhận câu hỏi, trả về AgentState với full trace.

    Args:
        task: Câu hỏi từ user

    Returns:
        AgentState với final_answer, trace, routing info, v.v.
    """
    state = make_initial_state(task)
    result = _graph(state)
    return result


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    """Lưu trace ra file JSON."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{state['run_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return filename


# ─────────────────────────────────────────────
# 8. Manual Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Day 09 Lab — Supervisor-Worker Graph")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
        "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run_graph(query)
        print(f"  Route   : {result['supervisor_route']}")
        print(f"  Reason  : {result['route_reason']}")
        print(f"  Workers : {result['workers_called']}")
        print(f"  Answer  : {result['final_answer'][:100]}...")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Latency : {result['latency_ms']}ms")

        # Lưu trace
        trace_file = save_trace(result)
        print(f"  Trace saved → {trace_file}")

    print("\n✅ graph.py test complete. Implement TODO sections in Sprint 1 & 2.")
