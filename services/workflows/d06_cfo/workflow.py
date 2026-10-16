"""D06 CFO / Finance Operations Workflow (MCS-OS v2.2 §3 & §3.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contracts.actions.envelope import ActionEnvelope, AuthorityClass
from services.workflows.base import BaseDepartmentWorkflow, WorkflowExecutionResult


class CFOWorkflow(BaseDepartmentWorkflow):
    def __init__(self, charter_path: str = "charters/d06_cfo.yaml", policy_engine=None):
        super().__init__("D06", charter_path, policy_engine)

    async def run_cycle(self, trigger_event: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        cycle_id = f"cycle-d06-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        usage_report = trigger_event.get("usage") if trigger_event else {
            "customer_id": "cust_broadcaster_lagos",
            "customer_name": "Lagos Linear TV Network",
            "product_slug": "cloudstream-vcp",
            "active_channels": 4,
            "stream_hours": 2880,
            "ad_impressions_served": 125000,
            "net_billable_usd": 1850.00,
        }

        # Action: finance.invoice.create_draft.v1 in MCS-ERP
        envelope = self.create_action_envelope(
            task_id="tsk-d06-inv-001",
            product_slug=usage_report["product_slug"],
            action_type="finance.invoice.create_draft.v1",
            authority_class=AuthorityClass.A2,
            payload={
                "customer": usage_report["customer_name"],
                "cost_center": "CloudStream-VCP",
                "items": [
                    {
                        "item_code": "VCP-CHANNEL-MONTHLY",
                        "qty": usage_report["active_channels"],
                        "rate": 250.00,
                        "amount": 1000.00,
                    },
                    {
                        "item_code": "SSAI-AD-IMPRESSIONS",
                        "qty": usage_report["ad_impressions_served"] / 1000.0,
                        "rate": 6.80,
                        "amount": 850.00,
                    },
                ],
                "total_amount_usd": usage_report["net_billable_usd"],
            },
            idempotency_key=f"idem-d06-inv-{usage_report['customer_id']}-202610",
            authorization_ref="standing:chr-d06-cfo:billing",
        )

        decision = self.policy_engine.evaluate(envelope)

        return WorkflowExecutionResult(
            department_id=self.department_id,
            cycle_id=cycle_id,
            status="completed",
            actions_proposed=1,
            actions_executed=1 if decision.is_authorized else 0,
            details={
                "invoice_action_id": envelope.action_id,
                "is_authorized": decision.is_authorized,
                "total_amount_usd": usage_report["net_billable_usd"],
            },
        )
