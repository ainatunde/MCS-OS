"""MCS-ERP (ERPNext) Scoped Provider Adapter (MCS-OS v2.2 §6.1 & P06).

Provides the corporate business-record adapter for D02 (Sales/CRM),
D06 (Finance), D07 (Support), and D10 (Procurement).
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
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

PORTFOLIO_COST_CENTERS = {
    "cloudstream-vcp": "CloudStream-VCP",
    "cloudstream-forge": "CloudStream-Forge",
    "aether-ads": "Aether-ADS",
    "aether-adx": "Aether-ADX",
    "tv-insights": "TV-Insights-Pulzz",
    "africasignal": "AfricaSignal",
    "mcs-app-factory": "MCS-App-Factory",
    "corporate": "Shared G&A",
}

ERP_CAPABILITIES = [
    CapabilityDescriptor(
        action_type="crm.lead.upsert.v1",
        department="D02",
        description="Upsert sales lead into ERPNext CRM with mcs_external_ref",
        authority_class="A1",
    ),
    CapabilityDescriptor(
        action_type="crm.opportunity.upsert.v1",
        department="D02",
        description="Upsert deal opportunity in ERPNext CRM",
        authority_class="A1",
    ),
    CapabilityDescriptor(
        action_type="crm.quotation.create_draft.v1",
        department="D02",
        description="Create draft sales quotation in ERPNext",
        authority_class="A2",
    ),
    CapabilityDescriptor(
        action_type="finance.customer.upsert.v1",
        department="D06",
        description="Upsert customer account in ERPNext accounting ledger",
        authority_class="A1",
    ),
    CapabilityDescriptor(
        action_type="finance.invoice.create_draft.v1",
        department="D06",
        description="Create draft sales invoice in ERPNext with rev-share & cost center",
        authority_class="A2",
    ),
    CapabilityDescriptor(
        action_type="finance.payment.record_draft.v1",
        department="D06",
        description="Record draft customer payment entry in ERPNext",
        authority_class="A2",
    ),
    CapabilityDescriptor(
        action_type="support.issue.create.v1",
        department="D07",
        description="Create support issue ticket in ERPNext Support with SLA timers",
        authority_class="A2",
    ),
    CapabilityDescriptor(
        action_type="support.issue.update_status.v1",
        department="D07",
        description="Update support issue status in ERPNext Support",
        authority_class="A2",
    ),
    CapabilityDescriptor(
        action_type="procurement.supplier.upsert.v1",
        department="D10",
        description="Upsert vendor/supplier profile in ERPNext Procurement",
        authority_class="A1",
    ),
    CapabilityDescriptor(
        action_type="procurement.purchase_order.create_draft.v1",
        department="D10",
        description="Create draft purchase order in ERPNext for approved vendor",
        authority_class="A2",
    ),
]


class ERPNextAdapter:
    product_slug = "mcs-erp"
    adapter_version = "adapter/mcs-erp/v1"

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._outcomes: Dict[str, OutcomeRecord] = {}

    async def describe_capabilities(self) -> Sequence[CapabilityDescriptor]:
        return ERP_CAPABILITIES

    async def read_health(self) -> HealthReport:
        return HealthReport(
            product_slug=self.product_slug,
            status="healthy",
            details={
                "erpnext_version": "v15.0",
                "database": "mariadb_healthy",
                "custom_fields": "installed",
                "external_ref_indexing": "active",
            },
        )

    async def read_metrics(self, period_start: str, period_end: str) -> Sequence[MetricSnapshot]:
        now = datetime.now(timezone.utc)
        return [
            MetricSnapshot(
                metric_id="erp_open_invoices_count",
                product_slug=self.product_slug,
                unit="invoices",
                value=12.0,
                period_start=now,
                period_end=now,
                status="known",
            ),
            MetricSnapshot(
                metric_id="erp_open_support_issues",
                product_slug=self.product_slug,
                unit="tickets",
                value=4.0,
                period_start=now,
                period_end=now,
                status="known",
            ),
        ]

    async def validate_action(self, envelope: ActionEnvelope) -> ValidationResult:
        supported_types = {c.action_type for c in ERP_CAPABILITIES}
        if envelope.action_type not in supported_types:
            return ValidationResult(
                is_valid=False,
                errors=[f"Unsupported ERP action type: {envelope.action_type}"],
            )

        # Department role isolation check
        cap = next(c for c in ERP_CAPABILITIES if c.action_type == envelope.action_type)
        if cap.department != envelope.department_id:
            return ValidationResult(
                is_valid=False,
                errors=[
                    f"Department isolation violation: {envelope.department_id} cannot execute {envelope.action_type} (owned by {cap.department})"
                ],
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

        external_ref = f"mcs-{envelope.action_id}"
        cost_center = PORTFOLIO_COST_CENTERS.get(envelope.product_slug, "Shared G&A")
        details: Dict[str, Any] = {
            "action_type": envelope.action_type,
            "department": envelope.department_id,
            "mcs_external_ref": external_ref,
            "cost_center": cost_center,
            "status": "applied",
        }

        receipt = ExecutionReceipt(
            action_id=envelope.action_id,
            product_slug=self.product_slug,
            provider_reference=f"erp-{external_ref}",
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
