"""Shared helpers: UTC timestamps and prefixed short ids (Contract §0)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def now() -> datetime:
    """ISO-8601 UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)


def gen_id(prefix: str) -> str:
    """Prefix + short uuid, e.g. wf_/nd_/ed_/ap_/rn_/ar_ (Contract §0)."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"
