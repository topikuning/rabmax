'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Database, Upload, Download, ShieldAlert, RefreshCw } from 'lucide-react';
import { api, auth } from '@/lib/api';
import { Button, Card, EmptyState, Spinner } from '@/components/ui';

type Stats = { ahsp_count: number; bahan_upah_count: number; bundled_ahsp_available: boolean };

export default function AdminPage() {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setStats(await api.adminStats());
  }, []);

  useEffect(() => {
    if (!auth.isAuthed()) {
      router.replace('/login');
      return;
    }
    api
      .me()
      .then((u) => {
        setAllowed(u.is_superuser);
        if (u.is_superuser) return loadStats();
      })
      .catch((e) => setErr(e.message));
  }, [router, loadStats]);

  async function run(key: string, fn: () => Promise<Record<string, unknown>>) {
    setErr(null);
    setMsg(null);
    setBusy(key);
    try {
      const r = await fn();
      setMsg(JSON.stringify(r));
      await loadStats();
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Gagal');
    } finally {
      setBusy(null);
    }
  }

  if (allowed === false)
    return (
      <EmptyState
        title="Akses ditolak"
        desc="Halaman admin hanya untuk superuser (user pertama yang mendaftar)."
      />
    );
  if (allowed === null)
    return <div className="flex justify-center py-16 text-muted-foreground"><Spinner /></div>;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-2">
        <ShieldAlert className="h-5 w-5 text-primary" />
        <h1 className="text-2xl font-bold tracking-tight">Admin — Data Master</h1>
      </div>

      {/* Stats */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold flex items-center gap-2">
            <Database className="h-4 w-4 text-muted-foreground" /> Statistik
          </h2>
          <Button variant="ghost" size="sm" onClick={loadStats}>
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </Button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-muted/50 p-3">
            <div className="text-2xl font-bold">{stats?.ahsp_count ?? '—'}</div>
            <div className="text-xs text-muted-foreground">AHSP</div>
          </div>
          <div className="rounded-lg bg-muted/50 p-3">
            <div className="text-2xl font-bold">{stats?.bahan_upah_count ?? '—'}</div>
            <div className="text-xs text-muted-foreground">Bahan &amp; Upah</div>
          </div>
        </div>
      </Card>

      {/* Seed bundled */}
      <Card className="p-5 space-y-3">
        <h2 className="font-semibold flex items-center gap-2">
          <Download className="h-4 w-4 text-muted-foreground" /> Seed AHSP bawaan (SE DJBK 47/2026)
        </h2>
        <p className="text-sm text-muted-foreground">
          Muat ~5.115 AHSP yang sudah dibundel di aplikasi. Aman diulang (idempotent).
        </p>
        <Button
          loading={busy === 'bundled'}
          disabled={!stats?.bundled_ahsp_available}
          onClick={() => run('bundled', () => api.seedBundled())}
        >
          <Download className="h-4 w-4" /> Seed dari data bawaan
        </Button>
      </Card>

      {/* Upload AHSP */}
      <UploadCard
        title="Upload AHSP (JSON/JSONL/.gz)"
        busy={busy === 'up-ahsp'}
        onUpload={(f) => run('up-ahsp', () => api.seedUpload('ahsp', f))}
      />
      {/* Upload Bahan & Upah */}
      <UploadCard
        title="Upload Harga Bahan & Upah (JSON/JSONL/.gz)"
        busy={busy === 'up-bu'}
        onUpload={(f) => run('up-bu', () => api.seedUpload('bahan-upah', f))}
      />

      {msg && (
        <Card className="p-3 text-xs bg-success/10 text-success break-all">{msg}</Card>
      )}
      {err && (
        <Card className="p-3 text-xs border-destructive/40 text-destructive break-all">{err}</Card>
      )}
    </div>
  );
}

function UploadCard({
  title, busy, onUpload,
}: {
  title: string;
  busy: boolean;
  onUpload: (f: File) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  return (
    <Card className="p-5 space-y-3">
      <h2 className="font-semibold flex items-center gap-2">
        <Upload className="h-4 w-4 text-muted-foreground" /> {title}
      </h2>
      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="file"
          accept=".json,.jsonl,.gz"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="flex-1 min-w-[200px] text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-muted file:px-3 file:py-2 file:text-sm file:font-medium hover:file:bg-muted/70 cursor-pointer"
        />
        <Button disabled={!file} loading={busy} onClick={() => file && onUpload(file)}>
          Upload &amp; Seed
        </Button>
      </div>
    </Card>
  );
}
