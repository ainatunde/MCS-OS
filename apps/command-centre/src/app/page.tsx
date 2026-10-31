'use client';

/**
 * MCS-OS Executive Command Centre — Next.js 14 Dashboard (MCS-OS v2.2 W10).
 *
 * Surfaces:
 *   1. Executive Leadership & Department Charters (D01–D11) with Live Role Switching
 *   2. Role-Scoped Decision Inbox (Approve Content vs Approve & Send vs Deny)
 *   3. Team Directory & ERPNext Access Directory (CFO, CTO, CCO, COO, Support)
 *   4. Emergency Halt Controls (Company-Wide & Per-Product Kill Switches)
 *   5. Real-Time Model Spend, ERP Balances & System Assurance
 */

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import MCSLogo from '@/components/MCSLogo';
import SecuritySession, { securityFetch } from '@/components/SecuritySession';

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
  roles: string;
  department: string;
  erp_desk_url: string;
}

interface ExecutiveDirective {
  directive_id: string;
  target_role: string;
  target_title: string;
  directive_type: 'strategic_priority' | 'policy_update' | 'immediate_action' | 'executive_memo';
  priority: 'routine' | 'high' | 'critical';
  title: string;
  instructions: string;
  deliverables?: string;
  deadline?: string;
  standing_authority_impact?: string;
  sync_erp_task: boolean;
  erp_task_id?: string;
  issuer: string;
  issuer_title: string;
  status: 'issued' | 'acknowledged' | 'in_progress' | 'completed' | 'revoked';
  created_at: string;
  acknowledged_at?: string | null;
  acknowledged_by?: string | null;
}

export default function ProtectedCommandCentre() {
  return <SecuritySession>{role => <CommandCentre sessionRole={role} />}</SecuritySession>;
}

function CommandCentre({ sessionRole }: { sessionRole: string }) {
  const [activePersona, setActivePersona] = useState<Persona>(sessionRole as Persona);
  const [inboxTab, setInboxTab] = useState<'my_mandate' | 'all'>('my_mandate');
  const [showTeamModal, setShowTeamModal] = useState<boolean>(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [auditLog, setAuditLog] = useState<string[]>([]);
  const [activeHalts, setActiveHalts] = useState<string[]>([]);

  // Executive Directive Dispatcher State
  const [directives, setDirectives] = useState<ExecutiveDirective[]>([
    {
      directive_id: 'dir-20261018-001',
      target_role: 'cto',
      target_title: 'Chief Technology Officer (CTO)',
      directive_type: 'strategic_priority',
      priority: 'critical',
      title: 'Aether ADX OpenRTB 3.0 SSP Latency Target (<5ms p99)',
      instructions: 'Audit RTB exchange request pipelines across Lagos and Johannesburg edge POPs. Optimize Valkey dynamic floor caches and ensure OpenRTB 3.0 serialized auction responses execute under 5ms at peak evening broadcast load.',
      deliverables: 'Benchmark latency telemetry report, cache concurrency tuning commits, and 100-event stress test log.',
      deadline: '2026-10-25',
      sync_erp_task: true,
      erp_task_id: 'TASK-2026-0042',
      issuer: 'founder_ceo',
      issuer_title: 'Founder & CEO',
      status: 'in_progress',
      created_at: '2026-10-18T09:00:00Z',
      acknowledged_at: '2026-10-18T09:15:00Z',
      acknowledged_by: 'cto@mcsolutions.stream',
    },
    {
      directive_id: 'dir-20261018-002',
      target_role: 'commercial',
      target_title: 'Chief Commercial Officer (CCO)',
      directive_type: 'policy_update',
      priority: 'high',
      title: 'Broadcaster Onboarding Rev-Share Terms Approval Thresholds',
      instructions: 'Maintain standard 40/15/45 rev-share split for linear tier-2 broadcasters. Any custom concession exceeding 5% margin for tier-1 national networks requires explicit A3 CEO approval in Decision Inbox before issuing formal quotation.',
      deliverables: 'Updated ERPNext quotation templates and sales enablement guide for Q4 pipeline.',
      deadline: '2026-10-22',
      sync_erp_task: true,
      erp_task_id: 'TASK-2026-0043',
      issuer: 'founder_ceo',
      issuer_title: 'Founder & CEO',
      status: 'acknowledged',
      created_at: '2026-10-18T10:30:00Z',
      acknowledged_at: '2026-10-18T11:00:00Z',
      acknowledged_by: 'commercial@mcsolutions.stream',
    },
  ]);

  const [showDirectiveForm, setShowDirectiveForm] = useState<boolean>(false);
  const [directiveForm, setDirectiveForm] = useState({
    target_role: 'all',
    directive_type: 'strategic_priority' as const,
    priority: 'high' as const,
    title: '',
    instructions: '',
    deliverables: '',
    deadline: '',
    sync_erp_task: true,
  });
  const [directiveFeedback, setDirectiveFeedback] = useState<string | null>(null);

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
      roles: 'Administrator, System Manager',
      department: 'Corporate Governance & Executive (D01–D11)',
      erp_desk_url: 'https://erp.mcsolutions.stream/app',
    },
    {
      role_code: 'CFO',
      persona: 'cfo',
      title: 'Chief Financial Officer',
      email: 'cfo@mcsolutions.stream',
      roles: 'Accounts Manager, Accounts User, Auditor, Desk User',
      department: 'D06 Finance & Treasury, D10 Vendor Admin',
      erp_desk_url: 'https://erp.mcsolutions.stream/app/accounting',
    },
    {
      role_code: 'CTO',
      persona: 'cto',
      title: 'Chief Technology Officer',
      email: 'cto@mcsolutions.stream',
      roles: 'System Manager, Desk User, Employee',
      department: 'D05 Technology & Reliability, D04 Intelligence, D08 Product',
      erp_desk_url: 'https://erp.mcsolutions.stream/app/settings',
    },
    {
      role_code: 'CCO',
      persona: 'commercial',
      title: 'Chief Commercial Officer',
      email: 'commercial@mcsolutions.stream',
      roles: 'Sales Manager, Sales User, Sales Master Manager, Desk User',
      department: 'D02 Sales & Partnerships, D03 Marketing',
      erp_desk_url: 'https://erp.mcsolutions.stream/app/selling',
    },
    {
      role_code: 'COO',
      persona: 'coo',
      title: 'Chief Operating Officer',
      email: 'coo@mcsolutions.stream',
      roles: 'Projects Manager, Stock Manager, Purchase Manager, Desk User',
      department: 'D01 Operations & COO, D07 Customer Success',
      erp_desk_url: 'https://erp.mcsolutions.stream/app/stock',
    },
    {
      role_code: 'Support',
      persona: 'coo',
      title: 'Customer Success Lead',
      email: 'support@mcsolutions.stream',
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
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://os.mcsolutions.stream';
      await securityFetch(`${apiUrl}/v1/approvals/${id}/decide`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision})});
      setApprovals(prev => prev.filter(a => a.id !== id));
      setAuditLog(prev => [`${id}: ${decision} confirmed by server`, ...prev.slice(0,4)]);
    } catch(e) { alert(e instanceof Error ? e.message : 'Decision was not accepted.'); }
  };

  const toggleHalt = async (slug: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://os.mcsolutions.stream';
      const active = activeHalts.includes(slug);
      await securityFetch(`${apiUrl}/v1/halts${active ? `/${encodeURIComponent(slug)}` : ''}`, {method:active?'DELETE':'POST',headers:{'Content-Type':'application/json'},body:active?undefined:JSON.stringify({scope:slug,reason:'Executive containment from console'})});
      setActiveHalts(prev => active ? prev.filter(s => s !== slug) : [...prev,slug]);
      setAuditLog(prev => [`${slug}: halt ${active?'lifted':'registered'} by server`,...prev.slice(0,4)]);
    } catch(e) { alert(e instanceof Error ? e.message : 'Containment was not confirmed.'); }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleIssueDirective = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!directiveForm.title.trim() || !directiveForm.instructions.trim()) {
      alert('Please provide a directive title and instructions.');
      return;
    }

    const roleMap: Record<string, string> = {
      all: 'Company-Wide (All Charters D01–D11)',
      cto: 'Chief Technology Officer (CTO)',
      cfo: 'Chief Financial Officer (CFO)',
      coo: 'Chief Operating Officer (COO)',
      commercial: 'Chief Commercial Officer (CCO)',
      support: 'Customer Success Lead',
    };

    const newDirective: ExecutiveDirective = {
      directive_id: `dir-${new Date().toISOString().replace(/[-:T.Z]/g, '').slice(0, 14)}`,
      target_role: directiveForm.target_role,
      target_title: roleMap[directiveForm.target_role] || `Department ${directiveForm.target_role}`,
      directive_type: directiveForm.directive_type,
      priority: directiveForm.priority,
      title: directiveForm.title.trim(),
      instructions: directiveForm.instructions.trim(),
      deliverables: directiveForm.deliverables.trim() || undefined,
      deadline: directiveForm.deadline || undefined,
      sync_erp_task: directiveForm.sync_erp_task,
      erp_task_id: directiveForm.sync_erp_task ? `TASK-2026-${Math.floor(1000 + Math.random() * 9000)}` : undefined,
      issuer: activePersona,
      issuer_title: activeMember.title,
      status: 'issued',
      created_at: new Date().toISOString(),
      acknowledged_at: null,
      acknowledged_by: null,
    };

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://os.mcsolutions.stream';
      const response = await securityFetch(`${apiUrl}/v1/directives`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(newDirective)});
      Object.assign(newDirective, await response.json());
    } catch(e) { alert(e instanceof Error ? e.message : 'Directive was not accepted.'); return; }
    setDirectives([newDirective, ...directives]);
    setDirectiveFeedback(`Directive "${newDirective.title}" successfully dispatched to ${newDirective.target_title}`);
    setAuditLog(prev => [`[${new Date().toLocaleTimeString()}] DIRECTIVE DISPATCHED: "${newDirective.title}" -> ${newDirective.target_role.toUpperCase()}`, ...prev.slice(0, 4)]);

    // Reset form
    setDirectiveForm({
      target_role: 'all',
      directive_type: 'strategic_priority',
      priority: 'high',
      title: '',
      instructions: '',
      deliverables: '',
      deadline: '',
      sync_erp_task: true,
    });
    setTimeout(() => setDirectiveFeedback(null), 5000);


  };

  const handleUpdateDirectiveStatus = async (id: string, newStatus: ExecutiveDirective['status']) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://os.mcsolutions.stream';
      await securityFetch(`${apiUrl}/v1/directives/${id}/status`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:newStatus})});
    } catch(e) { alert(e instanceof Error ? e.message : 'Status was not accepted.'); return; }

    setDirectives(directives.map(d => {
      if (d.directive_id === id) {
        return {
          ...d,
          status: newStatus,
          acknowledged_at: newStatus === 'acknowledged' && !d.acknowledged_at ? new Date().toISOString() : d.acknowledged_at,
          acknowledged_by: newStatus === 'acknowledged' ? activeMember.email : d.acknowledged_by,
        };
      }
      return d;
    }));

    setAuditLog(prev => [`[${new Date().toLocaleTimeString()}] Directive ${id} status updated to ${newStatus.toUpperCase()}`, ...prev.slice(0, 4)]);


  };

  const setRelativeDeadline = (daysOrType: number | 'today' | 'tomorrow' | 'end_of_week' | 'end_of_month') => {
    const now = new Date();
    let target = new Date();

    if (daysOrType === 'today') {
      target = now;
    } else if (daysOrType === 'tomorrow') {
      target.setDate(now.getDate() + 1);
    } else if (daysOrType === 'end_of_week') {
      const day = now.getDay();
      const daysUntilFriday = (5 - day + 7) % 7 || 7;
      target.setDate(now.getDate() + daysUntilFriday);
    } else if (daysOrType === 'end_of_month') {
      target = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    } else if (typeof daysOrType === 'number') {
      target.setDate(now.getDate() + daysOrType);
    }

    const yyyy = target.getFullYear();
    const mm = String(target.getMonth() + 1).padStart(2, '0');
    const dd = String(target.getDate()).padStart(2, '0');
    const dateStr = `${yyyy}-${mm}-${dd}`;
    setDirectiveForm(prev => ({ ...prev, deadline: dateStr }));
  };

  const formatDeadlinePreview = (dateStr: string) => {
    if (!dateStr) return null;
    const parts = dateStr.split('-').map(Number);
    if (parts.length !== 3 || isNaN(parts[0]) || isNaN(parts[1]) || isNaN(parts[2])) return null;
    const target = new Date(parts[0], parts[1] - 1, parts[2]);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diffTime = target.getTime() - today.getTime();
    const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));

    const formattedDate = target.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });

    if (diffDays === 0) return `Today (${formattedDate})`;
    if (diffDays === 1) return `Tomorrow (${formattedDate})`;
    if (diffDays < 0) return `${Math.abs(diffDays)}d ago (${formattedDate})`;
    return `In ${diffDays}d (${formattedDate})`;
  };

  const loadPreset = (preset: { target_role: string; type: any; priority: any; title: string; instructions: string; deliverables: string }) => {
    const in7Days = new Date();
    in7Days.setDate(in7Days.getDate() + 7);
    const yyyy = in7Days.getFullYear();
    const mm = String(in7Days.getMonth() + 1).padStart(2, '0');
    const dd = String(in7Days.getDate()).padStart(2, '0');
    const defaultDeadline = `${yyyy}-${mm}-${dd}`;

    setDirectiveForm({
      target_role: preset.target_role,
      directive_type: preset.type,
      priority: preset.priority,
      title: preset.title,
      instructions: preset.instructions,
      deliverables: preset.deliverables,
      deadline: defaultDeadline,
      sync_erp_task: true,
    });
    setShowDirectiveForm(true);
  };

  // Filter Decision Inbox
  const filteredApprovals = approvals.filter(item => {
    if (inboxTab === 'all' || activePersona === 'founder_ceo') {
      return true;
    }
    return item.mandate_roles.includes(activePersona);
  });

  return (
    <main className="p-6 md:p-8 max-w-7xl mx-auto font-sans bg-stone-50 min-h-screen text-stone-900">
      {/* Header */}
      <header className="mb-6 flex flex-col md:flex-row justify-between items-start md:items-center border-b pb-5 gap-4">
        <div className="flex items-center gap-3">
          <MCSLogo variant="mark" size="lg" showLink={false} />
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-stone-900">
                Multimedia Cloud Solutions — Operating System (MCS-OS)
              </h1>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-orange-100 text-orange-800 border border-orange-200">
                v2.2 Production
              </span>
            </div>
            <p className="text-stone-500 text-xs md:text-sm mt-1">
              Autonomous Corporate Control Plane • Africa/Lagos (WAT) • Connected to ERPNext v15
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2.5 items-center">
          {/* Executive Persona Switcher */}
          <div className="flex items-center bg-white border border-stone-300 rounded-lg p-1 text-xs font-medium shadow-sm">
            <span className="text-stone-400 px-2 font-semibold">Role:</span>
            <button
              disabled={sessionRole !== 'founder_ceo'} onClick={() => setActivePersona('founder_ceo')}
              className={`px-2.5 py-1 rounded transition ${activePersona === 'founder_ceo' ? 'bg-orange-600 text-white font-bold shadow-xs' : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'}`}
            >
              CEO
            </button>
            <button
              disabled={sessionRole !== 'cfo'} onClick={() => setActivePersona('cfo')}
              className={`px-2.5 py-1 rounded transition ${activePersona === 'cfo' ? 'bg-orange-600 text-white font-bold shadow-xs' : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'}`}
            >
              CFO
            </button>
            <button
              disabled={sessionRole !== 'cto'} onClick={() => setActivePersona('cto')}
              className={`px-2.5 py-1 rounded transition ${activePersona === 'cto' ? 'bg-orange-600 text-white font-bold shadow-xs' : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'}`}
            >
              CTO
            </button>
            <button
              disabled={sessionRole !== 'coo'} onClick={() => setActivePersona('coo')}
              className={`px-2.5 py-1 rounded transition ${activePersona === 'coo' ? 'bg-orange-600 text-white font-bold shadow-xs' : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'}`}
            >
              COO
            </button>
            <button
              disabled={sessionRole !== 'commercial'} onClick={() => setActivePersona('commercial')}
              className={`px-2.5 py-1 rounded transition ${activePersona === 'commercial' ? 'bg-orange-600 text-white font-bold shadow-xs' : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'}`}
            >
              CCO
            </button>
          </div>

          {/* Team Logins Directory Modal Trigger */}
          <button
            onClick={() => setShowTeamModal(true)}
            className="px-3 py-1.5 bg-white border border-stone-300 hover:border-stone-400 text-stone-700 rounded-lg text-xs font-semibold shadow-sm transition flex items-center gap-1.5"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            Team Logins
          </button>

          {/* Products & Solutions Showcase */}
          <Link
            href="/products"
            className="px-3 py-1.5 bg-orange-50 border border-orange-300 hover:bg-orange-100 text-orange-900 rounded-lg text-xs font-bold transition flex items-center gap-1 shadow-xs"
          >
            <span>Products & Solutions</span>
            <span>→</span>
          </Link>

          {/* Direct Link to ERPNext */}
          <a
            href={activeMember.erp_desk_url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 bg-amber-50 border border-amber-200 text-amber-700 rounded-lg text-xs font-semibold hover:bg-amber-100 transition flex items-center gap-1"
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
      <section className="mb-6 bg-gradient-to-r from-stone-900 via-orange-950 to-stone-900 text-white rounded-xl p-4 md:p-5 shadow-sm border border-stone-800">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 rounded-lg bg-orange-600 flex items-center justify-center font-bold text-lg text-white shadow-inner">
              {activeMember.role_code}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base">{activeMember.title}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-orange-500/30 text-orange-200 font-mono border border-orange-400/20">
                  {activeMember.email}
                </span>
              </div>
              <p className="text-xs text-stone-300 mt-1">
                Accountable Mandate: <span className="text-white font-medium">{activeMember.department}</span>
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 text-xs">
            <div className="bg-stone-800/80 px-3 py-1.5 rounded-lg border border-stone-700">
              <span className="text-stone-400 block text-[10px] uppercase font-bold">X-MCS-Actor Header</span>
              <code className="text-emerald-400 font-bold">{activePersona}</code>
            </div>
            <div className="bg-stone-800/80 px-3 py-1.5 rounded-lg border border-stone-700">
              <span className="text-stone-400 block text-[10px] uppercase font-bold">ERPNext User Role</span>
              <span className="text-orange-200">{activeMember.roles.split(',')[0]}</span>
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
            <h2 className="text-lg font-bold text-stone-900">Portfolio Product Matrix (8 Active Ventures)</h2>
            <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              ● 8 of 8 Healthy
            </span>
          </div>
          <span className="text-xs text-stone-500">Autonomous Microservices & Adaptors</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
          {products.map(p => (
            <div key={p.slug} className={`p-3.5 bg-white rounded-lg border shadow-xs transition ${activeHalts.includes(p.slug) ? 'border-red-400 bg-red-50/50' : 'hover:border-stone-300'}`}>
              <div className="flex justify-between items-start">
                <span className="font-semibold text-xs text-stone-900">{p.name}</span>
                <span className={`h-2.5 w-2.5 rounded-full ${activeHalts.includes(p.slug) ? 'bg-red-500 animate-pulse' : 'bg-emerald-500'}`} title={activeHalts.includes(p.slug) ? 'HALTED' : 'Healthy'}></span>
              </div>
              <p className="text-[11px] font-mono text-stone-400 mt-1">{p.slug}</p>
              <div className="mt-3 flex justify-between items-center pt-2 border-t border-stone-100">
                <span className="text-[11px] font-mono bg-stone-100 text-stone-600 px-1.5 py-0.5 rounded">{p.version}</span>
                <button
                  onClick={() => toggleHalt(p.slug)}
                  className={`text-[11px] font-semibold ${activeHalts.includes(p.slug) ? 'text-red-700 hover:text-red-900' : 'text-stone-500 hover:text-red-600'}`}
                >
                  {activeHalts.includes(p.slug) ? 'Lift Halt' : 'Halt'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Executive Strategic Directive Dispatcher (CEO Command Deck) */}
      <section className="mb-8 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white rounded-xl border border-indigo-900/60 p-5 shadow-lg relative overflow-hidden">
        {/* Glow ambient background effect */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>

        <div className="relative z-10">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center pb-4 border-b border-indigo-800/60 gap-3">
            <div>
              <div className="flex items-center gap-2.5">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
                <h2 className="text-lg md:text-xl font-bold tracking-tight text-white flex items-center gap-2">
                  <span>Executive Strategic Directive Dispatcher</span>
                  <span className="text-[10px] font-mono uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-400/30 px-2 py-0.5 rounded font-bold">
                    CEO Authority
                  </span>
                </h2>
              </div>
              <p className="text-xs text-indigo-200/80 mt-1">
                Issue binding strategic priorities, policy boundaries, and action mandates to CTO, CFO, CCO, COO, or Company-Wide charters.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowDirectiveForm(!showDirectiveForm)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-sm ${
                  showDirectiveForm
                    ? 'bg-indigo-600 text-white border border-indigo-400'
                    : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold'
                }`}
              >
                <span>{showDirectiveForm ? 'Close Directive Form' : '+ Issue New Directive'}</span>
              </button>
            </div>
          </div>

          {/* Quick Strategy Presets Bar */}
          <div className="mt-4 pt-1">
            <span className="text-[11px] font-semibold text-indigo-300 uppercase tracking-wider block mb-2">
              Quick Strategy Presets (Click to Load):
            </span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => loadPreset({
                  target_role: 'cto',
                  type: 'strategic_priority',
                  priority: 'critical',
                  title: 'Aether ADX OpenRTB 3.0 Latency Target (<5ms p99)',
                  instructions: 'Audit RTB auction engine pipelines across Lagos and Johannesburg edge POPs. Optimize Valkey dynamic floor caches and ensure OpenRTB 3.0 serialized auction responses execute under 5ms at peak evening broadcast load.',
                  deliverables: 'Latency benchmark telemetry report, Valkey cache concurrency commits, and 100-event stress test log.',
                })}
                className="px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700/90 border border-indigo-700/50 text-[11px] text-cyan-300 transition flex items-center gap-1"
              >
                <span>⚡ OpenRTB 3.0 &lt;5ms (CTO)</span>
              </button>

              <button
                type="button"
                onClick={() => loadPreset({
                  target_role: 'cfo',
                  type: 'policy_update',
                  priority: 'high',
                  title: 'Cloud Infrastructure Spend Audit & Reserve Reallocation',
                  instructions: 'Audit line-item compute invoices across Contabo VPS and GCP. Ensure AI model spending strictly conforms to the $15/day company ceiling and reconcile escrow balances with ERPNext General Ledger.',
                  deliverables: 'Audited monthly cloud expense breakdown and GL reconciliation journal entry in ERPNext.',
                })}
                className="px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700/90 border border-indigo-700/50 text-[11px] text-emerald-300 transition flex items-center gap-1"
              >
                <span>💰 Cloud Spend & Reserves (CFO)</span>
              </button>

              <button
                type="button"
                onClick={() => loadPreset({
                  target_role: 'commercial',
                  type: 'policy_update',
                  priority: 'high',
                  title: 'Broadcaster Onboarding Rev-Share Terms Approval Thresholds',
                  instructions: 'Enforce standard 40/15/45 rev-share schedule for all linear tier-2 broadcasters. Require explicit A3 CEO approval in Decision Inbox before issuing formal quotation with any custom concession exceeding 5% margin.',
                  deliverables: 'Updated ERPNext quotation templates and sales enablement guide for Q4 pipeline.',
                })}
                className="px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700/90 border border-indigo-700/50 text-[11px] text-amber-300 transition flex items-center gap-1"
              >
                <span>🤝 40/15/45 Rev-Share Split (CCO)</span>
              </button>

              <button
                type="button"
                onClick={() => loadPreset({
                  target_role: 'coo',
                  type: 'immediate_action',
                  priority: 'critical',
                  title: 'Audit 24/7 SCTE-35 Frame-Accurate DAI Splice Logs & Watermarks',
                  instructions: 'Audit second-by-second ad insertion logs on CloudStream VCP across all active feeds. Verify deterministic ad detection accuracy against TV-Insights Pulzz audio watermark database.',
                  deliverables: 'Zero-error splice audit report and 90-day compliance verification archive.',
                })}
                className="px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700/90 border border-indigo-700/50 text-[11px] text-purple-300 transition flex items-center gap-1"
              >
                <span>🛡️ SCTE-35 & Watermark Audit (COO)</span>
              </button>
            </div>
          </div>

          {/* Feedback message */}
          {directiveFeedback && (
            <div className="mt-4 p-3 bg-emerald-950/80 border border-emerald-500/50 text-emerald-200 text-xs rounded-lg flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span>{directiveFeedback}</span>
            </div>
          )}

          {/* Collapsible / Expandable Directive Composer Form */}
          {showDirectiveForm && (
            <form onSubmit={handleIssueDirective} className="mt-5 p-4 md:p-5 bg-slate-800/90 rounded-xl border border-indigo-600/40 shadow-inner">
              <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                <span className="text-cyan-400">📝</span> Compose Strategic Directive
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 mb-3.5">
                <div>
                  <label className="block text-[11px] font-semibold text-indigo-300 uppercase mb-1">Target Executive / Scope</label>
                  <select
                    value={directiveForm.target_role}
                    onChange={e => setDirectiveForm({ ...directiveForm, target_role: e.target.value as any })}
                    className="w-full bg-slate-900 border border-indigo-700/60 rounded-lg px-3 py-2 text-xs text-white focus:outline-hidden focus:ring-1 focus:ring-cyan-400"
                  >
                    <option value="all">Company-Wide (All Charters D01–D11)</option>
                    <option value="cto">Chief Technology Officer (CTO) — D04, D05, D08</option>
                    <option value="cfo">Chief Financial Officer (CFO) — D06, D10</option>
                    <option value="commercial">Chief Commercial Officer (CCO) — D02, D03</option>
                    <option value="coo">Chief Operating Officer (COO) — D01, D07</option>
                    <option value="support">Customer Success & SLAs — D07</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-indigo-300 uppercase mb-1">Directive Class</label>
                  <select
                    value={directiveForm.directive_type}
                    onChange={e => setDirectiveForm({ ...directiveForm, directive_type: e.target.value as any })}
                    className="w-full bg-slate-900 border border-indigo-700/60 rounded-lg px-3 py-2 text-xs text-white focus:outline-hidden focus:ring-1 focus:ring-cyan-400"
                  >
                    <option value="strategic_priority">Strategic Priority (Sprint Focus)</option>
                    <option value="policy_update">Policy / Budget Ceiling Update</option>
                    <option value="immediate_action">Immediate Action Order (Urgent)</option>
                    <option value="executive_memo">Executive Strategy Memo / Guidance</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-indigo-300 uppercase mb-1">Urgency / Priority</label>
                  <select
                    value={directiveForm.priority}
                    onChange={e => setDirectiveForm({ ...directiveForm, priority: e.target.value as any })}
                    className="w-full bg-slate-900 border border-indigo-700/60 rounded-lg px-3 py-2 text-xs text-white focus:outline-hidden focus:ring-1 focus:ring-cyan-400"
                  >
                    <option value="routine">Routine (Standard Operating Queue)</option>
                    <option value="high">High Priority (Next Cycle Review)</option>
                    <option value="critical">Critical / Urgent (Blocker)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 mb-3.5">
                <div className="md:col-span-2">
                  <label className="block text-[11px] font-semibold text-indigo-300 uppercase mb-1">Directive Subject / Title</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Optimize Aether ADX DSP Latency to <5ms"
                    value={directiveForm.title}
                    onChange={e => setDirectiveForm({ ...directiveForm, title: e.target.value })}
                    className="w-full bg-slate-900 border border-indigo-700/60 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-hidden focus:ring-1 focus:ring-cyan-400"
                  />
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-[11px] font-semibold text-indigo-300 uppercase">
                      Target Horizon / Deadline
                    </label>
                    {directiveForm.deadline && (
                      <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-800 font-bold">
                        {formatDeadlinePreview(directiveForm.deadline)}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5">
                    <input
                      type="date"
                      value={directiveForm.deadline}
                      onChange={e => setDirectiveForm({ ...directiveForm, deadline: e.target.value })}
                      className="w-full bg-slate-900 border border-indigo-700/60 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-hidden focus:ring-1 focus:ring-cyan-400"
                    />
                    {directiveForm.deadline && (
                      <button
                        type="button"
                        onClick={() => setDirectiveForm({ ...directiveForm, deadline: '' })}
                        className="px-2.5 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white rounded-lg border border-slate-700 transition"
                        title="Clear deadline"
                      >
                        ✕
                      </button>
                    )}
                  </div>

                  {/* 1-Click Quick Horizon Pills */}
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    <button
                      type="button"
                      onClick={() => setRelativeDeadline('today')}
                      className={`px-1.5 py-0.5 rounded text-[10px] font-medium transition ${
                        formatDeadlinePreview(directiveForm.deadline)?.startsWith('Today')
                          ? 'bg-cyan-500 text-slate-950 font-bold'
                          : 'bg-slate-800/80 hover:bg-slate-700 text-indigo-200 border border-indigo-800/60'
                      }`}
                    >
                      Today
                    </button>
                    <button
                      type="button"
                      onClick={() => setRelativeDeadline('tomorrow')}
                      className={`px-1.5 py-0.5 rounded text-[10px] font-medium transition ${
                        formatDeadlinePreview(directiveForm.deadline)?.startsWith('Tomorrow')
                          ? 'bg-cyan-500 text-slate-950 font-bold'
                          : 'bg-slate-800/80 hover:bg-slate-700 text-indigo-200 border border-indigo-800/60'
                      }`}
                    >
                      Tomorrow
                    </button>
                    <button
                      type="button"
                      onClick={() => setRelativeDeadline('end_of_week')}
                      className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800/80 hover:bg-slate-700 text-indigo-200 border border-indigo-800/60 transition"
                    >
                      This Fri
                    </button>
                    <button
                      type="button"
                      onClick={() => setRelativeDeadline(3)}
                      className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800/80 hover:bg-slate-700 text-indigo-200 border border-indigo-800/60 transition"
                    >
                      +3d
                    </button>
                    <button
                      type="button"
                      onClick={() => setRelativeDeadline(7)}
                      className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800/80 hover:bg-slate-700 text-indigo-200 border border-indigo-800/60 transition"
                    >
                      +7d
                    </button>
                    <button
                      type="button"
                      onClick={() => setRelativeDeadline(14)}
                      className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800/80 hover:bg-slate-700 text-indigo-200 border border-indigo-800/60 transition"
                    >
                      +14d
                    </button>
                    <button
                      type="button"
                      onClick={() => setRelativeDeadline('end_of_month')}
                      className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-800/80 hover:bg-slate-700 text-indigo-200 border border-indigo-800/60 transition"
                    >
                      End of Mo
                    </button>
                  </div>
                </div>
              </div>

              <div className="mb-3.5">
                <label className="block text-[11px] font-semibold text-indigo-300 uppercase mb-1">Instructions & Strategic Intent</label>
                <textarea
                  rows={3}
                  required
                  placeholder="Detail the tactical objective, technical or financial requirements, expected behavior, and operational boundaries..."
                  value={directiveForm.instructions}
                  onChange={e => setDirectiveForm({ ...directiveForm, instructions: e.target.value })}
                  className="w-full bg-slate-900 border border-indigo-700/60 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-hidden focus:ring-1 focus:ring-cyan-400"
                ></textarea>
              </div>

              <div className="mb-3.5">
                <label className="block text-[11px] font-semibold text-indigo-300 uppercase mb-1">Key Deliverables & Acceptance Criteria</label>
                <input
                  type="text"
                  placeholder="e.g. Telemetry benchmarks, signed audit log, ERPNext quotation template"
                  value={directiveForm.deliverables}
                  onChange={e => setDirectiveForm({ ...directiveForm, deliverables: e.target.value })}
                  className="w-full bg-slate-900 border border-indigo-700/60 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-hidden focus:ring-1 focus:ring-cyan-400"
                />
              </div>

              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pt-3 border-t border-indigo-700/40 gap-3">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-indigo-200">
                  <input
                    type="checkbox"
                    checked={directiveForm.sync_erp_task}
                    onChange={e => setDirectiveForm({ ...directiveForm, sync_erp_task: e.target.checked })}
                    className="rounded border-indigo-700 text-cyan-500 focus:ring-cyan-400 h-4 w-4 bg-slate-900"
                  />
                  <span>Sync as Official Task in ERPNext Project Management</span>
                </label>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowDirectiveForm(false)}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-bold rounded-lg text-xs shadow-md transition"
                  >
                    🚀 Broadcast Directive
                  </button>
                </div>
              </div>
            </form>
          )}

          {/* Active Directives Feed */}
          <div className="mt-5 pt-4 border-t border-indigo-800/60">
            <div className="flex justify-between items-center mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-white uppercase tracking-wider">Active Strategic Directives</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/30 text-indigo-200 border border-indigo-400/30">
                  {directives.length} Issued
                </span>
              </div>
              <span className="text-[11px] text-indigo-300">
                Logged in Control API • Governed under Master Spec §4.1
              </span>
            </div>

            <div className="space-y-3">
              {directives.map(dir => (
                <div
                  key={dir.directive_id}
                  className="p-3.5 bg-slate-800/70 border border-indigo-700/40 rounded-xl transition hover:border-indigo-500/70"
                >
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-slate-900 text-cyan-300 border border-cyan-400/30">
                        {dir.directive_id}
                      </span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                        dir.target_role === 'cto'
                          ? 'bg-blue-500/20 text-blue-300 border border-blue-400/30'
                          : dir.target_role === 'cfo'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/30'
                          : dir.target_role === 'commercial'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-400/30'
                          : 'bg-purple-500/20 text-purple-300 border border-purple-400/30'
                      }`}>
                        Target: {dir.target_title}
                      </span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                        dir.priority === 'critical'
                          ? 'bg-red-500/20 text-red-300 border border-red-400/30'
                          : dir.priority === 'high'
                          ? 'bg-orange-500/20 text-orange-300 border border-orange-400/30'
                          : 'bg-slate-700 text-slate-300'
                      }`}>
                        {dir.priority}
                      </span>
                      <span className="text-[10px] text-indigo-300 font-mono">
                        {dir.directive_type.replace('_', ' ')}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {dir.erp_task_id && (
                        <a
                          href="https://erp.mcsolutions.stream/app/task"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[10px] font-mono text-cyan-300 hover:text-cyan-200 bg-cyan-950/60 border border-cyan-800 px-2 py-0.5 rounded transition flex items-center gap-1"
                        >
                          <span>{dir.erp_task_id}</span>
                          <span>↗</span>
                        </a>
                      )}
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                        dir.status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/40'
                          : dir.status === 'in_progress'
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/40'
                          : dir.status === 'acknowledged'
                          ? 'bg-blue-500/20 text-blue-300 border border-blue-400/40'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-400/40'
                      }`}>
                        ● {dir.status.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  <h4 className="text-sm font-bold text-white mt-2.5">{dir.title}</h4>
                  <p className="text-xs text-slate-300 mt-1 leading-relaxed">{dir.instructions}</p>

                  {dir.deliverables && (
                    <div className="mt-2 text-[11px] text-indigo-200/90 bg-slate-900/50 p-2 rounded-lg border border-indigo-900/50">
                      <span className="font-semibold text-indigo-300">Deliverables: </span>
                      {dir.deliverables}
                    </div>
                  )}

                  <div className="mt-3 pt-2 border-t border-slate-700/60 flex flex-wrap justify-between items-center text-[10px] text-slate-400 gap-2">
                    <div className="flex items-center gap-3">
                      <span>Issued: {new Date(dir.created_at).toLocaleDateString()} by {dir.issuer_title}</span>
                      {dir.deadline && <span className="text-amber-300">Deadline: {dir.deadline}</span>}
                      {dir.acknowledged_by && <span className="text-emerald-300">Ack by {dir.acknowledged_by}</span>}
                    </div>

                    <div className="flex items-center gap-1.5">
                      {dir.status !== 'acknowledged' && dir.status !== 'in_progress' && dir.status !== 'completed' && (
                        <button
                          onClick={() => handleUpdateDirectiveStatus(dir.directive_id, 'acknowledged')}
                          className="px-2 py-0.5 bg-blue-900/60 hover:bg-blue-800 text-blue-200 border border-blue-700/50 rounded text-[10px] font-semibold transition"
                        >
                          Acknowledge
                        </button>
                      )}
                      {dir.status !== 'completed' && (
                        <button
                          onClick={() => handleUpdateDirectiveStatus(dir.directive_id, 'completed')}
                          className="px-2 py-0.5 bg-emerald-900/60 hover:bg-emerald-800 text-emerald-200 border border-emerald-700/50 rounded text-[10px] font-semibold transition"
                        >
                          Mark Completed
                        </button>
                      )}
                      {dir.status !== 'revoked' && (
                        <button
                          onClick={() => handleUpdateDirectiveStatus(dir.directive_id, 'revoked')}
                          className="px-2 py-0.5 bg-slate-900 hover:bg-red-950/60 text-slate-400 hover:text-red-300 border border-slate-700 rounded text-[10px] transition"
                        >
                          Revoke
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Decision Inbox (Filtered by Role Mandate) */}
      <section className="mb-8 bg-white rounded-xl border border-stone-200 p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 border-b pb-3 gap-2">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-stone-900">Decision Inbox & Sign-Offs</h2>
              <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-orange-50 text-orange-700 border border-orange-200">
                {filteredApprovals.length} Pending
              </span>
            </div>
            <p className="text-xs text-stone-500 mt-0.5">
              Filtered for <span className="font-semibold text-stone-700">{activeMember.title}</span> • Standing A0/A1/A2 routines bypass this queue automatically
            </p>
          </div>

          <div className="flex items-center bg-stone-100 p-0.5 rounded-lg text-xs font-medium">
            <button
              onClick={() => setInboxTab('my_mandate')}
              className={`px-3 py-1 rounded-md transition ${inboxTab === 'my_mandate' ? 'bg-white shadow-xs font-bold text-orange-700' : 'text-stone-600 hover:text-stone-900'}`}
            >
              My Mandate ({approvals.filter(a => activePersona === 'founder_ceo' || a.mandate_roles.includes(activePersona)).length})
            </button>
            <button
              onClick={() => setInboxTab('all')}
              className={`px-3 py-1 rounded-md transition ${inboxTab === 'all' ? 'bg-white shadow-xs font-bold text-orange-700' : 'text-stone-600 hover:text-stone-900'}`}
            >
              All Corporate ({approvals.length})
            </button>
          </div>
        </div>

        {filteredApprovals.length === 0 ? (
          <div className="text-center py-10 bg-stone-50 rounded-lg border border-dashed border-stone-200">
            <p className="text-sm font-medium text-stone-600">Inbox Zero for {activeMember.role_code}!</p>
            <p className="text-xs text-stone-400 mt-1">All operations in your department are running within autonomous policy limits.</p>
          </div>
        ) : (
          <div className="space-y-3.5">
            {filteredApprovals.map(req => {
              const hasDirectMandate = activePersona === 'founder_ceo' || req.mandate_roles.includes(activePersona);
              return (
                <div key={req.id} className={`p-4 border rounded-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-4 transition ${hasDirectMandate ? 'border-stone-200 bg-white hover:border-orange-200' : 'border-stone-200/60 bg-stone-50/50'}`}>
                  <div className="flex-1">
                    <div className="flex flex-wrap gap-2 items-center">
                      <span className="px-2 py-0.5 bg-orange-100 text-orange-800 text-xs font-mono font-bold rounded">
                        {req.department}
                      </span>
                      <span className="text-xs font-semibold text-stone-700">{req.action_type}</span>
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
                        <span className="px-2 py-0.5 bg-stone-100 text-stone-600 text-[10px] font-medium rounded">
                          Informational (Escalated to CEO/CFO)
                        </span>
                      )}
                    </div>
                    <h4 className="font-semibold text-sm text-stone-900 mt-1.5">{req.title}</h4>
                    <p className="text-xs text-stone-600 mt-0.5">{req.proposed_effect}</p>
                    <p className="text-[11px] font-mono text-stone-400 mt-1">Evidence Hash: {req.evidence_hash}</p>
                  </div>

                  <div className="flex gap-2 w-full md:w-auto justify-end">
                    <button
                      onClick={() => handleDecision(req.id, 'approve_content')}
                      className="px-3 py-1.5 border border-orange-600 text-orange-600 text-xs font-semibold rounded-lg hover:bg-orange-50 transition"
                      title="Approves text/content without releasing execution queue"
                    >
                      Approve Content
                    </button>
                    <button
                      onClick={() => handleDecision(req.id, 'approve_and_send')}
                      className="px-3 py-1.5 bg-orange-600 text-white text-xs font-semibold rounded-lg hover:bg-orange-700 transition shadow-xs"
                      title="Authorizes execution and releases send queue"
                    >
                      Approve & Send
                    </button>
                    <button
                      onClick={() => handleDecision(req.id, 'deny')}
                      className="px-3 py-1.5 border border-stone-300 text-stone-600 text-xs font-medium rounded-lg hover:bg-stone-100 transition"
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
      <section className="mb-8 bg-white rounded-xl border border-stone-200 p-5 shadow-xs">
        <div className="flex justify-between items-center mb-4 border-b pb-3">
          <div>
            <h2 className="text-lg font-bold text-stone-900">Department Charters & Leadership (D01–D11)</h2>
            <p className="text-xs text-stone-500 mt-0.5">Authoritative PostgreSQL 16 Catalog • Highlighted for active role: <span className="font-semibold text-orange-700">{activeMember.role_code}</span></p>
          </div>
          <span className="text-xs font-mono bg-orange-50 text-orange-700 px-3 py-1 rounded-full font-semibold border border-orange-200">
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
                    ? 'border-orange-400 bg-orange-50/20 shadow-xs ring-1 ring-orange-300/40'
                    : 'border-stone-200 bg-stone-50/40 opacity-70 hover:opacity-100'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-mono font-bold text-orange-700 bg-orange-100 px-2 py-0.5 rounded">
                      {dept.code}
                    </span>
                    {isOwned && (
                      <span className="text-[10px] font-bold text-orange-700 bg-orange-50 px-1.5 py-0.2 rounded border border-orange-200">
                        Your Mandate
                      </span>
                    )}
                  </div>
                  <span className="text-xs font-semibold text-stone-700">{dept.executive}</span>
                </div>
                <p className="text-xs font-bold text-stone-900 mt-2">{dept.name}</p>
                <div className="flex justify-between items-center text-[11px] text-stone-500 mt-3 pt-2 border-t border-stone-200/60">
                  <span>Accountable: <code className="text-stone-800 font-semibold">{dept.accountable_role}</code></span>
                  <span className="font-semibold text-stone-600">Max: {dept.authority_ceiling} (${dept.daily_budget_usd}/d)</span>
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
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Treasury Invoiced Balance</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">₦14,850,000 <span className="text-xs font-normal text-stone-400">NGN</span></p>
              <p className="text-xs text-emerald-600 mt-3 font-medium">● Reconciled with ERPNext v15 Accounting</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Finance Department AI Burn</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">$2.14 <span className="text-xs font-normal text-stone-400">/ $10.00 ceiling</span></p>
              <div className="w-full bg-stone-100 h-2 rounded-full mt-3 overflow-hidden">
                <div className="bg-orange-600 h-2" style={{ width: '21.4%' }}></div>
              </div>
              <p className="text-xs text-stone-500 mt-2">D06 + D10 procurement governance</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Revenue Payout Reserves</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">$125,000 <span className="text-xs font-normal text-stone-400">USD</span></p>
              <p className="text-xs text-stone-500 mt-3">Segregated channel owner escrow (D11 Audited)</p>
            </div>
          </>
        ) : activePersona === 'cto' ? (
          <>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Edge Service Health</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">8 / 8 <span className="text-xs font-normal text-emerald-600">Active</span></p>
              <p className="text-xs text-stone-500 mt-3">Lagos, Johannesburg, Nairobi POPs online</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Engineering AI Burn</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">$4.18 <span className="text-xs font-normal text-stone-400">/ $30.00 ceiling</span></p>
              <div className="w-full bg-stone-100 h-2 rounded-full mt-3 overflow-hidden">
                <div className="bg-orange-600 h-2" style={{ width: '13.9%' }}></div>
              </div>
              <p className="text-xs text-stone-500 mt-2">D05 Engineering & Code Generation</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">CI/CD Continuous Deployment</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">Coolify <span className="text-xs font-normal text-stone-400">Automated</span></p>
              <p className="text-xs text-emerald-600 mt-3">● Zero-downtime rolling reload</p>
            </div>
          </>
        ) : activePersona === 'commercial' ? (
          <>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Active Product Pipelines</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">7 Product Lines <span className="text-xs font-normal text-stone-400">+ ERP</span></p>
              <p className="text-xs text-stone-500 mt-3">SSAI, ADX OpenRTB, TV-Insights Live</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Commercial AI Burn</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">$0.90 <span className="text-xs font-normal text-stone-400">/ $25.00 ceiling</span></p>
              <div className="w-full bg-stone-100 h-2 rounded-full mt-3 overflow-hidden">
                <div className="bg-orange-600 h-2" style={{ width: '3.6%' }}></div>
              </div>
              <p className="text-xs text-stone-500 mt-2">D02 Commercial & D03 Marketing campaigns</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">CRM Lead Ingestion</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">100% Synced <span className="text-xs font-normal text-emerald-600">Active</span></p>
              <p className="text-xs text-emerald-600 mt-3">● Pulzz $\rightarrow$ ERPNext Automated Lead Sync</p>
            </div>
          </>
        ) : activePersona === 'coo' ? (
          <>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Operational Ingest Status</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">1,420 Feeds <span className="text-xs font-normal text-emerald-600">Active</span></p>
              <p className="text-xs text-stone-500 mt-3">TV-Insights crawlers + EPG ingestion active</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Operations AI Burn</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">$1.20 <span className="text-xs font-normal text-stone-400">/ $15.00 ceiling</span></p>
              <div className="w-full bg-stone-100 h-2 rounded-full mt-3 overflow-hidden">
                <div className="bg-orange-600 h-2" style={{ width: '8.0%' }}></div>
              </div>
              <p className="text-xs text-stone-500 mt-2">D01 Executive Ops & D07 Customer Support</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Vendor SLA Compliance</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">99.98% <span className="text-xs font-normal text-emerald-600">Verified</span></p>
              <p className="text-xs text-emerald-600 mt-3">● Full compliance across telecom & CDN suppliers</p>
            </div>
          </>
        ) : (
          <>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Daily AI Model Spend</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">$8.42 <span className="text-xs font-normal text-stone-400">/ $50.00 ceiling</span></p>
              <div className="w-full bg-stone-100 h-2 rounded-full mt-3 overflow-hidden">
                <div className="bg-orange-600 h-2" style={{ width: '16.8%' }}></div>
              </div>
              <p className="text-xs text-stone-500 mt-2">Recovery reservations protected (D11 Guardian)</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Authoritative ERP Balances</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">₦14,850,000 <span className="text-xs font-normal text-stone-400">Invoiced</span></p>
              <p className="text-xs text-emerald-600 mt-3 font-medium">● Synced with ainatunde/MCS-ERP (ERPNext)</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-xs">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Assurance & Acceptance</h3>
              <p className="text-2xl md:text-3xl font-bold mt-2 text-stone-900">20 / 20 <span className="text-xs font-normal text-stone-400">L01–L20 Qualified</span></p>
              <p className="text-xs text-stone-500 mt-3">Zero waivers permitted • Continuous Guardian audit</p>
            </div>
          </>
        )}
      </section>

      {/* Team Logins & Access Credentials Modal */}
      {showTeamModal && (
        <div className="fixed inset-0 bg-stone-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-stone-200 max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-start border-b pb-4">
              <div>
                <h3 className="text-xl font-bold text-stone-900">MCS Executive Team Logins</h3>
                <p className="text-xs text-stone-500 mt-0.5">Company account directory — passwords are managed in ERPNext</p>
              </div>
              <button
                onClick={() => setShowTeamModal(false)}
                className="text-stone-400 hover:text-stone-600 text-lg font-bold p-1"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 space-y-3">
              {teamMembers.map(member => (
                <div key={member.email} className="p-3.5 bg-stone-50 border border-stone-200 rounded-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-800">
                        {member.role_code}
                      </span>
                      <span className="font-semibold text-sm text-stone-900">{member.title}</span>
                    </div>
                    <div className="text-xs text-stone-600 mt-1 flex flex-col gap-0.5">
                      <span>Email: <code className="text-orange-600 font-semibold">{member.email}</code></span>
                      <span className="text-[11px] text-stone-500">Roles: {member.roles}</span>
                    </div>
                  </div>

                  <div className="flex gap-2 w-full sm:w-auto">
                    <button
                      onClick={() => copyToClipboard(member.email, `email-${member.email}`)}
                      className="px-2.5 py-1.5 bg-white border border-stone-300 hover:bg-stone-100 rounded text-xs font-medium text-stone-700 transition"
                    >
                      {copiedKey === `email-${member.email}` ? 'Copied Email!' : 'Copy Email'}
                    </button>
                    <a
                      href={member.erp_desk_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded text-xs font-semibold transition"
                    >
                      Login ↗
                    </a>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 pt-4 border-t flex justify-between items-center text-xs text-stone-500">
              <span>Host URL: <code className="text-orange-600 font-mono">https://erp.mcsolutions.stream/app</code></span>
              <button
                onClick={() => setShowTeamModal(false)}
                className="px-4 py-2 bg-stone-900 text-white rounded-lg font-semibold hover:bg-stone-800 transition"
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
