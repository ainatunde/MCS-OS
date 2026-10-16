"""AfricaSignal Scoped Product Adapter (MCS-OS v2.2 §6.1)."""

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


class AfricaSignalAdapter:
    product_slug = "africasignal"
    adapter_version = "adapter/africasignal/v1"

    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self._outcomes: Dict[str, OutcomeRecord] = {}

    async def describe_capabilities(self) -> Sequence[CapabilityDescriptor]:
        return [
            CapabilityDescriptor(
                action_type="content.social.publish.v1",
                department="D03",
                description="Publish verified economic fact-check or research note to social channels",
                authority_class="A2",
            ),
            CapabilityDescriptor(
                action_type="claims.verify.v1",
                department="D04",
                description="Verify macroeconomic and regulatory claims against authoritative datasets",
                authority_class="A1",
            ),
            CapabilityDescriptor(
                action_type="runner.assessment.execute.v1",
                department="D05",
                description="Execute automated signal ingestion and evaluation runner batches",
                authority_class="A1",
            ),
        ]

    async def read_health(self) -> HealthReport:
        return HealthReport(
            product_slug=self.product_slug,
            status="healthy",
            details={
                "eval_runner": "active",
                "claim_store": "online",
                "citation_engine": "grounded",
                "distribution_gate": "bounded",
            },
        )

    async def read_metrics(self, period_start: str, period_end: str) -> Sequence[MetricSnapshot]:
        now = datetime.now(timezone.utc)
        return [
            MetricSnapshot(
                metric_id="verified_economic_claims",
                product_slug=self.product_slug,
                unit="claims",
                value=840.0,
                period_start=now,
                period_end=now,
                status="known",
            ),
            MetricSnapshot(
                metric_id="published_factchecks",
                product_slug=self.product_slug,
                unit="articles",
                value=124.0,
                period_start=now,
                period_end=now,
                status="known",
            ),
        ]

    async def validate_action(self, envelope: ActionEnvelope) -> ValidationResult:
        supported = [
            "content.social.publish.v1",
            "claims.verify.v1",
            "runner.assessment.execute.v1",
        ]
        if envelope.action_type not in supported:
            return ValidationResult(
                is_valid=False,
                errors=[f"Unsupported action type for africasignal: {envelope.action_type}"],
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
            "claim_id": envelope.payload.get("claim_id", "default"),
            "status": "applied",
        }
        receipt = ExecutionReceipt(
            action_id=envelope.action_id,
            product_slug=self.product_slug,
            provider_reference=f"as-exec-{envelope.action_id}",
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
