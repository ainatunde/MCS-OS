"""CloudStream VCP Scoped Product Adapter (MCS-OS v2.2 §6.1)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence
from contracts.actions.envelope import ActionEnvelope, OutcomeState
from contracts.products.base import (
    CapabilityDescriptor,
    ExecutionReceipt,
    HealthReport,
    MetricSnapshot,
    OutcomeRecord,
    ValidationResult,
)


class CloudStreamVCPAdapter:
    product_slug = "cloudstream-vcp"
    adapter_version = "adapter/cloudstream-vcp/v1"

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._outcomes: Dict[str, OutcomeRecord] = {}

    async def describe_capabilities(self) -> Sequence[CapabilityDescriptor]:
        return [
            CapabilityDescriptor(
                action_type="channel.onboard.v1",
                department="D02",
                description="Onboard new broadcast channel feed into VCP live ingest",
                authority_class="A2",
            ),
            CapabilityDescriptor(
                action_type="stream.diagnose.v1",
                department="D07",
                description="Query stream lag, SCTE-35 markers, and VLM confidence",
                authority_class="A0",
            ),
            CapabilityDescriptor(
                action_type="adbreak.telemetry.read.v1",
                department="D06",
                description="Read ad break and impression counts for billing export",
                authority_class="A0",
            ),
        ]

    async def read_health(self) -> HealthReport:
        return HealthReport(
            product_slug=self.product_slug,
            status="healthy",
            details={"ingest": "active", "ai_detector": "online", "vlm_arbiter": "ready"},
        )

    async def read_metrics(self, period_start: str, period_end: str) -> Sequence[MetricSnapshot]:
        now = datetime.now(timezone.utc)
        return [
            MetricSnapshot(
                metric_id="active_linear_channels",
                product_slug=self.product_slug,
                unit="channels",
                value=25.0,
                period_start=now,
                period_end=now,
                status="known",
            )
        ]

    async def validate_action(self, envelope: ActionEnvelope) -> ValidationResult:
        if envelope.action_type not in ["channel.onboard.v1", "stream.diagnose.v1", "adbreak.telemetry.read.v1"]:
            return ValidationResult(is_valid=False, errors=[f"Unsupported action type: {envelope.action_type}"])
        return ValidationResult(is_valid=True)

    async def execute_action(self, envelope: ActionEnvelope) -> ExecutionReceipt:
        validation = await self.validate_action(envelope)
        if not validation.is_valid:
            receipt = ExecutionReceipt(
                action_id=envelope.action_id,
                product_slug=self.product_slug,
                outcome=OutcomeState.NOT_SUPPORTED,
                error_message="; ".join(validation.errors),
            )
            return receipt

        # Record receipt & idempotent outcome
        receipt = ExecutionReceipt(
            action_id=envelope.action_id,
            product_slug=self.product_slug,
            provider_reference=f"vcp-exec-{envelope.action_id}",
            outcome=OutcomeState.APPLIED,
            details={"channel_id": envelope.payload.get("channel_id", "default"), "status": "active"},
        )
        self._outcomes[envelope.idempotency_key] = OutcomeRecord(
            action_id=envelope.action_id,
            idempotency_key=envelope.idempotency_key,
            outcome=OutcomeState.APPLIED,
            details=receipt.details,
        )
        return receipt

    async def lookup_outcome(self, action_id: str, idempotency_key: str) -> OutcomeRecord:
        if idempotency_key in self._outcomes:
            return self._outcomes[idempotency_key]
        return OutcomeRecord(
            action_id=action_id,
            idempotency_key=idempotency_key,
            outcome=OutcomeState.NOT_APPLIED,
            details={"lookup": "not_found"},
        )

    async def compensate(self, envelope: ActionEnvelope) -> ExecutionReceipt:
        return ExecutionReceipt(
            action_id=envelope.action_id,
            product_slug=self.product_slug,
            outcome=OutcomeState.CANCELLED,
            details={"compensated_action_id": envelope.compensates_action_id},
        )
