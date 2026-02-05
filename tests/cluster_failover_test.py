from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path

import pytest

from datastore.remote_interface import DatastoreConnector
from datastore.node_config import DatastoreSettings, RemoteNodeConfig
from datastore.socket_gateway import DatastoreServer


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="Set RUN_INTEGRATION=1 to run")
def test_failover(tmp_path: Path):
    base = tmp_path / "cluster"
    base.mkdir()

    nodes = [
        RemoteNodeConfig(1, "127.0.0.1", 0),
        RemoteNodeConfig(2, "127.0.0.1", 0),
        RemoteNodeConfig(3, "127.0.0.1", 0),
    ]

    def bind_port(node: RemoteNodeConfig) -> RemoteNodeConfig:
        sock = socket.socket()
        sock.bind((node.host, 0))
        host, port = sock.getsockname()
        sock.close()
        return RemoteNodeConfig(node.node_id, host, port)

    nodes = [bind_port(n) for n in nodes]

    servers: list[DatastoreServer] = []
    threads: list[threading.Thread] = []

    for node in nodes:
        peers = [n for n in nodes if n.node_id != node.node_id]
        settings = DatastoreSettings(
            node_id=node.node_id,
            host=node.host,
            port=node.port,
            data_dir=str(base / f"node_{node.node_id}"),
            role="primary" if node.node_id == 1 else "secondary",
            peers=peers,
        )
        server = DatastoreServer(settings)
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        servers.append(server)
        threads.append(thread)

    primary = servers[0]
    client = DatastoreConnector(primary.settings.host, primary.settings.port)
    client.set("k", "v1")
    primary.shutdown()

    time.sleep(2)

    new_primary = None
    for server in servers[1:]:
        if server.state.get_role() == "primary":
            new_primary = server
            break
    assert new_primary is not None

    client = DatastoreConnector(new_primary.settings.host, new_primary.settings.port)
    client.set("k", "v2")
    assert client.get("k") == "v2"

    for server in servers[1:]:
        server.shutdown()
