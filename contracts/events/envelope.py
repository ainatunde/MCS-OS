"""Standard Event Envelope for Ingress & Audit.

Governed by MCS-OS Master Specification v2.2 Section 6.4:
  - Event ID, producer, schema version, product/tenant, occurred_at,
    received_at, correlation/causation IDs, payload hash and verified signature.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class EventEnvelope(BaseModel):
    event_id: str
    producer: str
    schema_version: str = "v1"
    product_slug: str
    occurred_at: datetime
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str
    causation_id: Optional[str] = None
    payload_hash: str
    signature: Optional[str] = None
    payload: Dict[str, Any]

    @field_validator("payload_hash")
    @classmethod
    def verify_event_hash(cls, v: str, info) -> str:
        payload = info.data.get("payload")
        if payload is not None:
            canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            expected = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
            if v != expected:
                raise ValueError(f"Event payload_hash mismatch: given {v}, calculated {expected}")
        return v
