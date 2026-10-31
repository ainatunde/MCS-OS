# Pulzz / ERPNext integration

The control API stores source events, actions, approvals, halts, directives,
provider outcomes, callbacks, incidents and heartbeats in PostgreSQL. ERPNext
owns business/accounting documents; Pulzz owns source eligibility, consent and
product access. Product attribution (`tv-insights`) is distinct from the
execution provider (`mcs-erp`).

Pulzz signs complete versioned events; the OS verifies scoped credentials and
durably deduplicates content before routing. A supervised worker rechecks the
current product source, calls the private ERP gateway, verifies the receipt and
returns immutable, sequenced receipts to Pulzz. Expired dispatched leases only
reconcile; ambiguous outcomes are never blindly resent. Unchanged documents
receive periodic freshness receipts. Derived approval/invoice projections do
not create a second economic order.

Qualified workflows create/adopt draft invoices for plans, reports, confirmed
lead deliveries and priced sponsorships, plus explicitly enabled consented CRM.
Draft creation is an applied operation, not posting, payment or access. Posting
is denied to the recurring ERP account. Existing operator approval remains the
access decision; paid access requires a fresh verified submitted/part-paid/paid
invoice. Legacy approved access backed only by a draft is an exception for
finance review, never silently revoked or represented as paid.

Individual identity remains an ERP session checked on each protected request.
Approval dispatch revalidates the encrypted originating ERP session, local
revocation, role, expiry and exact immutable action content. Database/runtime
credentials are separate from migration credentials and excluded from images.

Guardian checks worker/Guardian freshness, signed dependency connectivity,
queue/action lag, unknown age, callback delivery, quarantine, unresolved
reconciliation and source withdrawal exceptions. Read-only health probes cannot
refresh a stopped Guardian. The Pulzz Guardian independently probes OS health;
bounded native `corporate_sync` recovery retries only immutable source events.
Financial mismatches require authoritative recheck or finance disposition.

Deployment needs additive migrations and restricted runtime roles before the
API starts, scoped product identity provisioning, a pinned private gateway image,
the variables in `.env.example`, and disabling the legacy recurring invoice
creator. Compose supervises and caps API, worker, Guardian and gateway. Back up
before migration. Rollback halts admission, retains journals and reconciles
ambiguous outcomes before any replay; it does not restore over newer external
financial effects.

Qualification uses real PostgreSQL, real HTTP between the three services and a
separate real Frappe/ERPNext QA site. Company-wide eleven-department readiness
remains false; this release does not qualify unrelated portfolio workflows.
