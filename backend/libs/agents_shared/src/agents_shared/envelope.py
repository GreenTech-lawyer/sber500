"""Utilities for creating and validating unified message envelopes.

Envelope contract:
{
  "user_id": "string",
  "session_id": "string",
  "correlation_id": "uuid",
  "source": "frontend|parser|legal|assistant|ocr|ws-gateway",
  "event": "event.name",
  "payload": { ... }
}

This module provides small helpers to create and validate envelopes and to unwrap
legacy messages for a smooth migration.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional, Tuple


def create_envelope(
    *,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    source: str,
    event: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    envelope = {
        "user_id": user_id,
        "session_id": session_id,
        "correlation_id": correlation_id,
        "source": source,
        "event": event,
        "payload": payload,
    }
    return envelope


def validate_envelope(envelope: Dict[str, Any]) -> None:
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a dict")
    required = ["correlation_id", "source", "event", "payload"]
    for k in required:
        if k not in envelope:
            raise ValueError(f"envelope missing required field: {k}")
    if not isinstance(envelope["payload"], dict):
        raise ValueError("envelope.payload must be a dict")


def unwrap_payload_or_legacy(message: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Return (envelope, correlation_id).

    If message already matches the envelope contract, return it unchanged.
    Otherwise wrap legacy messages into an envelope with sensible defaults.
    """
    if not isinstance(message, dict):
        raise ValueError("message must be a dict")
    # Already an envelope if it has 'event' and 'correlation_id' and 'payload'
    if all(k in message for k in ("event", "correlation_id", "payload")):
        # ensure payload is a dict
        if not isinstance(message["payload"], dict):
            raise ValueError("envelope.payload must be a dict")
        return message, message["correlation_id"]

    # Legacy: try to extract common fields
    payload = {}
    if "text" in message:
        payload["text"] = message.get("text")
    if "session_id" in message:
        payload["session_id"] = message.get("session_id")
    if "user_id" in message:
        user_id = message.get("user_id")
    else:
        user_id = None
    # Use provided key or generate new correlation id
    correlation_id = message.get("correlation_id") or str(uuid.uuid4())
    envelope = create_envelope(
        user_id=user_id,
        session_id=message.get("session_id"),
        source=message.get("source", "legacy"),
        event=message.get("event", "legacy.message"),
        payload=payload,
        correlation_id=correlation_id,
    )
    return envelope, correlation_id
