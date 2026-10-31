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
from pydantic import BaseModel, Field, model_validator


class EventEnvelope(BaseModel):
    event_id: str
    producer: str
    event_type: str = "unspecified.v1"
    schema_version: str = "v1"
    product_slug: str
    occurred_at: datetime
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str
    causation_id: Optional[str] = None
    payload_hash: str
    signature: Optional[str] = None
    payload: Dict[str, Any]

    @model_validator(mode="after")
    def verify_event_hash(self):
        canonical_json = json.dumps(self.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        expected = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        if self.payload_hash != expected:
            raise ValueError("Event payload_hash mismatch")
        return self
