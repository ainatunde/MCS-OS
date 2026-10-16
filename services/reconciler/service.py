"""Outcome Reconciler Service for MCS-OS v2.2.

Governed by MCS-OS Master Specification v2.2 Section 7.2:
  - Non-mutating lookup for outcome_unknown actions.
  - Automatic resend requires positive evidence that effect was not applied.
  - Settles budget reservations once outcome is determined.
"""

from __future__ import annotations

from typing import Dict, Optional, Protocol
from contracts.actions.envelope import ExecutionState, OutcomeState
from contracts.products.base import ExecutionReceipt, MCSProductAdapter, OutcomeRecord


class ReconcilerRepository(Protocol):
    async def get_unknown_actions(self) -> list: ...
    async def settle_action(self, action_id: str, execution_state: ExecutionState, outcome: OutcomeState, details: dict) -> bool: ...


class ReconcilerService:
    def __init__(self, repository: ReconcilerRepository, adapters: Dict[str, MCSProductAdapter]):
        self.repo = repository
        self.adapters = adapters

    async def reconcile_action(self, action_id: str, product_slug: str, idempotency_key: str) -> OutcomeRecord:
        adapter = self.adapters.get(product_slug)
        if not adapter:
            record = OutcomeRecord(
                action_id=action_id,
                idempotency_key=idempotency_key,
                outcome=OutcomeState.NOT_SUPPORTED,
                details={"error": f"Adapter for {product_slug} not found"},
            )
            await self.repo.settle_action(action_id, ExecutionState.FAILED, OutcomeState.NOT_SUPPORTED, record.details)
            return record

        # Non-mutating lookup via adapter
        record = await adapter.lookup_outcome(action_id, idempotency_key)

        if record.outcome == OutcomeState.APPLIED:
            await self.repo.settle_action(action_id, ExecutionState.CONFIRMED, OutcomeState.APPLIED, record.details)
        elif record.outcome == OutcomeState.NOT_APPLIED:
            await self.repo.settle_action(action_id, ExecutionState.RETRY_WAIT, OutcomeState.NOT_APPLIED, record.details)
        elif record.outcome == OutcomeState.CANCELLED:
            await self.repo.settle_action(action_id, ExecutionState.CANCELLED, OutcomeState.CANCELLED, record.details)
        else:
            # Remains unknown until next reconciliation cycle
            await self.repo.settle_action(action_id, ExecutionState.OUTCOME_UNKNOWN, OutcomeState.UNKNOWN, record.details)

        return record
