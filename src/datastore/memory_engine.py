"""Core datastore engine with full persistence and indexing."""

from __future__ import annotations

import math
import threading
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .lookup_tables import EmbeddingIndex, FullTextIndex, ValueIndex
from .backup_manager import JournalEntry, PersistenceEngine


class DatastoreCore:
    """Primary data storage engine with atomic operations and durability."""

    def __init__(self, data_dir: str, drop_rate: float = 0.0) -> None:
        self._persistence = PersistenceEngine(data_dir, drop_rate=drop_rate)
        self._data: Dict[str, Any] = self._persistence.load()
        self._lock = threading.Lock()
        self._value_index = ValueIndex()
        self._text_index = FullTextIndex()
        self._embedding_index = EmbeddingIndex()
        self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        for key, value in self._data.items():
            self._index_value(key, value)

    def _index_value(self, key: str, value: Any) -> None:
        if self._is_hashable(value):
            self._value_index.add(key, value)
        text_value = self._extract_text(value)
        if text_value:
            self._text_index.add_document(key, text_value)
        vector = self._extract_vector(value)
        if vector:
            self._embedding_index.add_vector(key, vector)

    def _unindex_value(self, key: str, value: Any) -> None:
        if self._is_hashable(value):
            self._value_index.remove(key, value)
        text_value = self._extract_text(value)
        if text_value:
            self._text_index.remove_document(key, text_value)
        vector = self._extract_vector(value)
        if vector:
            self._embedding_index.remove_vector(key)

    @staticmethod
    def _is_hashable(value: Any) -> bool:
        try:
            hash(value)
        except TypeError:
            return False
        return True

    @staticmethod
    def _extract_text(value: Any) -> Optional[str]:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str):
                return text
        return None

    @staticmethod
    def _extract_vector(value: Any) -> Optional[List[float]]:
        if isinstance(value, dict):
            vector = value.get("vector")
            if isinstance(vector, list) and all(isinstance(v, (int, float)) for v in vector):
                return [float(v) for v in vector]
        return None

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._data.get(key)

    def set(self, key: str, value: Any, simulate_drop: bool = False) -> None:
        entry = JournalEntry(op="set", data={"key": key, "value": value})
        with self._lock:
            if key in self._data:
                self._unindex_value(key, self._data[key])
            self._persistence.append_journal(entry)
            self._data[key] = value
            self._index_value(key, value)
            self._persistence.save_snapshot(self._data, simulate_drop=simulate_drop)

    def delete(self, key: str, simulate_drop: bool = False) -> None:
        entry = JournalEntry(op="delete", data={"key": key})
        with self._lock:
            self._persistence.append_journal(entry)
            if key in self._data:
                self._unindex_value(key, self._data[key])
                self._data.pop(key, None)
            self._persistence.save_snapshot(self._data, simulate_drop=simulate_drop)

    def bulk_set(self, items: Iterable[Tuple[str, Any]], simulate_drop: bool = False) -> None:
        items_list = list(items)
        entry = JournalEntry(op="bulk_set", data={"items": items_list})
        with self._lock:
            self._persistence.append_journal(entry)
            for key, value in items_list:
                if key in self._data:
                    self._unindex_value(key, self._data[key])
                self._data[key] = value
                self._index_value(key, value)
            self._persistence.save_snapshot(self._data, simulate_drop=simulate_drop)

    def apply_replication(self, op: str, payload: Dict[str, Any]) -> None:
        if op == "set":
            self.set(payload["key"], payload["value"], simulate_drop=False)
        elif op == "delete":
            self.delete(payload["key"], simulate_drop=False)
        elif op == "bulk_set":
            self.bulk_set(payload["items"], simulate_drop=False)
        elif op == "add_vector":
            self.set(payload["key"], {"vector": payload["vector"]}, simulate_drop=False)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    def search_by_value(self, value: Any) -> List[str]:
        with self._lock:
            return self._value_index.search(value)

    def search_text(self, term: str) -> List[str]:
        with self._lock:
            return self._text_index.search(term)

    def add_vector(self, key: str, vector: List[float], simulate_drop: bool = False) -> None:
        self.set(key, {"vector": vector}, simulate_drop=simulate_drop)

    def vector_search(self, vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        with self._lock:
            scores: List[Dict[str, Any]] = []
            for key, candidate in self._embedding_index.items():
                score = self._cosine_similarity(vector, candidate)
                if score is not None:
                    scores.append({"key": key, "score": score})
            scores.sort(key=lambda item: item["score"], reverse=True)
            return scores[:top_k]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> Optional[float]:
        if len(a) != len(b) or not a:
            return None
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return None
        return dot / (norm_a * norm_b)
