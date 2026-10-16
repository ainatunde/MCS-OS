"""Standard MCS Product Adapter Protocol & Data Contracts.

Governed by MCS-OS Master Specification v2.2 Section 6.1:
  - describe_capabilities()
  - read_health()
  - read_metrics(period_start, period_end)
  - validate_action(envelope)
  - execute_action(envelope)
  - lookup_outcome(action_id, idempotency_key)
  - compensate(envelope)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Sequence, runtime_checkable
from pydantic import BaseModel, Field

from contracts.actions.envelope import ActionEnvelope, OutcomeState


class CapabilityDescriptor(BaseModel):
    action_type: str
    version: str = "v1"
    department: str
    description: str
    authority_class: str  # A0, A1, A2, A3
    idempotency_window_seconds: int = 86400
    supports_compensation: bool = False
    compensation_action_type: Optional[str] = None


class HealthReport(BaseModel):
    product_slug: str
    status: str  # healthy, degraded, down
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)
    active_incidents: List[str] = Field(default_factory=list)


class MetricSnapshot(BaseModel):
    metric_id: str
    product_slug: str
    unit: str
    value: float
    currency: Optional[str] = None
    period_start: datetime
    period_end: datetime
    status: str = "known"  # known, partial, stale, unknown


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    requires_approval: bool = False


class ExecutionReceipt(BaseModel):
    action_id: str
    product_slug: str
    provider_reference: Optional[str] = None
    outcome: OutcomeState
    details: Dict[str, Any] = Field(default_factory=dict)
    dispatched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None


class OutcomeRecord(BaseModel):
    action_id: str
    idempotency_key: str
    outcome: OutcomeState
    evidence_pointer: Optional[str] = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class MCSProductAdapter(Protocol):
    """Protocol that every MCS product adapter must satisfy."""

    product_slug: str
    adapter_version: str

    async def describe_capabilities(self) -> Sequence[CapabilityDescriptor]: ...
    async def read_health(self) -> HealthReport: ...
    async def read_metrics(self, period_start: str, period_end: str) -> Sequence[MetricSnapshot]: ...
    async def validate_action(self, envelope: ActionEnvelope) -> ValidationResult: ...
    async def execute_action(self, envelope: ActionEnvelope) -> ExecutionReceipt: ...
    async def lookup_outcome(self, action_id: str, idempotency_key: str) -> OutcomeRecord: ...
    async def compensate(self, envelope: ActionEnvelope) -> ExecutionReceipt: ...
