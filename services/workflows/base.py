"""Base Department Workflow & Orchestration Contract (MCS-OS v2.2 §3.1 & §3.3).

Provides the foundation for deterministic observation workers, LangGraph
coordination, ActionEnvelope proposal, and authority-governed execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional
import yaml

from contracts.actions.envelope import ActionEnvelope, AuthorityClass, OutcomeState, canonical_payload_hash
from contracts.products.base import ExecutionReceipt
from services.policy.engine import PolicyEngine

logger = logging.getLogger("workflows")


@dataclass
class WorkflowExecutionResult:
    department_id: str
    cycle_id: str
    status: str  # completed, escalated, halted, failed
    actions_proposed: int = 0
    actions_executed: int = 0
    actions_awaiting_approval: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseDepartmentWorkflow:
    """Base class for autonomous department workflows."""

    def __init__(
        self,
        department_id: str,
        charter_path: str,
        policy_engine: Optional[PolicyEngine] = None,
    ):
        self.department_id = department_id
        self.charter_path = charter_path
        self.charter: Dict[str, Any] = self._load_charter(charter_path)
        self.policy_engine = policy_engine or PolicyEngine()

    def _load_charter(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def create_action_envelope(
        self,
        task_id: str,
        product_slug: str,
        action_type: str,
        authority_class: AuthorityClass,
        payload: Dict[str, Any],
        idempotency_key: str,
        authorization_ref: str = "standing_charter_v2.2",
        evidence_citations: Optional[List[str]] = None,
        fencing_token: int = 1,
    ) -> ActionEnvelope:
        """Constructs a strictly validated, immutable ActionEnvelope."""
        return ActionEnvelope(
            action_id=f"act-{self.department_id.lower()}-{hashlib.sha256(idempotency_key.encode()).hexdigest()[:12]}",
            task_id=task_id,
            charter_id=self.charter.get("charter_id", f"chr-{self.department_id.lower()}"),
            department_id=self.department_id,
            product_slug=product_slug,
            action_type=action_type,
            authority_class=authority_class,
            payload=payload,
            canonical_payload_hash=canonical_payload_hash(payload),
            idempotency_key=idempotency_key,
            fencing_token=fencing_token,
            authorization_ref=authorization_ref,
            evidence_citations=evidence_citations or [],
        )

    async def run_cycle(self, trigger_event: Optional[Dict[str, Any]] = None) -> WorkflowExecutionResult:
        """Executes one deterministic cycle of the department workflow."""
        raise NotImplementedError("Subclasses must implement run_cycle()")
