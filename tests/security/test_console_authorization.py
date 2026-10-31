"""Security invariants for the existing console; no integration services enabled."""
import json
import os
import time
from cryptography.fernet import Fernet
from sqlalchemy import select
from services.control.store import Store, Base, Identity, Action, Record, digest
from pathlib import Path

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import apps.control_api.main as api
import apps.control_api.security as security
from contracts.actions.envelope import ActionEnvelope, canonical_payload_hash
from services.policy.engine import PolicyEngine


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MCS_OS_ENV", "production")
    monkeypatch.setenv("MCS_CONTROL_API_TOKEN", "fixture-shared-read-token")
    monkeypatch.setenv("MCS_ROLE_BINDINGS", json.dumps({"cfo@example.test": "cfo", "cto@example.test": "cto", "ceo@example.test": "founder_ceo"}))
    monkeypatch.setenv("MCS_CORS_ORIGINS", "https://command.example.test")
    monkeypatch.setenv("MCS_SESSION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    st = Store(os.getenv("MCS_TEST_DATABASE_URL", "postgresql+psycopg://postgres:integration-local-fixture@127.0.0.1:55439/os_control_test"))
    Base.metadata.drop_all(st.engine)
    st.migrate()
    with st.transaction() as db:
        for email,role in security.bindings().items():
            db.add(Identity(identity_id="operator:"+email,kind="operator",role=role,scopes={}))
    async def resolve(sid):
        if sid == "revoked":
            raise HTTPException(401, "Session revoked")
        roles = {"cfo-session": ("cfo@example.test", "cfo"), "cto-session": ("cto@example.test", "cto"), "ceo-session": ("ceo@example.test", "founder_ceo")}
        if sid not in roles:
            raise HTTPException(401, "Invalid session")
        return roles[sid]
    monkeypatch.setattr(security, "resolve_session", resolve)
    with TestClient(api.create_app(st)) as c:
        yield c
    st.engine.dispose()


def actor(client, sid):
    client.cookies.set(security.COOKIE, sid)
    return {"Origin": "https://command.example.test"}


def pending(client, department="D05"):
    payload = {"fixture": True}
    env = {"product_slug":"tv-insights","department_id":department,"action_type":"finance.invoice.create_draft.v1","payload":payload,"canonical_payload_hash":digest(payload)}
    with client.app.state.store.transaction() as db:
        db.add(Action(action_id="security-fixture",idempotency_key="security-fixture",product_slug="tv-insights",department_id=department,provider="mcs-erp",envelope=env,input_hash=digest(env),effective_authority="A3",status="awaiting_approval"))


def action(client):
    with client.app.state.store.transaction() as db:
        return db.get(Action,"security-fixture")


def test_service_token_cannot_assume_executive_or_write(client):
    headers = {"Authorization": "Bearer fixture-shared-read-token", "X-MCS-Actor": "founder_ceo"}
    assert client.get("/v1/products", headers=headers).status_code in {200, 401, 403}
    for path, body in [("/v1/halts", {"scope": "company_wide", "reason": "Fixture probe"}), ("/v1/approvals/missing/decide", {"decision": "approve_and_send", "actor": "founder_ceo"}), ("/v1/directives", {"target_role": "cto", "title": "Fixture", "instructions": "Fixture only"})]:
        assert client.post(path, headers=headers, json=body).status_code == 403


def test_body_and_header_cannot_substitute_identity(client):
    pending(client)
    headers = actor(client, "cfo-session")
    response = client.post("/v1/approvals/security-fixture/decide", headers={**headers, "X-MCS-Actor": "founder_ceo"}, json={"decision": "approve_and_send", "actor": "founder_ceo"})
    assert response.status_code == 403
    assert action(client).status == "awaiting_approval"


def test_authenticated_cfo_cannot_approve_cto_department(client):
    pending(client)
    assert client.post("/v1/approvals/security-fixture/decide", headers=actor(client, "cfo-session"), json={"decision": "approve_and_send"}).status_code == 403


def test_authenticated_cfo_can_approve_own_department(client):
    pending(client, "D06")
    response = client.post("/v1/approvals/security-fixture/decide", headers=actor(client, "cfo-session"), json={"decision": "approve_content"})
    assert response.status_code == 200
    assert response.json()["action_status"] == "content_approved"
    assert action(client).status == "content_approved"


def test_rejected_action_cannot_be_approved(client):
    pending(client)
    with client.app.state.store.transaction() as db:
        db.get(Action,"security-fixture").status = "rejected"
    response = client.post("/v1/approvals/security-fixture/decide", headers=actor(client, "ceo-session"), json={"decision": "approve_and_send"})
    assert response.status_code == 409


def test_changed_payload_cannot_reuse_existing_approval(client):
    pending(client, "D06")
    with client.app.state.store.transaction() as db:
        row=db.get(Action,"security-fixture")
        row.envelope={**row.envelope,"payload":{"fixture":"changed"}}
    assert client.post("/v1/approvals/security-fixture/decide", headers=actor(client, "cfo-session"), json={"decision": "approve_and_send"}).status_code == 409


def test_revoked_session_and_untrusted_origin_fail_closed(client):
    assert client.get("/v1/session", headers=actor(client, "revoked")).status_code == 401
    actor(client, "ceo-session")
    assert client.post("/v1/halts", headers={"Origin": "https://untrusted.example"}, json={"scope": "company_wide", "reason": "Fixture"}).status_code == 403
    with client.app.state.store.transaction() as db:
        assert not db.scalars(select(Record).where(Record.namespace=="halt")).all()


def test_wrong_department_cannot_propose_action(client):
    payload = {"customer": "Fixture"}
    env = ActionEnvelope(action_id="fixture-proposal", task_id="fixture", charter_id="fixture", department_id="D05", product_slug="corporate", action_type="engineering.production_deploy.v1", authority_class="A3", payload=payload, canonical_payload_hash=canonical_payload_hash(payload), idempotency_key="fixture-proposal")
    assert client.post("/v1/action-intents", headers=actor(client, "cfo-session"), json=env.model_dump(mode="json")).status_code == 403
    with client.app.state.store.transaction() as db:
        assert not db.scalars(select(Action)).all()


def test_directive_and_company_halt_scope(client):
    headers = actor(client, "cfo-session")
    assert client.post("/v1/directives", headers=headers, json={"target_role": "all", "title": "Fixture", "instructions": "Fixture directive"}).status_code == 403
    assert client.delete("/v1/halts/company_wide", headers=headers).status_code == 403


def test_no_console_credentials_in_source_or_team_api(client):
    source = Path("apps/command-centre/src/app/page.tsx").read_text(encoding="utf-8")
    assert "password_hint" not in source and "Copy Pwd" not in source
    response = client.get("/v1/team", headers=actor(client, "ceo-session"))
    assert response.status_code == 404  # no credential-bearing team directory is exposed


@pytest.mark.asyncio
async def test_erp_identity_is_revalidated_on_each_request(monkeypatch):
    monkeypatch.setenv("ERPNEXT_URL", "https://erp.example.test")
    monkeypatch.setenv("MCS_ROLE_BINDINGS", '{"cfo@example.test":"cfo"}')
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"message": "cfo@example.test" if len(calls) == 1 else "Guest"})
    real_client = httpx.AsyncClient
    monkeypatch.setattr(security.httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    assert (await security.resolve_session("opaque-fixture"))[1] == "cfo"
    with pytest.raises(HTTPException) as refused:
        await security.resolve_session("opaque-fixture")
    assert refused.value.status_code == 401 and len(calls) == 2
