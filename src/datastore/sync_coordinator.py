"""Replication and cluster coordination."""

from __future__ import annotations

import queue
import socket
import threading
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from .wire_protocol import decode_message, encode_message
from .node_config import DatastoreSettings, RemoteNodeConfig


@dataclass
class ReplicationEvent:
    op: str
    payload: Dict[str, Any]


class NodeState:
    """Tracks current role in cluster (primary or secondary)."""

    def __init__(self, role: str) -> None:
        self._role = role
        self._lock = threading.Lock()

    def get_role(self) -> str:
        with self._lock:
            return self._role

    def set_role(self, role: str) -> None:
        with self._lock:
            self._role = role


class ChangeLog:
    """Queues and broadcasts changes to peer nodes."""

    def __init__(self, settings: DatastoreSettings) -> None:
        self._settings = settings
        self._queue: queue.Queue[ReplicationEvent] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        if self._settings.peers:
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def enqueue(self, event: ReplicationEvent) -> None:
        if self._settings.peers:
            self._queue.put(event)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                event = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            for peer in self._settings.peers or []:
                self._replicate_to_peer(peer, event)

    def _replicate_to_peer(self, peer: RemoteNodeConfig, event: ReplicationEvent) -> None:
        try:
            with socket.create_connection((peer.host, peer.port), timeout=self._settings.replication_timeout) as sock:
                sock.sendall(encode_message({"op": "replicate", "event": {"op": event.op, "payload": event.payload}}))
                _ = sock.recv(4096)
        except OSError:
            return


class ClusterCoordinator:
    """Handles leader election and node discovery."""

    def __init__(self, settings: DatastoreSettings, state: NodeState) -> None:
        self._settings = settings
        self._state = state
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        if self._settings.peers:
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._check_primary()
            self._stop.wait(self._settings.election_interval)

    def _check_primary(self) -> None:
        if self._state.get_role() == "primary":
            return
        primary = self._find_primary()
        if primary is None:
            self._elect_new_primary()

    def _find_primary(self) -> Optional[RemoteNodeConfig]:
        for node in self._settings.peers or []:
            if self._query_role(node) == "primary":
                return node
        return None

    def _query_role(self, node: RemoteNodeConfig) -> Optional[str]:
        try:
            with socket.create_connection((node.host, node.port), timeout=self._settings.replication_timeout) as sock:
                sock.sendall(encode_message({"op": "who_is_primary"}))
                response = decode_message(sock.recv(4096))
                return response.get("role")
        except OSError:
            return None

    def _elect_new_primary(self) -> None:
        candidates = [self._settings.node_id]
        for node in self._settings.peers or []:
            if self._query_role(node) is not None:
                candidates.append(node.node_id)
        if not candidates:
            return
        winner = min(candidates)
        if winner == self._settings.node_id:
            self._state.set_role("primary")
            return
        for node in self._settings.peers or []:
            if node.node_id == winner:
                self._promote(node)
                return

    def _promote(self, node: RemoteNodeConfig) -> None:
        try:
            with socket.create_connection((node.host, node.port), timeout=self._settings.replication_timeout) as sock:
                sock.sendall(encode_message({"op": "promote"}))
                _ = sock.recv(4096)
        except OSError:
            return
