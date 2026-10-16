# Multimedia Cloud Solutions (MCS) — Portfolio & Repository Inventory (W01)

**Revision:** 1.0 • **Date:** 16 October 2026, Africa/Lagos  
**Work Package:** W01 (Discovery, Inventory & Scope Register)  
**Contract Baseline:** MCS-OS Master Specification v2.2  

---

## 1. Verified Repository State

This inventory documents the verified git commit, branch, test status, build mechanism, and runtime contract boundaries for all existing Multimedia Cloud Solutions products.

| Product Slug | Product Name | Repository Path | Branch / Verified Commit | Build & Runtime Profile | Existing Test / CI Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`cloudstream-vcp`** | CloudStream VCP | `cloudstream-vcp/` | `main` (`270f76e`) | Python 3.12 / FastAPI, Caddy, GStreamer/FFmpeg, Valkey | `./verification.sh`, pytest |
| **`cloudstream-forge`** | CloudStream Forge | `cloudstream-forge/` | `main` (`afdb310`) | Node 24 / TypeScript, Android/CTV build tools | `npm test` passing (46/46 passed) |
| **`aether-ads`** | Aether ADS | `AETHER-ADS/` | `main` (`04add8b`) | Go 1.22+ monorepo (`go.work`), Postgres, Valkey, ClickHouse | GitHub CI matrix; RLS tests in `tests/rls` |
| **`aether-adx`** | Aether ADX | `AETHER-ADS/openrtb` | `main` (`04add8b`) | Go OpenRTB 2.5/3.0 SSP & Prebid Server module | OpenRTB unit tests in Go |
| **`tv-insights`** | TV-Insights / Pulzz | `tv-insights/` | `feat/channel-owner-research` (`d289a5e`) | Python 3.12 / FastAPI / SQLAlchemy / SQLite/PG | `pytest` test suite, Guardian checks |
| **`africasignal`** | AfricaSignal | `AfricaSignal-autonomy-implementation/` | `main` (`ca74a51`) | Python 3.12 / FastAPI / Alembic 0056 | CI Run 73 passed (2,141 passed) |
| **`mcs-app-factory`** | MCS App Factory | `mcs-platform/` | `master` (`3c8cb01`) | Python 3.12 / FastAPI / Alembic 008, Next.js | `./scripts/ci.sh` 6-gate harness, 192 unit tests |
| **`mcs-erp`** *(P06)* | MCS-ERP (ERPNext) | `MCS-ERP-review/` | `main` (`5f50996`) | Python 3.12 client / Frappe ERPNext v15 + MariaDB/Redis | `test_mcs_os_adapter.py` ALL PASS, `test_mock_erp.py` ALL PASS |

---

## 2. Detailed Product Integrity & Integration Contracts

### 2.1 `cloudstream-vcp` (Live Broadcast & SSAI Engine)
- **Verified Capabilities:**
  - `health.read.v1`: `/healthz` endpoint returning live ingest, GPU logo tracker, FFT acoustic, and VLM escalation states.
  - `metrics.read.v1`: Active channel concurrency, ad break counts, ad impression counts, and fill rates.
  - `support.diagnose.v1`: Stream lag, SCTE-35 markerless break detection confidence score, manifest generation latency.
  - `release.deploy.v1`: Channel onboarding and stream profile configuration.
- **Invariants:**
  - Retains its own stream ingest and customer token validation contracts.
  - Does not compute authoritative billing figures in prose; outputs raw stream and impression telemetry to the OS event ingress.

### 2.2 `cloudstream-forge` (White-Label FAST TV Platform)
- **Verified Capabilities:**
  - `build.generate.v1`: Generation of white-label Android TV, mobile, and web FAST clients.
  - `telemetry.client.v1`: ExperienceBus WebSocket health, DVR scrub suppression, presence and reaction stats.
  - `support.diagnose.v1`: Client bootstrap latency, token refresh cycle diagnostics.
- **Invariants:**
  - A successful build does not imply working video playback; customer playback metrics must be verified on staging before release.

### 2.3 `aether-ads` & `aether-adx` (Ad Decision Server & Programmatic Exchange)
- **Deployment Independence Verification (§6.2):**
  - While `openrtb` lives in the `AETHER-ADS` monorepo, `Aether ADX` is treated as an independent product entity.
  - `Aether ADX` and `Aether ADS` communicate through versioned OpenRTB HTTP endpoints (e.g., `/v1/openrtb/auction`), not shared database transactions or shared internal Go structs.
- **Verified Capabilities (`aether-ads`):**
  - `decision.serve.v1`: Direct-sold and house ad serving (sub-3ms p99 at 15k RPS).
  - `budget.reserve.v1`: Valkey two-phase campaign budget reservation.
  - `floor.adjust.v1`: Dynamic floor pricing adjustments with bounded movement ($\pm 10\%$).
- **Verified Capabilities (`aether-adx`):**
  - `exchange.auction.v1`: OpenRTB bid prefetcher, SSP auction resolution, Prebid Server connectivity.
  - `exchange.settlement.v1`: Partner bid reconciliation and clearing price telemetry.

### 2.4 `tv-insights` (Broadcast & Media Intelligence)
- **Verified Capabilities:**
  - `intelligence.query.v1`: Programme rankings, EPG schedule revision alerts, advertiser share-of-voice data.
  - `guardian.health.v1`: Guardian self-healing supervisor and incident alerts.
- **Invariants:**
  - Channel rankings indicate observed broadcast schedules and talent metadata; they do not prove broadcast carriage rights or verified viewer counts without primary measurement records.

### 2.5 `africasignal` (Economic & Policy Sensemaking)
- **Verified Capabilities:**
  - `sensemaking.assess.v1`: Deterministic T1 (price change) and T2 (policy rate) assessments.
  - `publish.social.v1`: Outbox-mediated fact dispatch to X, Facebook, and Telegram.
- **Invariants:**
  - Bounded to structured, cited claims. Output that fails semantic grounding or negation tests abstains.

### 2.6 `mcs-app-factory` (Verified Information App Factory)
- **Verified Active Applications (§1.1):**
  - **`visatrack-africa`** (`VisaTrack Africa` / `visatrack.africa`): UK/Canada immigration policies and official tracking.
  - **`skilledpath-africa`** (`SkilledPath Africa` / `skilledpath.africa`): Global skilled trade pathways and licensing guidance.
- **Verified Capabilities:**
  - `demand.radar.v1`: Ingest and rank unfulfilled consumer search queries and topic coverage gaps.
  - `verification.hashchain.v1`: Hash-chained document snapshotting and fact adjudication.
  - `tenant.provision.v1`: Zero-touch tenant website rendering and sitemap generation.

### 2.7 `mcs-erp` (Authoritative Business-Record Platform — Decision P06)
- **System Identity:** Self-hosted `ainatunde/MCS-ERP` (ERPNext v15 + Frappe `hrms`).
- **Verified Capabilities (`adapter/mcs-erp/v1`):**
  - `crm.lead.upsert.v1` & `crm.opportunity.upsert.v1` (D02 Commercial).
  - `finance.sales_invoice.create_draft.v1` & `finance.payment_entry.create_draft.v1` (D06 Finance).
  - `support.issue.create.v1` & `support.issue.update_status.v1` (D07 Customer Support).
  - `procurement.purchase_order.create_draft.v1` (D10 Vendor Operations).
- **Invariants:**
  - MCS-OS passes an immutable `ActionEnvelope` carrying `canonical_payload_hash`, `idempotency_key`, and `mcs_external_ref`.
  - ERPNext owns customer, supplier, general ledger, and invoice records; MCS-OS never maintains conflicting shadow accounts.
