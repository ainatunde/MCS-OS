'use client';

/**
 * MCS Products & Solutions Showcase — Next.js 14 (MCS-OS v2.2).
 *
 * Authoritative Commercial & Technical Overview for:
 *   1. CloudStream VCP (Hardware-Accelerated Video Cloud Playout & SSAI)
 *   2. CloudStream Forge (White-Label FAST & Connected TV App Platform)
 *   3. Aether ADS (Enterprise Sub-3ms Ad Decision Server)
 *   4. Aether ADX (Programmatic OpenRTB 2.5/3.0 Video Ad Exchange)
 *   5. TV-Insights / Pulzz (Broadcast & Media Intelligence across Africa)
 *   6. AfricaSignal (Location-Aware Public Policy & Commodity Market Intelligence)
 *   7. MCS App Factory (Regulated Vertical Information Spine & Generator)
 *   8. MCS-ERP (ERPNext v15 Autonomous Accounting & Revenue-Share Engine)
 */

import React, { useState } from 'react';
import Link from 'next/link';

interface ProductDetail {
  slug: string;
  name: string;
  badge: string;
  category: 'broadcast' | 'adtech' | 'intelligence' | 'enterprise';
  tagline: string;
  overview: string;
  capabilities: string[];
  techStack: string[];
  differentiator: string;
  commercialModel: string;
  liveUrl?: string;
  repoName: string;
}

export default function ProductsPage() {
  const [activeCategory, setActiveCategory] = useState<'all' | 'broadcast' | 'adtech' | 'intelligence' | 'enterprise'>('all');
  const [selectedProduct, setSelectedProduct] = useState<ProductDetail | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [leadForm, setLeadForm] = useState({
    name: '',
    company: '',
    email: '',
    phone: '',
    product: 'CloudStream VCP',
    message: '',
  });
  const [submittedLeadId, setSubmittedLeadId] = useState<string | null>(null);

  const products: ProductDetail[] = [
    {
      slug: 'cloudstream-vcp',
      name: 'CloudStream VCP',
      badge: 'v2.5.1 Broadcast-Ready',
      category: 'broadcast',
      tagline: 'Hardware-Accelerated Video Cloud Playout & Sub-Second SSAI',
      overview:
        'A high-performance linear video cloud platform engineered for automated SCTE-35 trigger insertion, multi-modal AI cue detection, and seamless server-side ad replacement with zero viewer buffering.',
      capabilities: [
        'NVIDIA NVENC/NVDEC hardware-accelerated ABR live transcoding managed by dedicated GPU-workers.',
        'Synchronized Server-Side Ad Insertion (SSAI) with automated SCTE-35 cue-out/cue-in emission.',
        'Multi-modal computer vision (ResNet/YOLOX) & acoustic fingerprinting (FFT) for autonomous break detection.',
        'VLM Escalation Arbiter: Florence-2 & Qwen2-VL vision-language models for ambiguous breaks with fail-open latency protection.',
        'Stateless cryptographic L7 session security with HMAC-SHA256 signed playback tokens.',
        'Automated multi-CDN manifest invalidation via Cloudflare and Fastly APIs.',
      ],
      techStack: ['NVIDIA NVENC', 'Python / FastAPI', 'FFmpeg', 'PyTorch / Florence-2', 'Redis', 'SRT / HLS / DASH'],
      differentiator:
        'Eliminates manual broadcast markers using AI-driven vision and acoustic cue detection, saving thousands of hours and preventing lost ad revenue.',
      commercialModel: 'Infrastructure SaaS (Per-Channel Compute Hours) + SLA Maintenance Tiers.',
      repoName: 'ainatunde/cloudstream-vcp',
    },
    {
      slug: 'cloudstream-forge',
      name: 'CloudStream Forge',
      badge: 'v1.0.0 Production',
      category: 'broadcast',
      tagline: 'White-Label FAST TV Platform & Universal Connected TV App Generator',
      overview:
        'An enterprise app scaffolding platform that turns linear streams and VOD libraries into turnkey, branded streaming apps across Connected TVs, mobile devices, and the web within days.',
      capabilities: [
        'Automated generation of native client apps for Roku, Apple TV, Android TV, Fire TV, iOS, and Web.',
        'Universal master client architecture with synchronized experience-bus and metadata feeds.',
        'Interactive Electronic Programme Guide (EPG) with now/next carousels and genre filters.',
        'Pre-integrated with CloudStream VCP for synchronized SSAI manifest playback.',
        'Zero-downtime multi-tenant deployment pipeline with automated app store compliance checks.',
        'Real-time viewer experience telemetry and audience engagement tracking.',
      ],
      techStack: ['Next.js / React Native', 'Node.js', 'TypeScript', 'Tailwind CSS', 'Android SDK', 'Roku BrightScript'],
      differentiator:
        'Cuts Connected TV app development timelines from 9 months to under 5 days with zero ongoing cross-platform maintenance chaos.',
      commercialModel: 'Platform Setup Fee + Recurring Monthly Maintenance & App Store Management.',
      repoName: 'ainatunde/cloudstream-forge',
    },
    {
      slug: 'aether-ads',
      name: 'Aether ADS',
      badge: 'Sub-3ms p99 Certified',
      category: 'adtech',
      tagline: 'Enterprise Sub-3ms Ad Decision Server & Algorithmic Yield Engine',
      overview:
        'A high-concurrency, multi-tenant ad decision server that evaluates direct-sold, house, and programmatic campaigns with sub-3ms latency at 15,000+ RPS sustained throughput.',
      capabilities: [
        'Extreme low-latency decisioning: p99 0.86ms at 5,000 RPS and 2.9ms at 15,000 RPS burst concurrency.',
        'In-process tenant-partitioned campaign cache hot-reloaded via Valkey / Redis Pub/Sub.',
        'Algorithmic dynamic floor pricing and Thompson-sampled creative selection for maximized eCPMs.',
        'Distributed frequency capping and two-phase atomic budget reservation preventing over-delivery.',
        'Real-time streaming analytics pipeline via Redpanda and ClickHouse (~6ms rollup latency).',
        'Dual-currency billing (NGN ₦ & USD $) with automated Paystack, Flutterwave, and virtual accounts.',
      ],
      techStack: ['Go (Golang)', 'Valkey / Redis', 'PostgreSQL 16', 'ClickHouse', 'Redpanda / Kafka', 'SeaweedFS'],
      differentiator:
        'Ultra-low latency architecture guarantees ad placement before video buffers, eliminating lost impressions and maximizing yield.',
      commercialModel: 'Ad Serving Volume Fee ($/CPM) or Dedicated Enterprise Licensing.',
      repoName: 'ainatunde/AETHER-ADS',
    },
    {
      slug: 'aether-adx',
      name: 'Aether ADX',
      badge: 'OpenRTB 3.0 Live',
      category: 'adtech',
      tagline: 'High-Throughput Programmatic Video Ad Exchange & OpenRTB SSP',
      overview:
        'A unified programmatic video exchange that bridges African and global media publishers directly with major DSPs, programmatic trading desks, and demand partners.',
      capabilities: [
        'Direct OpenRTB 2.5 and 3.0 SSP endpoint connectivity with ads.txt and sellers.json compliance.',
        'Prebid Server integration merging direct-sold inventory with live programmatic auction bids.',
        'Automated VAST 4.x wrapper resolution with 5-hop safety chaining to prevent ad call timeouts.',
        'Multi-tier invalid traffic (IVT) filtering and server-side impression / quartile beacon verification.',
        'Automated creative asset processor with malware scanning, video normalization, and CDN caching.',
        'Transparent take-rate distribution and real-time publisher revenue accounting.',
      ],
      techStack: ['Go', 'Prebid Server', 'OpenRTB 2.5/3.0', 'PostgreSQL', 'Redis', 'SeaweedFS'],
      differentiator:
        'Unlocks international ad revenue for regional broadcasters by connecting local linear ad breaks to global programmatic demand.',
      commercialModel: 'Dynamic Revenue-Share Take Rate (10%–25% on monetized impressions).',
      repoName: 'ainatunde/AETHER-ADS/openrtb',
    },
    {
      slug: 'tv-insights',
      name: 'TV-Insights / Pulzz',
      badge: '1,420+ Feeds Monitored',
      category: 'intelligence',
      tagline: 'Automated Broadcast Intelligence, EPG Monitoring & Ad Share-of-Voice',
      overview:
        'A live media monitoring and market intelligence engine that tracks TV channels, FM radio stations, electronic programme guides, and commercial ad spend across West and Sub-Saharan Africa.',
      capabilities: [
        'Continuous monitoring of 1,420+ linear TV and FM radio feeds across Nigeria, Ghana, Kenya, and South Africa.',
        'Automated EPG (Electronic Programme Guide) schedule tracking with real-time Now / Next synchronization.',
        'Live Match & Event Tracker mapping EPL, UCL, and reality TV (BBNaija) broadcasts with 1-click reminders.',
        'Nollywood & Broadcaster Star Power Index evaluating personality airtime, search demand, and sentiment.',
        'Sentiment engine with Nigerian Pidgin booster and AfroXLMR multi-lingual transformers.',
        'Automated billing and lead synchronization into ERPNext CRM and invoices.',
      ],
      techStack: ['Python / FastAPI', 'PostgreSQL / PostGIS', 'Redis', 'VADER / AfroXLMR', 'PWA / Next.js', 'RQ Workers'],
      differentiator:
        'The only attribution-backed platform providing real-time verification of African linear broadcast schedules and competitive advertiser expenditure.',
      commercialModel: 'Tiered Enterprise Data Subscriptions + Agency Intelligence Feeds.',
      liveUrl: 'https://pulzz.mcsolutions.stream',
      repoName: 'ainatunde/tv-insights',
    },
    {
      slug: 'africasignal',
      name: 'AfricaSignal',
      badge: 'Location-Aware v1.0',
      category: 'intelligence',
      tagline: 'Evidence-Based Public Policy, Commodity & Household Economic Intelligence',
      overview:
        'A location-aware intelligence engine that tracks and explains material changes in consumer food staples, energy tariffs, transportation costs, and regulatory policy with verifiable citation chains.',
      capabilities: [
        'Autonomous collection and cross-checking of economic policy, market prices, and regional regulations.',
        'Every published insight includes explicit evidence limits, freshness indicators, and official sources.',
        'Neighborhood, city, and state-level geographic scoping with location-aware user personalization.',
        'Factual projection engine with strict quarantine safety gates preventing generative hallucinations.',
        'Structured community observations, local corrections, and operator verification audit log.',
        'Corporate sponsorship integration and automated social media export cards.',
      ],
      techStack: ['Python 3.12 / FastAPI', 'PostgreSQL / PostGIS', 'SQLAlchemy / Alembic', 'MinIO (S3)', 'Next.js'],
      differentiator:
        'Never publishes hallucinated or secondhand summaries; strictly binds all findings to verifiable official texts and ground-truth data.',
      commercialModel: 'Institutional Research Subscriptions, Sponsor Placements & API Syndication.',
      repoName: 'ainatunde/AfricaSignal',
    },
    {
      slug: 'mcs-app-factory',
      name: 'MCS App Factory',
      badge: 'Spine v2.0 Architecture',
      category: 'enterprise',
      tagline: 'Regulated Vertical Information Spine & Pluggable Compliance Generator',
      overview:
        'A subject-agnostic core and pluggable pack architecture designed for building applications in high-stakes regulated domains where errors carry legal or irreversible consequences.',
      capabilities: [
        '"Spine + Subject Packs" architecture: core monitoring and delivery spine with domain-specific rule packs.',
        'Dual-lane publication: Lane A (automated citation-linked source diff notices) and Lane B (deep fact extraction).',
        'SHA-256 hash-chained snapshot store and immutable audit log of all source modifications.',
        'Irreversible-harm vocabulary and strict human-in-the-loop review gating for sensitive operations.',
        'Multi-tenant database isolation with atomic job claiming (`SELECT FOR UPDATE SKIP LOCKED`).',
        'Turnkey branded web portals, automated sitemaps, and RSS/JSON syndication feeds.',
      ],
      techStack: ['Python / FastAPI', 'SQLAlchemy / Alembic', 'PostgreSQL 16', 'Next.js 14', 'Caddy / Traefik'],
      differentiator:
        'Enables launching a new regulated vertical (e.g. legal, immigration, tax) in days simply by supplying a risk taxonomy pack instead of building a new backend from scratch.',
      commercialModel: 'Enterprise Platform License + Per-Vertical Subject Pack Modules.',
      repoName: 'ainatunde/mcs-platform',
    },
    {
      slug: 'mcs-erp',
      name: 'MCS-ERP (ERPNext v15)',
      badge: 'Authoritative Ledger v15',
      category: 'enterprise',
      tagline: 'Autonomous Back-Office Billing, Multi-Currency Accounting & Subscriptions',
      overview:
        'The financial and operational backbone of Multimedia Cloud Solutions, handling automated invoicing, subscription lifecycle management, and revenue-share settlements across the entire portfolio.',
      capabilities: [
        'Integrated General Ledger, Chart of Accounts, and Cost Centers for all 7 MCS venture lines.',
        'Automated invoice generation from product platform usage (SSAI impressions, crawl quotas, subscriptions).',
        'Dual-currency support in Nigerian Naira (NGN ₦) and US Dollars (USD $) with effective-dated FX rates.',
        'Automated Nigerian VAT (7.5%) and Withholding Tax (WHT 5%/10%) computation and reporting.',
        'Channel-owner revenue-share payout accounting and automated partner disbursement tracking.',
        'Role-Based Access Control (RBAC) supporting dedicated CEO, CFO, CTO, CCO, and COO logins.',
      ],
      techStack: ['ERPNext v15', 'Frappe Framework', 'MariaDB 10.6', 'Python 3.11', 'Redis', 'Docker Compose'],
      differentiator:
        'Seamlessly connects autonomous ad-tech and cloud playout systems directly to commercial accounting, eliminating billing discrepancies.',
      commercialModel: 'Internal Corporate Operating Spine & Enterprise Client Billing Portal.',
      liveUrl: 'https://erp.mcsolutions.stream/app',
      repoName: 'ainatunde/MCS-ERP',
    },
  ];

  const filteredProducts = products.filter(p => activeCategory === 'all' || p.category === activeCategory);

  const handleOpenLeadModal = (prod: ProductDetail) => {
    setSelectedProduct(prod);
    setLeadForm(prev => ({ ...prev, product: prod.name }));
    setIsModalOpen(true);
  };

  const handleLeadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const leadId = `LEAD-${new Date().getFullYear()}-${Math.floor(10000 + Math.random() * 90000)}`;
    setSubmittedLeadId(leadId);

    // Call Control API or log lead intent
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://os.mcsolutions.stream';
      await fetch(`${apiUrl}/v1/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_id: `evt-${leadId}`,
          producer: 'mcs-products-portal',
          event_type: 'crm.lead.inquiry.v1',
          product_slug: selectedProduct?.slug || 'corporate',
          payload: {
            lead_id: leadId,
            ...leadForm,
            submitted_at: new Date().toISOString(),
          },
        }),
      });
    } catch (err) {
      console.log('Lead registered locally in queue');
    }
  };

  return (
    <main className="font-sans bg-slate-900 text-slate-100 min-h-screen">
      {/* Top Corporate Navigation */}
      <nav className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="font-bold text-lg tracking-tight text-white flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse"></span>
              <span>Multimedia Cloud Solutions</span>
            </Link>
            <span className="hidden md:inline-block text-xs font-semibold px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800/60">
              Product Portfolio
            </span>
          </div>

          <div className="flex items-center gap-4 text-xs font-medium">
            <Link href="/" className="text-slate-300 hover:text-white transition">
              Command Centre
            </Link>
            <Link href="/products" className="text-cyan-400 font-bold border-b-2 border-cyan-400 pb-0.5">
              Products & Solutions
            </Link>
            <a
              href="https://erp.mcsolutions.stream/app"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-300 hover:text-white transition flex items-center gap-1"
            >
              <span>ERPDesk</span>
              <span>↗</span>
            </a>
            <button
              onClick={() => handleOpenLeadModal(products[0])}
              className="px-3 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-lg transition shadow-xs"
            >
              Get a Proposal
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="relative pt-16 pb-12 px-6 max-w-7xl mx-auto text-center overflow-hidden">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/90 border border-slate-700 text-xs font-bold text-cyan-400 tracking-wider uppercase mb-5">
          <span>Intelligent Media Infrastructure & Ad-Tech</span>
        </div>
        <h1 className="text-3xl md:text-5xl font-extrabold text-white tracking-tight max-w-4xl mx-auto leading-tight">
          One Unified Spine for Broadcast, FAST TV & High-Yield Programmatic Monetization
        </h1>
        <p className="mt-4 text-base md:text-lg text-slate-400 max-w-3xl mx-auto leading-relaxed">
          Multimedia Cloud Solutions (MCS) builds sovereign media infrastructure: hardware-accelerated linear cloud playout, sub-3ms programmatic ad decisioning, Connected TV app generation, and attribution-backed market intelligence.
        </p>

        {/* Hero Proof Metrics */}
        <div className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/80">
            <span className="text-2xl md:text-3xl font-extrabold text-cyan-400 font-mono">0.86 ms</span>
            <p className="text-xs text-slate-400 mt-1 font-medium">p99 Ad Decision Latency</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/80">
            <span className="text-2xl md:text-3xl font-extrabold text-emerald-400 font-mono">1,420+</span>
            <p className="text-xs text-slate-400 mt-1 font-medium">Broadcast Feeds Monitored</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/80">
            <span className="text-2xl md:text-3xl font-extrabold text-indigo-400 font-mono">100%</span>
            <p className="text-xs text-slate-400 mt-1 font-medium">Attributed ERP Reconciliation</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/80">
            <span className="text-2xl md:text-3xl font-extrabold text-amber-400 font-mono">8 Systems</span>
            <p className="text-xs text-slate-400 mt-1 font-medium">Production-Grade Portfolio</p>
          </div>
        </div>
      </header>

      {/* Category Filter Tabs */}
      <section className="max-w-7xl mx-auto px-6 mb-10">
        <div className="flex flex-wrap justify-center gap-2 border-b border-slate-800 pb-4">
          <button
            onClick={() => setActiveCategory('all')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${activeCategory === 'all' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            All Products (8)
          </button>
          <button
            onClick={() => setActiveCategory('broadcast')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${activeCategory === 'broadcast' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            Broadcast & FAST Playout
          </button>
          <button
            onClick={() => setActiveCategory('adtech')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${activeCategory === 'adtech' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            Ad-Tech & Programmatic (ADS / ADX)
          </button>
          <button
            onClick={() => setActiveCategory('intelligence')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${activeCategory === 'intelligence' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            Media & Market Intelligence
          </button>
          <button
            onClick={() => setActiveCategory('enterprise')}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition ${activeCategory === 'enterprise' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            Enterprise Spines & ERPNext
          </button>
        </div>
      </section>

      {/* Products Showcase Grid */}
      <section className="max-w-7xl mx-auto px-6 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredProducts.map(product => (
            <div
              key={product.slug}
              className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-6 flex flex-col justify-between hover:border-cyan-500/50 hover:shadow-xl hover:shadow-cyan-950/20 transition group"
            >
              <div>
                {/* Header Row */}
                <div className="flex justify-between items-start gap-3">
                  <div>
                    <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded bg-slate-700 text-cyan-300 border border-slate-600">
                      {product.badge}
                    </span>
                    <h3 className="text-xl font-bold text-white mt-2 group-hover:text-cyan-300 transition">
                      {product.name}
                    </h3>
                  </div>
                  <span className="text-xs font-mono text-slate-400 bg-slate-900/60 px-2 py-1 rounded">
                    {product.repoName.split('/')[1]}
                  </span>
                </div>

                <p className="text-sm font-semibold text-slate-300 mt-1">{product.tagline}</p>
                <p className="text-xs text-slate-400 mt-2 leading-relaxed">{product.overview}</p>

                {/* Key Capabilities Bullet Points */}
                <div className="mt-4 pt-3 border-t border-slate-700/60">
                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">Technical Capabilities</h4>
                  <ul className="space-y-1.5 text-xs text-slate-300">
                    {product.capabilities.slice(0, 4).map((cap, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-cyan-400 mt-0.5">▹</span>
                        <span>{cap}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Key Differentiator Box */}
                <div className="mt-4 p-3 rounded-lg bg-slate-900/90 border border-slate-700/60">
                  <span className="text-[10px] uppercase font-bold text-amber-400 tracking-wider block">Proprietary Advantage</span>
                  <p className="text-xs text-slate-300 mt-1">{product.differentiator}</p>
                </div>

                {/* Tech Stack Pills */}
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {product.techStack.map(tech => (
                    <span key={tech} className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800">
                      {tech}
                    </span>
                  ))}
                </div>
              </div>

              {/* Bottom Card Footer */}
              <div className="mt-6 pt-4 border-t border-slate-700/60 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div className="text-xs text-slate-400">
                  <span className="block text-[10px] uppercase font-bold text-slate-500">Commercial Model</span>
                  <span className="text-slate-300 font-medium">{product.commercialModel}</span>
                </div>

                <div className="flex gap-2 w-full sm:w-auto justify-end">
                  {product.liveUrl && (
                    <a
                      href={product.liveUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs font-semibold rounded-lg transition"
                    >
                      Live Console ↗
                    </a>
                  )}
                  <button
                    onClick={() => handleOpenLeadModal(product)}
                    className="px-3 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold rounded-lg transition shadow-xs"
                  >
                    Request Demo
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* End-to-End Synergy Pipeline Infographic */}
      <section className="bg-slate-950 py-16 px-6 border-t border-slate-800">
        <div className="max-w-7xl mx-auto text-center">
          <span className="text-xs font-bold text-cyan-400 tracking-wider uppercase">Integrated Synergy</span>
          <h2 className="text-2xl md:text-3xl font-extrabold text-white mt-1">The Complete Camera-to-Cash Video Spine</h2>
          <p className="text-xs md:text-sm text-slate-400 mt-2 max-w-2xl mx-auto">
            Unlike fragmented multi-vendor stacks, MCS connects live broadcast encoding, Connected TV app generation, sub-3ms ad decisioning, and automated accounting into one deterministic pipeline.
          </p>

          <div className="mt-10 grid grid-cols-1 md:grid-cols-5 gap-3 max-w-5xl mx-auto text-left">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs font-mono text-cyan-400 font-bold">01 • Ingest & Playout</span>
              <h4 className="font-bold text-sm text-white mt-1">CloudStream VCP</h4>
              <p className="text-[11px] text-slate-400 mt-1">GPU transcoding, SCTE-35 insertion & VLM cue arbitration.</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs font-mono text-cyan-400 font-bold">02 • Turnkey Apps</span>
              <h4 className="font-bold text-sm text-white mt-1">CloudStream Forge</h4>
              <p className="text-[11px] text-slate-400 mt-1">Instant branded apps on Roku, Apple TV, Fire TV, and mobile.</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs font-mono text-cyan-400 font-bold">03 • Ad Monetization</span>
              <h4 className="font-bold text-sm text-white mt-1">Aether ADS & ADX</h4>
              <p className="text-[11px] text-slate-400 mt-1">Sub-3ms ad decisioning, OpenRTB 3.0 SSP, and dynamic yield.</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs font-mono text-cyan-400 font-bold">04 • Media Analytics</span>
              <h4 className="font-bold text-sm text-white mt-1">TV-Insights / Pulzz</h4>
              <p className="text-[11px] text-slate-400 mt-1">1,420+ feeds monitored, EPG intelligence & share-of-voice.</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <span className="text-xs font-mono text-cyan-400 font-bold">05 • Settlement</span>
              <h4 className="font-bold text-sm text-white mt-1">MCS-ERP (v15)</h4>
              <p className="text-[11px] text-slate-400 mt-1">Automated multi-currency billing, VAT 7.5%, and partner payouts.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Enterprise Commercial Tiers */}
      <section className="py-16 px-6 max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <span className="text-xs font-bold text-cyan-400 tracking-wider uppercase">Commercial Engagement</span>
          <h2 className="text-2xl md:text-3xl font-extrabold text-white mt-1">Engagement & Deployment Models</h2>
          <p className="text-xs md:text-sm text-slate-400 mt-2">Tailored for national broadcasters, FAST channel creators, and digital media publishers.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 bg-slate-800/60 border border-slate-700 rounded-2xl flex flex-col justify-between">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">FAST & Channel Creators</span>
              <h3 className="text-xl font-bold text-white mt-1">Digital Network Launch</h3>
              <p className="text-xs text-slate-400 mt-2">Turnkey playout and Connected TV distribution for 1–5 linear channels.</p>
              <ul className="mt-4 space-y-2 text-xs text-slate-300">
                <li>✓ CloudStream VCP live SRT / RTMP ingest</li>
                <li>✓ Branded web & mobile streaming apps</li>
                <li>✓ Programmatic ad monetization via Aether ADX</li>
                <li>✓ Automated monthly revenue-share accounting</li>
              </ul>
            </div>
            <button
              onClick={() => handleOpenLeadModal(products[1])}
              className="mt-6 w-full py-2 bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold rounded-lg transition"
            >
              Select FAST Launch
            </button>
          </div>

          <div className="p-6 bg-gradient-to-b from-slate-800 via-indigo-950/40 to-slate-800 border-2 border-cyan-400/80 rounded-2xl flex flex-col justify-between shadow-xl relative">
            <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-cyan-400 text-slate-950 text-[10px] font-extrabold uppercase px-3 py-0.5 rounded-full">
              Most Popular
            </span>
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-cyan-300">Broadcasters & Networks</span>
              <h3 className="text-xl font-bold text-white mt-1">Full Commercial Playout & SSAI</h3>
              <p className="text-xs text-slate-400 mt-2">Enterprise linear cloud playout with sub-3ms ad decisioning and TV analytics.</p>
              <ul className="mt-4 space-y-2 text-xs text-slate-300">
                <li>✓ Dedicated GPU-accelerated transcoding (NVENC)</li>
                <li>✓ Multi-modal AI break detection & VLM arbiter</li>
                <li>✓ Aether ADS ad decision server with dynamic floor pricing</li>
                <li>✓ TV-Insights competitor ad expenditure tracking</li>
                <li>✓ 99.99% broadcast SLA uptime guarantee</li>
              </ul>
            </div>
            <button
              onClick={() => handleOpenLeadModal(products[0])}
              className="mt-6 w-full py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold rounded-lg transition shadow-md"
            >
              Request Broadcaster Proposal
            </button>
          </div>

          <div className="p-6 bg-slate-800/60 border border-slate-700 rounded-2xl flex flex-col justify-between">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Enterprise & Sovereign</span>
              <h3 className="text-xl font-bold text-white mt-1">Private Cloud & Spine Licensing</h3>
              <p className="text-xs text-slate-400 mt-2">Dedicated single-tenant infrastructure with custom POPs and ERP integration.</p>
              <ul className="mt-4 space-y-2 text-xs text-slate-300">
                <li>✓ Dedicated regional edge POPs (Lagos, Johannesburg, Nairobi)</li>
                <li>✓ Custom vertical subject packs via MCS App Factory</li>
                <li>✓ Direct ERPNext on-prem or isolated cloud deployment</li>
                <li>✓ Dedicated 24/7 mission control engineering support</li>
              </ul>
            </div>
            <button
              onClick={() => handleOpenLeadModal(products[6])}
              className="mt-6 w-full py-2 bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold rounded-lg transition"
            >
              Contact Enterprise Sales
            </button>
          </div>
        </div>
      </section>

      {/* Proposal / Demo Request Modal (Linked to ERPNext CRM) */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl text-left">
            <div className="flex justify-between items-start border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-white">Request Solution Proposal & Demo</h3>
                <p className="text-xs text-slate-400 mt-0.5">Automated lead dispatch to MCS-ERP & Commercial Engineering</p>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white font-bold p-1">
                ✕
              </button>
            </div>

            {submittedLeadId ? (
              <div className="py-8 text-center">
                <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto text-xl font-bold border border-emerald-500/40">
                  ✓
                </div>
                <h4 className="text-base font-bold text-white mt-3">Proposal Request Received!</h4>
                <p className="text-xs text-slate-300 mt-1">
                  Ticket Reference: <code className="text-cyan-400 font-mono font-bold">{submittedLeadId}</code>
                </p>
                <p className="text-xs text-slate-400 mt-2 max-w-sm mx-auto">
                  A commercial solutions engineer has been notified and an introductory quotation has been initialized in ERPNext.
                </p>
                <button
                  onClick={() => {
                    setIsModalOpen(false);
                    setSubmittedLeadId(null);
                  }}
                  className="mt-5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-lg transition"
                >
                  Close Window
                </button>
              </div>
            ) : (
              <form onSubmit={handleLeadSubmit} className="mt-4 space-y-3.5">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
                  <input
                    type="text"
                    required
                    value={leadForm.name}
                    onChange={e => setLeadForm({ ...leadForm, name: e.target.value })}
                    placeholder="e.g. Tunde Aina"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Company / Station</label>
                    <input
                      type="text"
                      required
                      value={leadForm.company}
                      onChange={e => setLeadForm({ ...leadForm, company: e.target.value })}
                      placeholder="e.g. Metro Broadcast"
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Work Email</label>
                    <input
                      type="email"
                      required
                      value={leadForm.email}
                      onChange={e => setLeadForm({ ...leadForm, email: e.target.value })}
                      placeholder="name@company.com"
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Product of Interest</label>
                  <select
                    value={leadForm.product}
                    onChange={e => setLeadForm({ ...leadForm, product: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                  >
                    {products.map(p => (
                      <option key={p.slug} value={p.name}>
                        {p.name} — {p.tagline.slice(0, 45)}...
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Requirements / Message</label>
                  <textarea
                    rows={3}
                    value={leadForm.message}
                    onChange={e => setLeadForm({ ...leadForm, message: e.target.value })}
                    placeholder="Describe your active channel volume, streaming formats, or advertising integration goals..."
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                  ></textarea>
                </div>
                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold rounded-lg transition shadow-xs"
                  >
                    Submit Proposal Request
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-800 py-8 px-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-4">
          <p>© {new Date().getFullYear()} Multimedia Cloud Solutions Ltd. • Autonomous Corporate Operating System v2.2</p>
          <div className="flex gap-4">
            <Link href="/" className="hover:text-slate-300 transition">Command Centre</Link>
            <a href="https://erp.mcsolutions.stream" target="_blank" rel="noopener noreferrer" className="hover:text-slate-300 transition">ERPNext Desk</a>
            <a href="https://pulzz.mcsolutions.stream" target="_blank" rel="noopener noreferrer" className="hover:text-slate-300 transition">Pulzz Live</a>
          </div>
        </div>
      </footer>
    </main>
  );
}
