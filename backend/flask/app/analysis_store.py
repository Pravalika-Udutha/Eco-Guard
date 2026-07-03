"""In-memory store for analysis jobs (referenced by POST /verify)."""

from __future__ import annotations

import threading
import uuid
from typing import Any

_lock = threading.Lock()
_store: dict[str, dict[str, Any]] = {}


def save_analysis(payload: dict[str, Any]) -> str:
    """Store analysis result; return analysis_id."""
    aid = str(uuid.uuid4())
    rec = {"analysis_id": aid, **payload}
    with _lock:
        _store[aid] = rec
    return aid


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    with _lock:
        return _store.get(analysis_id)


def pop_analysis(analysis_id: str) -> dict[str, Any] | None:
    """Optional: remove after verify (we keep for audit)."""
    with _lock:
        return _store.get(analysis_id)