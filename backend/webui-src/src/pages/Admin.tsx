import { useEffect, useState } from 'react';
import { Database, Download, Upload, ShieldAlert, RefreshCw, Sparkles, Zap } from 'lucide-react';
import { api, type AIProvider, type AITestResult } from '@/lib/api';
import { Button, Spinner, useToast } from '@/components/ui';

function AiTest() {
  const [providers, setProviders] = useState<AIProvider[]>([]);
  const [provider, setProvider] = useState('claude');
  const [prompt, setPrompt] = useState('Balas satu kata: OK');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AITestResult | null>(null);

  const load = () => api.aiStatus().then((s) => setProviders(s.providers)).catch(() => {});
  useEffect(() => { load(); }, []);

  async function test() {
    setBusy(true); setResult(null);
    try { setResult(await api.aiTest(provider, prompt)); }
    catch (e) { setResult({ ok: false, provider, latency_ms: 0, error: e instanceof Error ? e.message : 'Gagal' }); }
    finally { setBusy(false); }
  }

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2"><Sparkles className="h-4 w-4 text-muted" /> Tes AI &amp; Integrasi</h2>
        <Button variant="ghost" onClick={load}><RefreshCw className="h-3.5 w-3.5" /> Refresh</Button>
      </div>

      <div className="grid sm:grid-cols-3 gap-2">
        {providers.map((p) => (
          <div key={p.provider} className="rounded-lg border border-border p-3">
            <div className="flex items-center justify-between">
              <span className="font-medium capitalize">{p.provider}</span>
              <span className={'chip ' + (p.configured ? 'bg-success/15 text-success' : 'bg-warning/15 text-warning')}>
                {p.configured ? 'siap' : 'belum'}
              </span>
            </div>
            <div className="text-xs text-muted mt-1">{p.default_model}</div>
            <div className="text-xs text-muted mt-0.5">{p.reason}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-2 items-end flex-wrap">
        <label className="text-sm">
          <span className="block text-xs text-muted mb-1">Provider</span>
          <select className="input w-36" value={provider} onChange={(e) => setProvider(e.target.value)}>
            {providers.map((p) => <option key={p.provider} value={p.provider}>{p.provider}</option>)}
          </select>
        </label>
        <label className="text-sm flex-1 min-w-[200px]">
          <span className="block text-xs text-muted mb-1">Prompt uji</span>
          <input className="input" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        </label>
        <Button loading={busy} onClick={test}><Zap className="h-4 w-4" /> Test</Button>
      </div>

      {result && (
        <div className={'rounded-lg p-3 text-sm ' + (result.ok ? 'bg-success/10' : 'bg-danger/10 text-danger')}>
          {result.ok ? (
            <div className="space-y-1">
              <div className="font-medium text-success">✓ {result.provider} · {result.model} · {result.latency_ms} ms</div>
              <div className="font-mono text-xs break-words">{result.text}</div>
              <div className="text-xs text-muted">tokens in/out: {result.input_tokens}/{result.output_tokens}</div>
            </div>
          ) : (
            <div><span className="font-medium">✗ Gagal ({result.latency_ms} ms):</span> {result.error}</div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Admin() {
  const toast = useToast();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [stats, setStats] = useState<{ ahsp_count: number; bahan_upah_count: number; bundled_ahsp_available: boolean } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const loadStats = () => api.adminStats().then(setStats).catch(() => {});
  useEffect(() => {
    api.me().then((u) => { setAllowed(u.is_superuser); if (u.is_superuser) loadStats(); }).catch(() => setAllowed(false));
  }, []);

  function upload(kind: 'ahsp' | 'bahan-upah') {
    const inp = document.createElement('input'); inp.type = 'file'; inp.accept = '.json,.jsonl,.gz';
    inp.onchange = async () => {
      const f = inp.files?.[0]; if (!f) return;
      setBusy(kind);
      try { const r = await api.seedUpload(kind, f); toast('Seed OK: ' + JSON.stringify(r).slice(0, 100)); loadStats(); }
      catch (e) { toast(e instanceof Error ? e.message : 'Gagal', false); }
      finally { setBusy(null); }
    };
    inp.click();
  }

  if (allowed === null) return <div className="flex-1 flex items-center justify-center text-muted"><Spinner /></div>;
  if (!allowed) return (
    <div className="flex-1 flex flex-col items-center justify-center text-center text-muted gap-2">
      <ShieldAlert className="h-8 w-8" /><p>Halaman admin hanya untuk superuser (user pertama yang mendaftar).</p>
    </div>
  );

  return (
    <div className="max-w-2xl space-y-5">
      <div className="flex items-center gap-2"><ShieldAlert className="h-5 w-5 text-primary" /><h1 className="text-xl font-bold tracking-tight">Admin — Data Master</h1></div>

      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold flex items-center gap-2"><Database className="h-4 w-4 text-muted" /> Statistik</h2>
          <Button variant="ghost" onClick={loadStats}><RefreshCw className="h-3.5 w-3.5" /> Refresh</Button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-bg p-3"><div className="text-2xl font-bold">{stats?.ahsp_count?.toLocaleString('id-ID') ?? '—'}</div><div className="text-xs text-muted">AHSP</div></div>
          <div className="rounded-lg bg-bg p-3"><div className="text-2xl font-bold">{stats?.bahan_upah_count?.toLocaleString('id-ID') ?? '—'}</div><div className="text-xs text-muted">Bahan &amp; Upah</div></div>
        </div>
      </div>

      <div className="card p-5 space-y-3">
        <h2 className="font-semibold flex items-center gap-2"><Download className="h-4 w-4 text-muted" /> Seed AHSP bawaan (SE DJBK 47/2026)</h2>
        <p className="text-sm text-muted">Muat ~5.115 AHSP yang dibundel. Aman diulang (idempotent).</p>
        <Button loading={busy === 'bundled'} disabled={!stats?.bundled_ahsp_available}
          onClick={async () => { setBusy('bundled'); try { const r = await api.seedBundled(); toast(`Seed: +${r.created} baru`); loadStats(); } catch (e) { toast(e instanceof Error ? e.message : 'Gagal', false); } finally { setBusy(null); } }}>
          <Download className="h-4 w-4" /> Seed data bawaan
        </Button>
      </div>

      <div className="card p-5 space-y-3">
        <h2 className="font-semibold flex items-center gap-2"><Upload className="h-4 w-4 text-muted" /> Upload data baru (JSON/JSONL/.gz)</h2>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" loading={busy === 'ahsp'} onClick={() => upload('ahsp')}>Upload AHSP</Button>
          <Button variant="outline" loading={busy === 'bahan-upah'} onClick={() => upload('bahan-upah')}>Upload Harga Bahan &amp; Upah</Button>
        </div>
      </div>

      <AiTest />
    </div>
  );
}
