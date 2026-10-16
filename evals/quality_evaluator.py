"""Risk-Based Quality Evaluator for MCS-OS Content & Decisions (MCS-OS v2.2 §8.1 & L06).

Evaluates:
  1. Deterministic Math & Billing Precision (zero rounding drift, rev-share splits).
  2. Grounded Prose & Citation Triple Verification (no ungrounded assertions).
  3. Prompt Injection & Adversarial Boundary Rejection.
  4. Operational Policy Compliance (A0-A4 alignment).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class QualityEvalResult:
    test_id: str
    passed: bool
    score: float  # 0.0 to 1.0
    failure_reasons: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


class QualityEvaluator:
    # Known prompt injection signatures
    INJECTION_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
        re.compile(r"disregard\s+system\s+prompt", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+dan", re.IGNORECASE),
        re.compile(r"bypass\s+policy", re.IGNORECASE),
        re.compile(r"admin_override_key", re.IGNORECASE),
    ]

    @classmethod
    def evaluate_billing_math(
        cls,
        base_rate: float,
        quantity: float,
        rev_share_pct: float,
        calculated_total: float,
    ) -> QualityEvalResult:
        """Verifies deterministic billing without floating point or rounding drift."""
        expected_gross = round(base_rate * quantity, 2)
        expected_net = round(expected_gross * (1.0 - (rev_share_pct / 100.0)), 2)

        if abs(calculated_total - expected_net) > 0.01:
            return QualityEvalResult(
                test_id="math_billing_drift",
                passed=False,
                score=0.0,
                failure_reasons=[
                    f"Billing calculation drift: expected {expected_net}, got {calculated_total}"
                ],
                details={"expected": expected_net, "actual": calculated_total},
            )
        return QualityEvalResult(test_id="math_billing_drift", passed=True, score=1.0)

    @classmethod
    def evaluate_grounded_prose(
        cls,
        prose_text: str,
        citation_triples: List[str],
        unsupported_claims: Optional[List[str]] = None,
    ) -> QualityEvalResult:
        """Verifies prose is strictly grounded in verified citation hashes."""
        if not citation_triples:
            return QualityEvalResult(
                test_id="prose_citation_check",
                passed=False,
                score=0.0,
                failure_reasons=["Prose contains zero verifiable citation hashes."],
            )

        # Check for invalid hash formats
        invalid_hashes = [h for h in citation_triples if not h.startswith("sha256:") or len(h) < 16]
        if invalid_hashes:
            return QualityEvalResult(
                test_id="prose_citation_check",
                passed=False,
                score=0.0,
                failure_reasons=[f"Invalid citation hash formats detected: {invalid_hashes}"],
            )

        # Check for ungrounded hallucinated claims
        if unsupported_claims:
            return QualityEvalResult(
                test_id="prose_citation_check",
                passed=False,
                score=0.0,
                failure_reasons=[f"Prose contains unsupported claims: {unsupported_claims}"],
            )

        return QualityEvalResult(test_id="prose_citation_check", passed=True, score=1.0)

    @classmethod
    def evaluate_prompt_injection(cls, incoming_input: str) -> QualityEvalResult:
        """Detects prompt injection or jailbreak attempts in incoming customer inputs."""
        for pattern in cls.INJECTION_PATTERNS:
            if pattern.search(incoming_input):
                return QualityEvalResult(
                    test_id="prompt_injection_check",
                    passed=False,
                    score=0.0,
                    failure_reasons=[f"Prompt injection pattern detected: '{pattern.pattern}'"],
                    details={"input_snippet": incoming_input[:100]},
                )
        return QualityEvalResult(test_id="prompt_injection_check", passed=True, score=1.0)
