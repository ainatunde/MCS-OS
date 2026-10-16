"""D07 Customer Operations & Support Workflow (MCS-OS v2.2 §3 & §3.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contracts.actions.envelope import ActionEnvelope, AuthorityClass
from services.workflows.base import BaseDepartmentWorkflow, WorkflowExecutionResult


class CustomerWorkflow(BaseDepartmentWorkflow):
    def __init__(self, charter_path: str = "charters/d07_customer.yaml", policy_engine=None):
        super().__init__("D07", charter_path, policy_engine)

    async def run_cycle(self, trigger_event: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        cycle_id = f"cycle-d07-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        ticket = trigger_event.get("ticket") if trigger_event else {
            "ticket_id": "TCK-8921",
            "customer": "Silverbird Prime Broadcast",
            "product_slug": "cloudstream-vcp",
            "subject": "Intermittent SCTE-35 ad break splice delay",
            "priority": "Medium",
            "sla_target_minutes": 15,
        }

        # Action: support.issue.create.v1 in MCS-ERP Support
        envelope = self.create_action_envelope(
            task_id="tsk-d07-sup-001",
            product_slug=ticket["product_slug"],
            action_type="support.issue.create.v1",
            authority_class=AuthorityClass.A2,
            payload={
                "subject": ticket["subject"],
                "customer": ticket["customer"],
                "priority": ticket["priority"],
                "issue_type": "Technical",
                "sla_target_minutes": ticket["sla_target_minutes"],
            },
            idempotency_key=f"idem-d07-tck-{ticket['ticket_id']}",
            authorization_ref="standing:chr-d07-customer:support",
        )

        decision = self.policy_engine.evaluate(envelope)

        return WorkflowExecutionResult(
            department_id=self.department_id,
            cycle_id=cycle_id,
            status="completed",
            actions_proposed=1,
            actions_executed=1 if decision.is_authorized else 0,
            details={
                "support_action_id": envelope.action_id,
                "is_authorized": decision.is_authorized,
                "ticket_id": ticket["ticket_id"],
            },
        )
