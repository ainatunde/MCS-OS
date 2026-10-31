"""Security boundary: ERP sessions authenticate people; headers cannot assign roles."""
from __future__ import annotations

import hmac
import json
import os

import httpx
from fastapi import Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

COOKIE = "mcs_erp_session"


def enforced():
    return os.getenv("MCS_OS_ENV", "development").lower() != "development" or os.getenv("MCS_OS_AUTH_REQUIRED", "0") == "1"


def bindings():
    try:
        result = json.loads(os.environ.get("MCS_ROLE_BINDINGS", "{}"))
        if not isinstance(result, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in result.items()):
            raise ValueError()
        return {k.casefold(): v for k, v in result.items()}
    except (ValueError, TypeError):
        raise HTTPException(503, "Operator role configuration unavailable") from None


def origin_check(request):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        allowed = set(filter(None, os.getenv("MCS_CORS_ORIGINS", "https://command.mcsolutions.stream,https://os.mcsolutions.stream").split(",")))
        if request.headers.get("origin") not in {o.strip() for o in allowed}:
            raise HTTPException(403, "Trusted browser origin required")


def erp_url():
    url = os.environ.get("ERPNEXT_URL", "").rstrip("/")
    if not url.startswith(("https://", "http://")):
        raise HTTPException(503, "ERP identity service unavailable")
    return url


async def resolve_session(sid):
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            r = await client.get(erp_url() + "/api/method/frappe.auth.get_logged_user", cookies={"sid": sid})
        user = r.json().get("message") if r.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, "ERP identity service unavailable") from None
    role = bindings().get(user.casefold()) if isinstance(user, str) and user != "Guest" else None
    if not role:
        raise HTTPException(401, "Session expired, revoked or not authorized for the console")
    return user, role


async def verify_control_auth(request: Request, authorization: str | None = Header(default=None), x_mcs_api_key: str | None = Header(default=None)) -> str:
    if not isinstance(authorization, str):
        authorization = request.headers.get("authorization")
    if not isinstance(x_mcs_api_key, str):
        x_mcs_api_key = request.headers.get("x-mcs-api-key")
    if not enforced():
        request.state.auth_email, request.state.auth_role = "development", "founder_ceo"
        return "founder_ceo"
    sid = request.cookies.get(COOKIE)
    if sid:
        origin_check(request)
        email, role = await resolve_session(sid)
        request.state.auth_email, request.state.auth_role = email, role
        return role
    supplied = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else x_mcs_api_key or ""
    expected = os.getenv("MCS_CONTROL_API_TOKEN", "")
    if expected and supplied and hmac.compare_digest(expected, supplied):
        if request.method not in {"GET", "HEAD"}:
            raise HTTPException(403, "Shared service credential is read-only; individual sign-in required")
        request.state.auth_email, request.state.auth_role = "service", "read_only"
        return "read_only"
    raise HTTPException(401, "Individual sign-in required")


async def verify_principal_auth(request: Request) -> str:
    role = await verify_control_auth(request)
    # Role is derived from the authenticated ERP account and the server binding.
    if role not in {"founder_ceo", "ceo", "principal", "board_chair", "cfo", "cto", "coo", "commercial", "commercial_lead"}:
        raise HTTPException(403, "Authenticated executive required")
    return role


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)


def register_sessions(app):
    @app.post("/v1/session")
    async def login(req: LoginRequest, request: Request, response: Response):
        origin_check(request)
        if req.username.casefold() not in bindings():
            raise HTTPException(401, "Sign-in failed")
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                r = await client.post(erp_url() + "/api/method/login", data={"usr": req.username, "pwd": req.password})
                sid = client.cookies.get("sid")
                if r.status_code != 200 or not sid or sid == "Guest":
                    raise HTTPException(401, "Sign-in failed")
                email, role = await resolve_session(sid)
                if email.casefold() != req.username.casefold():
                    raise HTTPException(401, "ERP account identity mismatch")
        except httpx.HTTPError:
            raise HTTPException(503, "ERP identity service unavailable") from None
        response.set_cookie(COOKIE, sid, secure=enforced(), httponly=True, samesite="lax", path="/")
        response.headers["Cache-Control"] = "no-store"
        return {"role": role, "email": email}

    @app.get("/v1/session")
    async def current(request: Request, response: Response):
        role = await verify_control_auth(request)
        if role == "read_only":
            raise HTTPException(403, "Individual session required")
        response.headers["Cache-Control"] = "no-store"
        return {"role": role, "email": request.state.auth_email}

    @app.delete("/v1/session")
    async def logout(request: Request, response: Response):
        origin_check(request)
        sid = request.cookies.get(COOKIE)
        if sid:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.get(erp_url() + "/api/method/logout", cookies={"sid": sid})
                    if r.status_code not in {200, 401, 403}:
                        raise HTTPException(503, "ERP sign-out could not be confirmed")
            except httpx.HTTPError:
                raise HTTPException(503, "ERP identity service unavailable") from None
        response.delete_cookie(COOKIE, path="/")
        response.headers["Cache-Control"] = "no-store"
        return {"status": "signed_out"}
