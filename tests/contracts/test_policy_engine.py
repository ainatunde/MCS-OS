"""Tests for services/policy/engine.py (A0-A4 Authority Gates)."""

import pytest
from contracts.actions.envelope import ActionEnvelope, AuthorityClass, canonical_payload_hash
from services.policy.engine import PolicyEngine


@pytest.fixture
def policy_engine():
    return PolicyEngine()


def make_envelope(action_type: str, authority_class: AuthorityClass, payload: dict, citations=None, auth_ref=None, product="cloudstream-vcp"):
    c_hash = canonical_payload_hash(payload)
    return ActionEnvelope(
        action_id="act-test",
        task_id="tsk-test",
        charter_id="chr-test",
        department_id="D02",
        product_slug=product,
        action_type=action_type,
        authority_class=authority_class,
        payload=payload,
        canonical_payload_hash=c_hash,
        idempotency_key="idemp-test",
        evidence_citations=citations or [],
        authorization_ref=auth_ref,
    )


def test_a1_routine_internal_admitted(policy_engine):
    env = make_envelope("crm.lead.upsert.v1", AuthorityClass.A1, {"lead_name": "Test Broadcaster"})
    decision = policy_engine.evaluate(env)
    assert decision.admitted is True
    assert decision.promoted_state == "ready"


def test_a2_evidence_required_rejection(policy_engine):
    # commercial.outreach.send.v1 requires evidence citations
    env = make_envelope("commercial.outreach.send.v1", AuthorityClass.A2, {"recipient": "ceo@broadcaster.com"})
    decision = policy_engine.evaluate(env)
    assert decision.admitted is False
    assert decision.promoted_state == "rejected"
    assert "requires verifiable evidence citations" in decision.reasons[0]


def test_a2_with_evidence_admitted(policy_engine):
    env = make_envelope(
        "commercial.outreach.send.v1",
        AuthorityClass.A2,
        {"recipient": "ceo@broadcaster.com"},
        citations=["ref:tv-insights:channel:101"]
    )
    decision = policy_engine.evaluate(env)
    assert decision.admitted is True
    assert decision.promoted_state == "ready"


def test_a3_without_approval_awaiting(policy_engine):
    env = make_envelope("finance.treasury_transfer.v1", AuthorityClass.A3, {"amount": 5000})
    decision = policy_engine.evaluate(env)
    assert decision.admitted is False
    assert decision.requires_approval is True
    assert decision.promoted_state == "awaiting_approval"


def test_a3_with_valid_approval_admitted(policy_engine):
    payload = {"amount": 5000}
    c_hash = canonical_payload_hash(payload)
    policy_engine.record_approval("appr-123", c_hash)

    env = make_envelope("finance.treasury_transfer.v1", AuthorityClass.A3, payload, auth_ref="appr-123")
    decision = policy_engine.evaluate(env)
    assert decision.admitted is True
    assert decision.promoted_state == "ready"


def test_a4_prohibited_action_hard_rejected(policy_engine):
    env = make_envelope("legal.contract.sign.v1", AuthorityClass.A4, {"contract_id": "c1"})
    decision = policy_engine.evaluate(env)
    assert decision.admitted is False
    assert decision.promoted_state == "rejected"
    assert "strictly prohibited" in decision.reasons[0]


def test_emergency_halt_rejection(policy_engine):
    policy_engine.register_halt("cloudstream-vcp")
    env = make_envelope("crm.lead.upsert.v1", AuthorityClass.A1, {"lead_name": "Test Broadcaster"})
    decision = policy_engine.evaluate(env)
    assert decision.admitted is False
    assert decision.promoted_state == "rejected"
    assert "Emergency halt is active on product" in decision.reasons[0]
