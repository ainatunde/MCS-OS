"""Transactional Outbox Executor Worker for MCS-OS v2.2.

Governed by MCS-OS Master Specification v2.2:
  - Section 4.1: Separate worker pool for dispatch.
  - Section 7.1: Steps 6-8 (Claim, monotonic lease, dispatch admitted, receipt persist).
  - Section 7.2: Execution states (ready -> leased -> dispatching -> confirmed / outcome_unknown).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

from contracts.actions.envelope import ActionEnvelope, ExecutionState, OutcomeState
from contracts.products.base import ExecutionReceipt, MCSProductAdapter


class OutboxRepository(Protocol):
    async def claim_ready_action(self, worker_id: str, lease_seconds: int) -> Optional[ActionEnvelope]: ...
    async def mark_dispatching(self, action_id: str, fencing_token: int) -> bool: ...
    async def mark_confirmed(self, action_id: str, receipt: ExecutionReceipt) -> bool: ...
    async def mark_outcome_unknown(self, action_id: str, error_detail: str) -> bool: ...
    async def is_halted(self, product_slug: str) -> bool: ...


class OutboxWorker:
    def __init__(
        self,
        worker_id: str,
        repository: OutboxRepository,
        adapters: Dict[str, MCSProductAdapter],
        lease_seconds: int = 60,
        dispatch_timeout_seconds: float = 30.0,
    ):
        self.worker_id = worker_id
        self.repo = repository
        self.adapters = adapters
        self.lease_seconds = lease_seconds
        self.dispatch_timeout_seconds = dispatch_timeout_seconds

    async def execute_one(self) -> Optional[ExecutionReceipt]:
        # 1. Atomic claim & lease
        envelope = await self.repo.claim_ready_action(self.worker_id, self.lease_seconds)
        if not envelope:
            return None

        # 2. Recheck halt/revocation at dispatch admission (pre-dispatch: not sent)
        if await self.repo.is_halted(envelope.product_slug):
            if hasattr(self.repo, "settle_action"):
                await self.repo.settle_action(
                    envelope.action_id,
                    ExecutionState.CANCELLED,
                    OutcomeState.NOT_APPLIED,
                    {"reason": "Halt detected at dispatch admission"},
                )
            else:
                await self.repo.mark_outcome_unknown(envelope.action_id, "Halt detected at dispatch admission")
            return None

        # 3. Mark dispatching
        admitted = await self.repo.mark_dispatching(envelope.action_id, envelope.fencing_token)
        if not admitted:
            return None

        # 4. Lookup product adapter
        adapter = self.adapters.get(envelope.product_slug)
        if not adapter:
            receipt = ExecutionReceipt(
                action_id=envelope.action_id,
                product_slug=envelope.product_slug,
                outcome=OutcomeState.NOT_SUPPORTED,
                error_message=f"No adapter registered for product slug: {envelope.product_slug}",
            )
            await self.repo.mark_confirmed(envelope.action_id, receipt)
            return receipt

        # 5. Execute action with timeout protection
        try:
            receipt = await asyncio.wait_for(
                adapter.execute_action(envelope), timeout=self.dispatch_timeout_seconds
            )
            await self.repo.mark_confirmed(envelope.action_id, receipt)
            return receipt
        except asyncio.TimeoutError:
            # Ambiguous network timeout: Must enter outcome_unknown (never blind retry!)
            await self.repo.mark_outcome_unknown(
                envelope.action_id, "Network timeout during external dispatch; transitioned to outcome_unknown"
            )
            return None
        except Exception as e:
            # If exception occurred during or after dispatch, quarantine as outcome_unknown
            await self.repo.mark_outcome_unknown(
                envelope.action_id, f"Execution exception: {str(e)}; quarantined for reconciliation"
            )
            return None
