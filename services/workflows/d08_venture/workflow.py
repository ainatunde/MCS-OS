"""D08 Venture & Product Development Workflow (MCS-OS v2.2 §3 & §3.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contracts.actions.envelope import ActionEnvelope, AuthorityClass
from services.workflows.base import BaseDepartmentWorkflow, WorkflowExecutionResult


class VentureWorkflow(BaseDepartmentWorkflow):
    def __init__(self, charter_path: str = "charters/d08_venture.yaml", policy_engine=None):
        super().__init__("D08", charter_path, policy_engine)

    async def run_cycle(self, trigger_event: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        cycle_id = f"cycle-d08-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        radar_signal = trigger_event.get("signal") if trigger_event else {
            "topic": "healthcare_logistics_nigeria",
            "demand_score": 8.7,
            "target_portal": "healthpath-africa",
            "opportunity_summary": "High search volume and lack of verified cold-chain route databases.",
        }

        # Action: venture.brief.generate.v1 (A1 routine internal brief compilation)
        envelope = self.create_action_envelope(
            task_id="tsk-d08-vnt-001",
            product_slug="mcs-app-factory",
            action_type="venture.brief.generate.v1",
            authority_class=AuthorityClass.A1,
            payload={
                "topic": radar_signal["topic"],
                "demand_score": radar_signal["demand_score"],
                "target_portal": radar_signal["target_portal"],
                "summary": radar_signal["opportunity_summary"],
                "requires_principal_greenlight": True,
            },
            idempotency_key=f"idem-d08-brief-{radar_signal['topic']}",
            authorization_ref="standing:chr-d08-venture:brief",
        )

        decision = self.policy_engine.evaluate(envelope)

        return WorkflowExecutionResult(
            department_id=self.department_id,
            cycle_id=cycle_id,
            status="completed",
            actions_proposed=1,
            actions_executed=1 if decision.is_authorized else 0,
            details={
                "brief_action_id": envelope.action_id,
                "is_authorized": decision.is_authorized,
                "topic": radar_signal["topic"],
            },
        )
