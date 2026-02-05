from __future__ import annotations

import socket
import threading
from pathlib import Path

import pytest

from datastore.remote_interface import DatastoreConnector
from datastore.node_config import DatastoreSettings
from datastore.socket_gateway import DatastoreServer


@pytest.fixture()
def server(tmp_path: Path):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    sock.close()

    settings = DatastoreSettings(node_id=1, host=host, port=port, data_dir=str(tmp_path))
    server = DatastoreServer(settings)

    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    yield server
    server.shutdown()


def test_set_get(server: DatastoreServer):
    client = DatastoreConnector(server.settings.host, server.settings.port)
    client.set("alpha", {"value": 1})
    assert client.get("alpha") == {"value": 1}


def test_set_delete_get(server: DatastoreServer):
    client = DatastoreConnector(server.settings.host, server.settings.port)
    client.set("beta", 2)
    client.delete("beta")
    assert client.get("beta") is None


def test_get_missing(server: DatastoreServer):
    client = DatastoreConnector(server.settings.host, server.settings.port)
    assert client.get("missing") is None


def test_overwrite(server: DatastoreServer):
    client = DatastoreConnector(server.settings.host, server.settings.port)
    client.set("gamma", 1)
    client.set("gamma", 2)
    assert client.get("gamma") == 2
