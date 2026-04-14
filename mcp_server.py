"""
mcp_server.py — Mock MCP Server
Sprint 3: Implement ít nhất 2 MCP tools.

Mô phỏng MCP (Model Context Protocol) interface trong Python.
Agent (MCP client) gọi dispatch_tool() thay vì hard-code từng API.

Tools available:
    1. search_kb(query, top_k)           → tìm kiếm Knowledge Base
    2. get_ticket_info(ticket_id)        → tra cứu thông tin ticket (mock data)
    3. check_access_permission(level, requester_role)  → kiểm tra quyền truy cập
    4. create_ticket(priority, title, description)     → tạo ticket mới (mock)
    5. get_leave_process(days, leave_type)             → tra cứu quy trình nghỉ phép
    6. get_late_penalty(minutes_late)                  → tra cứu mức nhắc nhở đi muộn (mock)

Sử dụng:
    from mcp_server import dispatch_tool, list_tools

    # Discover available tools
    tools = list_tools()

    # Call a tool
    result = dispatch_tool("search_kb", {"query": "SLA P1", "top_k": 3})

Sprint 3 TODO:
    - Option Standard: Sử dụng file này as-is (mock class)
    - Option Advanced: Implement HTTP server với FastAPI hoặc dùng `mcp` library

Chạy thử:
    python mcp_server.py
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────
# Tool Definitions (Schema Discovery)
# Giống với cách MCP server expose tool list cho client
# ─────────────────────────────────────────────

TOOL_SCHEMAS = {
    "search_kb": {
        "name": "search_kb",
        "description": "Tìm kiếm Knowledge Base nội bộ bằng semantic search. Trả về top-k chunks liên quan nhất.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Câu hỏi hoặc keyword cần tìm"},
                "top_k": {"type": "integer", "description": "Số chunks cần trả về", "default": 3},
            },
            "required": ["query"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "chunks": {"type": "array"},
                "sources": {"type": "array"},
                "total_found": {"type": "integer"},
            },
        },
    },
    "get_ticket_info": {
        "name": "get_ticket_info",
        "description": "Tra cứu thông tin ticket từ hệ thống Jira nội bộ.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "ID ticket (VD: IT-1234, P1-LATEST)"},
            },
            "required": ["ticket_id"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "priority": {"type": "string"},
                "status": {"type": "string"},
                "assignee": {"type": "string"},
                "created_at": {"type": "string"},
                "sla_deadline": {"type": "string"},
            },
        },
    },
    "check_access_permission": {
        "name": "check_access_permission",
        "description": "Kiểm tra điều kiện cấp quyền truy cập theo Access Control SOP.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "access_level": {"type": "integer", "description": "Level cần cấp (1, 2, hoặc 3)"},
                "requester_role": {"type": "string", "description": "Vai trò của người yêu cầu"},
                "is_emergency": {"type": "boolean", "description": "Có phải khẩn cấp không", "default": False},
            },
            "required": ["access_level", "requester_role"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "can_grant": {"type": "boolean"},
                "required_approvers": {"type": "array"},
                "emergency_override": {"type": "boolean"},
                "source": {"type": "string"},
            },
        },
    },
    "create_ticket": {
        "name": "create_ticket",
        "description": "Tạo ticket mới trong hệ thống Jira (MOCK — không tạo thật trong lab).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["priority", "title"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "url": {"type": "string"},
                "created_at": {"type": "string"},
            },
        },
    },
    "get_leave_process": {
        "name": "get_leave_process",
        "description": "Tra cứu quy trình xin nghỉ phép theo chính sách HR nội bộ.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "leave_days": {"type": "integer", "description": "Số ngày nghỉ mong muốn"},
                "leave_type": {
                    "type": "string",
                    "enum": ["annual", "sick", "maternity", "holiday"],
                    "default": "annual",
                },
                "is_emergency": {"type": "boolean", "description": "Trường hợp khẩn cấp", "default": False},
            },
            "required": ["leave_days"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "leave_type": {"type": "string"},
                "leave_days": {"type": "integer"},
                "submission_channel": {"type": "string"},
                "minimum_notice_days": {"type": "integer"},
                "approval_sla_working_days": {"type": "integer"},
                "documents_required": {"type": "array"},
                "notes": {"type": "array"},
                "source": {"type": "string"},
            },
        },
    },
    "get_late_penalty": {
        "name": "get_late_penalty",
        "description": "Tra cứu mức nhắc nhở/kỷ luật đi muộn theo policy mô phỏng nội bộ.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "minutes_late": {"type": "integer", "description": "Số phút đi muộn"},
                "late_count_this_month": {
                    "type": "integer",
                    "description": "Số lần đi muộn trong tháng",
                    "default": 1,
                },
            },
            "required": ["minutes_late"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "minutes_late": {"type": "integer"},
                "late_count_this_month": {"type": "integer"},
                "level": {"type": "string"},
                "action": {"type": "string"},
                "source": {"type": "string"},
            },
        },
    },
}


# ─────────────────────────────────────────────
# Tool Implementations
# ─────────────────────────────────────────────

def tool_search_kb(query: str, top_k: int = 3) -> dict:
    """
    Tìm kiếm Knowledge Base bằng semantic search.

    TODO Sprint 3: Kết nối với ChromaDB thực.
    Hiện tại: Delegate sang retrieval worker.
    """
    try:
        # Tái dùng retrieval logic từ workers/retrieval.py
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from workers.retrieval import retrieve_dense
        chunks = retrieve_dense(query, top_k=top_k)
        sources = list({c["source"] for c in chunks})
        return {
            "chunks": chunks,
            "sources": sources,
            "total_found": len(chunks),
        }
    except Exception as e:
        # Fallback: return mock data nếu ChromaDB chưa setup
        return {
            "chunks": [
                {
                    "text": f"[MOCK] Không thể query ChromaDB: {e}. Kết quả giả lập.",
                    "source": "mock_data",
                    "score": 0.5,
                }
            ],
            "sources": ["mock_data"],
            "total_found": 1,
        }


# Mock ticket database
MOCK_TICKETS = {
    "P1-LATEST": {
        "ticket_id": "IT-9847",
        "priority": "P1",
        "title": "API Gateway down — toàn bộ người dùng không đăng nhập được",
        "status": "in_progress",
        "assignee": "nguyen.van.a@company.internal",
        "created_at": "2026-04-13T22:47:00",
        "sla_deadline": "2026-04-14T02:47:00",
        "escalated": True,
        "escalated_to": "senior_engineer_team",
        "notifications_sent": ["slack:#incident-p1", "email:incident@company.internal", "pagerduty:oncall"],
    },
    "IT-1234": {
        "ticket_id": "IT-1234",
        "priority": "P2",
        "title": "Feature login chậm cho một số user",
        "status": "open",
        "assignee": None,
        "created_at": "2026-04-13T09:15:00",
        "sla_deadline": "2026-04-14T09:15:00",
        "escalated": False,
    },
}


def tool_get_ticket_info(ticket_id: str) -> dict:
    """
    Tra cứu thông tin ticket (mock data).
    """
    ticket = MOCK_TICKETS.get(ticket_id.upper())
    if ticket:
        return ticket
    # Không tìm thấy
    return {
        "error": f"Ticket '{ticket_id}' không tìm thấy trong hệ thống.",
        "available_mock_ids": list(MOCK_TICKETS.keys()),
    }


# Mock access control rules
ACCESS_RULES = {
    1: {
        "required_approvers": ["Line Manager"],
        "emergency_can_bypass": False,
        "note": "Standard user access",
    },
    2: {
        "required_approvers": ["Line Manager", "IT Admin"],
        "emergency_can_bypass": True,
        "emergency_bypass_note": "Level 2 có thể cấp tạm thời với approval đồng thời của Line Manager và IT Admin on-call.",
        "note": "Elevated access",
    },
    3: {
        "required_approvers": ["Line Manager", "IT Admin", "IT Security"],
        "emergency_can_bypass": False,
        "note": "Admin access — không có emergency bypass",
    },
}


def tool_check_access_permission(access_level: int, requester_role: str, is_emergency: bool = False) -> dict:
    """
    Kiểm tra điều kiện cấp quyền theo Access Control SOP.
    """
    rule = ACCESS_RULES.get(access_level)
    if not rule:
        return {"error": f"Access level {access_level} không hợp lệ. Levels: 1, 2, 3."}

    can_grant = True
    notes = []

    if is_emergency and rule.get("emergency_can_bypass"):
        notes.append(rule.get("emergency_bypass_note", ""))
        can_grant = True
    elif is_emergency and not rule.get("emergency_can_bypass"):
        notes.append(f"Level {access_level} KHÔNG có emergency bypass. Phải follow quy trình chuẩn.")

    return {
        "access_level": access_level,
        "can_grant": can_grant,
        "required_approvers": rule["required_approvers"],
        "approver_count": len(rule["required_approvers"]),
        "emergency_override": is_emergency and rule.get("emergency_can_bypass", False),
        "notes": notes,
        "source": "access_control_sop.txt",
    }


def tool_create_ticket(priority: str, title: str, description: str = "") -> dict:
    """
    Tạo ticket mới (MOCK — in log, không tạo thật).
    """
    mock_id = f"IT-{9900 + hash(title) % 99}"
    ticket = {
        "ticket_id": mock_id,
        "priority": priority,
        "title": title,
        "description": description[:200],
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "url": f"https://jira.company.internal/browse/{mock_id}",
        "note": "MOCK ticket — không tồn tại trong hệ thống thật",
    }
    print(f"  [MCP create_ticket] MOCK: {mock_id} | {priority} | {title[:50]}")
    return ticket


def tool_get_leave_process(leave_days: int, leave_type: str = "annual", is_emergency: bool = False) -> dict:
    """
    Tra cứu quy trình nghỉ phép theo tài liệu HR nội bộ.
    """
    leave_type = (leave_type or "annual").lower()
    if leave_days <= 0:
        return {"error": "leave_days phải lớn hơn 0."}

    valid_leave_types = {"annual", "sick", "maternity", "holiday"}
    if leave_type not in valid_leave_types:
        return {
            "error": f"leave_type '{leave_type}' không hợp lệ.",
            "supported_types": sorted(valid_leave_types),
        }

    notes = []
    docs_required = []
    if leave_type == "sick" and leave_days > 3:
        docs_required.append("Giấy tờ y tế từ bệnh viện")

    if is_emergency:
        notes.append("Trường hợp khẩn cấp có thể gửi yêu cầu muộn, cần Line Manager đồng ý trực tiếp.")

    return {
        "leave_type": leave_type,
        "leave_days": leave_days,
        "submission_channel": "HR Portal (https://hr.company.internal)",
        "minimum_notice_days": 3,
        "approval_sla_working_days": 1,
        "documents_required": docs_required,
        "notes": notes,
        "source": "hr_leave_policy.txt",
    }


def tool_get_late_penalty(minutes_late: int, late_count_this_month: int = 1) -> dict:
    """
    Tra cứu mức nhắc nhở đi muộn (MOCK policy để demo MCP config/tool binding).
    """
    if minutes_late < 0:
        return {"error": "minutes_late không được âm."}

    if minutes_late < 10:
        level = "L0"
        action = "Nhắc nhở nhẹ"
    elif minutes_late < 30:
        level = "L1"
        action = "Nhắc nhở chính thức qua email"
    else:
        level = "L2"
        action = "Lập biên bản đi muộn"

    if late_count_this_month >= 4:
        action += " + chuyển Line Manager review"

    return {
        "minutes_late": minutes_late,
        "late_count_this_month": late_count_this_month,
        "level": level,
        "action": action,
        "source": "attendance_policy_mock.txt",
    }


# ─────────────────────────────────────────────
# Dispatch Layer — MCP server interface
# ─────────────────────────────────────────────

TOOL_REGISTRY = {
    "search_kb": tool_search_kb,
    "get_ticket_info": tool_get_ticket_info,
    "check_access_permission": tool_check_access_permission,
    "create_ticket": tool_create_ticket,
    "get_leave_process": tool_get_leave_process,
    "get_late_penalty": tool_get_late_penalty,
}


def list_tools() -> list:
    """
    MCP discovery: trả về danh sách tools có sẵn.
    Tương đương với `tools/list` trong MCP protocol.
    """
    return list(TOOL_SCHEMAS.values())


def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    """
    MCP execution: nhận tool_name và input, gọi tool tương ứng.
    Tương đương với `tools/call` trong MCP protocol.

    Args:
        tool_name: tên tool (phải có trong TOOL_REGISTRY)
        tool_input: input dict (phải match với tool's inputSchema)

    Returns:
        Tool output dict, hoặc error dict nếu thất bại
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "error": f"Tool '{tool_name}' không tồn tại. Available: {list(TOOL_REGISTRY.keys())}"
        }

    tool_fn = TOOL_REGISTRY[tool_name]
    try:
        result = tool_fn(**tool_input)
        return result
    except TypeError as e:
        return {
            "error": f"Invalid input for tool '{tool_name}': {e}",
            "schema": TOOL_SCHEMAS[tool_name]["inputSchema"],
        }
    except Exception as e:
        return {
            "error": f"Tool '{tool_name}' execution failed: {e}",
        }


# ─────────────────────────────────────────────
# Test & Demo
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MCP Server — Tool Discovery & Test")
    print("=" * 60)

    # 1. Discover tools
    print("\n📋 Available Tools:")
    for tool in list_tools():
        print(f"  • {tool['name']}: {tool['description'][:60]}...")

    # 2. Test search_kb
    print("\n🔍 Test: search_kb")
    result = dispatch_tool("search_kb", {"query": "SLA P1 resolution time", "top_k": 2})
    if result.get("chunks"):
        for c in result["chunks"]:
            print(f"  [{c.get('score', '?')}] {c.get('source')}: {c.get('text', '')[:70]}...")
    else:
        print(f"  Result: {result}")

    # 3. Test get_ticket_info
    print("\n🎫 Test: get_ticket_info")
    ticket = dispatch_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
    print(f"  Ticket: {ticket.get('ticket_id')} | {ticket.get('priority')} | {ticket.get('status')}")
    if ticket.get("notifications_sent"):
        print(f"  Notifications: {ticket['notifications_sent']}")

    # 4. Test check_access_permission
    print("\n🔐 Test: check_access_permission (Level 3, emergency)")
    perm = dispatch_tool("check_access_permission", {
        "access_level": 3,
        "requester_role": "contractor",
        "is_emergency": True,
    })
    print(f"  can_grant: {perm.get('can_grant')}")
    print(f"  required_approvers: {perm.get('required_approvers')}")
    print(f"  emergency_override: {perm.get('emergency_override')}")
    print(f"  notes: {perm.get('notes')}")

    # 5. Test invalid tool
    print("\n❌ Test: invalid tool")
    err = dispatch_tool("nonexistent_tool", {})
    print(f"  Error: {err.get('error')}")

    # 6. Test get_leave_process
    print("\n🏖️  Test: get_leave_process")
    leave = dispatch_tool("get_leave_process", {"leave_days": 3, "leave_type": "annual", "is_emergency": False})
    print(f"  leave_days: {leave.get('leave_days')} | notice: {leave.get('minimum_notice_days')} ngày")
    print(f"  channel: {leave.get('submission_channel')}")

    # 7. Test get_late_penalty
    print("\n⏰ Test: get_late_penalty")
    late = dispatch_tool("get_late_penalty", {"minutes_late": 35, "late_count_this_month": 2})
    print(f"  level: {late.get('level')} | action: {late.get('action')}")

    print("\n✅ MCP server test done.")
    print("\nTODO Sprint 3: Implement HTTP server nếu muốn bonus +2.")
