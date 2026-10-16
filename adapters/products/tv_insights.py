"""TV-Insights / Pulzz Scoped Product Adapter (MCS-OS v2.2 §6.1)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from contracts.actions.envelope import ActionEnvelope, OutcomeState
from contracts.products.base import (
    CapabilityDescriptor,
    ExecutionReceipt,
    HealthReport,
    MetricSnapshot,
    OutcomeRecord,
    ValidationResult,
)


class TVInsightsAdapter:
    product_slug = "tv-insights"
    adapter_version = "adapter/tv-insights/v1"

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self._outcomes: Dict[str, OutcomeRecord] = {}

    async def describe_capabilities(self) -> Sequence[CapabilityDescriptor]:
        return [
            CapabilityDescriptor(
                action_type="content.editorial.publish.v1",
                department="D03",
                description="Publish verified media ranking insight with citation triple",
                authority_class="A2",
            ),
            CapabilityDescriptor(
                action_type="intelligence.signal.route.v1",
                department="D04",
                description="Route broadcaster schedule/ad gap signal to commercial lead pipeline",
                authority_class="A1",
            ),
            CapabilityDescriptor(
                action_type="schedule.feed.sync.v1",
                department="D05",
                description="Synchronize EPG broadcast schedule feeds and talent ranking models",
                authority_class="A1",
            ),
        ]

    async def read_health(self) -> HealthReport:
        return HealthReport(
            product_slug=self.product_slug,
            status="healthy",
            details={
                "epg_feed": "active",
                "star_rankings": "current",
                "ad_tracker": "online",
                "database": "sqlite_wal_ok",
            },
        )

    async def read_metrics(self, period_start: str, period_end: str) -> Sequence[MetricSnapshot]:
        now = datetime.now(timezone.utc)
        return [
            MetricSnapshot(
                metric_id="tracked_linear_schedules",
                product_slug=self.product_slug,
                unit="programs",
                value=1420.0,
                period_start=now,
                period_end=now,
                status="known",
            ),
            MetricSnapshot(
                metric_id="ranked_broadcast_talent",
                product_slug=self.product_slug,
                unit="profiles",
                value=350.0,
                period_start=now,
                period_end=now,
                status="known",
            ),
        ]

    async def validate_action(self, envelope: ActionEnvelope) -> ValidationResult:
        supported = [
            "content.editorial.publish.v1",
            "intelligence.signal.route.v1",
            "schedule.feed.sync.v1",
        ]
        if envelope.action_type not in supported:
            return ValidationResult(
                is_valid=False,
                errors=[f"Unsupported action type for tv-insights: {envelope.action_type}"],
            )
        return ValidationResult(is_valid=True)

    async def execute_action(self, envelope: ActionEnvelope) -> ExecutionReceipt:
        validation = await self.validate_action(envelope)
        if not validation.is_valid:
            return ExecutionReceipt(
                action_id=envelope.action_id,
                product_slug=self.product_slug,
                outcome=OutcomeState.NOT_SUPPORTED,
                error_message="; ".join(validation.errors),
            )

        details: Dict[str, Any] = {
            "action_type": envelope.action_type,
            "target": envelope.payload.get("target_id", "default"),
            "status": "applied",
        }
        receipt = ExecutionReceipt(
            action_id=envelope.action_id,
            product_slug=self.product_slug,
            provider_reference=f"tvi-exec-{envelope.action_id}",
            outcome=OutcomeState.APPLIED,
            details=details,
        )
        self._outcomes[envelope.idempotency_key] = OutcomeRecord(
            action_id=envelope.action_id,
            idempotency_key=envelope.idempotency_key,
            outcome=OutcomeState.APPLIED,
            details=details,
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
