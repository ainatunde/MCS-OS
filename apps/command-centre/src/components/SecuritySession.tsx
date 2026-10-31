'use client';

import React, { useEffect, useState } from 'react';

const api = process.env.NEXT_PUBLIC_API_URL || 'https://os.mcsolutions.stream';

export async function securityFetch(url: string, options: RequestInit = {}) {
  const result = await fetch(url, { ...options, credentials: 'include', cache: 'no-store' });
  if (!result.ok) {
    const body = await result.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${result.status}). Sign in again or retry.`);
  }
  return result;
}

export default function SecuritySession({ children }: { children: (role: string) => React.ReactNode }) {
  const [session, setSession] = useState<{role: string; email: string} | null>(null);
  const [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  useEffect(() => {
    let active = true;
    securityFetch(`${api}/v1/session`).then(r => r.json()).then(s => { if (active) setSession(s); })
      .catch(() => {}).finally(() => { if (active) setChecking(false); });
    return () => { active = false; };
  }, []);
  if (checking) return <main className="mx-auto max-w-lg p-8" role="status">Checking your session…</main>;
  if (session) return <><div className="flex flex-wrap justify-between gap-3 border-b border-stone-200 bg-white px-6 py-3 text-sm"><span>Signed in as {session.email}</span><button className="font-semibold underline underline-offset-4 disabled:opacity-50" disabled={busy} onClick={async () => {setBusy(true);setError('');try {await securityFetch(`${api}/v1/session`, {method:'DELETE'});setSession(null);}catch(e){setError(e instanceof Error?e.message:'Sign-out failed');}finally{setBusy(false);}}}>Sign out</button></div>{error && <p role="alert" className="p-4 text-red-800">{error}</p>}{children(session.role)}</>;
  return <main className="mx-auto max-w-lg px-6 py-16 text-stone-900"><h1 className="text-2xl font-bold">Company command centre</h1><p className="mt-4 leading-relaxed text-stone-600">Sign in with your individual ERPNext account. Permissions follow your verified company role.</p><form className="mt-8 space-y-5" onSubmit={async e => {e.preventDefault();setBusy(true);setError('');try{const r=await securityFetch(`${api}/v1/session`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username,password})});setSession(await r.json());setPassword('');}catch(e){setPassword('');setError(e instanceof Error?e.message:'Sign-in failed');}finally{setBusy(false);}}}><label className="block font-medium">ERPNext username<input className="mt-2 w-full rounded-lg border border-stone-400 bg-white px-3 py-3 text-base focus:outline-orange-700" autoComplete="username" required value={username} onChange={e=>setUsername(e.target.value)} /></label><label className="block font-medium">Password<input className="mt-2 w-full rounded-lg border border-stone-400 bg-white px-3 py-3 text-base focus:outline-orange-700" type="password" autoComplete="current-password" required value={password} onChange={e=>setPassword(e.target.value)} /></label>{error && <p role="alert" className="text-red-800">{error}</p>}<button className="rounded-lg bg-orange-700 px-5 py-3 font-semibold text-white hover:bg-orange-800 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-orange-700" disabled={busy}>{busy?'Signing in…':'Sign in'}</button></form><a className="mt-6 inline-block underline underline-offset-4" href="https://erp.mcsolutions.stream/login#forgot">Reset your ERPNext password</a></main>;
}
