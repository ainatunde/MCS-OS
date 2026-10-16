# Principal Decision Register: P01–P07 (W01)

**Revision:** 1.0 • **Date:** 16 October 2026, Africa/Lagos  
**Work Package:** W01 (Decision Register)  
**Governed By:** MCS-OS Master Specification v2.2 Section 15  

---

## 1. Decision Records

### P01: Authoritative Existing Product & Application Inventory
- **Decision:** The authoritative product registry consists of:
  1. `cloudstream-vcp` (Live Broadcast & SSAI Engine)
  2. `cloudstream-forge` (White-Label FAST Platform)
  3. `aether-ads` (Ad Decision Server)
  4. `aether-adx` (OpenRTB Exchange — separately deployable over HTTP contracts)
  5. `tv-insights` (Broadcast & Media Intelligence / Pulzz)
  6. `africasignal` (Economic & Policy Sensemaking)
  7. `mcs-app-factory` (Verified Information App Factory — active tenants `visatrack-africa` and `skilledpath-africa`)
- **Accountable Roles:**
  - Founder / CEO & Board: Tunde Aina
  - Operating Lead (D01): Autonomous COO Agent
  - Integration Owner (W04): Autonomous CTO Agent
- **Status:** **Ratified**.

---

### P02: Company, Product & Department Budgets
- **Decision:**
  - Company Daily AI Spend Ceiling: **$15.00 USD**
  - Department Daily Ceilings:
    - Commercial (D02): $3.00 USD
    - Communications / CMO (D03): $2.50 USD
    - Intelligence (D04): $2.00 USD
    - Technology / CTO (D05): $2.50 USD
    - Customer Support (D07): $2.00 USD
    - Venture / Product (D08): $1.50 USD
    - Executive / Governance (D01, D06, D09, D10, D11): $1.50 USD
  - Reserve Cap: Every LangGraph cycle reserves estimated maximum cost in Valkey before LLM invocation. Unused quota settles immediately; uncertain timeouts remain reserved until reconciled.
- **Status:** **Ratified**.

---

### P03: Contact Eligibility, Approved Offers & Campaign Permissions
- **Decision:**
  - Commercial Outreach (D02): Permitted exclusively to verified business contacts at NBC-licensed broadcasters and verified digital publishers. Suppression lists strictly enforced. Unsolicited bulk messaging strictly forbidden (A4).
  - Standard Offers: Zero-upfront onboarding with standard revenue share (40% Content Partner / 15% Platform / 45% Net MCS per CloudStream VCP charter). Any deviation from this schedule requires explicit A3 approval.
  - Content Publishing (D03): All outbound assertions must link directly to structured claims or official measurement records. If semantic grounding or negation tests fail, the workflow must abstain.
- **Status:** **Ratified**.

---

### P04: Hosting Arrangement, Deployment & Recovery Targets
- **Decision:**
  - Primary Hosting: Self-hosted VPS managed via Coolify container runner.
  - Authoritative Control DB: PostgreSQL 16 Alpine container with WAL archiving.
  - Recovery Time Objective (RTO): Restore control plane within **60 minutes** during DR drills.
  - Recovery Point Objective (RPO): Primary-data loss capped at **5 minutes**.
  - Off-Host External Monitor: Independent external heartbeat listener outside the primary VPS failure domain.
- **Status:** **Ratified**.

---

### P05: Source-Use, Retention & Jurisdiction Obligations
- **Decision:**
  - Republication Rule: Ingested source text cannot be republished verbatim unless `may_republish_numbers` or explicit license grant is verified.
  - Bounded Pointers: MCS-OS retains citation triples (source, date, passage hash, URL pointer) rather than storing full copyrighted third-party texts.
  - DSAR / Deletion: Deletion requests delete the subject record and purge derived vector embeddings.
- **Status:** **Ratified**.

---

### P06: Authoritative Accounting, CRM & Support Systems
- **Decision (Resolved 2026-10-16):**
  - **Platform Selection:** `ainatunde/MCS-ERP` (self-hosted ERPNext v15 + Frappe `hrms`).
  - **Ownership Boundary:** ERPNext is the single source of truth for:
    - General Ledger, Invoices & Payments (D06 Finance)
    - Leads, Opportunities & Quotes (D02 Commercial)
    - Issues, Tickets & 24/7 SLA Tracking (D07 Customer Support)
    - Suppliers, Purchase Orders & Payroll (D10 Vendor Operations)
  - **Integration Architecture:** Scoped `adapter/mcs-erp/v1` (§6.1 protocol) using `ActionEnvelope` and `mcs_external_ref`. MCS-OS stores external document references, eliminating duplicate customer masters or shadow accounting balances.
- **Status:** **Ratified & Implementation Validated**.

---

### P07: Acceptance Baseline, Live Tests & Emergency Contacts
- **Decision:**
  - Single Integrated Launch Gate: L01–L20 acceptance contract is mandatory for all shared controls and required routine workflows (§3.3).
  - Risk-Based Evaluation: Workflow families are governed by signed stratified evaluation plans (§8.1) with zero critical permission or hallucination failures.
  - Emergency Halt: An authoritative emergency halt immediately halts execution admissions across the target scope.
- **Status:** **Ratified**.
