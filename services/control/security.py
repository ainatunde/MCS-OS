"""Server-owned identities; full-envelope service authentication."""
from dataclasses import dataclass
import hashlib
import hmac
import os
import time

from fastapi import HTTPException, Request
from sqlalchemy import select

from services.control.store import Identity, canonical, token_hash

DEPARTMENTS = {"founder_ceo": ["*"], "cfo": ["D06", "D10", "D02"], "cto": ["D05", "D04", "D08"], "coo": ["D01", "D07", "D10"], "commercial": ["D02", "D03"], "support": ["D07"]}


@dataclass(frozen=True)
class Principal:
    identity_id: str
    role: str
    kind: str
    scopes: dict

    def department(self, department):
        return "*" in DEPARTMENTS.get(self.role, []) or department in DEPARTMENTS.get(self.role, [])


def authenticate(request: Request) -> Principal:
    provided = request.headers.get("authorization", "")
    bearer = provided[7:].strip() if provided.lower().startswith("bearer ") else request.cookies.get("mcs_session", "")
    if not bearer:
        raise HTTPException(401, "Sign in required")
    with request.app.state.store.transaction() as s:
        identity = s.scalar(select(Identity).where(Identity.token_hash == token_hash(bearer)))
        if not identity or not identity.enabled or (identity.expires_at is not None and identity.expires_at <= time.time()):
            raise HTTPException(401, "Session or service credential expired/revoked")
        if identity.parent_id:
            parent = s.get(Identity, identity.parent_id)
            if not parent or not parent.enabled or parent.role != identity.role:
                raise HTTPException(401, "Account disabled or role changed")
        result = Principal(identity.identity_id, identity.role, identity.kind, dict(identity.scopes))
    if identity.kind == "session" and request.method not in {"GET", "HEAD", "OPTIONS"}:
        origins = set(request.app.state.origins)
        if request.headers.get("origin") not in origins:
            raise HTTPException(403, "Trusted browser origin required")
    return result


def operator(principal: Principal):
    if principal.kind not in {"session", "operator"} or principal.role not in DEPARTMENTS:
        raise HTTPException(403, "Operator identity required")


def service_event(request: Request, principal: Principal, body: dict):
    if principal.kind != "service" or principal.scopes.get("producer") != body.get("producer") or principal.scopes.get("product_slug") != body.get("product_slug"):
        raise HTTPException(403, "Producer/product credential scope mismatch")
    stamp = request.headers.get("x-mcs-timestamp", "")
    try:
        if abs(time.time() - int(stamp)) > 300:
            raise ValueError()
    except ValueError:
        raise HTTPException(401, "Fresh service timestamp required") from None
    with request.app.state.store.transaction() as s:
        identity = s.get(Identity, principal.identity_id)
        if not identity or not identity.enabled or not identity.secret_env:
            raise HTTPException(401, "Service disabled")
        secret = os.getenv(identity.secret_env, "")
        if len(secret) < 32 or not identity.secret_hash or not hmac.compare_digest(token_hash(secret), identity.secret_hash):
            raise HTTPException(503, "Service signing key unavailable")
    expected = hmac.new(secret.encode(), (stamp + "." + canonical(body)).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.headers.get("x-mcs-signature", ""), expected):
        raise HTTPException(401, "Invalid complete-envelope signature")


def signed_headers(token: str, secret: str, body: dict):
    if len(token) < 32 or len(secret) < 32:
        raise RuntimeError("Scoped service token and signing secret required")
    stamp = str(int(time.time()))
    signature = hmac.new(secret.encode(), (stamp + "." + canonical(body)).encode(), hashlib.sha256).hexdigest()
    return {"Authorization": "Bearer " + token, "X-MCS-Timestamp": stamp, "X-MCS-Signature": signature}
