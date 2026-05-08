"""MCP智能缓存 - 精确匹配 + RAG语义检索复用 (sentence-transformers升级版)"""

import json
import hashlib
from typing import Any, Optional, Dict, List
from datetime import datetime


_embedding_model = None
_embedding_available = False


def _init_embedding_model():
    global _embedding_model, _embedding_available
    if _embedding_model is not None:
        return
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        _embedding_available = True
        print("✅ [语义缓存] sentence-transformers 模型加载成功 (all-MiniLM-L6-v2)")
    except Exception as e:
        _embedding_available = False
        print(f"⚠️ [语义缓存] sentence-transformers 不可用,降级到简单向量: {e}")


def _get_embedding(text: str) -> List[float]:
    global _embedding_model, _embedding_available
    if _embedding_available and _embedding_model is not None:
        try:
            vec = _embedding_model.encode(text, normalize_embeddings=True)
            return vec.tolist()
        except Exception:
            pass
    return _simple_embedding(text)


def _simple_embedding(text: str) -> List[float]:
    embedding = [0.0] * 64
    for i, ch in enumerate(text):
        embedding[i % 64] += ord(ch) / 65535.0
    norm = sum(x * x for x in embedding) ** 0.5
    if norm > 0:
        embedding = [x / norm for x in embedding]
    return embedding


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class MCPCache:
    """MCP缓存系统 - 精确匹配 + RAG语义检索 (sentence-transformers)"""

    def __init__(self, max_size: int = 200, default_ttl: int = 3600):
        self._cache: Dict[str, Any] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._embedding_cache: Dict[str, List[float]] = {}
        self._hits = 0
        self._misses = 0
        _init_embedding_model()

    def _generate_key(self, tool_name: str, params: dict) -> str:
        sorted_params = json.dumps(params, sort_keys=True, ensure_ascii=False)
        content = f"{tool_name}:{sorted_params}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_text_embedding(self, text: str) -> List[float]:
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        emb = _get_embedding(text)
        self._embedding_cache[text] = emb
        return emb

    def get(self, tool_name: str, params: dict) -> Optional[str]:
        key = self._generate_key(tool_name, params)
        cached = self._cache.get(key)
        if cached:
            elapsed = (datetime.now() - cached["timestamp"]).total_seconds()
            if elapsed < cached["ttl"]:
                self._hits += 1
                print(f"  💾 [MCP缓存] 精确命中: {tool_name}")
                return cached["data"]
            else:
                del self._cache[key]
        self._misses += 1
        return None

    def rag_search(self, tool_name: str, params: dict, threshold: float = 0.85) -> Optional[str]:
        query_text = f"{tool_name}:{json.dumps(params, ensure_ascii=False)}"
        query_emb = self._get_text_embedding(query_text)
        best_score = 0.0
        best_data = None
        for key, entry in self._cache.items():
            if entry.get("tool_name") != tool_name:
                continue
            elapsed = (datetime.now() - entry["timestamp"]).total_seconds()
            if elapsed >= entry["ttl"]:
                continue
            entry_text = f"{entry['tool_name']}:{json.dumps(entry['params'], ensure_ascii=False)}"
            entry_emb = self._get_text_embedding(entry_text)
            score = _cosine_similarity(query_emb, entry_emb)
            if score > best_score:
                best_score = score
                best_data = entry["data"]
        if best_score >= threshold and best_data:
            print(f"  🔍 [MCP缓存] RAG语义命中: {tool_name} (相似度={best_score:.3f})")
            self._hits += 1
            return best_data
        return None

    def set(self, tool_name: str, params: dict, data: str, ttl: Optional[int] = None):
        key = self._generate_key(tool_name, params)
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache, key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]
        weather_tools = {"search_weather", "amap_maps_weather"}
        if tool_name in weather_tools:
            ttl = ttl or 1800
        self._cache[key] = {
            "data": data,
            "tool_name": tool_name,
            "params": params,
            "timestamp": datetime.now(),
            "ttl": ttl or self.default_ttl,
        }

    def get_with_rag(self, tool_name: str, params: dict, threshold: float = 0.85) -> Optional[str]:
        exact = self.get(tool_name, params)
        if exact:
            return exact
        rag_result = self.rag_search(tool_name, params, threshold)
        if rag_result:
            return rag_result
        return None

    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            "total_entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.2%}",
            "embedding_engine": "sentence-transformers" if _embedding_available else "simple_hash",
        }

    def clear(self):
        self._cache.clear()
        self._embedding_cache.clear()
        self._hits = 0
        self._misses = 0


_mcp_cache = MCPCache()


def get_mcp_cache() -> MCPCache:
    return _mcp_cache
