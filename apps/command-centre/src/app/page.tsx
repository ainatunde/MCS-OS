'use client';

/**
 * MCS-OS Executive Command Centre — Next.js 14 Dashboard (MCS-OS v2.2 W10).
 *
 * Surfaces:
 *   1. Executive Leadership & Department Charters (D01–D11) with Role Switching
 *   2. Portfolio Health Matrix (7 Products + ERPNext)
 *   3. Decision Inbox (Approve Content vs Approve & Send vs Deny)
 *   4. Emergency Halt Controls (Company-Wide & Per-Product Kill Switches)
 *   5. Real-Time Model Spend, ERP Balances & System Assurance
 */

import React, { useState } from 'react';

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
  proposed_effect: string;
  evidence_hash: string;
  amount_usd?: number;
}

interface DepartmentLead {
  code: string;
  name: string;
  executive: string;
  accountable_role: string;
  authority_ceiling: string;
  daily_budget_usd: number;
  status: 'active' | 'halted';
}

export default function CommandCentre() {
  const [activePersona, setActivePersona] = useState<'founder_ceo' | 'cto' | 'cfo' | 'coo'>('founder_ceo');

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
    { code: 'D01', name: 'Executive Operations & COO', executive: 'Chief Operating Officer (COO)', accountable_role: 'coo', authority_ceiling: 'A2', daily_budget_usd: 15.0, status: 'active' },
    { code: 'D02', name: 'Sales & Commercial Partnerships', executive: 'Chief Commercial Officer (CCO)', accountable_role: 'commercial_lead', authority_ceiling: 'A2', daily_budget_usd: 25.0, status: 'active' },
    { code: 'D03', name: 'Marketing & Communications', executive: 'Chief Marketing Officer (CMO)', accountable_role: 'cmo', authority_ceiling: 'A2', daily_budget_usd: 20.0, status: 'active' },
    { code: 'D04', name: 'Intelligence & Research', executive: 'Head of Intelligence', accountable_role: 'intelligence_lead', authority_ceiling: 'A1', daily_budget_usd: 15.0, status: 'active' },
    { code: 'D05', name: 'Technology, Engineering & Reliability', executive: 'Chief Technology Officer (CTO)', accountable_role: 'cto', authority_ceiling: 'A2', daily_budget_usd: 30.0, status: 'active' },
    { code: 'D06', name: 'Finance & Treasury Operations', executive: 'Chief Financial Officer (CFO)', accountable_role: 'cfo', authority_ceiling: 'A2', daily_budget_usd: 10.0, status: 'active' },
    { code: 'D07', name: 'Customer Success & Operations', executive: 'Head of Customer Operations', accountable_role: 'customer_ops_lead', authority_ceiling: 'A2', daily_budget_usd: 20.0, status: 'active' },
    { code: 'D08', name: 'Venture & Product Development', executive: 'Chief Product Officer (CPO)', accountable_role: 'product_lead', authority_ceiling: 'A2', daily_budget_usd: 20.0, status: 'active' },
    { code: 'D09', name: 'Legal & Regulatory Compliance', executive: 'General Counsel', accountable_role: 'general_counsel', authority_ceiling: 'A1', daily_budget_usd: 10.0, status: 'active' },
    { code: 'D10', name: 'People & Vendor Administration', executive: 'Head of People & Procurement', accountable_role: 'people_vendor_lead', authority_ceiling: 'A2', daily_budget_usd: 10.0, status: 'active' },
    { code: 'D11', name: 'Independent Assurance & Guardian', executive: 'Chief Internal Auditor', accountable_role: 'chief_auditor', authority_ceiling: 'A2', daily_budget_usd: 20.0, status: 'active' },
  ]);

  const [approvals, setApprovals] = useState<ApprovalRequest[]>([
    {
      id: 'appr-d02-001',
      department: 'D02',
      action_type: 'commercial.nonstandard_offer.v1',
      proposed_effect: 'Special multi-channel SSAI agreement for Metro Broadcast (35% rev-share)',
      evidence_hash: 'sha256:4a8b...12c9',
      amount_usd: 12000.0,
    },
    {
      id: 'appr-d03-002',
      department: 'D03',
      action_type: 'content.campaign.launch.v1',
      proposed_effect: 'Q4 West Africa Linear Ad Benchmark Whitepaper distribution',
      evidence_hash: 'sha256:9f3b...ec45',
    },
  ]);

  const [activeHalts, setActiveHalts] = useState<string[]>([]);

  const handleDecision = (id: string, decision: 'approve_content' | 'approve_and_send' | 'deny') => {
    setApprovals(approvals.filter(a => a.id !== id));
    console.log(`Action ${id} decided as ${decision} by ${activePersona}`);
  };

  const toggleHalt = (slug: string) => {
    if (activeHalts.includes(slug)) {
      setActiveHalts(activeHalts.filter(s => s !== slug));
    } else {
      setActiveHalts([...activeHalts, slug]);
    }
  };

  return (
    <main className="p-8 max-w-7xl mx-auto font-sans bg-gray-50 min-h-screen text-gray-900">
      {/* Header */}
      <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center border-b pb-4 gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Multimedia Cloud Solutions — Operating System (MCS-OS)</h1>
          <p className="text-gray-500 text-sm mt-1">Autonomous Corporate Control Plane • Specification v2.2 • Africa/Lagos (WAT)</p>
        </div>
        <div className="flex flex-wrap gap-3 items-center">
          {/* Executive Persona Switcher */}
          <div className="flex items-center bg-white border rounded-lg p-1 text-xs font-medium shadow-sm">
            <span className="text-gray-400 px-2">Role:</span>
            <button
              onClick={() => setActivePersona('founder_ceo')}
              className={`px-2.5 py-1 rounded ${activePersona === 'founder_ceo' ? 'bg-indigo-600 text-white font-semibold' : 'text-gray-600 hover:text-gray-900'}`}
            >
              CEO
            </button>
            <button
              onClick={() => setActivePersona('cfo')}
              className={`px-2.5 py-1 rounded ${activePersona === 'cfo' ? 'bg-indigo-600 text-white font-semibold' : 'text-gray-600 hover:text-gray-900'}`}
            >
              CFO
            </button>
            <button
              onClick={() => setActivePersona('cto')}
              className={`px-2.5 py-1 rounded ${activePersona === 'cto' ? 'bg-indigo-600 text-white font-semibold' : 'text-gray-600 hover:text-gray-900'}`}
            >
              CTO
            </button>
            <button
              onClick={() => setActivePersona('coo')}
              className={`px-2.5 py-1 rounded ${activePersona === 'coo' ? 'bg-indigo-600 text-white font-semibold' : 'text-gray-600 hover:text-gray-900'}`}
            >
              COO
            </button>
          </div>

          <a
            href="https://erp.mcsolutions.stream"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg text-xs font-semibold hover:bg-blue-100 transition"
          >
            Open ERPNext ↗
          </a>

          <button
            onClick={() => toggleHalt('company_wide')}
            className={`px-4 py-2 rounded text-sm font-bold text-white transition ${
              activeHalts.includes('company_wide') ? 'bg-red-800 ring-2 ring-red-400' : 'bg-red-600 hover:bg-red-700'
            }`}
          >
            {activeHalts.includes('company_wide') ? 'LIFT EMERGENCY HALT' : 'EMERGENCY HALT (ALL)'}
          </button>
        </div>
      </header>

      {/* Portfolio Coverage Matrix */}
      <section className="mb-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Portfolio Product Matrix (8 Active Ventures)</h2>
          <span className="text-xs font-semibold text-green-700 bg-green-50 px-2.5 py-1 rounded-full border border-green-200">
            ● 8 of 8 Systems Healthy
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {products.map(p => (
            <div key={p.slug} className="p-4 bg-white rounded-lg border shadow-sm hover:shadow-md transition">
              <div className="flex justify-between items-start">
                <span className="font-semibold text-sm">{p.name}</span>
                <span className="h-2.5 w-2.5 rounded-full bg-green-500" title="Healthy"></span>
              </div>
              <p className="text-xs text-gray-400 mt-1">Slug: {p.slug}</p>
              <div className="mt-4 flex justify-between items-center">
                <span className="text-xs font-mono bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{p.version}</span>
                <button
                  onClick={() => toggleHalt(p.slug)}
                  className="text-xs text-red-600 hover:text-red-800 font-medium"
                >
                  {activeHalts.includes(p.slug) ? 'Lift Halt' : 'Halt'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Executive Leadership & Chartered Departments (D01-D11) */}
      <section className="mb-8 bg-white rounded-lg border p-6 shadow-sm">
        <div className="flex justify-between items-center mb-4 border-b pb-3">
          <div>
            <h2 className="text-xl font-bold">Executive Leadership & Department Charters (D01–D11)</h2>
            <p className="text-xs text-gray-500 mt-0.5">Authoritative PostgreSQL 16 Role Catalog • Standing A0/A1/A2 Limits with A3 Gating</p>
          </div>
          <span className="text-xs font-mono bg-indigo-50 text-indigo-700 px-3 py-1 rounded-full font-semibold border border-indigo-200">
            Current Persona: {activePersona.toUpperCase()}
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {departments.map(dept => (
            <div key={dept.code} className="p-3.5 border rounded-lg bg-gray-50/50 hover:bg-white hover:border-indigo-300 transition">
              <div className="flex justify-between items-start">
                <span className="text-xs font-mono font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">{dept.code}</span>
                <span className="text-xs font-semibold text-gray-700">{dept.executive}</span>
              </div>
              <p className="text-xs font-medium text-gray-900 mt-2">{dept.name}</p>
              <div className="flex justify-between items-center text-[11px] text-gray-500 mt-3 pt-2 border-t border-gray-200/60">
                <span>Accountable: <code className="text-gray-700">{dept.accountable_role}</code></span>
                <span className="font-semibold text-gray-600">Max: {dept.authority_ceiling} (${dept.daily_budget_usd}/d)</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Decision Inbox (Approve Content vs Approve & Send) */}
      <section className="mb-8 bg-white rounded-lg border p-6 shadow-sm">
        <div className="flex justify-between items-center mb-4 border-b pb-3">
          <div>
            <h2 className="text-xl font-bold">Decision Inbox (Principal Governance)</h2>
            <p className="text-xs text-gray-500 mt-0.5">Standing A0/A1/A2 routines bypass this queue automatically</p>
          </div>
          <span className="text-xs text-gray-400 font-mono">X-MCS-Actor: {activePersona}</span>
        </div>
        {approvals.length === 0 ? (
          <p className="text-sm text-gray-400 py-6 text-center">Inbox zero. All autonomous operations running under standing authority.</p>
        ) : (
          <div className="space-y-4">
            {approvals.map(req => (
              <div key={req.id} className="p-4 border rounded-md flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <div className="flex gap-2 items-center">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-mono rounded">{req.department}</span>
                    <span className="text-sm font-semibold">{req.action_type}</span>
                    {req.amount_usd && (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-xs font-bold rounded">
                        ${req.amount_usd.toLocaleString()} USD
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-700 mt-1">{req.proposed_effect}</p>
                  <p className="text-xs font-mono text-gray-400 mt-1">Evidence Hash: {req.evidence_hash}</p>
                </div>
                <div className="flex gap-2 w-full md:w-auto justify-end">
                  <button
                    onClick={() => handleDecision(req.id, 'approve_content')}
                    className="px-3 py-1.5 border border-blue-600 text-blue-600 text-xs font-medium rounded hover:bg-blue-50 transition"
                  >
                    Approve Content
                  </button>
                  <button
                    onClick={() => handleDecision(req.id, 'approve_and_send')}
                    className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700 transition"
                  >
                    Approve & Send
                  </button>
                  <button
                    onClick={() => handleDecision(req.id, 'deny')}
                    className="px-3 py-1.5 border border-gray-300 text-gray-600 text-xs font-medium rounded hover:bg-gray-100 transition"
                  >
                    Deny
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Finance & AI Spend Real-Time Burn */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500">Daily AI Model Spend</h3>
          <p className="text-3xl font-bold mt-2">$8.42 <span className="text-sm font-normal text-gray-400">/ $50.00 ceiling</span></p>
          <div className="w-full bg-gray-200 h-2 rounded-full mt-4 overflow-hidden">
            <div className="bg-blue-600 h-2" style={{ width: '16.8%' }}></div>
          </div>
          <p className="text-xs text-gray-500 mt-2">Recovery reservations protected (D11 Guardian)</p>
        </div>
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500">Authoritative ERP Balances</h3>
          <p className="text-3xl font-bold mt-2">₦14,850,000 <span className="text-sm font-normal text-gray-400">Invoiced</span></p>
          <p className="text-xs text-green-600 mt-4">● Synced with ainatunde/MCS-ERP (ERPNext)</p>
        </div>
        <div className="bg-white p-6 rounded-lg border shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500">Assurance & Acceptance</h3>
          <p className="text-3xl font-bold mt-2">20 / 20 <span className="text-sm font-normal text-gray-400">L01–L20 Qualified</span></p>
          <p className="text-xs text-gray-500 mt-4">Zero waivers permitted • Continuous Guardian audit</p>
        </div>
      </section>
    </main>
  );
}
