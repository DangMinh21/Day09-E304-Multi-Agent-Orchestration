# Plan — Worker Owner (Day 09)

Vai trò: Xây dựng 3 workers trong `workers/` và đảm bảo contract khớp.
Sprint chính: Sprint 2. Tham gia Sprint 1 (align state) và Sprint 3 (hỗ trợ MCP).

---

## Bước 0 — Align với M1 (15 phút đầu)

Trước khi code, chốt với M1 về `AgentState` trong `graph.py`.

Cần xác nhận các key sau đã có trong state:

```python
state = {
    "task": str,               # câu hỏi đầu vào
    "retrieved_chunks": list,  # output của retrieval_worker
    "retrieved_sources": list, # danh sách nguồn
    "policy_result": dict,     # output của policy_tool_worker
    "mcp_tools_used": list,    # danh sách MCP calls
    "final_answer": str,       # output của synthesis_worker
    "sources": list,
    "confidence": float,
    "workers_called": list,
    "worker_io_logs": list,
    "needs_tool": bool,
    "risk_high": bool,
}
```

> State này đã được định nghĩa trong `graph.py` — chỉ cần đọc và xác nhận.

---

## Bước 1 — Đảm bảo ChromaDB index tồn tại

Workers dùng ChromaDB từ Day 08. Kiểm tra collection `rag_lab` đã có chưa:

```bash
python3 -c "
import chromadb
client = chromadb.PersistentClient(path='./chroma_db')
col = client.get_collection('rag_lab')
print('Chunks:', col.count())
"
```

Nếu báo lỗi hoặc count = 0 → chạy lại index từ Day 08:

```bash
cd day08/lab && python3 index.py
```

Sau đó copy `chroma_db/` sang thư mục gốc Day 09 (hoặc dùng symlink).

> Lưu ý: `workers/retrieval.py` hiện đang trỏ vào `./chroma_db` với collection `day09_docs`.
> Cần đổi thành `rag_lab` (collection đã build từ Day 08) hoặc build lại collection mới.

---

## Bước 2 — Fix `workers/retrieval.py`

File đã có skeleton. Việc cần làm:

**2a. Đổi embedding function sang OpenAI** (nhất quán với Day 08):

Trong `_get_embedding_fn()`, hiện tại ưu tiên Sentence Transformers. Đổi thứ tự để OpenAI được dùng trước:

```python
def _get_embedding_fn():
    from openai import OpenAI
    import os
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    def embed(text: str) -> list:
        resp = client.embeddings.create(input=text, model="text-embedding-3-small")
        return resp.data[0].embedding
    return embed
```

**2b. Đổi collection name** trong `_get_collection()`:

```python
collection = client.get_collection("rag_lab")  # thay vì "day09_docs"
```

**2c. Kiểm tra `run(state)` trả về đúng contract:**

- `state["retrieved_chunks"]` — list of `{text, source, score, metadata}`
- `state["retrieved_sources"]` — list of unique source strings
- `state["worker_io_logs"]` — append log entry

**2d. Test độc lập:**

```bash
python3 workers/retrieval.py
```

Kết quả mong đợi: 3 câu hỏi test đều trả về chunks có score > 0.

---

## Bước 3 — Fix `workers/policy_tool.py`

File đã có skeleton với rule-based exception detection. Việc cần làm:

**3a. Upgrade `analyze_policy()` dùng LLM** (thay vì chỉ rule-based):

Uncomment phần LLM call trong `analyze_policy()` và implement:

```python
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
context_text = "\n\n".join([c.get("text", "") for c in chunks])

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": (
                "Bạn là policy analyst. Dựa vào context, xác định:\n"
                "1. Policy có áp dụng không (policy_applies: true/false)\n"
                "2. Có exceptions nào không (flash_sale, digital_product, activated)\n"
                "Trả về JSON: {\"policy_applies\": bool, \"exceptions\": [str], \"explanation\": str}"
            )
        },
        {"role": "user", "content": f"Task: {task}\n\nContext:\n{context_text}"}
    ],
    temperature=0,
    response_format={"type": "json_object"},
)
```

Giữ lại rule-based check như fallback nếu LLM call thất bại.

**3b. Đảm bảo xử lý đúng 2 exception cases bắt buộc:**

- Flash Sale → `policy_applies = False`
- Digital product / license key → `policy_applies = False`

**3c. Test độc lập:**

```bash
python3 workers/policy_tool.py
```

Kết quả mong đợi:
- Flash Sale case → `policy_applies: False`, có exception entry
- License key case → `policy_applies: False`, có exception entry
- Sản phẩm lỗi bình thường → `policy_applies: True`

---

## Bước 4 — Kiểm tra `workers/synthesis.py`

File này đã implement khá đầy đủ. Chỉ cần verify:

**4a. `_call_llm()` dùng đúng API key:**

Đảm bảo `.env` có `OPENAI_API_KEY` và `LLM_MODEL=gpt-4o-mini`.

**4b. Citation format đúng:**

Answer phải có `[source_name]` hoặc `[1]` — kiểm tra trong `SYSTEM_PROMPT`.

**4c. Abstain khi không có chunks:**

Nếu `retrieved_chunks = []` → answer phải chứa "Không đủ thông tin", không hallucinate.

**4d. Test độc lập:**

```bash
python3 workers/synthesis.py
```

Kết quả mong đợi:
- Test 1 (SLA P1): answer có citation `[sla_p1_2026.txt]`, confidence > 0.5
- Test 2 (Flash Sale): answer nêu rõ exception, confidence thấp hơn

---

## Bước 5 — Cập nhật `contracts/worker_contracts.yaml`

Sau khi implement xong, cập nhật `actual_implementation.status` cho từng worker:

```yaml
actual_implementation:
  status: "done"
  notes: "Dùng OpenAI text-embedding-3-small, collection rag_lab"
```

---

## Bước 6 — Kết nối vào `graph.py` (phối hợp với M1)

Sau khi 3 workers test độc lập OK, báo M1 để uncomment trong `graph.py`:

```python
# Uncomment các dòng này trong graph.py:
from workers.retrieval import run as retrieval_run
from workers.policy_tool import run as policy_tool_run
from workers.synthesis import run as synthesis_run

# Và thay placeholder trong các node functions:
def retrieval_worker_node(state):
    return retrieval_run(state)

def policy_tool_worker_node(state):
    return policy_tool_run(state)

def synthesis_worker_node(state):
    return synthesis_run(state)
```

Chạy thử end-to-end:

```bash
python3 graph.py
```

---

## Bước 7 — Hỗ trợ Sprint 3 (MCP)

Khi M3 implement `mcp_server.py`, `policy_tool.py` cần gọi MCP thay vì trực tiếp ChromaDB.

Phần này đã có skeleton trong `_call_mcp_tool()` — chỉ cần đảm bảo `mcp_server.dispatch_tool()` hoạt động.

Kiểm tra sau khi M3 xong:

```python
from mcp_server import dispatch_tool
result = dispatch_tool("search_kb", {"query": "refund policy", "top_k": 3})
print(result)
```

---

## Checklist Definition of Done

- [ ] `python3 workers/retrieval.py` — 3 queries đều trả về chunks có score > 0
- [ ] `python3 workers/policy_tool.py` — Flash Sale và digital product đều detect đúng exception
- [ ] `python3 workers/synthesis.py` — answer có citation, abstain khi không có chunks
- [ ] `contracts/worker_contracts.yaml` — 3 workers đều có `status: "done"`
- [ ] `python3 graph.py` — pipeline chạy end-to-end với workers thật (không phải placeholder)

---

## Thứ tự ưu tiên nếu hết thời gian

1. `retrieval.py` — quan trọng nhất, mọi thứ phụ thuộc vào đây
2. `synthesis.py` — cần để có output cuối
3. `policy_tool.py` — có thể dùng rule-based đơn giản nếu không kịp LLM upgrade
4. Contract update — làm cuối cùng
