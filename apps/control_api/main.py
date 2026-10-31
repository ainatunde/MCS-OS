"""Authenticated, durable corporate control API. No demonstration state in production."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
import secrets
import time
import uuid

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from contracts.actions.envelope import ActionEnvelope
from services.control.security import DEPARTMENTS, Principal, authenticate, operator, service_event
from services.control.store import Action, Event, Identity, Record, Store, canonical, configured_store, digest, token_hash
from services.policy.engine import PolicyEngine


class Login(BaseModel):
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class EventSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=3, max_length=128)
    producer: str = Field(min_length=2, max_length=64)
    event_type: str = Field(min_length=3, max_length=128)
    product_slug: str
    schema_version: str = "v1"
    occurred_at: str
    payload: dict


class ApprovalDecision(BaseModel):
    decision: str
    actor: str | None = None  # compatibility only; never an authorization source
    rationale: str = Field(default="", max_length=2048)


class HaltRequest(BaseModel):
    scope: str = Field(min_length=2, max_length=64)
    reason: str = Field(min_length=3, max_length=512)


class DirectiveRequest(BaseModel):
    target_role: str
    directive_type: str = "immediate_action"
    priority: str = "routine"
    title: str = Field(min_length=3, max_length=256)
    instructions: str = Field(min_length=5, max_length=4096)
    deliverables: str | None = None
    deadline: str | None = None
    sync_erp_task: bool = False


def create_app(store: Store | None = None):
    @asynccontextmanager
    async def lifespan(app):
        if not hasattr(app.state, "store"):
            app.state.store = configured_store()
        yield

    app = FastAPI(title="MCS-OS Corporate Control API", version="2.3.0", lifespan=lifespan)
    if store is not None:
        app.state.store = store
    origins = [o.strip() for o in os.getenv("MCS_CORS_ORIGINS", "https://command.mcsolutions.stream,https://os.mcsolutions.stream").split(",") if o.strip()]
    app.state.origins = origins
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type", "X-MCS-Timestamp", "X-MCS-Signature"])

    @app.get("/healthz")
    def health(request: Request):
        try:
            with request.app.state.store.transaction() as s:
                marker = s.get(Record, ("schema", "version"))
                if not marker or marker.body.get("version") != 1:
                    raise RuntimeError("Control schema migration required")
            return {"status": "healthy", "service": "mcs-control-api", "version": "2.3.0", "commit": os.getenv("SOURCE_COMMIT", os.getenv("BUILD_SHA", "unknown")), "security_release": "console-auth-v1"}
        except Exception:
            return JSONResponse({"status": "unhealthy", "service": "mcs-control-api"}, status_code=503)

    from apps.control_api.security import register_sessions
    register_sessions(app)

    @app.get("/v1/products")
    async def products(request: Request, principal: Principal = Depends(authenticate)):
        if principal.kind != "read_only":
            operator(principal)
        targets = [("tv-insights", os.getenv("PULZZ_URL", "").rstrip("/") + "/ready"), ("mcs-erp", os.getenv("MCS_ERP_GATEWAY_URL", "").rstrip("/") + "/healthz")]
        results = []
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            for slug, url in targets:
                status, detail = "unconfigured", "Endpoint not configured"
                if url.startswith(("https://", "http://")):
                    try:
                        headers = {"Authorization": "Bearer " + os.getenv("MCS_ERP_GATEWAY_TOKEN", "")} if slug == "mcs-erp" else {}
                        r = await client.get(url, headers=headers)
                        status = "healthy" if r.status_code == 200 else "degraded"
                        detail = "HTTP " + str(r.status_code)
                    except httpx.HTTPError:
                        status, detail = "down", "Connection unavailable"
                results.append({"product_slug": slug, "health": {"status": status, "details": {"observation": detail}, "observed_at": time.time()}})
        return {"count": len(results), "products": results}

    @app.post("/v1/events", status_code=201)
    def events(req: EventSubmission, request: Request, principal: Principal = Depends(authenticate)):
        body = req.model_dump()
        service_event(request, principal, body)
        if req.schema_version != "v1":
            raise HTTPException(422, "Unsupported event schema")
        try:
            when = datetime.fromisoformat(req.occurred_at.replace("Z", "+00:00"))
            if when.tzinfo is None or when.timestamp() > time.time() + 300:
                raise ValueError()
        except ValueError:
            raise HTTPException(422, "Timezone-aware source occurrence time required") from None
        content_hash = digest(body)
        st = request.app.state.store
        try:
            with st.transaction() as s:
                existing = s.get(Event, (req.producer, req.event_id))
                if existing:
                    if existing.content_hash != content_hash:
                        raise HTTPException(409, "Event key reused with different content")
                    return {"status": "accepted", "event_id": req.event_id, "is_duplicate": True}
                s.add(Event(producer=req.producer, event_id=req.event_id, event_type=req.event_type, product_slug=req.product_slug, content_hash=content_hash, envelope=body))
                st.audit(s, principal.identity_id, "event.accepted", req.event_id, {"content_hash": content_hash})
        except IntegrityError:
            with st.transaction() as s:
                row = s.get(Event, (req.producer, req.event_id))
                if not row or row.content_hash != content_hash:
                    raise HTTPException(409, "Concurrent event content conflict") from None
            return {"status": "accepted", "event_id": req.event_id, "is_duplicate": True}
        return {"status": "accepted", "event_id": req.event_id, "is_duplicate": False}

    @app.post("/v1/action-intents", status_code=201)
    def propose(envelope: ActionEnvelope, request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        if not principal.department(envelope.department_id):
            raise HTTPException(403, "Department outside authenticated mandate")
        st = request.app.state.store
        raw = envelope.model_dump(mode="json")
        # Execution target is independent of the business product attribution.
        provider = "mcs-erp" if envelope.action_type.startswith(("crm.", "finance.", "support.issue.", "procurement.")) else "tv-insights"
        with st.transaction() as s:
            engine = PolicyEngine()
            for halt in s.scalars(select(Record).where(Record.namespace == "halt")):
                engine.register_halt(halt.record_id)
            decision = engine.evaluate(envelope)
            # This API cannot import caller-supplied authorization references.
            if decision.requires_approval and decision.promoted_state != "rejected":
                state = "awaiting_approval"
            else:
                state = decision.promoted_state
            existing = s.get(Action, envelope.action_id)
            if existing:
                if existing.input_hash != digest(raw):
                    raise HTTPException(409, "Action revision requires a new immutable action ID")
                return st.public_action(existing)
            row = Action(action_id=envelope.action_id, idempotency_key=envelope.idempotency_key, product_slug=envelope.product_slug, department_id=envelope.department_id, provider=provider, effective_authority=decision.assigned_authority.value, envelope=raw, input_hash=digest(raw), status=state)
            s.add(row)
            s.flush()
            st.audit(s, principal.identity_id, "action.proposed", row.action_id)
            return {**st.public_action(row), "policy_decision": {"admitted": decision.admitted, "requires_approval": state == "awaiting_approval", "reasons": decision.reasons}}

    @app.get("/v1/actions")
    def actions(request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        with request.app.state.store.transaction() as s:
            rows = s.scalars(select(Action).order_by(Action.created_at.desc()).limit(200)).all()
            return {"actions": [Store.public_action(r) for r in rows if principal.department(r.department_id)]}

    @app.get("/v1/actions/{action_id}")
    def action(action_id: str, request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        with request.app.state.store.transaction() as s:
            row = s.get(Action, action_id)
            if not row or not principal.department(row.department_id):
                raise HTTPException(404, "Action not found")
            return Store.public_action(row)

    @app.get("/v1/approvals")
    def approvals(request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        with request.app.state.store.transaction() as s:
            rows = s.scalars(select(Action).where(Action.status.in_(["awaiting_approval", "content_approved"]))).all()
            return {"approvals": [Store.public_action(r) for r in rows if principal.department(r.department_id)]}

    @app.post("/v1/approvals/{action_id}/decide")
    def decide(action_id: str, req: ApprovalDecision, request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        if req.actor and req.actor != principal.role:
            raise HTTPException(403, "Request actor cannot replace authenticated identity")
        st = request.app.state.store
        with st.transaction() as s:
            row = s.get(Action, action_id, with_for_update=True)
            if not row:
                raise HTTPException(404, "Action not found")
            if not principal.department(row.department_id):
                raise HTTPException(403, "Approval outside authenticated mandate")
            if row.status in {"dispatching", "confirmed", "outcome_unknown"}:
                raise HTTPException(409, "Dispatched effects require separate reconciliation/compensation")
            if req.decision.startswith("approve") and row.status not in {"awaiting_approval", "content_approved"}:
                raise HTTPException(409, "Only a policy-admissible pending approval can be granted")
            if digest(row.envelope) != row.input_hash or digest(row.envelope["payload"]) != row.envelope["canonical_payload_hash"]:
                raise HTTPException(409, "Action content changed; a new immutable revision is required")
            if row.effective_authority == "A4":
                raise HTTPException(403, "Prohibited actions cannot be approved")
            if req.decision == "approve_content":
                row.status = "content_approved"
            elif req.decision == "approve_and_send":
                if st.halted(s, row.product_slug):
                    raise HTTPException(409, "Emergency halt active")
                row.approval = {"actor_id": principal.identity_id, "role": principal.role, "input_hash": row.input_hash, "expires_at": time.time() + 1800, "revoked": False}
                row.status = "ready"
            elif req.decision in {"revoke", "deny"}:
                row.approval = None
                row.status = "cancelled" if req.decision == "revoke" else "rejected"
            elif req.decision == "request_revision":
                row.status, row.approval = "proposed", None
            else:
                raise HTTPException(422, "Unsupported decision")
            row.updated_at = time.time()
            st.audit(s, principal.identity_id, "approval." + req.decision, action_id, {"input_hash": row.input_hash, "rationale": req.rationale})
            return {"status": row.status, "action_status": row.status, "action_id": action_id}

    @app.get("/v1/halts")
    def halts(request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        with request.app.state.store.transaction() as s:
            return {"active_halts": list(s.scalars(select(Record.record_id).where(Record.namespace == "halt")))}

    @app.post("/v1/halts", status_code=201)
    def halt(req: HaltRequest, request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        if principal.role not in {"founder_ceo", "coo", "cto"}:
            raise HTTPException(403, "Halt authority required")
        with request.app.state.store.transaction() as s:
            Store.put(s, "halt", req.scope, {"reason": req.reason, "actor_id": principal.identity_id})
            Store.audit(s, principal.identity_id, "halt.registered", req.scope)
        return {"status": "halt_registered", "scope": req.scope}

    @app.delete("/v1/halts/{scope}")
    def lift(scope: str, request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        if principal.role != "founder_ceo":
            raise HTTPException(403, "Principal required to lift containment")
        with request.app.state.store.transaction() as s:
            row = s.get(Record, ("halt", scope))
            if row:
                s.delete(row)
            Store.audit(s, principal.identity_id, "halt.lifted", scope)
        return {"status": "halt_lifted", "scope": scope}

    def records(request, namespace):
        with request.app.state.store.transaction() as s:
            rows = s.scalars(select(Record).where(Record.namespace == namespace).order_by(Record.updated_at.desc()).limit(200))
            return [dict(r.body, record_id=r.record_id, updated_at=r.updated_at) for r in rows]

    @app.get("/v1/directives")
    def directives(request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        rows = records(request, "directive")
        return {"directives": [r for r in rows if principal.role == "founder_ceo" or r["target_role"] in {principal.role, "all"}]}

    @app.post("/v1/directives", status_code=201)
    def directive(req: DirectiveRequest, request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        if principal.role != "founder_ceo":
            raise HTTPException(403, "Principal required to issue directives")
        if req.target_role not in {*DEPARTMENTS, "all"}:
            raise HTTPException(422, "Unknown target role")
        if req.sync_erp_task:
            raise HTTPException(422, "Corporate tasks are owned by MCS-OS; ERP task mirroring is not qualified")
        key = "dir-" + str(uuid.uuid4())
        body = {**req.model_dump(), "directive_id": key, "issuer": principal.identity_id, "status": "issued", "created_at": time.time()}
        with request.app.state.store.transaction() as s:
            Store.put(s, "directive", key, body)
            Store.audit(s, principal.identity_id, "directive.issued", key)
        return body

    @app.post("/v1/directives/{key}/status")
    def directive_status(key: str, req: dict, request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        with request.app.state.store.transaction() as s:
            row = s.get(Record, ("directive", key), with_for_update=True)
            if not row:
                raise HTTPException(404, "Directive not found")
            if principal.role not in {"founder_ceo", row.body["target_role"]}:
                raise HTTPException(403, "Directive outside mandate")
            state = req.get("status")
            if state not in {"acknowledged", "in_progress", "completed", "revoked"}:
                raise HTTPException(422, "Invalid state")
            if state == "completed" and not req.get("evidence"):
                raise HTTPException(422, "Completion evidence required")
            if state == "revoked" and principal.role != "founder_ceo":
                raise HTTPException(403, "Principal required to revoke")
            row.body = {**row.body, "status": state, "evidence": req.get("evidence"), "actor_id": principal.identity_id}
            row.updated_at = time.time()
            Store.audit(s, principal.identity_id, "directive." + state, key)
            return row.body

    @app.get("/v1/tasks")
    def tasks(request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        return {"tasks": [r for r in records(request, "task") if principal.department(r.get("department_id", "D01"))]}

    @app.get("/v1/incidents")
    def incidents(request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        return {"incidents": records(request, "incident")}

    @app.get("/v1/briefings")
    def briefings(request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        return {"briefings": records(request, "briefing")}

    @app.get("/v1/integration-status")
    def integration_status(request: Request, principal: Principal = Depends(authenticate)):
        operator(principal)
        with request.app.state.store.transaction() as s:
            rows = s.scalars(select(Action)).all()
            counts = {}
            for r in rows:
                counts[r.status] = counts.get(r.status, 0) + 1
            beats = records(request, "heartbeat")
            return {"action_counts": counts, "heartbeats": beats, "financial_balances": None, "financial_balance_status": "not_qualified", "observed_at": time.time(), "launch_qualified": False}

    @app.get("/v1/integrations/health")
    def integration_health(request: Request, principal: Principal = Depends(authenticate)):
        if principal.kind == "service" and not principal.scopes.get("read_health"):
            raise HTTPException(403, "Health scope required")
        from services.control.guardian import inspect
        result = inspect(request.app.state.store, repair=False)
        return JSONResponse(result, status_code=200 if result["status"] == "healthy" else 503)

    return app


app = create_app()
