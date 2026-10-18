"""MCS-OS Central Control API Gateway (FastAPI) (MCS-OS v2.2 §4.1 & §7).

Provides the authenticated corporate control plane for:
  - Product Registry & Capabilities (/v1/products)
  - Event Ingress & Deduplication (/v1/events)
  - Task Orchestration (/v1/tasks)
  - Action Proposals & Policy Evaluation (/v1/action-intents)
  - Decision Inbox & Approvals (/v1/approvals)
  - Execution Status & Reconciliation (/v1/actions/{id})
  - Incidents Registry (/v1/incidents)
  - Emergency Halts & Containment (/v1/halts)
  - Executive 07:30 WAT Briefings (/v1/briefings)
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from contracts.actions.envelope import ActionEnvelope, AuthorityClass, OutcomeState, canonical_payload_hash
from contracts.events.envelope import EventEnvelope
from services.policy.engine import PolicyEngine, PolicyDecision
from services.ingress.service import IngressService, IngressResult
from adapters.products.cloudstream_vcp import CloudStreamVCPAdapter
from adapters.products.cloudstream_forge import CloudStreamForgeAdapter
from adapters.products.aether_ads import AetherADSAdapter
from adapters.products.aether_adx import AetherADXAdapter
from adapters.products.tv_insights import TVInsightsAdapter
from adapters.products.africasignal import AfricaSignalAdapter
from adapters.products.mcs_app_factory import MCSAppFactoryAdapter
from adapters.providers.erpnext_adapter import ERPNextAdapter

app = FastAPI(
    title="MCS-OS Corporate Control API",
    version="2.2.0",
    description="Multimedia Cloud Solutions Autonomous Operating System API",
)

default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://command.mcsolutions.stream",
    "https://os.mcsolutions.stream",
    "https://erp.mcsolutions.stream",
]
env_origins = [
    origin.strip()
    for origin in os.environ.get("MCS_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
allowed_origins = list(dict.fromkeys(default_origins + env_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-MCS-API-Key", "X-MCS-Actor", "X-MCS-Signature"],
)

# Global services & state
policy_engine = PolicyEngine()
ingress_service = IngressService()

adapters = {
    "cloudstream-vcp": CloudStreamVCPAdapter(),
    "cloudstream-forge": CloudStreamForgeAdapter(),
    "aether-ads": AetherADSAdapter(),
    "aether-adx": AetherADXAdapter(),
    "tv-insights": TVInsightsAdapter(),
    "africasignal": AfricaSignalAdapter(),
    "mcs-app-factory": MCSAppFactoryAdapter(),
    "mcs-erp": ERPNextAdapter(),
}

# Executive Persona Governance & Department Mandates (MCS-OS v2.2 §4.1)
PRINCIPAL_ACTORS = {
    "founder_ceo", "ceo", "principal", "board_chair",
    "cfo", "cto", "coo", "commercial_lead", "commercial",
}

ROLE_AUTHORITY_SCOPES: Dict[str, Dict[str, Any]] = {
    "founder_ceo": {
        "title": "Chief Executive Officer (CEO)",
        "departments": ["*"],
        "can_halt_company": True,
        "email": "aina_tunde@hotmail.com",
    },
    "ceo": {
        "title": "Chief Executive Officer (CEO)",
        "departments": ["*"],
        "can_halt_company": True,
        "email": "aina_tunde@hotmail.com",
    },
    "principal": {
        "title": "Corporate Principal",
        "departments": ["*"],
        "can_halt_company": True,
        "email": "aina_tunde@hotmail.com",
    },
    "board_chair": {
        "title": "Board Chair",
        "departments": ["*"],
        "can_halt_company": True,
        "email": "aina_tunde@hotmail.com",
    },
    "cfo": {
        "title": "Chief Financial Officer (CFO)",
        "departments": ["D06", "D10", "D02"],
        "can_halt_company": False,
        "email": "cfo@mcsolutions.stream",
    },
    "cto": {
        "title": "Chief Technology Officer (CTO)",
        "departments": ["D05", "D04", "D08"],
        "can_halt_company": True,
        "email": "cto@mcsolutions.stream",
    },
    "coo": {
        "title": "Chief Operating Officer (COO)",
        "departments": ["D01", "D07", "D10"],
        "can_halt_company": True,
        "email": "coo@mcsolutions.stream",
    },
    "commercial": {
        "title": "Chief Commercial Officer (CCO)",
        "departments": ["D02", "D03"],
        "can_halt_company": False,
        "email": "commercial@mcsolutions.stream",
    },
    "commercial_lead": {
        "title": "Chief Commercial Officer (CCO)",
        "departments": ["D02", "D03"],
        "can_halt_company": False,
        "email": "commercial@mcsolutions.stream",
    },
}

# Runtime stores with pre-seeded executive proposals
tasks_store: Dict[str, Dict[str, Any]] = {}
actions_store: Dict[str, Dict[str, Any]] = {
    "act-d02-001": {
        "action_id": "act-d02-001",
        "envelope": {"product_slug": "aether-ads", "department_id": "D02"},
        "status": "awaiting_approval",
    },
    "act-d06-001": {
        "action_id": "act-d06-001",
        "envelope": {"product_slug": "corporate", "department_id": "D06"},
        "status": "awaiting_approval",
    },
    "act-d05-001": {
        "action_id": "act-d05-001",
        "envelope": {"product_slug": "cloudstream-vcp", "department_id": "D05"},
        "status": "awaiting_approval",
    },
    "act-d01-001": {
        "action_id": "act-d01-001",
        "envelope": {"product_slug": "tv-insights", "department_id": "D01"},
        "status": "awaiting_approval",
    },
}

approvals_store: Dict[str, Dict[str, Any]] = {
    "act-d02-001": {
        "approval_id": "appr-d02-001",
        "action_id": "act-d02-001",
        "department_id": "D02",
        "action_type": "commercial.nonstandard_offer.v1",
        "payload_hash": "sha256:4a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b",
        "title": "Metro Broadcast SSAI Agreement (35% rev-share)",
        "proposed_effect": "Special multi-channel SSAI agreement for Metro Broadcast (35% rev-share)",
        "amount_usd": 12000.0,
        "status": "pending",
        "created_at": "2026-10-17T12:00:00Z",
    },
    "act-d06-001": {
        "approval_id": "appr-d06-001",
        "action_id": "act-d06-001",
        "department_id": "D06",
        "action_type": "finance.treasury_allocation.v1",
        "payload_hash": "sha256:6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d",
        "title": "Quarterly Reserved GPU Compute Cluster Commitment",
        "proposed_effect": "Quarterly cloud reservation for edge neural transcoders ($24,500 commitment)",
        "amount_usd": 24500.0,
        "status": "pending",
        "created_at": "2026-10-17T14:30:00Z",
    },
    "act-d05-001": {
        "approval_id": "appr-d05-001",
        "action_id": "act-d05-001",
        "department_id": "D05",
        "action_type": "engineering.infrastructure_autoscale.v1",
        "payload_hash": "sha256:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
        "title": "Transcoding Cluster Dynamic Scale Ceiling Increase (24 to 48 nodes)",
        "proposed_effect": "Dynamic scaling threshold expansion for Lagos & Johannesburg edge POPs",
        "status": "pending",
        "created_at": "2026-10-17T16:00:00Z",
    },
    "act-d01-001": {
        "approval_id": "appr-d01-001",
        "action_id": "act-d01-001",
        "department_id": "D01",
        "action_type": "operations.vendor_sla_waiver.v1",
        "payload_hash": "sha256:2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c",
        "title": "TV-Insights Regional Feed Ingest Temporary Concurrency Expansion",
        "proposed_effect": "Temporary crawler concurrency multiplier during prime-time broadcasting",
        "status": "pending",
        "created_at": "2026-10-17T18:15:00Z",
    },
}

incidents_store: Dict[str, Dict[str, Any]] = {}
briefings_store: List[Dict[str, Any]] = [
    {
        "briefing_id": "brf-20261016-0730",
        "date": "2026-10-16",
        "scheduled_time": "07:30 WAT",
        "headline": "Portfolio Launch Baseline: 8 of 8 Systems Healthy",
        "departments_ready": 11,
        "active_halts": 0,
        "standing_authority_execution": "100%",
    }
]


def _is_auth_enforced() -> bool:
    return (
        os.environ.get("MCS_OS_AUTH_REQUIRED", "0") == "1"
        or os.environ.get("MCS_OS_ENV", "development").lower() == "production"
    )


async def verify_control_auth(
    authorization: Optional[str] = Header(default=None),
    x_mcs_api_key: Optional[str] = Header(default=None),
) -> str:
    expected_token = os.environ.get("MCS_CONTROL_API_TOKEN", "")
    provided = x_mcs_api_key or ""
    if authorization and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()

    if _is_auth_enforced():
        if not expected_token or not provided or not hmac.compare_digest(provided, expected_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid Bearer token or X-MCS-API-Key required",
            )
    return provided or "dev-session"


async def verify_principal_auth(
    _token: str = Depends(verify_control_auth),
    x_mcs_actor: Optional[str] = Header(default=None),
) -> str:
    actor = x_mcs_actor or "founder_ceo"
    if _is_auth_enforced() and (not x_mcs_actor or x_mcs_actor not in PRINCIPAL_ACTORS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Principal role (X-MCS-Actor) required for A3 approvals and emergency halts",
        )
    return actor


# Pydantic Request Models
class EventSubmissionRequest(BaseModel):
    event_id: str = Field(..., min_length=3, max_length=128)
    producer: str = Field(..., min_length=2, max_length=64)
    event_type: str = Field(..., min_length=3, max_length=128)
    payload: Dict[str, Any]
    product_slug: Optional[str] = "corporate"
    schema_version: str = "v1"
    signature: Optional[str] = None


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approve_content" | "approve_and_send" | "deny" | "revoke" | "request_revision"
    actor: str = "founder_ceo"
    rationale: Optional[str] = None


class HaltRequest(BaseModel):
    scope: str = Field(..., min_length=2, max_length=64)
    reason: str = Field(..., min_length=3, max_length=512)


class IncidentCreateRequest(BaseModel):
    incident_id: str = Field(..., min_length=3, max_length=64)
    product_slug: str = Field(..., min_length=2, max_length=64)
    severity: str = Field(default="high", max_length=32)
    summary: str = Field(..., min_length=3, max_length=512)


@app.get("/healthz")
async def healthz():
    return {
        "status": "healthy",
        "service": "mcs-control-api",
        "version": "2.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_halts": list(policy_engine.active_halts),
    }


@app.get("/v1/products")
async def list_products(_auth: str = Depends(verify_control_auth)):
    product_list = []
    for slug, adapter in adapters.items():
        health = await adapter.read_health()
        caps = await adapter.describe_capabilities()
        product_list.append({
            "product_slug": slug,
            "adapter_version": getattr(adapter, "adapter_version", "v1"),
            "health": health.model_dump(),
            "capabilities_count": len(caps),
            "capabilities": [c.model_dump() for c in caps],
        })
    return {"count": len(product_list), "products": product_list}


@app.post("/v1/events", status_code=status.HTTP_201_CREATED)
async def submit_event(
    req: EventSubmissionRequest,
    x_mcs_signature: Optional[str] = Header(default=None),
    _auth: str = Depends(verify_control_auth),
):
    canonical_json = json.dumps(req.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    payload_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    webhook_secret = os.environ.get("MCS_WEBHOOK_SECRET", "")
    provided_sig = x_mcs_signature or req.signature
    if webhook_secret or _is_auth_enforced():
        if not webhook_secret or not provided_sig:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature (X-MCS-Signature)",
            )
        expected_sig = hmac.new(
            webhook_secret.encode("utf-8"),
            f"{req.event_id}:{payload_hash}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(provided_sig, expected_sig):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

    envelope = EventEnvelope(
        event_id=req.event_id,
        producer=req.producer,
        product_slug=req.product_slug or "corporate",
        occurred_at=datetime.now(timezone.utc),
        correlation_id=f"corr-{req.event_id}",
        payload=req.payload,
        payload_hash=payload_hash,
        schema_version=req.schema_version,
        signature=provided_sig,
    )
    result = ingress_service.ingest(envelope)
    return {
        "status": "accepted" if result.accepted else "rejected",
        "event_id": result.event_id,
        "is_duplicate": result.is_duplicate,
    }


@app.get("/v1/tasks")
async def list_tasks(department: Optional[str] = None, _auth: str = Depends(verify_control_auth)):
    results = list(tasks_store.values())
    if department:
        results = [t for t in results if t.get("department_id") == department]
    return {"count": len(results), "tasks": results}


@app.post("/v1/action-intents", status_code=status.HTTP_201_CREATED)
async def propose_action_intent(envelope: ActionEnvelope, _auth: str = Depends(verify_control_auth)):
    decision = policy_engine.evaluate(envelope)

    record = {
        "action_id": envelope.action_id,
        "envelope": envelope.model_dump(mode="json"),
        "policy_decision": {
            "admitted": decision.admitted,
            "requires_approval": decision.requires_approval,
            "assigned_authority": decision.assigned_authority.value,
            "reasons": decision.reasons,
            "promoted_state": decision.promoted_state,
        },
        "status": decision.promoted_state,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    actions_store[envelope.action_id] = record

    if decision.requires_approval:
        approvals_store[envelope.action_id] = {
            "approval_id": f"appr-{envelope.action_id}",
            "action_id": envelope.action_id,
            "department_id": envelope.department_id,
            "action_type": envelope.action_type,
            "payload_hash": envelope.canonical_payload_hash,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    return record


@app.get("/v1/approvals")
async def list_approvals(status_filter: Optional[str] = None, _auth: str = Depends(verify_control_auth)):
    results = list(approvals_store.values())
    if status_filter:
        results = [a for a in results if a.get("status") == status_filter]
    return {"count": len(results), "approvals": results}


@app.post("/v1/approvals/{action_id}/decide")
async def decide_approval(
    action_id: str,
    req: ApprovalDecisionRequest,
    principal_actor: str = Depends(verify_principal_auth),
):
    approval = approvals_store.get(action_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    action = actions_store.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    actor = req.actor or principal_actor
    if actor not in PRINCIPAL_ACTORS:
        raise HTTPException(status_code=403, detail=f"Actor '{actor}' is not an authorized A3 Principal or Executive")

    # Verify department governance scope
    scope_info = ROLE_AUTHORITY_SCOPES.get(actor, {})
    allowed_depts = scope_info.get("departments", ["*"])
    dept = approval.get("department_id")
    if "*" not in allowed_depts and dept and dept not in allowed_depts:
        raise HTTPException(
            status_code=403,
            detail=f"Actor '{actor}' is not authorized to sign off for department {dept}. Mandate: {allowed_depts}",
        )

    product_slug = action["envelope"].get("product_slug", "corporate")
    approval_ref = f"appr-{action_id}"

    if req.decision == "approve_content":
        # Spec §5.3: 'Approve content' alone never releases the send queue.
        approval["status"] = "content_approved"
        approval["decision"] = req.decision
        approval["actor"] = actor
        action["status"] = "content_approved"
    elif req.decision == "approve_and_send":
        if "company_wide" in policy_engine.active_halts or product_slug in policy_engine.active_halts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot release action '{action_id}' while emergency halt is active",
            )
        approval["status"] = "granted"
        approval["decision"] = req.decision
        approval["actor"] = actor
        action["status"] = "ready"
        policy_engine.record_approval(approval_ref, approval["payload_hash"])
    elif req.decision == "deny":
        approval["status"] = "denied"
        approval["decision"] = req.decision
        approval["actor"] = actor
        action["status"] = "rejected"
        policy_engine.revoke_approval(approval_ref)
    elif req.decision == "revoke":
        approval["status"] = "revoked"
        approval["decision"] = req.decision
        approval["actor"] = actor
        action["status"] = "cancelled"
        policy_engine.revoke_approval(approval_ref)
    elif req.decision == "request_revision":
        approval["status"] = "revision_requested"
        approval["decision"] = req.decision
        approval["actor"] = actor
        action["status"] = "proposed"
        policy_engine.revoke_approval(approval_ref)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid decision: {req.decision}")

    return {"status": approval["status"], "action_id": action_id, "action_status": action["status"]}


@app.get("/v1/actions/{action_id}")
async def get_action(action_id: str, _auth: str = Depends(verify_control_auth)):
    action = actions_store.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@app.post("/v1/actions/{action_id}/reconcile")
async def reconcile_action(action_id: str, _auth: str = Depends(verify_control_auth)):
    action = actions_store.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    envelope_data = action["envelope"]
    product_slug = envelope_data["product_slug"]
    adapter = adapters.get(product_slug)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"No adapter for product: {product_slug}")

    outcome = await adapter.lookup_outcome(action_id, envelope_data["idempotency_key"])
    action["reconciled_outcome"] = outcome.model_dump(mode="json")
    return action["reconciled_outcome"]


@app.get("/v1/incidents")
async def list_incidents(product_slug: Optional[str] = None, _auth: str = Depends(verify_control_auth)):
    results = list(incidents_store.values())
    if product_slug:
        results = [i for i in results if i.get("product_slug") == product_slug]
    return {"count": len(results), "incidents": results}


@app.post("/v1/incidents", status_code=status.HTTP_201_CREATED)
async def create_incident(req: IncidentCreateRequest, _auth: str = Depends(verify_control_auth)):
    record = {
        "incident_id": req.incident_id,
        "product_slug": req.product_slug,
        "severity": req.severity,
        "summary": req.summary,
        "state": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    incidents_store[req.incident_id] = record
    return record


@app.get("/v1/halts")
async def list_halts(_auth: str = Depends(verify_control_auth)):
    return {"active_halts": list(policy_engine.active_halts)}


@app.post("/v1/halts", status_code=status.HTTP_201_CREATED)
async def create_halt(req: HaltRequest, principal_actor: str = Depends(verify_principal_auth)):
    if req.scope == "company_wide":
        scope_info = ROLE_AUTHORITY_SCOPES.get(principal_actor, {})
        if not scope_info.get("can_halt_company", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Actor '{principal_actor}' is not authorized to trigger company-wide emergency halts",
            )
    policy_engine.register_halt(req.scope)
    return {"status": "halt_registered", "scope": req.scope, "active_halts": list(policy_engine.active_halts)}


@app.delete("/v1/halts/{scope}")
async def remove_halt(scope: str, _principal: str = Depends(verify_principal_auth)):
    policy_engine.lift_halt(scope)
    return {"status": "halt_lifted", "scope": scope, "active_halts": list(policy_engine.active_halts)}


@app.get("/v1/briefings")
async def get_briefings(_auth: str = Depends(verify_control_auth)):
    return {"count": len(briefings_store), "briefings": briefings_store}


@app.get("/v1/team")
async def get_team_directory(_auth: str = Depends(verify_control_auth)):
    return {
        "count": 6,
        "team": [
            {
                "persona": "founder_ceo",
                "role_code": "CEO",
                "title": "Chief Executive Officer",
                "email": "aina_tunde@hotmail.com",
                "departments": ["*"],
                "authority_ceiling": "A3 (Unlimited)",
                "erp_role": "Administrator",
                "erp_link": "https://erp.mcsolutions.stream/app",
            },
            {
                "persona": "cfo",
                "role_code": "CFO",
                "title": "Chief Financial Officer",
                "email": "cfo@mcsolutions.stream",
                "departments": ["D06", "D10", "D02"],
                "authority_ceiling": "A2 ($10/day burn, $25,000 limit)",
                "erp_role": "Accounts Manager, Accounts User, Auditor",
                "erp_link": "https://erp.mcsolutions.stream/app/accounting",
            },
            {
                "persona": "cto",
                "role_code": "CTO",
                "title": "Chief Technology Officer",
                "email": "cto@mcsolutions.stream",
                "departments": ["D05", "D04", "D08"],
                "authority_ceiling": "A2 ($30/day burn, Infrastructure Gates)",
                "erp_role": "System Manager",
                "erp_link": "https://erp.mcsolutions.stream/app/settings",
            },
            {
                "persona": "coo",
                "role_code": "COO",
                "title": "Chief Operating Officer",
                "email": "coo@mcsolutions.stream",
                "departments": ["D01", "D07", "D10"],
                "authority_ceiling": "A2 ($15/day burn, Operations Execution)",
                "erp_role": "Projects Manager, Stock Manager, Purchase Manager",
                "erp_link": "https://erp.mcsolutions.stream/app/stock",
            },
            {
                "persona": "commercial",
                "role_code": "CCO",
                "title": "Chief Commercial Officer",
                "email": "commercial@mcsolutions.stream",
                "departments": ["D02", "D03"],
                "authority_ceiling": "A2 ($25/day burn, Deal Structuring)",
                "erp_role": "Sales Manager, Sales User, Sales Master Manager",
                "erp_link": "https://erp.mcsolutions.stream/app/selling",
            },
            {
                "persona": "support",
                "role_code": "Support",
                "title": "Customer Success Lead",
                "email": "support@mcsolutions.stream",
                "departments": ["D07"],
                "authority_ceiling": "A1 (Support Triage)",
                "erp_role": "Support Team",
                "erp_link": "https://erp.mcsolutions.stream/app/support",
            },
        ],
    }
