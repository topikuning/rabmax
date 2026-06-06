'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, BookOpen } from 'lucide-react';
import { api, auth } from '@/lib/api';
import { Badge, Card, EmptyState, Input, Spinner } from '@/components/ui';
import type { AHSP } from '@/types';

export default function AhspPage() {
  const router = useRouter();
  const [q, setQ] = useState('');
  const [rows, setRows] = useState<AHSP[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.isAuthed()) {
      router.replace('/login');
      return;
    }
    const t = setTimeout(() => {
      setLoading(true);
      api
        .listAhsp(q)
        .then(setRows)
        .catch((e) => setErr(e.message))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [q, router]);

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div className="flex items-center gap-2">
        <BookOpen className="h-5 w-5 text-primary" />
        <h1 className="text-2xl font-bold tracking-tight">Katalog AHSP</h1>
      </div>
      <p className="text-sm text-muted-foreground -mt-3">
        Analisa Harga Satuan Pekerjaan (Permen PUPR 8/2023).
      </p>

      <div className="relative">
        <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Cari kode atau uraian…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      {err && <Card className="p-4 border-destructive/40 text-destructive text-sm">{err}</Card>}

      {loading ? (
        <div className="flex justify-center py-12 text-muted-foreground"><Spinner /></div>
      ) : rows.length === 0 ? (
        <EmptyState
          title="Belum ada data AHSP"
          desc="Katalog AHSP perlu di-seed lebih dulu (lihat scripts/ — roadmap seeding)."
        />
      ) : (
        <Card className="divide-y divide-border overflow-hidden">
          {rows.map((a) => (
            <div key={a.id} className="p-3 hover:bg-muted/40 transition-colors">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-xs text-primary">{a.kode}</span>
                <div className="flex items-center gap-2">
                  {a.work_group && <Badge tone="primary">{a.work_group}</Badge>}
                  <Badge>{a.satuan}</Badge>
                </div>
              </div>
              <p className="text-sm mt-1">{a.uraian}</p>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
