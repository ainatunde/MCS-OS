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


def test_approve_content_does_not_release_queue(client):
    payload = {"beneficiary": "Content Studio", "amount_usd": 5000.0}
    env = ActionEnvelope(
        action_id="act-a3-content-only",
        task_id="tsk-cmo-002",
        charter_id="chr-d03-cmo",
        department_id="D06",
        product_slug="corporate",
        action_type="finance.treasury_transfer.v1",
        authority_class=AuthorityClass.A3,
        payload=payload,
        canonical_payload_hash=canonical_payload_hash(payload),
        idempotency_key="idem-a3-content-only",
    )
    client.post("/v1/action-intents", json=env.model_dump(mode="json"))

    decide_resp = client.post(
        "/v1/approvals/act-a3-content-only/decide",
        json={"decision": "approve_content", "actor": "founder_ceo"},
    )
    assert decide_resp.status_code == 200
    assert decide_resp.json()["status"] == "content_approved"
    assert decide_resp.json()["action_status"] == "content_approved"


def test_production_auth_and_rbac_enforced(client, monkeypatch):
    monkeypatch.setenv("MCS_OS_AUTH_REQUIRED", "1")
    monkeypatch.setenv("MCS_CONTROL_API_TOKEN", "secret-control-token")
    assert client.get("/v1/products").status_code == 401
    headers = {"Authorization": "Bearer secret-control-token", "X-MCS-Actor": "founder_ceo"}
    assert client.get("/v1/products", headers=headers).status_code == 200
    assert client.post("/v1/halts", json={"scope": "aether-ads", "reason": "Fixture"}, headers=headers).status_code == 403


def test_directives_flow(client):
    # 1. List initial directives
    list_resp = client.get("/v1/directives")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["count"] >= 2
    assert any(d["target_role"] == "cto" for d in data["directives"])

    # 2. Issue a new directive
    new_dir_payload = {
        "target_role": "cfo",
        "directive_type": "policy_update",
        "priority": "critical",
        "title": "Cloud Infrastructure Spend Audit & Reserve Reallocation",
        "instructions": "Audit monthly compute bills across Contabo and GCP. Ensure reserves reconcile with ERPNext ledger.",
        "deliverables": "Audited variance spreadsheet and GL reconciliation journal entry.",
        "deadline": "2026-10-30",
        "sync_erp_task": True,
    }
    create_resp = client.post(
        "/v1/directives",
        json=new_dir_payload,
        headers={"X-MCS-Actor": "founder_ceo"},
    )
    assert create_resp.status_code == 201
    created_dir = create_resp.json()
    assert created_dir["target_role"] == "cfo"
    assert created_dir["status"] == "issued"
    assert created_dir["erp_task_id"] is not None
    dir_id = created_dir["directive_id"]

    # 3. Filter by target_role
    filtered = client.get("/v1/directives?target_role=cfo")
    assert filtered.status_code == 200
    assert any(d["directive_id"] == dir_id for d in filtered.json()["directives"])

    # 4. Acknowledge directive
    ack_resp = client.post(
        f"/v1/directives/{dir_id}/status",
        json={"status": "acknowledged", "actor": "cfo@mcsolutions.stream"},
        headers={"X-MCS-Actor": "cfo"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "acknowledged"
    assert ack_resp.json()["acknowledged_by"] == "founder_ceo"

    # 5. Complete directive
    comp_resp = client.post(
        f"/v1/directives/{dir_id}/status",
        json={"status": "completed"},
        headers={"X-MCS-Actor": "founder_ceo"},
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == "completed"

