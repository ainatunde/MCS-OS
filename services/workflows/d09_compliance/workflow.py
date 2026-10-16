"""D09 Legal/Compliance Administration Workflow (MCS-OS v2.2 §3 & §3.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contracts.actions.envelope import ActionEnvelope, AuthorityClass
from services.workflows.base import BaseDepartmentWorkflow, WorkflowExecutionResult


class ComplianceWorkflow(BaseDepartmentWorkflow):
    def __init__(self, charter_path: str = "charters/d09_compliance.yaml", policy_engine=None):
        super().__init__("D09", charter_path, policy_engine)

    async def run_cycle(self, trigger_event: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        cycle_id = f"cycle-d09-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        audit_target = trigger_event.get("audit") if trigger_event else {
            "registry": "content_republication_rights",
            "active_contracts": 14,
            "expiring_in_30_days": 1,
            "expired_contracts": 0,
        }

        # Action: compliance.rights.audit.v1 (A1 routine internal compliance audit)
        envelope = self.create_action_envelope(
            task_id="tsk-d09-cmp-001",
            product_slug="corporate",
            action_type="compliance.rights.audit.v1",
            authority_class=AuthorityClass.A1,
            payload={
                "registry": audit_target["registry"],
                "active_count": audit_target["active_contracts"],
                "expiring_soon_count": audit_target["expiring_in_30_days"],
                "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            idempotency_key=f"idem-d09-cmp-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            authorization_ref="standing:chr-d09-compliance:audit",
        )

        decision = self.policy_engine.evaluate(envelope)

        return WorkflowExecutionResult(
            department_id=self.department_id,
            cycle_id=cycle_id,
            status="completed",
            actions_proposed=1,
            actions_executed=1 if decision.is_authorized else 0,
            details={
                "audit_action_id": envelope.action_id,
                "is_authorized": decision.is_authorized,
            },
        )
