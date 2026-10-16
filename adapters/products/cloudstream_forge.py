"""CloudStream Forge Scoped Product Adapter (MCS-OS v2.2 §6.1)."""

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


class CloudStreamForgeAdapter:
    product_slug = "cloudstream-forge"
    adapter_version = "adapter/cloudstream-forge/v1"

    def __init__(self):
        self._outcomes: Dict[str, OutcomeRecord] = {}

    async def describe_capabilities(self) -> Sequence[CapabilityDescriptor]:
        return [
            CapabilityDescriptor(
                action_type="app.build.generate.v1",
                department="D05",
                description="Scaffold and compile white-label Android TV/mobile client",
                authority_class="A2",
            ),
            CapabilityDescriptor(
                action_type="app.experience_bus.diagnose.v1",
                department="D07",
                description="Check WebSocket ExperienceBus latency and presence",
                authority_class="A0",
            ),
        ]

    async def read_health(self) -> HealthReport:
        return HealthReport(
            product_slug=self.product_slug,
            status="healthy",
            details={"experience_bus": "connected", "build_runner": "ready"},
        )

    async def read_metrics(self, period_start: str, period_end: str) -> Sequence[MetricSnapshot]:
        now = datetime.now(timezone.utc)
        return [
            MetricSnapshot(
                metric_id="active_app_tenants",
                product_slug=self.product_slug,
                unit="apps",
                value=5.0,
                period_start=now,
                period_end=now,
                status="known",
            )
        ]

    async def validate_action(self, envelope: ActionEnvelope) -> ValidationResult:
        if envelope.action_type not in ["app.build.generate.v1", "app.experience_bus.diagnose.v1"]:
            return ValidationResult(is_valid=False, errors=[f"Unsupported action type: {envelope.action_type}"])
        return ValidationResult(is_valid=True)

    async def execute_action(self, envelope: ActionEnvelope) -> ExecutionReceipt:
        receipt = ExecutionReceipt(
            action_id=envelope.action_id,
            product_slug=self.product_slug,
            provider_reference=f"forge-build-{envelope.action_id}",
            outcome=OutcomeState.APPLIED,
            details={"tenant_app": envelope.payload.get("app_slug", "default"), "build_status": "success"},
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
