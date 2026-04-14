import os
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 5  # Tăng lên để rerank sau đó

# Khởi tạo clients một lần duy nhất (Singleton-ish)
_COLLECTION = None
_OPENAI_CLIENT = None

def _get_openai_client():
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        from openai import OpenAI
        _OPENAI_CLIENT = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _OPENAI_CLIENT

def _get_collection():
    global _COLLECTION
    if _COLLECTION is None:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        _COLLECTION = client.get_collection("rag_lab")
    return _COLLECTION

def simple_reranker(query: str, chunks: List[Dict]) -> List[Dict]:
    """
    Hàm tối ưu Confidence: Chấm điểm lại dựa trên sự xuất hiện của từ khóa 
    quan trọng từ câu hỏi trong chunk.
    """
    query_terms = set(query.lower().split())
    for chunk in chunks:
        text_lower = chunk["text"].lower()
        # Tính bonus point nếu chứa từ khóa chính xác
        term_matches = sum(1 for term in query_terms if term in text_lower)
        # Cập nhật score: score gốc (vector) + bonus từ keyword
        chunk["score"] = round(chunk["score"] + (term_matches * 0.05), 4)
    
    # Sắp xếp lại theo score mới
    return sorted(chunks, key=lambda x: x["score"], reverse=True)

def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict]:
    client = _get_openai_client()
    # 1. Embed query
    resp = client.embeddings.create(input=query, model="text-embedding-3-small")
    query_embedding = resp.data[0].embedding

    try:
        collection = _get_collection()
        # 2. Query vector db
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )

        chunks = []
        for doc, dist, meta in zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0]
        ):
            chunks.append({
                "text": doc,
                "source": meta.get("source", "unknown"),
                "score": round(1 - dist, 4), 
                "metadata": meta,
            })
        
        # 3. Rerank để đẩy độ chính xác lên
        reranked_chunks = simple_reranker(query, chunks)
        
        return reranked_chunks[:3] # Trả về top 3 chất lượng nhất sau rerank

    except Exception as e:
        print(f"⚠️ Retrieval failed: {e}")
        return []

def run(state: dict) -> dict:
    task = state.get("task", "")
    # Ưu tiên lấy top_k từ state (do supervisor quyết định)
    top_k = state.get("retrieval_top_k", DEFAULT_TOP_K)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        # Thực hiện tìm kiếm
        chunks = retrieve_dense(task, top_k=top_k)
        
        # Nếu score quá thấp (< 0.3), ghi chú vào history để synthesis_worker biết
        low_confidence = any(c["score"] < 0.35 for c in chunks) if chunks else True

        sources = list({c["source"] for c in chunks})
        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
            "low_confidence_flag": low_confidence
        }
        
        conf_msg = "LOW CONFIDENCE" if low_confidence else "HIGH CONFIDENCE"
        state["history"].append(
            f"[{WORKER_NAME}] {conf_msg}: retrieved {len(chunks)} chunks"
        )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state

# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Retrieval Worker — Standalone Test")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for c in chunks[:2]:
            print(f"    [{c['score']:.3f}] {c['source']}: {c['text'][:80]}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\n✅ retrieval_worker test done.")