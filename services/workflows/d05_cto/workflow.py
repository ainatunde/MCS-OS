"""D05 CTO / Engineering & Reliability Workflow (MCS-OS v2.2 §3 & §3.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from contracts.actions.envelope import ActionEnvelope, AuthorityClass
from services.workflows.base import BaseDepartmentWorkflow, WorkflowExecutionResult


class CTOWorkflow(BaseDepartmentWorkflow):
    def __init__(self, charter_path: str = "charters/d05_cto.yaml", policy_engine=None):
        super().__init__("D05", charter_path, policy_engine)

    async def run_cycle(self, trigger_event: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        cycle_id = f"cycle-d05-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        ci_report = trigger_event.get("ci_status") if trigger_event else {
            "product_slug": "cloudstream-forge",
            "passed_tests": 46,
            "failed_tests": 0,
            "commit_sha": "a1b2c3d4e5f67890",
            "runner": "canonical_pytest_runner",
        }

        # Action: Verify CI and trigger staging verification
        envelope = self.create_action_envelope(
            task_id="tsk-d05-ci-001",
            product_slug=ci_report["product_slug"],
            action_type="engineering.ci.verify.v1",
            authority_class=AuthorityClass.A1,
            payload={
                "commit_sha": ci_report["commit_sha"],
                "passed_tests": ci_report["passed_tests"],
                "failed_tests": ci_report["failed_tests"],
                "is_qualified": ci_report["failed_tests"] == 0,
            },
            idempotency_key=f"idem-d05-ci-{ci_report['commit_sha'][:10]}",
            authorization_ref="standing:chr-d05-cto:ci",
        )

        decision = self.policy_engine.evaluate(envelope)

        return WorkflowExecutionResult(
            department_id=self.department_id,
            cycle_id=cycle_id,
            status="completed",
            actions_proposed=1,
            actions_executed=1 if decision.is_authorized else 0,
            details={
                "ci_action_id": envelope.action_id,
                "is_authorized": decision.is_authorized,
                "commit_sha": ci_report["commit_sha"],
            },
        )
