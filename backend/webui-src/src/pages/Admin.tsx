import { useEffect, useState } from 'react';
import { Database, Download, Upload, ShieldAlert, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
import { Button, Spinner, useToast } from '@/components/ui';

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
    </div>
  );
}
