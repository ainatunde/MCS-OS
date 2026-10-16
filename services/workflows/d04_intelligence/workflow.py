"""D04 Intelligence & Research Workflow (MCS-OS v2.2 §3 & §3.3)."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Optional
from contracts.actions.envelope import ActionEnvelope, AuthorityClass
from services.workflows.base import BaseDepartmentWorkflow, WorkflowExecutionResult


class IntelligenceWorkflow(BaseDepartmentWorkflow):
    def __init__(self, charter_path: str = "charters/d04_intelligence.yaml", policy_engine=None):
        super().__init__("D04", charter_path, policy_engine)

    async def run_cycle(self, trigger_event: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        cycle_id = f"cycle-d04-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        observation = trigger_event.get("observation") if trigger_event else {
            "source": "tv_epg_lagos_ch52",
            "broadcaster": "Silverbird Prime",
            "slot": "2026-10-16 20:00 WAT",
            "unmonetized_break_seconds": 180,
            "estimated_lost_yield_usd": 450.0,
        }

        # Compute cryptographic citation triple
        raw_evidence = f"{observation['source']}:{observation['slot']}:{observation['unmonetized_break_seconds']}"
        citation_triple = f"sha256:{hashlib.sha256(raw_evidence.encode()).hexdigest()}"

        # Action: Route signal to D02 (Commercial Lead)
        envelope = self.create_action_envelope(
            task_id="tsk-d04-sig-001",
            product_slug="tv-insights",
            action_type="intelligence.signal.route.v1",
            authority_class=AuthorityClass.A1,
            payload={
                "target_department": "D02",
                "opportunity_kind": "broadcaster_unmonetized_slot",
                "lead_hint": observation["broadcaster"],
                "citation_triple": citation_triple,
                "metrics": {
                    "unmonetized_break_seconds": observation["unmonetized_break_seconds"],
                    "estimated_yield_usd": observation["estimated_lost_yield_usd"],
                },
            },
            idempotency_key=f"idem-d04-sig-{citation_triple[:16]}",
            authorization_ref="standing:chr-d04-intelligence:route",
            evidence_citations=[citation_triple],
        )

        decision = self.policy_engine.evaluate(envelope)

        return WorkflowExecutionResult(
            department_id=self.department_id,
            cycle_id=cycle_id,
            status="completed",
            actions_proposed=1,
            actions_executed=1 if decision.is_authorized else 0,
            details={
                "signal_action_id": envelope.action_id,
                "citation_triple": citation_triple,
                "is_authorized": decision.is_authorized,
            },
        )
