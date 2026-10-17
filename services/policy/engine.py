"""Deterministic Policy Evaluation Engine (A0-A4 Authority Gates).

Governed by MCS-OS Master Specification v2.2 Section 5:
  - 5.1 Authority classes: A0 (Observe), A1 (Routine internal),
    A2 (Bounded execution), A3 (Principal approval), A4 (Prohibited).
  - 5.2 Launch authority matrix.
  - 5.3 Authorization record binding & hash verification.
  - 5.4 Capability qualification & fault containment (emergency halts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from contracts.actions.envelope import ActionEnvelope, AuthorityClass, canonical_payload_hash


@dataclass
class PolicyRule:
    action_type: str
    department: str
    authority_class: AuthorityClass
    max_amount_usd: Optional[float] = None
    requires_evidence: bool = False
    supported_products: Set[str] = field(default_factory=set)


# Master Action Catalog mapping to Section 5.2 & Section 3.3
ACTION_CATALOG: Dict[str, PolicyRule] = {
    # A0 Observe
    "intelligence.observe.v1": PolicyRule("intelligence.observe.v1", "D04", AuthorityClass.A0),
    "intelligence.radar.collect.v1": PolicyRule("intelligence.radar.collect.v1", "D04", AuthorityClass.A0),
    "telemetry.read.v1": PolicyRule("telemetry.read.v1", "D05", AuthorityClass.A0),
    "stream.diagnose.v1": PolicyRule("stream.diagnose.v1", "D05", AuthorityClass.A0),
    "adbreak.telemetry.read.v1": PolicyRule("adbreak.telemetry.read.v1", "D05", AuthorityClass.A0),
    "app.experience_bus.diagnose.v1": PolicyRule("app.experience_bus.diagnose.v1", "D05", AuthorityClass.A0),
    "adserving.health.read.v1": PolicyRule("adserving.health.read.v1", "D05", AuthorityClass.A0),
    "openrtb.auction.telemetry.read.v1": PolicyRule("openrtb.auction.telemetry.read.v1", "D05", AuthorityClass.A0),
    "tenant.manifest.read.v1": PolicyRule("tenant.manifest.read.v1", "D01", AuthorityClass.A0),
    "guardian.health.probe.v1": PolicyRule("guardian.health.probe.v1", "D11", AuthorityClass.A0),
    "venture.research.v1": PolicyRule("venture.research.v1", "D08", AuthorityClass.A0),

    # A1 Routine internal
    "coo.briefing.compile.v1": PolicyRule("coo.briefing.compile.v1", "D01", AuthorityClass.A1),
    "coo.task.prioritize.v1": PolicyRule("coo.task.prioritize.v1", "D01", AuthorityClass.A1),
    "coo.exception.escalate.v1": PolicyRule("coo.exception.escalate.v1", "D01", AuthorityClass.A1),
    "executive.briefing.generate.v1": PolicyRule("executive.briefing.generate.v1", "D01", AuthorityClass.A1),
    "crm.lead.upsert.v1": PolicyRule("crm.lead.upsert.v1", "D02", AuthorityClass.A1),
    "crm.opportunity.upsert.v1": PolicyRule("crm.opportunity.upsert.v1", "D02", AuthorityClass.A1),
    "crm.opportunity.mark_lost.v1": PolicyRule("crm.opportunity.mark_lost.v1", "D02", AuthorityClass.A1),
    "intelligence.signal.route.v1": PolicyRule("intelligence.signal.route.v1", "D04", AuthorityClass.A1),
    "claims.verify.v1": PolicyRule("claims.verify.v1", "D04", AuthorityClass.A1),
    "runner.assessment.execute.v1": PolicyRule("runner.assessment.execute.v1", "D04", AuthorityClass.A1),
    "engineering.ci.verify.v1": PolicyRule("engineering.ci.verify.v1", "D05", AuthorityClass.A1),
    "engineering.pr.create.v1": PolicyRule("engineering.pr.create.v1", "D05", AuthorityClass.A1),
    "schedule.feed.sync.v1": PolicyRule("schedule.feed.sync.v1", "D05", AuthorityClass.A1),
    "finance.customer.upsert.v1": PolicyRule("finance.customer.upsert.v1", "D06", AuthorityClass.A1),
    "finance.reconciliation.verify.v1": PolicyRule("finance.reconciliation.verify.v1", "D06", AuthorityClass.A1),
    "venture.brief.generate.v1": PolicyRule("venture.brief.generate.v1", "D08", AuthorityClass.A1),
    "compliance.rights.audit.v1": PolicyRule("compliance.rights.audit.v1", "D09", AuthorityClass.A1),
    "compliance.retraction.issue.v1": PolicyRule("compliance.retraction.issue.v1", "D09", AuthorityClass.A1),
    "compliance.privacy.export.v1": PolicyRule("compliance.privacy.export.v1", "D09", AuthorityClass.A1),
    "procurement.supplier.upsert.v1": PolicyRule("procurement.supplier.upsert.v1", "D10", AuthorityClass.A1),
    "assurance.controls.audit.v1": PolicyRule("assurance.controls.audit.v1", "D11", AuthorityClass.A1),

    # A2 Bounded execution
    "commercial.outreach.send.v1": PolicyRule("commercial.outreach.send.v1", "D02", AuthorityClass.A2, requires_evidence=True),
    "crm.quotation.create_draft.v1": PolicyRule("crm.quotation.create_draft.v1", "D02", AuthorityClass.A2),
    "crm.sales_order.create_draft.v1": PolicyRule("crm.sales_order.create_draft.v1", "D02", AuthorityClass.A2),
    "campaign.create_direct.v1": PolicyRule("campaign.create_direct.v1", "D02", AuthorityClass.A2),
    "floor.adjust_dynamic.v1": PolicyRule("floor.adjust_dynamic.v1", "D02", AuthorityClass.A2),
    "openrtb.dsp.onboard.v1": PolicyRule("openrtb.dsp.onboard.v1", "D02", AuthorityClass.A2),
    "content.social.publish.v1": PolicyRule("content.social.publish.v1", "D03", AuthorityClass.A2, requires_evidence=True),
    "content.editorial.publish.v1": PolicyRule("content.editorial.publish.v1", "D03", AuthorityClass.A2, requires_evidence=True),
    "content.correction.withdraw.v1": PolicyRule("content.correction.withdraw.v1", "D03", AuthorityClass.A2),
    "engineering.release.deploy_staging.v1": PolicyRule("engineering.release.deploy_staging.v1", "D05", AuthorityClass.A2),
    "engineering.runbook.execute.v1": PolicyRule("engineering.runbook.execute.v1", "D05", AuthorityClass.A2),
    "channel.onboard.v1": PolicyRule("channel.onboard.v1", "D07", AuthorityClass.A2),
    "app.build.generate.v1": PolicyRule("app.build.generate.v1", "D08", AuthorityClass.A2),
    "finance.invoice.create_draft.v1": PolicyRule("finance.invoice.create_draft.v1", "D06", AuthorityClass.A2),
    "finance.invoice.submit_a2.v1": PolicyRule("finance.invoice.submit_a2.v1", "D06", AuthorityClass.A2, max_amount_usd=25000.0),
    "finance.credit_note.create_draft.v1": PolicyRule("finance.credit_note.create_draft.v1", "D06", AuthorityClass.A2),
    "finance.payment.record_draft.v1": PolicyRule("finance.payment.record_draft.v1", "D06", AuthorityClass.A2),
    "finance.payment.submit_a2.v1": PolicyRule("finance.payment.submit_a2.v1", "D06", AuthorityClass.A2, max_amount_usd=25000.0),
    "finance.journal.create_draft.v1": PolicyRule("finance.journal.create_draft.v1", "D06", AuthorityClass.A2),
    "support.issue.create.v1": PolicyRule("support.issue.create.v1", "D07", AuthorityClass.A2),
    "support.issue.update_status.v1": PolicyRule("support.issue.update_status.v1", "D07", AuthorityClass.A2),
    "support.ticket.triage.v1": PolicyRule("support.ticket.triage.v1", "D07", AuthorityClass.A2),
    "support.subscriber.help.v1": PolicyRule("support.subscriber.help.v1", "D07", AuthorityClass.A2),
    "venture.scaffold.execute.v1": PolicyRule("venture.scaffold.execute.v1", "D08", AuthorityClass.A2),
    "procurement.purchase_order.create_draft.v1": PolicyRule("procurement.purchase_order.create_draft.v1", "D10", AuthorityClass.A2, max_amount_usd=500.0),
    "procurement.po.create_draft.v1": PolicyRule("procurement.po.create_draft.v1", "D10", AuthorityClass.A2, max_amount_usd=500.0),
    "procurement.purchase_invoice.create_draft.v1": PolicyRule("procurement.purchase_invoice.create_draft.v1", "D10", AuthorityClass.A2, max_amount_usd=500.0),
    "vendor.access.revoke.v1": PolicyRule("vendor.access.revoke.v1", "D10", AuthorityClass.A2),
    "guardian.recovery.runbook.execute.v1": PolicyRule("guardian.recovery.runbook.execute.v1", "D11", AuthorityClass.A2),

    # A3 Principal approval (Always requires fresh exact approval)
    "commercial.nonstandard_offer.v1": PolicyRule("commercial.nonstandard_offer.v1", "D02", AuthorityClass.A3),
    "finance.treasury_transfer.v1": PolicyRule("finance.treasury_transfer.v1", "D06", AuthorityClass.A3),
    "engineering.production_deploy.v1": PolicyRule("engineering.production_deploy.v1", "D05", AuthorityClass.A3),
    "venture.incubation.greenlight.v1": PolicyRule("venture.incubation.greenlight.v1", "D08", AuthorityClass.A3),

    # A4 Prohibited for agent execution
    "legal.contract.sign.v1": PolicyRule("legal.contract.sign.v1", "D09", AuthorityClass.A4),
    "people.hiring_firing.v1": PolicyRule("people.hiring_firing.v1", "D10", AuthorityClass.A4),
    "security.override_policy.v1": PolicyRule("security.override_policy.v1", "D11", AuthorityClass.A4),
}


@dataclass
class PolicyDecision:
    admitted: bool
    requires_approval: bool
    assigned_authority: AuthorityClass
    reasons: List[str] = field(default_factory=list)
    canonical_hash: str = ""
    promoted_state: str = "proposed"

    @property
    def is_authorized(self) -> bool:
        return self.admitted and not self.requires_approval


class PolicyEngine:
    def __init__(self):
        self.catalog = ACTION_CATALOG
        self.active_halts: Set[str] = set()  # set of product_slug or "company_wide"
        self.valid_approvals: Dict[str, str] = {}  # approval_ref -> approved canonical_payload_hash

    def register_halt(self, scope: str) -> None:
        """Sets an emergency halt on 'company_wide' or a specific product_slug."""
        self.active_halts.add(scope)

    def lift_halt(self, scope: str) -> None:
        self.active_halts.discard(scope)

    def record_approval(self, approval_ref: str, payload_hash: str) -> None:
        self.valid_approvals[approval_ref] = payload_hash

    def revoke_approval(self, approval_ref: str) -> bool:
        return self.valid_approvals.pop(approval_ref, None) is not None

    @staticmethod
    def _extract_amount_usd(payload: dict) -> Optional[float]:
        for key in ("amount_usd", "total_amount_usd", "amount", "grand_total"):
            if key in payload and payload[key] is not None:
                try:
                    return float(payload[key])
                except (TypeError, ValueError):
                    return None
        return None

    def evaluate(self, envelope: ActionEnvelope) -> PolicyDecision:
        # 1. Emergency Halt Check
        if "company_wide" in self.active_halts:
            return PolicyDecision(
                admitted=False,
                requires_approval=False,
                assigned_authority=AuthorityClass.A4,
                reasons=["Company-wide emergency halt is active."],
                canonical_hash=envelope.canonical_payload_hash,
                promoted_state="rejected",
            )
        if envelope.product_slug in self.active_halts:
            return PolicyDecision(
                admitted=False,
                requires_approval=False,
                assigned_authority=AuthorityClass.A4,
                reasons=[f"Emergency halt is active on product: {envelope.product_slug}"],
                canonical_hash=envelope.canonical_payload_hash,
                promoted_state="rejected",
            )

        # 2. Action Catalog Lookup
        rule = self.catalog.get(envelope.action_type)
        if not rule:
            return PolicyDecision(
                admitted=False,
                requires_approval=False,
                assigned_authority=AuthorityClass.A4,
                reasons=[f"Action type '{envelope.action_type}' is unknown or not in action catalog."],
                canonical_hash=envelope.canonical_payload_hash,
                promoted_state="rejected",
            )

        # 3. Payload Integrity Check
        calc_hash = canonical_payload_hash(envelope.payload)
        if calc_hash != envelope.canonical_payload_hash:
            return PolicyDecision(
                admitted=False,
                requires_approval=False,
                assigned_authority=rule.authority_class,
                reasons=[f"Payload hash mismatch: envelope says {envelope.canonical_payload_hash}, calculated {calc_hash}"],
                canonical_hash=calc_hash,
                promoted_state="rejected",
            )

        # 4. Authority Class A4 Prohibition Check
        if rule.authority_class == AuthorityClass.A4:
            return PolicyDecision(
                admitted=False,
                requires_approval=False,
                assigned_authority=AuthorityClass.A4,
                reasons=[f"Action type '{envelope.action_type}' is strictly prohibited for agent execution (A4)."],
                canonical_hash=calc_hash,
                promoted_state="rejected",
            )

        # 5. Department Ownership Check
        if envelope.department_id != rule.department:
            return PolicyDecision(
                admitted=False,
                requires_approval=False,
                assigned_authority=rule.authority_class,
                reasons=[
                    f"Department ownership violation: '{envelope.action_type}' belongs to {rule.department}, "
                    f"not {envelope.department_id}."
                ],
                canonical_hash=calc_hash,
                promoted_state="rejected",
            )

        # 6. Product Scope Check (if restricted on rule)
        if rule.supported_products and envelope.product_slug not in rule.supported_products:
            return PolicyDecision(
                admitted=False,
                requires_approval=False,
                assigned_authority=rule.authority_class,
                reasons=[
                    f"Product scope violation: '{envelope.action_type}' is not permitted on {envelope.product_slug}."
                ],
                canonical_hash=calc_hash,
                promoted_state="rejected",
            )

        # 7. Evidence Requirements
        if rule.requires_evidence and not envelope.evidence_citations:
            return PolicyDecision(
                admitted=False,
                requires_approval=False,
                assigned_authority=rule.authority_class,
                reasons=[f"Action type '{envelope.action_type}' requires verifiable evidence citations."],
                canonical_hash=calc_hash,
                promoted_state="rejected",
            )

        # 8. Monetary Ceiling Escalation (A2 -> A3 when amount exceeds rule.max_amount_usd)
        effective_authority = rule.authority_class
        if rule.max_amount_usd is not None:
            amount = self._extract_amount_usd(envelope.payload)
            if amount is not None and amount > rule.max_amount_usd:
                effective_authority = AuthorityClass.A3

        # 9. A3 Human Approval Required
        if effective_authority == AuthorityClass.A3:
            if not envelope.authorization_ref:
                return PolicyDecision(
                    admitted=False,
                    requires_approval=True,
                    assigned_authority=AuthorityClass.A3,
                    reasons=["Action requires explicit authenticated principal approval (A3)."],
                    canonical_hash=calc_hash,
                    promoted_state="awaiting_approval",
                )
            approved_hash = self.valid_approvals.get(envelope.authorization_ref)
            if approved_hash != calc_hash:
                return PolicyDecision(
                    admitted=False,
                    requires_approval=True,
                    assigned_authority=AuthorityClass.A3,
                    reasons=["Approval reference does not match the canonical payload hash."],
                    canonical_hash=calc_hash,
                    promoted_state="awaiting_approval",
                )

        # 10. A2 Standing Execution or A1/A0 Internal
        return PolicyDecision(
            admitted=True,
            requires_approval=False,
            assigned_authority=effective_authority,
            reasons=["All policy checks passed."],
            canonical_hash=calc_hash,
            promoted_state="ready",
        )
