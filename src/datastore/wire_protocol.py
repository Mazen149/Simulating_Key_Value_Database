"""Protocol message serialization and deserialization."""

from __future__ import annotations

import json
from typing import Any, Dict


class ProtocolError(Exception):
    """Raised when message protocol validation fails."""
    pass


def encode_message(payload: Dict[str, Any]) -> bytes:
    """Encode a message dict to JSON bytes with newline."""
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")


def decode_message(raw: bytes) -> Dict[str, Any]:
    """Decode JSON bytes to message dict with validation."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ProtocolError("Invalid JSON") from exc
    if not isinstance(data, dict):
        raise ProtocolError("Message must be an object")
    return data
