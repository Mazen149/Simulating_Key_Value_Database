from __future__ import annotations

import socket
import threading
from pathlib import Path

from datastore.remote_interface import DatastoreConnector
from datastore.node_config import DatastoreSettings
from datastore.socket_gateway import DatastoreServer


def _start_server(data_dir: Path):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    sock.close()

    settings = DatastoreSettings(node_id=1, host=host, port=port, data_dir=str(data_dir))
    server = DatastoreServer(settings)
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    return server


def test_persistence(tmp_path: Path):
    server = _start_server(tmp_path)
    client = DatastoreConnector(server.settings.host, server.settings.port)
    client.set("persist", "yes")
    server.shutdown()

    server = _start_server(tmp_path)
    client = DatastoreConnector(server.settings.host, server.settings.port)
    assert client.get("persist") == "yes"
    server.shutdown()
