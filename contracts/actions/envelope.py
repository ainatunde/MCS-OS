"""Action Envelope & Authority Definitions for MCS-OS v2.2.

Governed by MCS-OS Master Specification v2.2:
  - Section 5.1: Authority classes A0 (Observe), A1 (Routine internal),
    A2 (Bounded execution), A3 (Principal approval), A4 (Prohibited).
  - Section 5.3: Canonical payload hash, authorization record binding,
    and revocation generation.
  - Section 6.1: Immutable ActionEnvelope passed to product adapters.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class AuthorityClass(str, Enum):
    A0 = "A0"  # Observe: permitted reads & internal analysis
    A1 = "A1"  # Routine internal: reversible internal tasks/CRM updates
    A2 = "A2"  # Bounded execution: external effects covered by standing authority
    A3 = "A3"  # Principal approval: requires fresh, exact authenticated human sign-off
    A4 = "A4"  # Prohibited: strictly forbidden for agent execution


class ExecutionState(str, Enum):
    PROPOSED = "proposed"
    AWAITING_APPROVAL = "awaiting_approval"
    READY = "ready"
    LEASED = "leased"
    DISPATCHING = "dispatching"
    PROVIDER_PENDING = "provider_pending"
    CONFIRMED = "confirmed"
    OUTCOME_UNKNOWN = "outcome_unknown"
    RETRY_WAIT = "retry_wait"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


class OutcomeState(str, Enum):
    NOT_APPLIED = "not_applied"
    PENDING = "pending"
    APPLIED = "applied"
    PARTIALLY_APPLIED = "partially_applied"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"
    NOT_SUPPORTED = "not_supported"


def canonical_payload_hash(payload: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hash over canonical JSON (sorted keys, no whitespace)."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class ActionEnvelope(BaseModel):
    """The immutable action envelope passed across policy, outbox, and executor adapters."""

    action_id: str
    task_id: str
    charter_id: str
    department_id: str
    product_slug: str
    action_type: str
    authority_class: AuthorityClass
    payload: Dict[str, Any]
    canonical_payload_hash: str
    idempotency_key: str
    fencing_token: int = 0
    authorization_ref: Optional[str] = None
    policy_version: str = "policy/launch-v1"
    qualification_ref: Optional[str] = None
    evidence_citations: List[str] = Field(default_factory=list)
    revocation_generation: int = 1
    compensates_action_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("canonical_payload_hash")
    @classmethod
    def verify_payload_hash(cls, v: str, info) -> str:
        payload = info.data.get("payload")
        if payload is not None:
            expected = canonical_payload_hash(payload)
            if v != expected:
                raise ValueError(f"canonical_payload_hash mismatch: given {v}, calculated {expected}")
        return v
