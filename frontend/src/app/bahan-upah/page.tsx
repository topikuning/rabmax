'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Boxes } from 'lucide-react';
import { api, auth } from '@/lib/api';
import { Badge, Card, EmptyState, Input, Spinner } from '@/components/ui';
import { formatRupiah } from '@/lib/utils';
import type { BahanUpah } from '@/types';

export default function BahanUpahPage() {
  const router = useRouter();
  const [q, setQ] = useState('');
  const [rows, setRows] = useState<BahanUpah[]>([]);
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
        .listBahanUpah(q)
        .then(setRows)
        .catch((e) => setErr(e.message))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(t);
  }, [q, router]);

  const tierTone = (t: string) =>
    t === 'A' ? 'success' : t === 'B' ? 'primary' : t === 'C' ? 'warning' : 'danger';

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div className="flex items-center gap-2">
        <Boxes className="h-5 w-5 text-primary" />
        <h1 className="text-2xl font-bold tracking-tight">Bahan &amp; Upah</h1>
      </div>
      <p className="text-sm text-muted-foreground -mt-3">
        Master harga material/upah/alat (SSH provinsi + distributor).
      </p>

      <div className="relative">
        <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Cari nama material/upah…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </div>

      {err && <Card className="p-4 border-destructive/40 text-destructive text-sm">{err}</Card>}

      {loading ? (
        <div className="flex justify-center py-12 text-muted-foreground"><Spinner /></div>
      ) : rows.length === 0 ? (
        <EmptyState
          title="Belum ada data harga"
          desc="Master bahan & upah perlu di-seed lebih dulu (roadmap seeding)."
        />
      ) : (
        <Card className="divide-y divide-border overflow-hidden">
          {rows.map((b) => (
            <div key={b.id} className="p-3 hover:bg-muted/40 transition-colors flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm truncate">{b.nama}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {b.source_label} · {b.tahun}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <Badge tone={tierTone(b.tier) as 'success'}>Tier {b.tier}</Badge>
                <div className="text-right">
                  <div className="text-sm font-semibold">{formatRupiah(b.harga)}</div>
                  <div className="text-xs text-muted-foreground">/ {b.satuan}</div>
                </div>
              </div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
