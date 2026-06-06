import { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { api, type BahanUpah } from '@/lib/api';
import { DataGrid, type ColDef } from '@/components/grid';
import { Button, Spinner, useToast } from '@/components/ui';
import { rupiah } from '@/lib/utils';

export default function BahanUpahPage() {
  const toast = useToast();
  const [rows, setRows] = useState<BahanUpah[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);

  const load = () => { setLoading(true); api.bahanUpah().then(setRows).catch((e) => toast(e.message, false)).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, []);

  const cols = useMemo<ColDef<BahanUpah>[]>(() => [
    { headerName: 'Nama', field: 'nama', flex: 2, minWidth: 220 },
    { headerName: 'Satuan', field: 'satuan', width: 90 },
    { headerName: 'Harga', field: 'harga', width: 150, type: 'rightAligned', valueFormatter: (p) => rupiah(p.value) },
    { headerName: 'Kategori', field: 'category', width: 110 },
    { headerName: 'Tier', field: 'tier', width: 80 },
    { headerName: 'TKDN', field: 'tkdn_factor', width: 90, valueFormatter: (p) => p.value != null ? `${(p.value * 100).toFixed(0)}%` : '-' },
    { headerName: 'Sumber', field: 'source_label', flex: 1.5, minWidth: 160 },
    { headerName: 'Tahun', field: 'tahun', width: 90 },
  ], []);

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Bahan &amp; Upah</h1>
          <p className="text-sm text-muted">{loading ? <Spinner /> : `${rows.length.toLocaleString('id-ID')} item · SSH / distributor`}</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
            <input className="input pl-8 w-64" placeholder="Cari nama…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Button variant="outline" onClick={load}>Muat ulang</Button>
        </div>
      </div>
      <DataGrid<BahanUpah> rowData={rows} columnDefs={cols} quickFilter={q} getRowId={(p) => String(p.data.id)} pageSize={100} />
    </div>
  );
}
