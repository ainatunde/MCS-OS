"""D03 CMO / Marketing & Communications Workflow (MCS-OS v2.2 §3 & §3.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contracts.actions.envelope import ActionEnvelope, AuthorityClass
from services.workflows.base import BaseDepartmentWorkflow, WorkflowExecutionResult


class CMOWorkflow(BaseDepartmentWorkflow):
    def __init__(self, charter_path: str = "charters/d03_cmo.yaml", policy_engine=None):
        super().__init__("D03", charter_path, policy_engine)

    async def run_cycle(self, trigger_event: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        cycle_id = f"cycle-d03-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        content_item = trigger_event.get("content") if trigger_event else {
            "title": "Sub-Saharan Linear Ad Yield Reaches New Benchmark",
            "summary": "SSAI ad-fill across West Africa linear streams increased by 22% in Q3.",
            "citation_triple": "sha256:d04_citation_9f3b2a81ec45b",
            "channel": "africasignal_social",
        }

        # Validate citation triple presence
        if not content_item.get("citation_triple"):
            return WorkflowExecutionResult(
                department_id=self.department_id,
                cycle_id=cycle_id,
                status="failed",
                details={"error": "Missing required citation triple for grounded publication"},
            )

        envelope = self.create_action_envelope(
            task_id="tsk-d03-pub-001",
            product_slug="africasignal",
            action_type="content.social.publish.v1",
            authority_class=AuthorityClass.A2,
            payload={
                "title": content_item["title"],
                "body": content_item["summary"],
                "citation_triple": content_item["citation_triple"],
                "channels": ["x", "telegram"],
            },
            idempotency_key=f"idem-d03-pub-{content_item['citation_triple']}",
            authorization_ref="standing:chr-d03-cmo:social",
            evidence_citations=[content_item["citation_triple"]],
        )

        decision = self.policy_engine.evaluate(envelope)

        return WorkflowExecutionResult(
            department_id=self.department_id,
            cycle_id=cycle_id,
            status="completed",
            actions_proposed=1,
            actions_executed=1 if decision.is_authorized else 0,
            details={
                "publication_action_id": envelope.action_id,
                "is_authorized": decision.is_authorized,
            },
        )
