"""Tests for ActionEnvelope and canonical payload hashing."""

import pytest
from contracts.actions.envelope import ActionEnvelope, AuthorityClass, canonical_payload_hash


def test_canonical_payload_hash_deterministic():
    p1 = {"b": 2, "a": 1, "nested": {"y": "yes", "x": "no"}}
    p2 = {"a": 1, "nested": {"x": "no", "y": "yes"}, "b": 2}
    assert canonical_payload_hash(p1) == canonical_payload_hash(p2)


def test_action_envelope_valid_hash():
    payload = {"lead_name": "Broadcaster A", "country": "NG"}
    c_hash = canonical_payload_hash(payload)
    env = ActionEnvelope(
        action_id="act-1",
        task_id="tsk-1",
        charter_id="sales-vcp",
        department_id="D02",
        product_slug="cloudstream-vcp",
        action_type="crm.lead.upsert.v1",
        authority_class=AuthorityClass.A1,
        payload=payload,
        canonical_payload_hash=c_hash,
        idempotency_key="mcs:lead:1",
    )
    assert env.canonical_payload_hash == c_hash


def test_action_envelope_tampered_hash_rejected():
    payload = {"lead_name": "Broadcaster A"}
    with pytest.raises(ValueError, match="canonical_payload_hash mismatch"):
        ActionEnvelope(
            action_id="act-2",
            task_id="tsk-1",
            charter_id="sales-vcp",
            department_id="D02",
            product_slug="cloudstream-vcp",
            action_type="crm.lead.upsert.v1",
            authority_class=AuthorityClass.A1,
            payload=payload,
            canonical_payload_hash="fake-hash-12345",
            idempotency_key="mcs:lead:2",
        )
