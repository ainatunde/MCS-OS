"""Tests for Central Control API Gateway (MCS-OS v2.2 W09)."""

import pytest
from fastapi.testclient import TestClient
from apps.control_api.main import app
from contracts.actions.envelope import ActionEnvelope, AuthorityClass, canonical_payload_hash


@pytest.fixture
def client():
    return TestClient(app)


def test_healthz_endpoint(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "mcs-control-api"


def test_list_products_endpoint(client):
    response = client.get("/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 8
    slugs = [p["product_slug"] for p in data["products"]]
    assert "cloudstream-vcp" in slugs
    assert "cloudstream-forge" in slugs
    assert "aether-ads" in slugs
    assert "aether-adx" in slugs
    assert "tv-insights" in slugs
    assert "africasignal" in slugs
    assert "mcs-app-factory" in slugs
    assert "mcs-erp" in slugs


def test_submit_and_deduplicate_event(client):
    req_payload = {
        "event_id": "evt-test-api-001",
        "producer": "tv-insights",
        "event_type": "source.feed.updated.v1",
        "product_slug": "tv-insights",
        "payload": {"schedule_count": 1420},
    }
    # First submission
    resp1 = client.post("/v1/events", json=req_payload)
    assert resp1.status_code == 201
    assert resp1.json()["is_duplicate"] is False

    # Second submission (duplicate)
    resp2 = client.post("/v1/events", json=req_payload)
    assert resp2.status_code == 201
    assert resp2.json()["is_duplicate"] is True


def test_action_intent_and_approval_flow(client):
    # Action requiring A3 approval
    payload = {"beneficiary": "Acme Media", "amount_usd": 25000.0}
    env = ActionEnvelope(
        action_id="act-a3-treasury-001",
        task_id="tsk-cfo-001",
        charter_id="chr-d06-cfo",
        department_id="D06",
        product_slug="corporate",
        action_type="finance.treasury_transfer.v1",
        authority_class=AuthorityClass.A3,
        payload=payload,
        canonical_payload_hash=canonical_payload_hash(payload),
        idempotency_key="idem-a3-treasury-001",
    )

    resp = client.post("/v1/action-intents", json=env.model_dump(mode="json"))
    assert resp.status_code == 201
    data = resp.json()
    assert data["policy_decision"]["requires_approval"] is True
    assert data["status"] == "awaiting_approval"

    # Verify listed in approvals
    appr_resp = client.get("/v1/approvals")
    assert appr_resp.status_code == 200
    approvals = appr_resp.json()["approvals"]
    assert any(a["action_id"] == "act-a3-treasury-001" for a in approvals)

    # Decide approval
    decide_resp = client.post(
        "/v1/approvals/act-a3-treasury-001/decide",
        json={"decision": "approve_and_send", "actor": "founder_ceo"},
    )
    assert decide_resp.status_code == 200
    assert decide_resp.json()["status"] == "granted"


def test_emergency_halt_registration_and_lifting(client):
    # Register halt
    halt_req = {"scope": "aether-ads", "reason": "Dynamic floor variance spike"}
    resp1 = client.post("/v1/halts", json=halt_req)
    assert resp1.status_code == 201
    assert "aether-ads" in resp1.json()["active_halts"]

    # List halts
    list_resp = client.get("/v1/halts")
    assert "aether-ads" in list_resp.json()["active_halts"]

    # Lift halt
    del_resp = client.delete("/v1/halts/aether-ads")
    assert del_resp.status_code == 200
    assert "aether-ads" not in del_resp.json()["active_halts"]


def test_get_briefings(client):
    resp = client.get("/v1/briefings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] > 0
    assert "07:30 WAT" in data["briefings"][0]["scheduled_time"]
