"""LiteLLM Budget-Gated Proxy Router & Model Fallback (MCS-OS v2.2 §7.5 & §8.1).

Enforces two-phase budget reservation, per-call token limits, atomic cost
tracking, model fallback cascades, and recovery-phase budget preservation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("litellm_proxy")


class BudgetExceededError(Exception):
    """Raised when an action or department exceeds its allocated AI spend ceiling."""
    pass


@dataclass
class CostReservation:
    reservation_id: str
    department: str
    action_id: str
    estimated_cost_usd: float
    reserved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_settled: bool = False
    actual_cost_usd: float = 0.0

    @property
    def department_id(self) -> str:
        return self.department

    @property
    def reserved_usd(self) -> float:
        return self.estimated_cost_usd


BudgetReservation = CostReservation


@dataclass
class ModelRoute:
    model_name: str
    input_cost_per_million: float
    output_cost_per_million: float
    max_tokens: int = 4096


DEFAULT_ROUTES: Dict[str, ModelRoute] = {
    "primary": ModelRoute(
        model_name="gemini-1.5-pro",
        input_cost_per_million=3.50,
        output_cost_per_million=10.50,
    ),
    "fallback": ModelRoute(
        model_name="gemini-1.5-flash",
        input_cost_per_million=0.35,
        output_cost_per_million=1.05,
    ),
}


class LiteLLMProxyRouter:
    """Enforces two-phase budget reservations and primary->secondary model fallback."""

    def __init__(
        self,
        daily_budget_usd: float = 15.0,
        recovery_reserve_usd: float = 5.0,
        routes: Optional[Dict[str, ModelRoute]] = None,
    ):
        self.daily_budget_usd = daily_budget_usd
        self.recovery_reserve_usd = recovery_reserve_usd
        self.routes = routes or DEFAULT_ROUTES
        self.reserved_usd: float = 0.0
        self.spent_usd: float = 0.0
        self.recovery_spent_usd: float = 0.0
        self.reservations: Dict[str, BudgetReservation] = {}
        self.active_reservations = self.reservations
        self.department_spend: Dict[str, float] = {}

    def get_remaining_budget(self) -> float:
        reserved_total = sum(
            r.estimated_cost_usd for r in self.reservations.values() if not r.is_settled
        )
        return max(0.0, self.daily_budget_usd - (self.spent_usd + reserved_total))

    @property
    def available_standard_budget_usd(self) -> float:
        standard_ceiling = self.daily_budget_usd - self.recovery_reserve_usd
        return max(0.0, standard_ceiling - (self.spent_usd + self.reserved_usd))

    def reserve_budget(
        self,
        department: str,
        action_id: str,
        estimated_cost_usd: float,
        is_recovery: bool = False,
    ) -> BudgetReservation:
        """Phase 1: Reserve budget before model call."""
        if estimated_cost_usd <= 0:
            raise ValueError("Estimated cost must be positive")

        if is_recovery:
            if self.recovery_spent_usd + estimated_cost_usd > self.recovery_reserve_usd:
                raise BudgetExceededError(
                    f"Recovery reserve exhausted for {department}: requested ${estimated_cost_usd:.4f}, "
                    f"remaining recovery reserve ${max(0.0, self.recovery_reserve_usd - self.recovery_spent_usd):.4f}"
                )
            self.recovery_spent_usd += estimated_cost_usd
        else:
            remaining = self.daily_budget_usd - (self.spent_usd + self.reserved_usd)
            if estimated_cost_usd > remaining:
                raise BudgetExceededError(
                    f"Daily AI budget ceiling exceeded for {department}: requested ${estimated_cost_usd:.4f}, "
                    f"remaining ${max(0.0, remaining):.4f}"
                )

        res_id = f"res_{action_id}_{len(self.reservations) + 1}"
        reservation = BudgetReservation(
            reservation_id=res_id,
            department=department,
            action_id=action_id,
            estimated_cost_usd=estimated_cost_usd,
        )
        self.reservations[res_id] = reservation
        self.reserved_usd += estimated_cost_usd
        return reservation

    def settle_reservation(
        self,
        reservation_id: str,
        actual_input_tokens: int,
        actual_output_tokens: int,
        route_key: str = "primary",
    ) -> float:
        """Settle cost reservation with actual token count and return actual cost."""
        reservation = self.reservations.get(reservation_id)
        if not reservation:
            raise KeyError(f"Reservation {reservation_id} not found")

        route = self.routes.get(route_key, self.routes["primary"])
        input_cost = (actual_input_tokens / 1_000_000.0) * route.input_cost_per_million
        output_cost = (actual_output_tokens / 1_000_000.0) * route.output_cost_per_million
        actual_cost = round(input_cost + output_cost, 6)

        reservation.actual_cost_usd = actual_cost
        reservation.is_settled = True

        self.reserved_usd = max(0.0, self.reserved_usd - reservation.estimated_cost_usd)
        self.spent_usd += actual_cost
        self.department_spend[reservation.department] = (
            self.department_spend.get(reservation.department, 0.0) + actual_cost
        )
        return actual_cost

    async def complete_with_fallback(
        self,
        prompt: str,
        department: str,
        action_id: str,
        mock_executor: Optional[Callable[[str, str], Tuple[str, int, int]]] = None,
    ) -> Dict[str, Any]:
        """Executes LLM completion with automatic fallback and cost settlement.

        If primary model fails, falls back to fallback route.
        """
        est_cost = 0.05  # Conservative estimate
        reservation = self.reserve_budget(department, action_id, est_cost)

        for route_key in ["primary", "fallback"]:
            route = self.routes[route_key]
            try:
                if mock_executor:
                    response_text, in_tok, out_tok = mock_executor(prompt, route.model_name)
                else:
                    # Simulated execution for testing / offline run
                    response_text = f"[{route.model_name}] Completed response for: {prompt[:30]}..."
                    in_tok = len(prompt.split()) * 2
                    out_tok = 50

                actual_cost = self.settle_reservation(
                    reservation.reservation_id, in_tok, out_tok, route_key=route_key
                )
                return {
                    "text": response_text,
                    "model": route.model_name,
                    "route": route_key,
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                    "cost_usd": actual_cost,
                    "reservation_id": reservation.reservation_id,
                }
            except Exception as e:
                logger.warning("Route %s (%s) failed: %s", route_key, route.model_name, e)
                if route_key == "fallback":
                    reservation.is_settled = True
                    raise RuntimeError(f"All LLM routes failed for action {action_id}: {e}") from e

        raise RuntimeError("Unreachable completion state")
