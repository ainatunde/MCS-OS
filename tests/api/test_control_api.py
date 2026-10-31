"""Control API authority, durable replay and recovery invariants.

Uses actual PostgreSQL; no passing mock is labelled live provider acceptance.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from apps.control_api.main import create_app
from contracts.actions.envelope import ActionEnvelope, canonical_payload_hash
from services.control.guardian import inspect, observe_dependencies
from services.control.security import signed_headers
from services.control.store import Action, Base, Event, Identity, Record, Store, digest, token_hash
from services.control.worker import IntegrationWorker


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("MCS_OS_ENV", "development")
    monkeypatch.setenv("MCS_PULZZ_SIGNING_SECRET", "fixture-signing-secret-32-characters-minimum")
    url = os.getenv("MCS_TEST_DATABASE_URL", "postgresql+psycopg://postgres:integration-local-fixture@127.0.0.1:55439/os_control_test")
    if not url.rsplit("/",1)[-1].endswith("_test"):
        raise RuntimeError("Tests require a dedicated _test database")
    st = Store(url)
    Base.metadata.drop_all(st.engine)
    st.migrate()
    with st.transaction() as s:
        for role in ["founder_ceo", "cfo", "cto", "coo", "commercial"]:
            s.add(Identity(identity_id="operator:"+role, kind="operator", role=role, token_hash=token_hash("fixture-"+role), scopes={}))
        s.add(Identity(identity_id="service:tv-insights", kind="service", role="producer", token_hash=token_hash("fixture-service-token-32-characters-minimum"), scopes={"producer":"tv-insights","product_slug":"tv-insights","read_health":True}, secret_env="MCS_PULZZ_SIGNING_SECRET", secret_hash=token_hash(os.environ["MCS_PULZZ_SIGNING_SECRET"])))
    yield st
    st.engine.dispose()


def headers(role="founder_ceo"):
    return {"Authorization":"Bearer fixture-"+role}


def event():
    return {"event_id":"fixture-event-001","producer":"tv-insights","event_type":"commercial.plan.requested.v1","product_slug":"tv-insights","schema_version":"v1","occurred_at":datetime.now(timezone.utc).isoformat(),"payload":{"source_kind":"plan_request","source_id":1,"source_revision":"fixture-source-revision"}}


def signed(body):
    return signed_headers("fixture-service-token-32-characters-minimum",os.environ["MCS_PULZZ_SIGNING_SECRET"],body)


def envelope(kind="engineering.production_deploy.v1", department="D05", action_id="fixture-action", payload=None):
    payload=payload or {"artifact":"fixture"}
    return ActionEnvelope(action_id=action_id,task_id="fixture-task",charter_id="fixture-charter",department_id=department,product_slug="tv-insights",action_type=kind,authority_class="A3",payload=payload,canonical_payload_hash=canonical_payload_hash(payload),idempotency_key=action_id).model_dump(mode="json")


def test_health_and_no_anonymous_control_reads(store):
    with TestClient(create_app(store)) as client:
        assert client.get("/healthz").status_code==200
        for path in ["/v1/products","/v1/actions","/v1/directives","/v1/halts"]:
            assert client.get(path).status_code==401


def test_caller_cannot_replace_role_to_approve(store):
    with TestClient(create_app(store)) as c:
        assert c.post("/v1/action-intents",json=envelope(),headers=headers("cto")).json()["status"]=="awaiting_approval"
        attempted=c.post("/v1/approvals/fixture-action/decide",json={"decision":"approve_and_send","actor":"founder_ceo"},headers={**headers("cfo"),"X-MCS-Actor":"founder_ceo"})
        assert attempted.status_code==403
        assert c.get("/v1/actions/fixture-action",headers=headers()).json()["status"]=="awaiting_approval"


def test_rejected_action_cannot_be_approved(store):
    with TestClient(create_app(store)) as c:
        body=envelope("security.override_policy.v1","D11")
        assert c.post("/v1/action-intents",json=body,headers=headers()).json()["status"]=="rejected"
        assert c.post("/v1/approvals/fixture-action/decide",json={"decision":"approve_and_send"},headers=headers()).status_code in {403,409}


def test_revoke_parent_identity_blocks_existing_session(store):
    with store.transaction() as s:
        s.add(Identity(identity_id="session:test",kind="session",role="cfo",parent_id="operator:cfo",token_hash=token_hash("fixture-session"),expires_at=time.time()+300,scopes={}))
    with TestClient(create_app(store)) as c:
        assert c.get("/v1/session",headers={"Authorization":"Bearer fixture-session"}).status_code==200
        with store.transaction() as s:s.get(Identity,"operator:cfo").enabled=False
        assert c.get("/v1/session",headers={"Authorization":"Bearer fixture-session"}).status_code==401


def test_signature_binds_full_envelope_and_scope(store):
    body=event(); sig=signed(body)
    with TestClient(create_app(store)) as c:
        assert c.post("/v1/events",json={**body,"event_type":"changed.v1"},headers=sig).status_code==401
        assert c.post("/v1/events",json={**body,"product_slug":"corporate"},headers=signed({**body,"product_slug":"corporate"})).status_code==403
        assert c.post("/v1/events",json=body,headers=sig).status_code==201


def test_restart_keeps_replay_dedupe_and_content_conflict(store):
    body=event()
    with TestClient(create_app(store)) as c: assert c.post("/v1/events",json=body,headers=signed(body)).json()["is_duplicate"] is False
    other=Store(str(store.engine.url).replace("***","integration-local-fixture"))
    try:
        with TestClient(create_app(other)) as c:
            assert c.post("/v1/events",json=body,headers=signed(body)).json()["is_duplicate"] is True
            changed={**body,"payload":{"changed":True}}
            assert c.post("/v1/events",json=changed,headers=signed(changed)).status_code==409
    finally:other.engine.dispose()


def test_concurrent_event_delivery_creates_one_inbox_row(store):
    body=event()
    def send(_):
        with TestClient(create_app(store)) as c:return c.post("/v1/events",json=body,headers=signed(body)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert list(pool.map(send,range(2)))==[201,201]
    with store.transaction() as s:assert len(s.scalars(select(Event)).all())==1


def test_action_revision_and_content_approval_do_not_release(store):
    with TestClient(create_app(store)) as c:
        body=envelope();c.post("/v1/action-intents",json=body,headers=headers())
        assert c.post("/v1/approvals/fixture-action/decide",json={"decision":"approve_content"},headers=headers()).json()["action_status"]=="content_approved"
        changed=envelope(payload={"artifact":"different"})
        assert c.post("/v1/action-intents",json=changed,headers=headers()).status_code==409


def test_halt_and_directive_persist_without_fabricated_erp_task(store):
    with TestClient(create_app(store)) as c:
        assert c.post("/v1/halts",json={"scope":"tv-insights","reason":"fixture halt"},headers=headers("cto")).status_code==201
        directive=c.post("/v1/directives",json={"target_role":"cfo","title":"Fixture work","instructions":"Inspect the fixture records"},headers=headers()).json()
        assert "erp_task_id" not in directive
    with TestClient(create_app(store)) as c:
        assert c.get("/v1/halts",headers=headers()).json()["active_halts"]==["tv-insights"]
        assert len(c.get("/v1/directives",headers=headers()).json()["directives"])==1
        assert c.delete("/v1/halts/tv-insights",headers=headers("cfo")).status_code==403


def seed_action(store, **kwargs):
    data={"action_id":"recovery","idempotency_key":"recovery-key","product_slug":"tv-insights","department_id":"D06","provider":"mcs-erp","envelope":{"action_type":"finance.invoice.create_draft.v1","payload":{}},"input_hash":digest({}),"status":"outcome_unknown","reconcile_only":True,"unknown_since":time.time()-600}
    data.update(kwargs)
    with store.transaction() as s:s.add(Action(**data))


def test_reconciliation_claim_survives_another_crash(store):
    seed_action(store)
    worker=IntegrationWorker(store,httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(500))))
    first=worker.claim();assert first[2] is True
    with store.transaction() as s:s.get(Action,"recovery").lease_until=time.time()-1
    assert worker.claim()[2] is True
    assert inspect(store)["checks"]["integration_unknown_outcomes"] is False


def test_unknown_outcome_alert_age_not_reset_by_retries(store):
    seed_action(store,updated_at=time.time())
    assert inspect(store)["checks"]["integration_unknown_outcomes"] is False


def test_receipt_retries_preserve_exact_body(store,monkeypatch):
    monkeypatch.setenv("PULZZ_URL","http://fixture-product")
    monkeypatch.setenv("MCS_PULZZ_RECEIPT_TOKEN","fixture-receipt-token-32-characters-minimum")
    payload={"source_kind":"plan_request","source_id":1,"source_revision":"r1","amount_minor":10000,"currency":"NGN"}
    with store.transaction() as s:s.add(Event(producer="tv-insights",event_id="callback-event",event_type="commercial.plan.requested.v1",product_slug="tv-insights",content_hash=digest(payload),envelope={"payload":payload}))
    seed_action(store,status="confirmed",event_id="callback-event",callback_state="pending",reconcile_only=False,receipt={"provider_reference":"INV-FIXTURE","document_state":"draft"})
    bodies=[]
    def lost_response(req):
        import json
        bodies.append(json.loads(req.content))
        raise httpx.ReadTimeout("Fixture lost response")
    worker=IntegrationWorker(store,httpx.Client(transport=httpx.MockTransport(lost_response)))
    worker.deliver_one()
    with store.transaction() as s:s.get(Action,"recovery").next_attempt=0
    worker.deliver_one()
    assert len(bodies)==2 and bodies[0]==bodies[1]


def test_guardian_read_probe_does_not_hide_stopped_daemon(store):
    with store.transaction() as s:
        store.put(s,"heartbeat","integration-worker",{"at":time.time()})
    assert inspect(store,repair=False)["checks"]["integration_guardian_heartbeat"] is False
    with store.transaction() as s:
        assert s.get(Record,("heartbeat","integration-guardian")) is None
    inspect(store)
    assert inspect(store,repair=False)["checks"]["integration_guardian_heartbeat"] is True


def test_health_rejects_missing_schema_marker(store):
    with store.transaction() as s:
        s.delete(s.get(Record,("schema","version")))
    with TestClient(create_app(store)) as c:
        assert c.get("/healthz").status_code==503


def test_crm_and_sponsorship_route_to_erp_with_product_scope(store):
    worker=IntegrationWorker(store,httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(500))))
    for kind in ("lead","sponsorship"):
        p={"source_kind":kind,"source_id":1,"source_revision":"r1","external_ref":"tvinsights:"+kind+":1",
           "eligible_for_draft":True,"customer_ref":"tvinsights:sponsor:1","customer":{"name":"Àdé","organisation":"Fixture"},
           "amount_minor":12345,"currency":"NGN","consent_version":"1","consented_at":"2026-10-31T00:00:00+00:00"}
        with store.transaction() as s:
            s.add(Event(producer="tv-insights",event_id=kind,event_type="crm.lead.inquiry.v1" if kind=="lead" else "commercial.order.requested.v1",product_slug="tv-insights",content_hash=digest(p),envelope={"payload":p}))
        assert worker.route_one()
    with store.transaction() as s:
        rows=s.scalars(select(Action)).all()
        assert len(rows)==3 and all(r.provider=="mcs-erp" and r.product_slug=="tv-insights" for r in rows)
        invoice=next(r for r in rows if r.dependency_id)
        assert invoice.envelope["payload"]["items"][0]["item_code"]=="TV-Insights Sponsorship"


def test_withdrawal_cancels_unsent_crm_and_erases_copied_contact(store):
    p={"source_kind":"lead","source_id":1,"source_revision":"r1","external_ref":"tvinsights:lead:1","eligible_for_draft":True,
       "customer":{"name":"Private contact","email":"private@example.invalid"},"consent_version":"1","consented_at":"2026-10-31T00:00:00Z"}
    with store.transaction() as s:
        s.add(Event(producer="tv-insights",event_id="lead-create",event_type="crm.lead.inquiry.v1",product_slug="tv-insights",content_hash=digest(p),envelope={"payload":p}))
    worker=IntegrationWorker(store,httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(500))))
    worker.route_one()
    withdrawal={"source_kind":"lead","source_id":1,"source_revision":"r2","external_ref":"tvinsights:lead:1","eligible_for_draft":False}
    with store.transaction() as s:
        s.add(Event(producer="tv-insights",event_id="withdrawal",event_type="commercial.source.withdrawn.v1",product_slug="tv-insights",content_hash=digest(withdrawal),envelope={"payload":withdrawal}))
    worker.route_one()
    with store.transaction() as s:
        row=s.scalar(select(Action))
        assert row.status=="cancelled" and "private@example.invalid" not in str(row.envelope)
        assert "private@example.invalid" not in str(s.get(Event,("tv-insights","lead-create")).envelope)


def test_unchanged_document_sends_periodic_freshness_receipt(store,monkeypatch):
    seed_action(store,status="confirmed",callback_state="delivered",reconcile_only=False,updated_at=time.time()-400,
                receipt={"provider_reference":"INV-FIXTURE","document_state":"draft","amount_minor":10000,"currency":"NGN"})
    worker=IntegrationWorker(store,object())
    monkeypatch.setattr(worker,"_gateway",lambda **kwargs:{"operation_outcome":"applied","provider_reference":"INV-FIXTURE","document_state":"draft","amount_minor":10000,"currency":"NGN"})
    assert worker.refresh_one()
    with store.transaction() as s:
        row=s.get(Action,"recovery")
        assert row.callback_state=="pending" and row.document_sequence==1


def test_guardian_detects_idle_dependency_outage_and_rechecks_recovery(store,monkeypatch):
    monkeypatch.setenv("MCS_OS_ENV","production")
    monkeypatch.setenv("MCS_ERP_GATEWAY_URL","http://qa-erp")
    monkeypatch.setenv("MCS_ERP_GATEWAY_TOKEN","fixture-gateway-token-32-characters-minimum")
    monkeypatch.setenv("PULZZ_URL","http://qa-product")
    monkeypatch.setenv("MCS_PULZZ_RECEIPT_TOKEN","fixture-receipt-token-32-characters-minimum")
    failed=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(503)))
    observe_dependencies(store,failed)
    checks=inspect(store)["checks"]
    assert not checks["erp_authenticated_connectivity"] and not checks["pulzz_authenticated_connectivity"]
    healthy=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={"status":"healthy"})))
    observe_dependencies(store,healthy)
    assert inspect(store)["checks"]["erp_authenticated_connectivity"]
    with store.transaction() as s:
        assert s.get(Record,("incident","erp_authenticated_connectivity")).body["status"]=="resolved"


def test_financial_projection_mismatch_is_unhealthy_until_verified_recovery(store,monkeypatch):
    seed_action(store,status="confirmed",callback_state="delivered",reconcile_only=False,
        receipt={"provider_reference":"INV-QA","document_state":"draft","amount_minor":10000,"currency":"NGN"})
    worker=IntegrationWorker(store,object())
    monkeypatch.setattr(worker,"_gateway",lambda **kwargs:{"operation_outcome":"applied","provider_reference":"INV-QA","document_state":"draft","amount_minor":10001,"currency":"NGN"})
    assert worker.refresh_one()
    assert not inspect(store)["checks"]["integration_reconciliation_integrity"]
    with store.transaction() as s:s.get(Action,"recovery").next_attempt=0
    monkeypatch.setattr(worker,"_gateway",lambda **kwargs:{"operation_outcome":"applied","provider_reference":"INV-QA","document_state":"draft","amount_minor":10000,"currency":"NGN"})
    assert worker.refresh_one()
    assert inspect(store)["checks"]["integration_reconciliation_integrity"]


def test_cancelled_claim_cannot_dispatch_after_a_stale_source_read(store,monkeypatch):
    monkeypatch.setenv("PULZZ_URL","http://qa-product")
    monkeypatch.setenv("MCS_PULZZ_RECEIPT_TOKEN","fixture-receipt-token-32-characters-minimum")
    p={"source_kind":"lead","source_id":1,"source_revision":"r1","external_ref":"tvinsights:lead:1","eligible_for_draft":True,
       "customer":{"name":"QA contact"},"consent_version":"1","consented_at":"2026-10-31T00:00:00Z"}
    with store.transaction() as s:
        s.add(Event(producer="tv-insights",event_id="race",event_type="crm.lead.inquiry.v1",product_slug="tv-insights",content_hash=digest(p),envelope={"payload":p}))
    calls=[]
    def stale_read(request):
        with store.transaction() as s:
            row=s.scalar(select(Action)); row.status="cancelled"; row.fence+=1; row.lease_owner=None
        return httpx.Response(200,json={"payload":p})
    worker=IntegrationWorker(store,httpx.Client(transport=httpx.MockTransport(stale_read)))
    monkeypatch.setattr(worker,"_gateway",lambda **kwargs:calls.append(kwargs))
    assert worker.route_one() and worker.execute_one()
    assert calls==[]
    with store.transaction() as s:assert s.scalar(select(Action)).status=="cancelled"
