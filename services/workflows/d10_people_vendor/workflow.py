"""D10 People & Vendor Administration Workflow (MCS-OS v2.2 §3 & §3.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contracts.actions.envelope import ActionEnvelope, AuthorityClass
from services.workflows.base import BaseDepartmentWorkflow, WorkflowExecutionResult


class PeopleVendorWorkflow(BaseDepartmentWorkflow):
    def __init__(self, charter_path: str = "charters/d10_people_vendor.yaml", policy_engine=None):
        super().__init__("D10", charter_path, policy_engine)

    async def run_cycle(self, trigger_event: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        cycle_id = f"cycle-d10-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        vendor_event = trigger_event.get("vendor") if trigger_event else {
            "supplier_name": "Hetzner Cloud GmbH",
            "supplier_group": "Infrastructure",
            "service": "CloudStream VCP edge relay nodes",
            "cost_center": "CloudStream-VCP",
            "monthly_amount_usd": 320.00,
        }

        # Action: procurement.purchase_order.create_draft.v1 in MCS-ERP Procurement
        envelope = self.create_action_envelope(
            task_id="tsk-d10-po-001",
            product_slug="cloudstream-vcp",
            action_type="procurement.purchase_order.create_draft.v1",
            authority_class=AuthorityClass.A2,
            payload={
                "supplier": vendor_event["supplier_name"],
                "cost_center": vendor_event["cost_center"],
                "items": [
                    {
                        "item_code": "CLOUD-INFRA-SERVER",
                        "qty": 4,
                        "rate": 80.00,
                        "amount": vendor_event["monthly_amount_usd"],
                    }
                ],
                "total_amount_usd": vendor_event["monthly_amount_usd"],
            },
            idempotency_key=f"idem-d10-po-{datetime.now(timezone.utc).strftime('%Y%m')}",
            authorization_ref="standing:chr-d10-people-vendor:procurement",
        )

        decision = self.policy_engine.evaluate(envelope)

        return WorkflowExecutionResult(
            department_id=self.department_id,
            cycle_id=cycle_id,
            status="completed",
            actions_proposed=1,
            actions_executed=1 if decision.is_authorized else 0,
            details={
                "po_action_id": envelope.action_id,
                "is_authorized": decision.is_authorized,
                "supplier": vendor_event["supplier_name"],
            },
        )
