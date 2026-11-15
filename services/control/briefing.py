"""The owner's morning briefing (D01): one email at 07:00 Africa/Lagos covering Pulzz, ERPNext, the OS and backups.

Runs as its own supervised service. Each Lagos day gets exactly one ``briefing`` record, claimed in the database
before anything is sent, so a restart or a second process can never send twice. A failed send is retried every
ten minutes for the rest of the day, and the Guardian check ``morning_briefing_sent`` reports a missed day.
Sources that fail are named in the email instead of stopping it: the briefing always goes out.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from html import escape
import json
import logging
import os
import smtplib
import ssl
import time

import httpx
from sqlalchemy import select

from services.control.security import signed_headers
from services.control.store import Action, Record, Store, configured_store

log = logging.getLogger(__name__)
LAGOS = timezone(timedelta(hours=1), "WAT")      # Nigeria keeps UTC+1 all year
SEND_AT = (7, 0)
RETRY_SECONDS = 600
LEASE_SECONDS = 300


def lagos_day(now: float) -> str:
    return datetime.fromtimestamp(now, LAGOS).strftime("%Y-%m-%d")


def due(now: float) -> bool:
    local = datetime.fromtimestamp(now, LAGOS)
    return (local.hour, local.minute) >= SEND_AT


# --------------------------------------------------------------------------- gathering

def _get(client, url, headers):
    response = client.get(url, headers=headers)
    if response.status_code != 200:
        raise RuntimeError("HTTP " + str(response.status_code))
    return response.json()


def gather(store: Store, client: httpx.Client, now: float) -> dict:
    data: dict = {"generated_at": now, "day": lagos_day(now), "errors": {}}
    try:
        data["pulzz"] = _get(client, os.environ["PULZZ_URL"].rstrip("/") + "/api/integrations/mcs-os/summary",
                             signed_headers(os.environ["MCS_PULZZ_RECEIPT_TOKEN"], os.environ["MCS_PULZZ_SIGNING_SECRET"], {}))
    except (KeyError, RuntimeError, ValueError, httpx.HTTPError) as exc:
        data["errors"]["pulzz"] = type(exc).__name__ if not isinstance(exc, RuntimeError) else str(exc)
    try:
        data["erp"] = _get(client, os.environ["MCS_ERP_GATEWAY_URL"].rstrip("/") + "/v1/summary",
                           {"Authorization": "Bearer " + os.environ["MCS_ERP_GATEWAY_TOKEN"]})
    except (KeyError, RuntimeError, ValueError, httpx.HTTPError) as exc:
        data["errors"]["erp"] = type(exc).__name__ if not isinstance(exc, RuntimeError) else str(exc)

    since = now - 24 * 3600
    with store.transaction() as s:
        actions = s.scalars(select(Action)).all()
        waiting = [a for a in actions if a.status in {"awaiting_approval", "content_approved"}]
        data["os"] = {
            "waiting": [{"action_id": a.action_id, "type": a.envelope.get("action_type"), "department": a.department_id,
                         "hours": round((now - a.created_at) / 3600, 1)} for a in sorted(waiting, key=lambda a: a.created_at)],
            "blocked": [{"type": a.envelope.get("action_type"), "error": (a.error or "")[:140]}
                        for a in actions if a.status in {"blocked", "rejected", "failed", "outcome_unknown"}],
            "done": _tally(a.envelope.get("action_type") for a in actions
                           if a.status in {"confirmed", "voided", "settled"} and a.updated_at >= since),
        }
        guardian = s.get(Record, ("heartbeat", "integration-guardian"))
        checks = (guardian.body.get("checks") if guardian else None) or {}
        data["os"]["checks_total"] = len(checks)
        data["os"]["checks_failing"] = sorted(k for k, v in checks.items() if not v)
        data["os"]["guardian_age"] = round(now - guardian.updated_at) if guardian else None
        data["os"]["findings"] = [{"check": r.record_id, "summary": (r.body.get("summary") or "")[:160]}
                                  for r in s.scalars(select(Record).where(Record.namespace == "incident"))
                                  if r.body.get("status") == "open"]
    data["backup"] = _backup(now)
    return data


def _tally(items) -> dict:
    out: dict = {}
    for item in items:
        out[item] = out.get(item, 0) + 1
    return out


def _backup(now: float) -> dict:
    try:
        with open(os.getenv("MCS_BACKUP_STATUS_FILE", "/var/lib/mcs-backup/status.json"), encoding="utf-8") as handle:
            status = json.load(handle)
        last = float(status["last_success_at"])
        return {"ok": status.get("last_result") == "ok" and now - last < 26 * 3600, "hours_ago": round((now - last) / 3600, 1),
                "gb": round(float(status.get("last_bytes") or 0) / 1e9, 2), "failed_step": status.get("failed_step")}
    except (OSError, ValueError, KeyError, TypeError):
        return {"ok": False, "hours_ago": None, "gb": None, "failed_step": "status unreadable"}


# --------------------------------------------------------------------------- writing

def _money(totals: dict | None, minor: bool = False) -> str:
    if not totals:
        return "none"
    parts = []
    for currency, amount in sorted(totals.items()):
        value = float(amount) / (100 if minor else 1)
        parts.append(f"{currency} {value:,.0f}" if value == int(value) else f"{currency} {value:,.2f}")
    return ", ".join(parts)


def attention(data: dict) -> list[str]:
    """The items that need the owner, most important first. Empty means all clear."""
    items = []
    os_ = data.get("os", {})
    for w in os_.get("waiting", []):
        items.append(f"Approval waiting: {w['type']} ({w['department']}), {w['hours']} h old")
    for b in os_.get("blocked", []):
        items.append(f"Action blocked: {b['type']}: {b['error']}")
    for name in os_.get("checks_failing", []):
        items.append(f"OS check failing: {name}")
    erp = data.get("erp") or {}
    rec = erp.get("receivables") or {}
    if rec.get("overdue_invoices"):
        items.append(f"Overdue customer invoices: {rec['overdue_invoices']} ({_money(rec.get('overdue'))})")
    pz = data.get("pulzz") or {}
    if (pz.get("plan_requests") or {}).get("waiting"):
        items.append(f"Pulzz plan requests waiting: {pz['plan_requests']['waiting']}")
    for name in (pz.get("guardian") or {}).get("critical_checks", []):
        items.append(f"Pulzz critical: {name}")
    if not data.get("backup", {}).get("ok"):
        items.append("Off-host backup is not current")
    for source, err in data.get("errors", {}).items():
        items.append(f"{'Pulzz' if source == 'pulzz' else 'ERPNext'} figures unavailable ({err})")
    return items


def sections(data: dict) -> list[tuple[str, list[str]]]:
    out = []
    pz = data.get("pulzz")
    if pz:
        subs, plans, spons = pz.get("subscribers", {}), pz.get("plan_requests", {}), pz.get("sponsorships", {})
        leads, guardian = pz.get("supplier_leads", {}), pz.get("guardian", {})
        out.append(("Pulzz", [
            f"Subscribers: {subs.get('total', 0):,} ({subs.get('new', 0)} new), {subs.get('paid_active', 0)} on a paid plan",
            f"Plan requests: {plans.get('new', 0)} new ({_money(plans.get('new_value'))}), {plans.get('waiting', 0)} waiting",
            f"Sponsorships live: {spons.get('live', 0)} ({_money(spons.get('booked_minor'), minor=True)} booked)",
            f"Supplier leads: {leads.get('new', 0)} new, {leads.get('delivered', 0)} delivered",
            f"Site health: {guardian.get('open', 0)} open findings, {len(guardian.get('critical_checks', []))} critical; "
            f"link to OS {pz.get('corporate_bridge', {}).get('status', 'unknown')}",
        ]))
    erp = data.get("erp")
    if erp:
        rec, posted, paid, bills = (erp.get("receivables", {}), erp.get("invoices_posted_or_changed", {}),
                                    erp.get("payments_received", {}), erp.get("payables", {}))
        out.append(("Money (ERPNext)", [
            f"Owed to us: {_money(rec.get('outstanding'))} on {rec.get('open_invoices', 0)} invoices; "
            f"overdue {_money(rec.get('overdue'))} on {rec.get('overdue_invoices', 0)}",
            f"Payments received: {paid.get('count', 0)} ({_money(paid.get('value'))})",
            f"Invoices posted or changed: {posted.get('count', 0)} ({_money(posted.get('value'))}); drafts waiting: {erp.get('draft_invoices', 0)}",
            f"We owe: {_money(bills.get('outstanding'))} on {bills.get('open_bills', 0)} bills, {bills.get('overdue_bills', 0)} overdue",
        ]))
    os_ = data.get("os", {})
    done = os_.get("done") or {}
    out.append(("Operations (MCS OS)", [
        f"Checks: {os_.get('checks_total', 0) - len(os_.get('checks_failing', []))} of {os_.get('checks_total', 0)} passing",
        "Done in the last day: " + (", ".join(f"{n} × {t}" for t, n in sorted(done.items())) or "nothing"),
        f"Waiting for you: {len(os_.get('waiting', []))}; open findings: {len(os_.get('findings', []))}",
    ]))
    b = data.get("backup", {})
    out.append(("Backups", [f"Last off-host backup {b['hours_ago']} h ago, {b['gb']} GB" if b.get("hours_ago") is not None
                            else "No off-host backup status"]))
    return out


def render(data: dict) -> tuple[str, str, str]:
    day = datetime.strptime(data["day"], "%Y-%m-%d").strftime("%a %d %b")
    needs = attention(data)
    subject = f"MCS briefing {day}: " + (f"{len(needs)} item{'s' if len(needs) != 1 else ''} need you" if needs else "all clear")
    lines = [subject, ""]
    lines += ["NEEDS YOU"] + [f"- {i}" for i in needs] + [""] if needs else ["Nothing needs you today.", ""]
    for title, rows in sections(data):
        lines += [title.upper()] + [f"- {r}" for r in rows] + [""]
    lines.append("Approvals and halts: https://command.mcsolutions.stream")
    text = "\n".join(lines)

    def ul(rows):
        return "<ul style='margin:4px 0 16px;padding-left:20px'>" + "".join(f"<li>{escape(r)}</li>" for r in rows) + "</ul>"
    html = ["<div style='font-family:-apple-system,Segoe UI,Arial,sans-serif;font-size:15px;line-height:1.45;color:#1c1917;max-width:640px'>",
            f"<h2 style='font-size:18px;margin:0 0 12px'>{escape(subject)}</h2>"]
    if needs:
        html.append("<h3 style='font-size:15px;margin:12px 0 4px;color:#9a3412'>Needs you</h3>" + ul(needs))
    else:
        html.append("<p style='margin:0 0 16px;color:#166534'>Nothing needs you today.</p>")
    for title, rows in sections(data):
        html.append(f"<h3 style='font-size:15px;margin:12px 0 4px'>{escape(title)}</h3>" + ul(rows))
    html.append("<p style='margin-top:20px'><a href='https://command.mcsolutions.stream'>Open the command centre</a> for approvals and halts.</p></div>")
    return subject, text, "".join(html)


# --------------------------------------------------------------------------- sending

def send(subject: str, text: str, html: str) -> None:
    message = EmailMessage()
    message["Subject"], message["From"], message["To"] = subject, os.environ["MCS_SMTP_FROM"], os.environ["MCS_BRIEFING_TO"]
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    with smtplib.SMTP(os.environ["MCS_SMTP_HOST"], int(os.getenv("MCS_SMTP_PORT", "587")), timeout=30) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(os.environ["MCS_SMTP_USER"], os.environ["MCS_SMTP_PASSWORD"])
        smtp.send_message(message)


def run_once(store: Store, now: float | None = None, *, client=None, sender=send) -> str:
    """Send today's briefing if it is due and not yet sent. Returns what happened (for logs and tests)."""
    now = time.time() if now is None else now
    if not due(now):
        return "not_due"
    day = lagos_day(now)
    with store.transaction() as s:
        row = s.scalar(select(Record).where(Record.namespace == "briefing", Record.record_id == day).with_for_update())
        body = dict(row.body) if row else {}
        if body.get("status") == "sent":
            return "already_sent"
        if body.get("status") == "sending" and now - body.get("claimed_at", 0) < LEASE_SECONDS:
            return "in_progress"
        if body.get("status") == "failed" and now - body.get("attempted_at", 0) < RETRY_SECONDS:
            return "waiting_retry"
        attempts = int(body.get("attempts", 0)) + 1
        store.put(s, "briefing", day, {**body, "day": day, "status": "sending", "claimed_at": now, "attempts": attempts})
    owned = client is None
    client = client or httpx.Client(timeout=20, follow_redirects=False)
    try:
        data = gather(store, client, now)
        subject, text, html = render(data)
        sender(subject, text, html)
    except Exception as exc:  # noqa: BLE001 - recorded and retried; never crash the loop
        with store.transaction() as s:
            store.put(s, "briefing", day, {"day": day, "status": "failed", "attempts": attempts, "attempted_at": now,
                                           "error": type(exc).__name__})
        log.error("Morning briefing failed: %s", type(exc).__name__)
        return "failed"
    finally:
        if owned:
            client.close()
    with store.transaction() as s:
        store.put(s, "briefing", day, {"day": day, "status": "sent", "attempts": attempts, "sent_at": time.time(),
                                       "subject": subject, "text": text, "needs_you": len(attention(data)),
                                       "sources_missing": sorted(data["errors"])})
        store.audit(s, "workflow:D01", "briefing.sent", day, {"needs_you": len(attention(data))})
    return "sent"


def briefing_current(store: Store, now: float) -> bool:
    """Guardian: today's briefing went out by 07:30 WAT (or, before then, yesterday's did); the sender is alive."""
    with store.transaction() as s:
        beat = s.get(Record, ("heartbeat", "briefing"))
        if not beat or now - beat.updated_at > 300:
            return False
        local = datetime.fromtimestamp(now, LAGOS)
        day = lagos_day(now) if (local.hour, local.minute) >= (7, 30) else lagos_day(now - 86400)
        row = s.get(Record, ("briefing", day))
        if row and row.body.get("status") == "sent":
            return True
        # A fresh install has no earlier day to have sent; only a missed due briefing is a failure.
        first = s.scalar(select(Record.record_id).where(Record.namespace == "briefing").order_by(Record.record_id).limit(1))
        return first is None and day != lagos_day(now)


def main():
    logging.basicConfig(level=logging.INFO)
    for key in ("MCS_SMTP_HOST", "MCS_SMTP_USER", "MCS_SMTP_PASSWORD", "MCS_SMTP_FROM", "MCS_BRIEFING_TO"):
        if not os.getenv(key):
            raise RuntimeError(key + " must be configured for the morning briefing")
    store = configured_store()
    while True:
        try:
            outcome = run_once(store)
            if outcome in {"sent", "failed"}:
                log.info("Morning briefing: %s", outcome)
            with store.transaction() as s:
                store.put(s, "heartbeat", "briefing", {"at": time.time(), "last_outcome": outcome})
        except Exception as exc:  # noqa: BLE001
            log.error("Briefing loop error: %s", type(exc).__name__)
        time.sleep(60)


if __name__ == "__main__":
    main()
