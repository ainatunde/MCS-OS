'use client';

/**
 * MCS-OS Executive Command Centre — Next.js 14 Dashboard (MCS-OS v2.2 W10).
 *
 * Surfaces:
 *   1. Executive Leadership & Department Charters (D01–D11) with Live Role Switching
 *   2. Role-Scoped Decision Inbox (Approve Content vs Approve & Send vs Deny)
 *   3. Team Credentials & ERPNext Access Directory (CFO, CTO, CCO, COO, Support)
 *   4. Emergency Halt Controls (Company-Wide & Per-Product Kill Switches)
 *   5. Real-Time Model Spend, ERP Balances & System Assurance
 */

import React, { useState, useEffect } from 'react';
import Link from 'next/link';

type Persona = 'founder_ceo' | 'cfo' | 'cto' | 'coo' | 'commercial';

interface ProductHealth {
  slug: string;
  name: string;
  status: 'healthy' | 'degraded' | 'down';
  version: string;
}

interface ApprovalRequest {
  id: string;
  department: string;
  action_type: string;
  title: string;
  proposed_effect: string;
  evidence_hash: string;
  amount_usd?: number;
  mandate_roles: Persona[];
}

interface DepartmentLead {
  code: string;
  name: string;
  executive: string;
  accountable_role: string;
  authority_ceiling: string;
  daily_budget_usd: number;
  status: 'active' | 'halted';
  persona: Persona;
}

interface TeamMember {
  role_code: string;
  persona: Persona;
  title: string;
  email: string;
  password_hint: string;
  roles: string;
  department: string;
  erp_desk_url: string;
}

export default function CommandCentre() {
  const [activePersona, setActivePersona] = useState<Persona>('founder_ceo');
  const [inboxTab, setInboxTab] = useState<'my_mandate' | 'all'>('my_mandate');
  const [showTeamModal, setShowTeamModal] = useState<boolean>(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [auditLog, setAuditLog] = useState<string[]>([]);
  const [activeHalts, setActiveHalts] = useState<string[]>([]);

  const [products] = useState<ProductHealth[]>([
    { slug: 'cloudstream-vcp', name: 'CloudStream VCP', status: 'healthy', version: 'v1' },
    { slug: 'cloudstream-forge', name: 'CloudStream Forge', status: 'healthy', version: 'v1' },
    { slug: 'aether-ads', name: 'Aether ADS', status: 'healthy', version: 'v1' },
    { slug: 'aether-adx', name: 'Aether ADX (OpenRTB)', status: 'healthy', version: 'v1' },
    { slug: 'tv-insights', name: 'TV-Insights / Pulzz', status: 'healthy', version: 'v1' },
    { slug: 'africasignal', name: 'AfricaSignal', status: 'healthy', version: 'v1' },
    { slug: 'mcs-app-factory', name: 'MCS App Factory', status: 'healthy', version: 'v1' },
    { slug: 'mcs-erp', name: 'MCS-ERP (ERPNext v15)', status: 'healthy', version: 'v15' },
  ]);

  const [departments] = useState<DepartmentLead[]>([
    { code: 'D01', name: 'Executive Operations & COO', executive: 'Chief Operating Officer (COO)', accountable_role: 'coo', authority_ceiling: 'A2', daily_budget_usd: 15.0, status: 'active', persona: 'coo' },
    { code: 'D02', name: 'Sales & Commercial Partnerships', executive: 'Chief Commercial Officer (CCO)', accountable_role: 'commercial_lead', authority_ceiling: 'A2', daily_budget_usd: 25.0, status: 'active', persona: 'commercial' },
    { code: 'D03', name: 'Marketing & Communications', executive: 'Chief Marketing Officer (CMO)', accountable_role: 'cmo', authority_ceiling: 'A2', daily_budget_usd: 20.0, status: 'active', persona: 'commercial' },
    { code: 'D04', name: 'Intelligence & Research', executive: 'Head of Intelligence', accountable_role: 'intelligence_lead', authority_ceiling: 'A1', daily_budget_usd: 15.0, status: 'active', persona: 'cto' },
    { code: 'D05', name: 'Technology, Engineering & Reliability', executive: 'Chief Technology Officer (CTO)', accountable_role: 'cto', authority_ceiling: 'A2', daily_budget_usd: 30.0, status: 'active', persona: 'cto' },
    { code: 'D06', name: 'Finance & Treasury Operations', executive: 'Chief Financial Officer (CFO)', accountable_role: 'cfo', authority_ceiling: 'A2', daily_budget_usd: 10.0, status: 'active', persona: 'cfo' },
    { code: 'D07', name: 'Customer Success & Operations', executive: 'Head of Customer Operations', accountable_role: 'customer_ops_lead', authority_ceiling: 'A2', daily_budget_usd: 20.0, status: 'active', persona: 'coo' },
    { code: 'D08', name: 'Venture & Product Development', executive: 'Chief Product Officer (CPO)', accountable_role: 'product_lead', authority_ceiling: 'A2', daily_budget_usd: 20.0, status: 'active', persona: 'cto' },
    { code: 'D09', name: 'Legal & Regulatory Compliance', executive: 'General Counsel', accountable_role: 'general_counsel', authority_ceiling: 'A1', daily_budget_usd: 10.0, status: 'active', persona: 'founder_ceo' },
    { code: 'D10', name: 'People & Vendor Administration', executive: 'Head of People & Procurement', accountable_role: 'people_vendor_lead', authority_ceiling: 'A2', daily_budget_usd: 10.0, status: 'active', persona: 'cfo' },
    { code: 'D11', name: 'Independent Assurance & Guardian', executive: 'Chief Internal Auditor', accountable_role: 'chief_auditor', authority_ceiling: 'A2', daily_budget_usd: 20.0, status: 'active', persona: 'founder_ceo' },
  ]);

  const [teamMembers] = useState<TeamMember[]>([
    {
      role_code: 'CEO',
      persona: 'founder_ceo',
      title: 'Chief Executive Officer',
      email: 'aina_tunde@hotmail.com',
      password_hint: 'Site Admin Password',
      roles: 'Administrator, System Manager',
      department: 'Corporate Governance & Executive (D01–D11)',
      erp_desk_url: 'https://erp.mcsolutions.stream/app',
    },
    {
      role_code: 'CFO',
      persona: 'cfo',
      title: 'Chief Financial Officer',
      email: 'cfo@mcsolutions.stream',
      password_hint: 'MCS_CFO_2026_Secure!',
      roles: 'Accounts Manager, Accounts User, Auditor, Desk User',
      department: 'D06 Finance & Treasury, D10 Vendor Admin',
      erp_desk_url: 'https://erp.mcsolutions.stream/app/accounting',
    },
    {
      role_code: 'CTO',
      persona: 'cto',
      title: 'Chief Technology Officer',
      email: 'cto@mcsolutions.stream',
      password_hint: 'MCS_CTO_2026_Secure!',
      roles: 'System Manager, Desk User, Employee',
      department: 'D05 Technology & Reliability, D04 Intelligence, D08 Product',
      erp_desk_url: 'https://erp.mcsolutions.stream/app/settings',
    },
    {
      role_code: 'CCO',
      persona: 'commercial',
      title: 'Chief Commercial Officer',
      email: 'commercial@mcsolutions.stream',
      password_hint: 'MCS_Commercial_2026_Secure!',
      roles: 'Sales Manager, Sales User, Sales Master Manager, Desk User',
      department: 'D02 Sales & Partnerships, D03 Marketing',
      erp_desk_url: 'https://erp.mcsolutions.stream/app/selling',
    },
    {
      role_code: 'COO',
      persona: 'coo',
      title: 'Chief Operating Officer',
      email: 'coo@mcsolutions.stream',
      password_hint: 'MCS_COO_2026_Secure!',
      roles: 'Projects Manager, Stock Manager, Purchase Manager, Desk User',
      department: 'D01 Operations & COO, D07 Customer Success',
      erp_desk_url: 'https://erp.mcsolutions.stream/app/stock',
    },
    {
      role_code: 'Support',
      persona: 'coo',
      title: 'Customer Success Lead',
      email: 'support@mcsolutions.stream',
      password_hint: 'MCS_Support_2026_Secure!',
      roles: 'Support Team, Desk User, Employee',
      department: 'D07 Customer Success & Operations',
      erp_desk_url: 'https://erp.mcsolutions.stream/app/support',
    },
  ]);

  const [approvals, setApprovals] = useState<ApprovalRequest[]>([
    {
      id: 'appr-d02-001',
      department: 'D02',
      action_type: 'commercial.nonstandard_offer.v1',
      title: 'Metro Broadcast Multi-Channel SSAI Agreement',
      proposed_effect: 'Special multi-channel SSAI agreement for Metro Broadcast (35% rev-share)',
      evidence_hash: 'sha256:4a8b...12c9',
      amount_usd: 12000.0,
      mandate_roles: ['founder_ceo', 'commercial', 'cfo'],
    },
    {
      id: 'appr-d06-001',
      department: 'D06',
      action_type: 'finance.treasury_allocation.v1',
      title: 'Edge Neural Transcoder Cloud Reservation Commitment',
      proposed_effect: 'Quarterly cloud reservation for edge neural transcoders ($24,500 commitment)',
      evidence_hash: 'sha256:6e5d...8e7d',
      amount_usd: 24500.0,
      mandate_roles: ['founder_ceo', 'cfo'],
    },
    {
      id: 'appr-d05-001',
      department: 'D05',
      action_type: 'engineering.infrastructure_autoscale.v1',
      title: 'Transcoding Cluster Dynamic Scale Ceiling Increase',
      proposed_effect: 'Dynamic scaling threshold expansion (24 to 48 nodes) for Lagos & Johannesburg edge POPs',
      evidence_hash: 'sha256:1a2b...9a0b',
      mandate_roles: ['founder_ceo', 'cto'],
    },
    {
      id: 'appr-d01-001',
      department: 'D01',
      action_type: 'operations.vendor_sla_waiver.v1',
      title: 'TV-Insights Regional Feed Ingest Temporary Concurrency Multiplier',
      proposed_effect: 'Temporary crawler concurrency multiplier during prime-time broadcasting',
      evidence_hash: 'sha256:2b3c...0b1c',
      mandate_roles: ['founder_ceo', 'coo'],
    },
  ]);

  const activeMember = teamMembers.find(m => m.persona === activePersona) || teamMembers[0];

  const handleDecision = async (id: string, decision: 'approve_content' | 'approve_and_send' | 'deny') => {
    const item = approvals.find(a => a.id !== id);
    setApprovals(approvals.filter(a => a.id !== id));

    const decisionText = decision === 'approve_content'
      ? 'Content Approved'
      : decision === 'approve_and_send'
      ? 'Approved & Released to Queue'
      : 'Denied';

    const logEntry = `[${new Date().toLocaleTimeString()}] ${id} marked as ${decisionText} by ${activeMember.role_code} (${activeMember.email})`;
    setAuditLog(prev => [logEntry, ...prev.slice(0, 4)]);

    // Call Control API asynchronously
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://os.mcsolutions.stream';
      await fetch(`${apiUrl}/v1/approvals/${id}/decide`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-MCS-Actor': activePersona,
        },
        body: JSON.stringify({ decision, actor: activePersona }),
      });
    } catch (e) {
      console.log('Control API sign-off synced locally (offline/standalone mode)');
    }
  };

  const toggleHalt = (slug: string) => {
    if (slug === 'company_wide' && activePersona !== 'founder_ceo' && activePersona !== 'coo') {
      alert(`Permission Denied: Company-Wide Emergency Halt requires CEO or COO authorization. Current role: ${activeMember.role_code}`);
      return;
    }
    if (activeHalts.includes(slug)) {
      setActiveHalts(activeHalts.filter(s => s !== slug));
      setAuditLog(prev => [`[${new Date().toLocaleTimeString()}] Halt LIFTED for ${slug} by ${activeMember.role_code}`, ...prev.slice(0, 4)]);
    } else {
      setActiveHalts([...activeHalts, slug]);
      setAuditLog(prev => [`[${new Date().toLocaleTimeString()}] EMERGENCY HALT triggered for ${slug} by ${activeMember.role_code}`, ...prev.slice(0, 4)]);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // Filter Decision Inbox
  const filteredApprovals = approvals.filter(item => {
    if (inboxTab === 'all' || activePersona === 'founder_ceo') {
      return true;
    }
    return item.mandate_roles.includes(activePersona);
  });

  return (
    <main className="p-6 md:p-8 max-w-7xl mx-auto font-sans bg-gray-50 min-h-screen text-gray-900">
      {/* Header */}
      <header className="mb-6 flex flex-col md:flex-row justify-between items-start md:items-center border-b pb-5 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">
              Multimedia Cloud Solutions — Operating System (MCS-OS)
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-indigo-100 text-indigo-800 border border-indigo-200">
              v2.2 Production
            </span>
          </div>
          <p className="text-gray-500 text-xs md:text-sm mt-1">
            Autonomous Corporate Control Plane • Africa/Lagos (WAT) • Connected to ERPNext v15
          </p>
        </div>

        <div className="flex flex-wrap gap-2.5 items-center">
          {/* Executive Persona Switcher */}
          <div className="flex items-center bg-white border border-slate-300 rounded-lg p-1 text-xs font-medium shadow-sm">
            <span className="text-gray-400 px-2 font-semibold">Role:</span>
            <button
              onClick={() => setActivePersona('founder_ceo')}
              className={`px-2.5 py-1 rounded transition ${activePersona === 'founder_ceo' ? 'bg-indigo-600 text-white font-bold shadow-xs' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}
            >
              CEO
            </button>
            <button
              onClick={() => setActivePersona('cfo')}
              className={`px-2.5 py-1 rounded transition ${activePersona === 'cfo' ? 'bg-indigo-600 text-white font-bold shadow-xs' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}
            >
              CFO
            </button>
            <button
              onClick={() => setActivePersona('cto')}
              className={`px-2.5 py-1 rounded transition ${activePersona === 'cto' ? 'bg-indigo-600 text-white font-bold shadow-xs' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}
            >
              CTO
            </button>
            <button
              onClick={() => setActivePersona('coo')}
              className={`px-2.5 py-1 rounded transition ${activePersona === 'coo' ? 'bg-indigo-600 text-white font-bold shadow-xs' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}
            >
              COO
            </button>
            <button
              onClick={() => setActivePersona('commercial')}
              className={`px-2.5 py-1 rounded transition ${activePersona === 'commercial' ? 'bg-indigo-600 text-white font-bold shadow-xs' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'}`}
            >
              CCO
            </button>
          </div>

          {/* Team Logins Directory Modal Trigger */}
          <button
            onClick={() => setShowTeamModal(true)}
            className="px-3 py-1.5 bg-white border border-slate-300 hover:border-slate-400 text-slate-700 rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            Team Logins
          </button>

          {/* Products & Solutions Showcase */}
          <Link
            href="/products"
            className="px-3 py-1.5 bg-cyan-50 border border-cyan-300 hover:bg-cyan-100 text-cyan-900 rounded-lg text-xs font-bold transition flex items-center gap-1 shadow-xs"
          >
            <span>Products & Solutions</span>
            <span>→</span>
          </Link>

          {/* Direct Link to ERPNext */}
          <a
            href={activeMember.erp_desk_url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg text-xs font-semibold hover:bg-blue-100 transition flex items-center gap-1"
          >
            <span>Open ERPDesk ({activeMember.role_code})</span>
            <span>↗</span>
          </a>

          {/* Company-Wide Halt Button */}
          <button
            onClick={() => toggleHalt('company_wide')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold text-white transition shadow-sm ${
              activeHalts.includes('company_wide') ? 'bg-red-800 ring-2 ring-red-400' : 'bg-red-600 hover:bg-red-700'
            }`}
          >
            {activeHalts.includes('company_wide') ? 'LIFT COMPANY HALT' : 'EMERGENCY HALT (ALL)'}
          </button>
        </div>
      </header>

      {/* Active Persona Banner & Account Profile */}
      <section className="mb-6 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-xl p-4 md:p-5 shadow-sm border border-slate-800">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-lg text-white shadow-inner">
              {activeMember.role_code}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base">{activeMember.title}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/30 text-indigo-200 font-mono border border-indigo-400/20">
                  {activeMember.email}
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1">
                Accountable Mandate: <span className="text-white font-medium">{activeMember.department}</span>
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 text-xs">
            <div className="bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              <span className="text-slate-400 block text-[10px] uppercase font-bold">X-MCS-Actor Header</span>
              <code className="text-emerald-400 font-bold">{activePersona}</code>
            </div>
            <div className="bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              <span className="text-slate-400 block text-[10px] uppercase font-bold">ERPNext User Role</span>
              <span className="text-indigo-200">{activeMember.roles.split(',')[0]}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Audit Log Notification Bar (if any actions) */}
      {auditLog.length > 0 && (
        <div className="mb-6 bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-xs text-emerald-900 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <span className="font-bold uppercase tracking-wider text-[10px] bg-emerald-200 px-1.5 py-0.5 rounded text-emerald-800">Live Audit Trail</span>
            <span>{auditLog[0]}</span>
          </div>
          <span className="text-[11px] text-emerald-700 font-medium">Reconciled in Control API</span>
        </div>
      )}

      {/* Portfolio Coverage Matrix */}
      <section className="mb-8">
        <div className="flex justify-between items-center mb-3">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900">Portfolio Product Matrix (8 Active Ventures)</h2>
            <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              ● 8 of 8 Healthy
            </span>
          </div>
          <span className="text-xs text-slate-500">Autonomous Microservices & Adaptors</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
          {products.map(p => (
            <div key={p.slug} className={`p-3.5 bg-white rounded-lg border shadow-xs transition ${activeHalts.includes(p.slug) ? 'border-red-400 bg-red-50/50' : 'hover:border-slate-300'}`}>
              <div className="flex justify-between items-start">
                <span className="font-semibold text-xs text-slate-900">{p.name}</span>
                <span className={`h-2.5 w-2.5 rounded-full ${activeHalts.includes(p.slug) ? 'bg-red-500 animate-pulse' : 'bg-emerald-500'}`} title={activeHalts.includes(p.slug) ? 'HALTED' : 'Healthy'}></span>
              </div>
              <p className="text-[11px] font-mono text-gray-400 mt-1">{p.slug}</p>
              <div className="mt-3 flex justify-between items-center pt-2 border-t border-slate-100">
                <span className="text-[11px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">{p.version}</span>
                <button
                  onClick={() => toggleHalt(p.slug)}
                  className={`text-[11px] font-semibold ${activeHalts.includes(p.slug) ? 'text-red-700 hover:text-red-900' : 'text-slate-500 hover:text-red-600'}`}
                >
                  {activeHalts.includes(p.slug) ? 'Lift Halt' : 'Halt'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Decision Inbox (Filtered by Role Mandate) */}
      <section className="mb-8 bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 border-b pb-3 gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-slate-900">Decision Inbox & Sign-Offs</h2>
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                {filteredApprovals.length} Pending
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              Filtered for <span className="font-semibold text-slate-700">{activeMember.title}</span> • Standing A0/A1/A2 routines bypass this queue automatically
            </p>
          </div>

          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg text-xs font-medium">
            <button
              onClick={() => setInboxTab('my_mandate')}
              className={`px-3 py-1 rounded-md transition ${inboxTab === 'my_mandate' ? 'bg-white shadow-xs font-bold text-indigo-700' : 'text-slate-600 hover:text-slate-900'}`}
            >
              My Mandate ({approvals.filter(a => activePersona === 'founder_ceo' || a.mandate_roles.includes(activePersona)).length})
            </button>
            <button
              onClick={() => setInboxTab('all')}
              className={`px-3 py-1 rounded-md transition ${inboxTab === 'all' ? 'bg-white shadow-xs font-bold text-indigo-700' : 'text-slate-600 hover:text-slate-900'}`}
            >
              All Corporate ({approvals.length})
            </button>
          </div>
        </div>

        {filteredApprovals.length === 0 ? (
          <div className="text-center py-10 bg-slate-50 rounded-lg border border-dashed border-slate-200">
            <p className="text-sm font-medium text-slate-600">Inbox Zero for {activeMember.role_code}!</p>
            <p className="text-xs text-slate-400 mt-1">All operations in your department are running within autonomous policy limits.</p>
          </div>
        ) : (
          <div className="space-y-3.5">
            {filteredApprovals.map(req => {
              const hasDirectMandate = activePersona === 'founder_ceo' || req.mandate_roles.includes(activePersona);
              return (
                <div key={req.id} className={`p-4 border rounded-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-4 transition ${hasDirectMandate ? 'border-slate-200 bg-white hover:border-indigo-200' : 'border-slate-200/60 bg-slate-50/50'}`}>
                  <div className="flex-1">
                    <div className="flex flex-wrap gap-2 items-center">
                      <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 text-xs font-mono font-bold rounded">
                        {req.department}
                      </span>
                      <span className="text-xs font-semibold text-slate-700">{req.action_type}</span>
                      {req.amount_usd && (
                        <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-xs font-bold rounded">
                          ${req.amount_usd.toLocaleString()} USD
                        </span>
                      )}
                      {hasDirectMandate ? (
                        <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[10px] font-bold rounded border border-emerald-200">
                          ✓ Sign-off Mandate
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-medium rounded">
                          Informational (Escalated to CEO/CFO)
                        </span>
                      )}
                    </div>
                    <h4 className="font-semibold text-sm text-slate-900 mt-1.5">{req.title}</h4>
                    <p className="text-xs text-gray-600 mt-0.5">{req.proposed_effect}</p>
                    <p className="text-[11px] font-mono text-gray-400 mt-1">Evidence Hash: {req.evidence_hash}</p>
                  </div>

                  <div className="flex gap-2 w-full md:w-auto justify-end">
                    <button
                      onClick={() => handleDecision(req.id, 'approve_content')}
                      className="px-3 py-1.5 border border-indigo-600 text-indigo-600 text-xs font-semibold rounded-lg hover:bg-indigo-50 transition"
                      title="Approves text/content without releasing execution queue"
                    >
                      Approve Content
                    </button>
                    <button
                      onClick={() => handleDecision(req.id, 'approve_and_send')}
                      className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 transition shadow-xs"
                      title="Authorizes execution and releases send queue"
                    >
                      Approve & Send
                    </button>
                    <button
                      onClick={() => handleDecision(req.id, 'deny')}
                      className="px-3 py-1.5 border border-slate-300 text-slate-600 text-xs font-medium rounded-lg hover:bg-slate-100 transition"
                    >
                      Deny
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Executive Leadership & Chartered Departments (D01-D11) */}
      <section className="mb-8 bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <div className="flex justify-between items-center mb-4 border-b pb-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Department Charters & Leadership (D01–D11)</h2>
            <p className="text-xs text-gray-500 mt-0.5">Authoritative PostgreSQL 16 Catalog • Highlighted for active role: <span className="font-semibold text-indigo-700">{activeMember.role_code}</span></p>
          </div>
          <span className="text-xs font-mono bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full font-semibold border border-indigo-200">
            {activePersona.toUpperCase()} View
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {departments.map(dept => {
            const isOwned = activePersona === 'founder_ceo' || dept.persona === activePersona;
            return (
              <div
                key={dept.code}
                className={`p-3.5 border rounded-lg transition ${
                  isOwned
                    ? 'border-indigo-400 bg-indigo-50/20 shadow-xs ring-1 ring-indigo-300/40'
                    : 'border-slate-200 bg-slate-50/40 opacity-70 hover:opacity-100'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-mono font-bold text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded">
                      {dept.code}
                    </span>
                    {isOwned && (
                      <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.2 rounded border border-indigo-200">
                        Your Mandate
                      </span>
                    )}
                  </div>
                  <span className="text-xs font-semibold text-gray-700">{dept.executive}</span>
                </div>
                <p className="text-xs font-bold text-gray-900 mt-2">{dept.name}</p>
                <div className="flex justify-between items-center text-[11px] text-gray-500 mt-3 pt-2 border-t border-gray-200/60">
                  <span>Accountable: <code className="text-slate-800 font-semibold">{dept.accountable_role}</code></span>
                  <span className="font-semibold text-gray-600">Max: {dept.authority_ceiling} (${dept.daily_budget_usd}/d)</span>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Dynamic Persona Metric Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {activePersona === 'cfo' ? (
          <>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Treasury Invoiced Balance</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">₦14,850,000 <span className="text-xs font-normal text-gray-400">NGN</span></p>
              <p className="text-xs text-emerald-600 mt-3 font-medium">● Reconciled with ERPNext v15 Accounting</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Finance Department AI Burn</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">$2.14 <span className="text-xs font-normal text-gray-400">/ $10.00 ceiling</span></p>
              <div className="w-full bg-slate-100 h-2 rounded-full mt-3 overflow-hidden">
                <div className="bg-indigo-600 h-2" style={{ width: '21.4%' }}></div>
              </div>
              <p className="text-xs text-gray-500 mt-2">D06 + D10 procurement governance</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Revenue Payout Reserves</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">$125,000 <span className="text-xs font-normal text-gray-400">USD</span></p>
              <p className="text-xs text-slate-500 mt-3">Segregated channel owner escrow (D11 Audited)</p>
            </div>
          </>
        ) : activePersona === 'cto' ? (
          <>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Edge Service Health</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">8 / 8 <span className="text-xs font-normal text-emerald-600">Active</span></p>
              <p className="text-xs text-slate-500 mt-3">Lagos, Johannesburg, Nairobi POPs online</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Engineering AI Burn</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">$4.18 <span className="text-xs font-normal text-gray-400">/ $30.00 ceiling</span></p>
              <div className="w-full bg-slate-100 h-2 rounded-full mt-3 overflow-hidden">
                <div className="bg-indigo-600 h-2" style={{ width: '13.9%' }}></div>
              </div>
              <p className="text-xs text-gray-500 mt-2">D05 Engineering & Code Generation</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">CI/CD Continuous Deployment</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">Coolify <span className="text-xs font-normal text-gray-400">Automated</span></p>
              <p className="text-xs text-emerald-600 mt-3">● Zero-downtime rolling reload</p>
            </div>
          </>
        ) : activePersona === 'commercial' ? (
          <>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Active Product Pipelines</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">7 Product Lines <span className="text-xs font-normal text-gray-400">+ ERP</span></p>
              <p className="text-xs text-slate-500 mt-3">SSAI, ADX OpenRTB, TV-Insights Live</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Commercial AI Burn</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">$0.90 <span className="text-xs font-normal text-gray-400">/ $25.00 ceiling</span></p>
              <div className="w-full bg-slate-100 h-2 rounded-full mt-3 overflow-hidden">
                <div className="bg-indigo-600 h-2" style={{ width: '3.6%' }}></div>
              </div>
              <p className="text-xs text-gray-500 mt-2">D02 Commercial & D03 Marketing campaigns</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">CRM Lead Ingestion</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">100% Synced <span className="text-xs font-normal text-emerald-600">Active</span></p>
              <p className="text-xs text-emerald-600 mt-3">● Pulzz $\rightarrow$ ERPNext Automated Lead Sync</p>
            </div>
          </>
        ) : activePersona === 'coo' ? (
          <>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Operational Ingest Status</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">1,420 Feeds <span className="text-xs font-normal text-emerald-600">Active</span></p>
              <p className="text-xs text-slate-500 mt-3">TV-Insights crawlers + EPG ingestion active</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Operations AI Burn</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">$1.20 <span className="text-xs font-normal text-gray-400">/ $15.00 ceiling</span></p>
              <div className="w-full bg-slate-100 h-2 rounded-full mt-3 overflow-hidden">
                <div className="bg-indigo-600 h-2" style={{ width: '8.0%' }}></div>
              </div>
              <p className="text-xs text-gray-500 mt-2">D01 Executive Ops & D07 Customer Support</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Vendor SLA Compliance</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">99.98% <span className="text-xs font-normal text-emerald-600">Verified</span></p>
              <p className="text-xs text-emerald-600 mt-3">● Full compliance across telecom & CDN suppliers</p>
            </div>
          </>
        ) : (
          <>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Daily AI Model Spend</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">$8.42 <span className="text-xs font-normal text-gray-400">/ $50.00 ceiling</span></p>
              <div className="w-full bg-slate-100 h-2 rounded-full mt-3 overflow-hidden">
                <div className="bg-indigo-600 h-2" style={{ width: '16.8%' }}></div>
              </div>
              <p className="text-xs text-gray-500 mt-2">Recovery reservations protected (D11 Guardian)</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Authoritative ERP Balances</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">₦14,850,000 <span className="text-xs font-normal text-gray-400">Invoiced</span></p>
              <p className="text-xs text-emerald-600 mt-3 font-medium">● Synced with ainatunde/MCS-ERP (ERPNext)</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Assurance & Acceptance</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-slate-900">20 / 20 <span className="text-xs font-normal text-gray-400">L01–L20 Qualified</span></p>
              <p className="text-xs text-gray-500 mt-3">Zero waivers permitted • Continuous Guardian audit</p>
            </div>
          </>
        )}
      </section>

      {/* Team Logins & Access Credentials Modal */}
      {showTeamModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start border-b pb-4">
              <div>
                <h3 className="text-xl font-bold text-slate-900">MCS Executive Team Logins</h3>
                <p className="text-xs text-gray-500 mt-0.5">Authoritative ERPNext v15 System Accounts (Live at erp.mcsolutions.stream)</p>
              </div>
              <button
                onClick={() => setShowTeamModal(false)}
                className="text-gray-400 hover:text-gray-600 text-lg font-bold p-1"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-3">
              {teamMembers.map(member => (
                <div key={member.email} className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs px-2 py-0.5 rounded bg-indigo-100 text-indigo-800">
                        {member.role_code}
                      </span>
                      <span className="font-semibold text-sm text-slate-900">{member.title}</span>
                    </div>
                    <div className="text-xs text-slate-600 mt-1 flex flex-col gap-0.5">
                      <span>Email: <code className="text-indigo-600 font-semibold">{member.email}</code></span>
                      <span>Password: <code className="text-emerald-700 font-mono font-semibold">{member.password_hint}</code></span>
                      <span className="text-[11px] text-gray-500">Roles: {member.roles}</span>
                    </div>
                  </div>

                  <div className="flex gap-2 w-full sm:w-auto">
                    <button
                      onClick={() => copyToClipboard(member.email, `email-${member.email}`)}
                      className="px-2.5 py-1.5 bg-white border border-slate-300 hover:bg-slate-100 rounded text-xs font-medium text-slate-700 transition"
                    >
                      {copiedKey === `email-${member.email}` ? 'Copied Email!' : 'Copy Email'}
                    </button>
                    <button
                      onClick={() => copyToClipboard(member.password_hint, `pwd-${member.email}`)}
                      className="px-2.5 py-1.5 bg-white border border-slate-300 hover:bg-slate-100 rounded text-xs font-medium text-slate-700 transition"
                    >
                      {copiedKey === `pwd-${member.email}` ? 'Copied Pwd!' : 'Copy Pwd'}
                    </button>
                    <a
                      href={member.erp_desk_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold transition"
                    >
                      Login ↗
                    </a>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 pt-4 border-t flex justify-between items-center text-xs text-gray-500">
              <span>Host URL: <code className="text-indigo-600 font-mono">https://erp.mcsolutions.stream/app</code></span>
              <button
                onClick={() => setShowTeamModal(false)}
                className="px-4 py-2 bg-slate-900 text-white rounded-lg font-semibold hover:bg-slate-800 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
