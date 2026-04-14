"""
workers/synthesis.py — Synthesis Worker
Sprint 2: Tổng hợp câu trả lời từ retrieved_chunks và policy_result.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: evidence từ retrieval_worker
    - policy_result: kết quả từ policy_tool_worker

Output (vào AgentState):
    - final_answer: câu trả lời cuối với citation
    - sources: danh sách nguồn tài liệu được cite
    - confidence: mức độ tin cậy (0.0 - 1.0)

Gọi độc lập để test:
    python workers/synthesis.py
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

WORKER_NAME = "synthesis_worker"

# Prompt được thiết kế để tận dụng tối đa kết quả từ Policy Tool
SYSTEM_PROMPT = """Bạn là chuyên gia IT Helpdesk nội bộ. 
Nhiệm vụ: Trả lời câu hỏi dựa trên Tài liệu và Phân tích chính sách được cung cấp.

Quy trình tư duy:
1. Kiểm tra mục 'PHÂN TÍCH CHÍNH SÁCH': Đây là nguồn tin cậy nhất về các quy định/exceptions.
2. Kiểm tra 'TÀI LIỆU THAM KHẢO': Dùng để lấy chi tiết quy trình, tên file và thông tin bổ trợ.
3. Trình bày: Nêu rõ ĐƯỢC hay KHÔNG ĐƯỢC trước, sau đó là điều kiện/ngoại lệ, cuối cùng là quy trình thực hiện.

Yêu cầu định dạng:
- Trích dẫn nguồn: [tên_file] ngay sau thông tin lấy từ file đó.
- In đậm: Thời gian (SLA), Access Level, Email, hoặc kết luận quan trọng nhất.
- Nếu không có thông tin: Trả lời "Hiện tại tài liệu nội bộ không đề cập đến [vấn đề X]".
"""

def _call_llm(messages: list) -> str:
    """Sử dụng GPT-4o-mini cho bước Synthesis để đảm bảo tốc độ và logic."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0, # Giữ tính ổn định cao nhất
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[SYNTHESIS ERROR] {str(e)}"

def _build_context(chunks: list, policy_result: dict) -> str:
    parts = []

    # 1. Đưa phân tích của Policy Tool lên đầu (Top priority)
    if policy_result:
        parts.append("=== PHÂN TÍCH CHÍNH SÁCH ===")
        if "explanation" in policy_result:
            parts.append(f"Kết luận từ chuyên gia: {policy_result['explanation']}")
        
        # Thêm thông tin từ MCP tools nếu có (Access levels, HR process...)
        for key in ["access_details", "hr_penalty_details", "leave_process"]:
            if key in policy_result:
                parts.append(f"Chi tiết từ hệ thống ({key}): {json.dumps(policy_result[key], ensure_ascii=False)}")

    # 2. Đưa các đoạn text raw xuống dưới để LLM trích dẫn nguồn
    if chunks:
        parts.append("\n=== TÀI LIỆU THAM KHẢO (DÙNG ĐỂ TRÍCH DẪN) ===")
        for i, chunk in enumerate(chunks, 1):
            parts.append(f"[{i}] Nguồn: {chunk.get('source')} | Nội dung: {chunk.get('text')}")

    return "\n\n".join(parts)

def _estimate_confidence(chunks: list, policy_result: dict, answer: str) -> float:
    """Logic tính điểm tin cậy thực tế hơn."""
    if not chunks and not policy_result:
        return 0.1
    
    # Điểm nền: Nếu Policy Tool đã phân tích xong thì tin cậy tối thiểu 0.7
    base_conf = 0.7 if policy_result.get("explanation") else 0.4
    
    # Thưởng điểm nếu retrieved chunks có score cao
    if chunks:
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
        base_conf += (avg_score * 0.3) # Max +0.3
    
    # Phạt điểm nếu LLM báo không thấy thông tin
    if "không đề cập" in answer or "Không đủ thông tin" in answer:
        base_conf = 0.3
        
    return round(min(0.98, base_conf), 2)

def run(state: dict) -> dict:
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    policy_result = state.get("policy_result", {})

    state.setdefault("workers_called", [])
    state["workers_called"].append(WORKER_NAME)

    context = _build_context(chunks, policy_result)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Câu hỏi: {task}\n\n{context}"}
    ]

    # Synthesis thực tế
    final_answer = _call_llm(messages)
    
    # Cập nhật state
    state["final_answer"] = final_answer
    state["sources"] = list({c.get("source") for c in chunks if c.get("source")})
    state["confidence"] = _estimate_confidence(chunks, policy_result, final_answer)
    
    # Log lịch sử
    state.setdefault("history", []).append(
        f"[{WORKER_NAME}] Final answer synthesized. Confidence: {state['confidence']}"
    )
    
    return state

# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Synthesis Worker — Standalone Test")
    print("=" * 50)

    test_state = {
        "task": "SLA ticket P1 là bao lâu?",
        "retrieved_chunks": [
            {
                "text": "Ticket P1: Phản hồi ban đầu 15 phút kể từ khi ticket được tạo. Xử lý và khắc phục 4 giờ. Escalation: tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút.",
                "source": "sla_p1_2026.txt",
                "score": 0.92,
            }
        ],
        "policy_result": {},
    }

    result = run(test_state.copy())
    print(f"\nAnswer:\n{result['final_answer']}")
    print(f"\nSources: {result['sources']}")
    print(f"Confidence: {result['confidence']}")

    print("\n--- Test 2: Exception case ---")
    test_state2 = {
        "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì lỗi nhà sản xuất.",
        "retrieved_chunks": [
            {
                "text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4.",
                "source": "policy_refund_v4.txt",
                "score": 0.88,
            }
        ],
        "policy_result": {
            "policy_applies": False,
            "exceptions_found": [{"type": "flash_sale_exception", "rule": "Flash Sale không được hoàn tiền."}],
        },
    }
    result2 = run(test_state2.copy())
    print(f"\nAnswer:\n{result2['final_answer']}")
    print(f"Confidence: {result2['confidence']}")

    print("\n✅ synthesis_worker test done.")
