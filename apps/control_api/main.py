"""MCS-OS Central Control API Gateway (FastAPI) (MCS-OS v2.2 §4.1 & §7).

Provides the authenticated corporate control plane for:
  - Product Registry & Capabilities (/v1/products)
  - Event Ingress & Deduplication (/v1/events)
  - Task Orchestration (/v1/tasks)
  - Action Proposals & Policy Evaluation (/v1/action-intents)
  - Decision Inbox & Approvals (/v1/approvals)
  - Execution Status & Reconciliation (/v1/actions/{id})
  - Emergency Halts & Containment (/v1/halts)
  - Executive 07:30 WAT Briefings (/v1/briefings)
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, status
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

# In-memory stores for runtime
tasks_store: Dict[str, Dict[str, Any]] = {}
actions_store: Dict[str, Dict[str, Any]] = {}
approvals_store: Dict[str, Dict[str, Any]] = {}
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


# Pydantic Request Models
class EventSubmissionRequest(BaseModel):
    event_id: str
    producer: str
    event_type: str
    payload: Dict[str, Any]
    product_slug: Optional[str] = "corporate"
    schema_version: str = "v1"


class ApprovalDecisionRequest(BaseModel):
    decision: str  # "approve_content" | "approve_and_send" | "deny"
    actor: str = "founder_ceo"
    rationale: Optional[str] = None


class HaltRequest(BaseModel):
    scope: str  # "company_wide" or a specific product_slug
    reason: str


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
async def list_products():
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
async def submit_event(req: EventSubmissionRequest):
    canonical_json = json.dumps(req.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    payload_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    envelope = EventEnvelope(
        event_id=req.event_id,
        producer=req.producer,
        product_slug=req.product_slug or "corporate",
        occurred_at=datetime.now(timezone.utc),
        correlation_id=f"corr-{req.event_id}",
        payload=req.payload,
        payload_hash=payload_hash,
        schema_version=req.schema_version,
    )
    result = ingress_service.ingest(envelope)
    return {
        "status": "accepted" if result.accepted else "rejected",
        "event_id": result.event_id,
        "is_duplicate": result.is_duplicate,
    }


@app.get("/v1/tasks")
async def list_tasks(department: Optional[str] = None):
    results = list(tasks_store.values())
    if department:
        results = [t for t in results if t.get("department_id") == department]
    return {"count": len(results), "tasks": results}


@app.post("/v1/action-intents", status_code=status.HTTP_201_CREATED)
async def propose_action_intent(envelope: ActionEnvelope):
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
async def list_approvals(status_filter: Optional[str] = None):
    results = list(approvals_store.values())
    if status_filter:
        results = [a for a in results if a.get("status") == status_filter]
    return {"count": len(results), "approvals": results}


@app.post("/v1/approvals/{action_id}/decide")
async def decide_approval(action_id: str, req: ApprovalDecisionRequest):
    approval = approvals_store.get(action_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")

    action = actions_store.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if req.decision in ["approve_content", "approve_and_send"]:
        approval["status"] = "granted"
        approval["decision"] = req.decision
        approval["actor"] = req.actor
        action["status"] = "ready"
        # Register approval with policy engine
        approval_ref = f"appr-{action_id}"
        policy_engine.record_approval(approval_ref, approval["payload_hash"])
    elif req.decision == "deny":
        approval["status"] = "denied"
        approval["actor"] = req.actor
        action["status"] = "rejected"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid decision: {req.decision}")

    return {"status": approval["status"], "action_id": action_id}


@app.get("/v1/actions/{action_id}")
async def get_action(action_id: str):
    action = actions_store.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@app.post("/v1/actions/{action_id}/reconcile")
async def reconcile_action(action_id: str):
    action = actions_store.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    envelope_data = action["envelope"]
    product_slug = envelope_data["product_slug"]
    adapter = adapters.get(product_slug)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"No adapter for product: {product_slug}")

    # Non-mutating lookup
    outcome = await adapter.lookup_outcome(action_id, envelope_data["idempotency_key"])
    action["reconciled_outcome"] = outcome.model_dump(mode="json")
    return action["reconciled_outcome"]


@app.get("/v1/halts")
async def list_halts():
    return {"active_halts": list(policy_engine.active_halts)}


@app.post("/v1/halts", status_code=status.HTTP_201_CREATED)
async def create_halt(req: HaltRequest):
    policy_engine.register_halt(req.scope)
    return {"status": "halt_registered", "scope": req.scope, "active_halts": list(policy_engine.active_halts)}


@app.delete("/v1/halts/{scope}")
async def remove_halt(scope: str):
    policy_engine.lift_halt(scope)
    return {"status": "halt_lifted", "scope": scope, "active_halts": list(policy_engine.active_halts)}


@app.get("/v1/briefings")
async def get_briefings():
    return {"count": len(briefings_store), "briefings": briefings_store}
