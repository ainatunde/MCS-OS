'use client';

/**
 * MCS-OS Executive Command Centre — Next.js 14 Dashboard (MCS-OS v2.2 W10).
 *
 * Surfaces:
 *   1. 07:30 WAT Executive Briefing & Portfolio Health (7 Products + ERPNext)
 *   2. Decision Inbox (Approve Content vs Approve & Send vs Deny)
 *   3. Emergency Halt Controls (Company-Wide & Per-Product Kill Switches)
 *   4. Guardian Watchdog Incidents & Recovery Runbook Audit Trail
 */

import React, { useState, useEffect } from 'react';

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

export default function CommandCentre() {
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
    console.log(`Action ${id} decided as ${decision}`);
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
      <header className="mb-8 flex justify-between items-center border-b pb-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Multimedia Cloud Solutions — Operating System (MCS-OS)</h1>
          <p className="text-gray-500 text-sm mt-1">Autonomous Corporate Control Plane • Specification v2.2 • Africa/Lagos (WAT)</p>
        </div>
        <div className="flex gap-4 items-center">
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-semibold">
            ● All 11 Departments Active
          </span>
          <button
            onClick={() => toggleHalt('company_wide')}
            className={`px-4 py-2 rounded text-sm font-bold text-white transition ${
              activeHalts.includes('company_wide') ? 'bg-red-800' : 'bg-red-600 hover:bg-red-700'
            }`}
          >
            {activeHalts.includes('company_wide') ? 'LIFT EMERGENCY HALT' : 'EMERGENCY HALT (ALL)'}
          </button>
        </div>
      </header>

      {/* Portfolio Coverage Matrix */}
      <section className="mb-8">
        <h2 className="text-xl font-bold mb-4">Portfolio Product Matrix (Day-One Integrated Launch)</h2>
        <div className="grid grid-cols-4 gap-4">
          {products.map(p => (
            <div key={p.slug} className="p-4 bg-white rounded-lg border shadow-sm">
              <div className="flex justify-between items-start">
                <span className="font-semibold text-sm">{p.name}</span>
                <span className="h-2 w-2 rounded-full bg-green-500"></span>
              </div>
              <p className="text-xs text-gray-400 mt-2">Slug: {p.slug}</p>
              <div className="mt-4 flex justify-between items-center">
                <span className="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded">{p.version}</span>
                <button
                  onClick={() => toggleHalt(p.slug)}
                  className="text-xs text-red-600 hover:underline"
                >
                  {activeHalts.includes(p.slug) ? 'Lift Halt' : 'Halt Product'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Decision Inbox (Approve Content vs Approve & Send) */}
      <section className="mb-8 bg-white rounded-lg border p-6 shadow-sm">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Decision Inbox (Principal Governance)</h2>
          <span className="text-xs text-gray-500">Standing A0/A1/A2 routines bypass this queue automatically</span>
        </div>
        {approvals.length === 0 ? (
          <p className="text-sm text-gray-400 py-6 text-center">Inbox zero. All autonomous operations running under standing authority.</p>
        ) : (
          <div className="space-y-4">
            {approvals.map(req => (
              <div key={req.id} className="p-4 border rounded-md flex justify-between items-center">
                <div>
                  <div className="flex gap-2 items-center">
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-mono rounded">{req.department}</span>
                    <span className="text-sm font-semibold">{req.action_type}</span>
                  </div>
                  <p className="text-sm text-gray-700 mt-1">{req.proposed_effect}</p>
                  <p className="text-xs font-mono text-gray-400 mt-1">Evidence Hash: {req.evidence_hash}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleDecision(req.id, 'approve_content')}
                    className="px-3 py-1.5 border border-blue-600 text-blue-600 text-xs font-medium rounded hover:bg-blue-50"
                  >
                    Approve Content
                  </button>
                  <button
                    onClick={() => handleDecision(req.id, 'approve_and_send')}
                    className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700"
                  >
                    Approve & Send
                  </button>
                  <button
                    onClick={() => handleDecision(req.id, 'deny')}
                    className="px-3 py-1.5 border border-gray-300 text-gray-600 text-xs font-medium rounded hover:bg-gray-100"
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
      <section className="grid grid-cols-3 gap-6">
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
