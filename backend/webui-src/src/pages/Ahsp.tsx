import { useEffect, useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { api, type AHSP } from '@/lib/api';
import { DataGrid, type ColDef } from '@/components/grid';
import { Button, Spinner, useToast } from '@/components/ui';

export default function Ahsp() {
  const toast = useToast();
  const [rows, setRows] = useState<AHSP[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);

  const load = () => { setLoading(true); api.ahsp().then(setRows).catch((e) => toast(e.message, false)).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, []);

  const cols = useMemo<ColDef<AHSP>[]>(() => [
    { headerName: 'Kode', field: 'kode', width: 170, cellClass: 'font-mono text-[12px]' },
    { headerName: 'Uraian', field: 'uraian', flex: 3, minWidth: 280, wrapText: false },
    { headerName: 'Satuan', field: 'satuan', width: 90 },
    { headerName: 'Work Group', field: 'work_group', width: 140 },
    { headerName: 'Sumber', field: 'source', width: 160 },
    { headerName: 'Tier', field: 'confidence_tier', width: 130 },
  ], []);

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Katalog AHSP</h1>
          <p className="text-sm text-muted">{loading ? <Spinner /> : `${rows.length.toLocaleString('id-ID')} item · Permen PUPR / SE DJBK`}</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
            <input className="input pl-8 w-72" placeholder="Cari kode / uraian / work group…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Button variant="outline" onClick={load}>Muat ulang</Button>
        </div>
      </div>
      <DataGrid<AHSP> rowData={rows} columnDefs={cols} quickFilter={q} getRowId={(p) => String(p.data.id)} pageSize={100} />
    </div>
  );
}
