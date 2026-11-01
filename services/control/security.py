"""Server-owned identities; full-envelope service authentication."""
from dataclasses import dataclass
import hashlib
import hmac
import os
import time
import httpx
from cryptography.fernet import Fernet, InvalidToken

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


def session_cipher():
    key = os.environ.get("MCS_SESSION_ENCRYPTION_KEY", "")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError):
        raise HTTPException(503, "Session encryption key unavailable") from None


def bind_session(request, sid, email, role):
    """Persist revocation/expiry without storing the ERP credential in plaintext."""
    key = "session:" + token_hash(sid)
    parent_id = "operator:" + ("Administrator" if email.casefold() == "administrator" else email.casefold())
    with request.app.state.store.transaction() as s:
        parent = s.get(Identity, parent_id)
        if not parent or not parent.enabled or parent.role != role:
            raise HTTPException(401, "Operator directory requires provisioning")
        row = s.get(Identity, key)
        if row is None:
            row = Identity(identity_id=key, kind="session", role=role, parent_id=parent_id, enabled=True,
                token_hash=token_hash(sid), expires_at=time.time() + 1800,
                scopes={"email": email, "provider_session": session_cipher().encrypt(sid.encode()).decode()})
            s.add(row)
        if not row.enabled or row.expires_at <= time.time() or row.role != role:
            raise HTTPException(401, "Session expired or revoked; sign in again")
        return Principal(row.identity_id, role, "session", {"email": email})


def validate_provider_session(identity):
    """Dispatch revalidates the same ERP session that authorized this approval."""
    if identity.kind != "session":
        return os.getenv("MCS_OS_ENV", "development") == "development"
    from apps.control_api.security import bindings, erp_url
    try:
        sid = session_cipher().decrypt(identity.scopes["provider_session"].encode()).decode()
        response = httpx.get(erp_url() + "/api/method/frappe.auth.get_logged_user",
            cookies={"sid": sid}, timeout=10, follow_redirects=False)
        user = response.json().get("message") if response.status_code == 200 else None
        return user == identity.scopes.get("email") and bindings().get(user.casefold()) == identity.role
    except (httpx.HTTPError, ValueError, KeyError, InvalidToken, HTTPException, AttributeError):
        return False


async def authenticate(request: Request) -> Principal:
    from apps.control_api.security import COOKIE, origin_check, resolve_session
    sid = request.cookies.get(COOKIE)
    if sid:
        origin_check(request)
        email, role = await resolve_session(sid)
        return bind_session(request, sid, email, role)
    provided = request.headers.get("authorization", "")
    bearer = provided[7:].strip() if provided.lower().startswith("bearer ") else request.cookies.get("mcs_session", "")
    legacy = os.getenv("MCS_CONTROL_API_TOKEN", "")
    if legacy and bearer and hmac.compare_digest(legacy, bearer):
        if request.method not in {"GET", "HEAD"}:
            raise HTTPException(403, "Shared service credential is read-only")
        return Principal("legacy:read_only", "read_only", "read_only", {})
    if not bearer:
        raise HTTPException(401, "Sign in required")
    with request.app.state.store.transaction() as s:
        identity = s.scalar(select(Identity).where(Identity.token_hash == token_hash(bearer)))
        if not identity or not identity.enabled or (identity.expires_at is not None and identity.expires_at <= time.time()):
            raise HTTPException(401, "Session or service credential expired/revoked")
        if os.getenv("MCS_OS_ENV", "development") != "development" and identity.kind != "service":
            raise HTTPException(401, "Individual ERP sign-in required")
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
