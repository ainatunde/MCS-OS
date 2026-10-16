"""D02 Commercial / Sales & Partnerships Workflow (MCS-OS v2.2 §3 & §3.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contracts.actions.envelope import ActionEnvelope, AuthorityClass
from services.workflows.base import BaseDepartmentWorkflow, WorkflowExecutionResult


class CommercialWorkflow(BaseDepartmentWorkflow):
    def __init__(self, charter_path: str = "charters/d02_commercial.yaml", policy_engine=None):
        super().__init__("D02", charter_path, policy_engine)

    async def run_cycle(self, trigger_event: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        cycle_id = f"cycle-d02-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        lead_data = trigger_event.get("lead") if trigger_event else {
            "lead_name": "Metro Broadcast Network Nigeria",
            "email": "partnerships@metrobroadcast.ng",
            "product_interest": "cloudstream-vcp",
            "channel_capacity": 5,
        }

        # 1. Action: crm.lead.upsert.v1 into MCS-ERP
        lead_payload = {
            "lead_name": lead_data["lead_name"],
            "email_id": lead_data["email"],
            "product_slug": lead_data["product_interest"],
            "status": "Lead",
        }
        envelope = self.create_action_envelope(
            task_id="tsk-d02-lead-001",
            product_slug="cloudstream-vcp",
            action_type="crm.lead.upsert.v1",
            authority_class=AuthorityClass.A1,
            payload=lead_payload,
            idempotency_key=f"idem-d02-lead-{lead_data['email']}",
            authorization_ref="standing:chr-d02-commercial:crm",
        )

        decision = self.policy_engine.evaluate(envelope)

        return WorkflowExecutionResult(
            department_id=self.department_id,
            cycle_id=cycle_id,
            status="completed",
            actions_proposed=1,
            actions_executed=1 if decision.is_authorized else 0,
            details={
                "lead_action_id": envelope.action_id,
                "is_authorized": decision.is_authorized,
                "lead_name": lead_data["lead_name"],
            },
        )
