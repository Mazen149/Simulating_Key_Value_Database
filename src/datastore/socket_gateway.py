"""Network server for accepting client connections."""

from __future__ import annotations

import json
import socketserver
from typing import Any, Dict, Optional

from .memory_engine import DatastoreCore
from .wire_protocol import ProtocolError, decode_message, encode_message
from .sync_coordinator import ChangeLog, ClusterCoordinator, NodeState, ReplicationEvent
from .node_config import DatastoreSettings


class RequestDispatcher(socketserver.StreamRequestHandler):
    server: "DatastoreServer"

    def handle(self) -> None:
        raw = self.rfile.readline()
        if not raw:
            return
        try:
            request = decode_message(raw)
        except ProtocolError as exc:
            self.wfile.write(encode_message({"status": "error", "error": str(exc)}))
            return
        response = self.server.handle_request(request)
        self.wfile.write(encode_message(response))


class DatastoreServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, settings: DatastoreSettings) -> None:
        self.settings = settings
        self.state = NodeState(settings.role)
        self.core = DatastoreCore(settings.data_dir, drop_rate=settings.drop_rate)
        self.changelog = ChangeLog(settings)
        self.coordinator = ClusterCoordinator(settings, self.state)
        super().__init__((settings.host, settings.port), RequestDispatcher)

    def start(self) -> None:
        self.changelog.start()
        self.coordinator.start()
        self.serve_forever()

    def shutdown(self) -> None:
        self.changelog.stop()
        self.coordinator.stop()
        super().shutdown()
        self.server_close()

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        op = request.get("op")
        if op == "who_is_primary":
            return {"status": "ok", "role": self.state.get_role()}
        if op == "promote":
            self.state.set_role("primary")
            return {"status": "ok"}
        if op == "replicate":
            event = request.get("event", {})
            self.core.apply_replication(event.get("op"), event.get("payload", {}))
            return {"status": "ok"}
        if self.settings.mode == "leader" and self.state.get_role() != "primary":
            return {"status": "error", "error": "not_primary"}
        try:
            return self._handle_primary(op, request)
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc)}

    def _handle_primary(self, op: Optional[str], request: Dict[str, Any]) -> Dict[str, Any]:
        if op == "get":
            value = self.core.get(request["key"])
            return {"status": "ok", "result": value}
        if op == "set":
            self.core.set(request["key"], request["value"], simulate_drop=bool(request.get("simulate_drop")))
            self.changelog.enqueue(ReplicationEvent(op="set", payload={"key": request["key"], "value": request["value"]}))
            return {"status": "ok"}
        if op == "delete":
            self.core.delete(request["key"], simulate_drop=bool(request.get("simulate_drop")))
            self.changelog.enqueue(ReplicationEvent(op="delete", payload={"key": request["key"]}))
            return {"status": "ok"}
        if op == "bulk_set":
            items = request.get("items", [])
            self.core.bulk_set(items, simulate_drop=bool(request.get("simulate_drop")))
            self.changelog.enqueue(ReplicationEvent(op="bulk_set", payload={"items": items}))
            return {"status": "ok"}
        if op == "search_value":
            keys = self.core.search_by_value(request.get("value"))
            return {"status": "ok", "result": keys}
        if op == "search_text":
            term = request.get("term", "")
            keys = self.core.search_text(term)
            return {"status": "ok", "result": keys}
        if op == "add_vector":
            self.core.add_vector(request["key"], request["vector"], simulate_drop=bool(request.get("simulate_drop")))
            self.changelog.enqueue(ReplicationEvent(op="add_vector", payload={"key": request["key"], "vector": request["vector"]}))
            return {"status": "ok"}
        if op == "vector_search":
            vector = request.get("vector", [])
            top_k = int(request.get("top_k", 5))
            results = self.core.vector_search(vector, top_k=top_k)
            return {"status": "ok", "result": results}
        return {"status": "error", "error": f"unknown op: {op}"}
