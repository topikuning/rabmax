import { useCallback, useEffect, useMemo, useState } from 'react';
import { MapPin, Search, ExternalLink, ChevronLeft, ChevronRight } from 'lucide-react';
import {
  api, type BahanUpah, type Provinsi, type Kota,
  type VendorRow, type SnapshotRow, type ConsensusRow, type PricingDataStats,
} from '@/lib/api';
import { DataGrid, type ColDef } from '@/components/grid';
import { Spinner, useToast } from '@/components/ui';
import { rupiah, num } from '@/lib/utils';

type Tab = 'lokasi' | 'vendor' | 'snapshot' | 'konsensus';
const TABS: { id: Tab; label: string }[] = [
  { id: 'lokasi', label: 'Harga per-lokasi' },
  { id: 'vendor', label: 'Vendor' },
  { id: 'snapshot', label: 'Snapshot (discovery)' },
  { id: 'konsensus', label: 'Konsensus' },
];
const PAGE = 200;

function Stat({ label, value, tone }: { label: string; value: number | string; tone?: string }) {
  return (
    <div className="card px-4 py-3 min-w-[8rem]">
      <div className={'text-lg font-bold ' + (tone || '')}>{typeof value === 'number' ? num(value) : value}</div>
      <div className="text-xs text-muted">{label}</div>
    </div>
  );
}

export default function DataHarga() {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>('lokasi');
  const [stats, setStats] = useState<PricingDataStats | null>(null);

  useEffect(() => { api.pricingDataStats().then(setStats).catch(() => {}); }, []);

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Data Harga (pricing intelligence)</h1>
        <p className="text-sm text-muted">Telusuri & audit semua data harga: SSH resmi per-kota, baseline nasional, vendor & snapshot hasil discovery, konsensus.</p>
      </div>

      {stats && (
        <div className="flex gap-3 flex-wrap">
          <Stat label="Harga (total baris)" value={stats.bahan_upah_total} />
          <Stat label="SSH per-kota" value={stats.bahan_upah_ssh} tone="text-primary" />
          <Stat label="Baseline nasional" value={stats.bahan_upah_nasional} />
          <Stat label="Kota terisi" value={stats.kota_terisi} />
          <Stat label="Vendor" value={stats.vendors} />
          <Stat label="Snapshot" value={stats.snapshots} />
          <Stat label="Konsensus" value={stats.consensus} />
          <Stat label="Override manual" value={stats.manual} />
        </div>
      )}

      <div className="flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={'px-3 h-9 text-sm border-b-2 -mb-px transition-colors ' +
              (tab === t.id ? 'border-primary text-primary font-medium' : 'border-transparent text-muted hover:text-fg')}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'lokasi' && <LokasiTab toast={toast} />}
      {tab === 'vendor' && <VendorTab toast={toast} />}
      {tab === 'snapshot' && <SnapshotTab toast={toast} />}
      {tab === 'konsensus' && <KonsensusTab toast={toast} />}
    </div>
  );
}

type Toast = ReturnType<typeof useToast>;

function LokasiTab({ toast }: { toast: Toast }) {
  const [rows, setRows] = useState<BahanUpah[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(0);
  const [q, setQ] = useState('');
  const [category, setCategory] = useState('');
  const [provinsi, setProvinsi] = useState<Provinsi[]>([]);
  const [kota, setKota] = useState<Kota[]>([]);
  const [provId, setProvId] = useState('');
  const [provNama, setProvNama] = useState('');
  const [kotaNama, setKotaNama] = useState('');

  useEffect(() => { api.provinsi().then(setProvinsi).catch(() => {}); }, []);
  useEffect(() => { if (provId) api.kota(Number(provId)).then(setKota).catch(() => {}); else setKota([]); }, [provId]);

  const filters = useMemo(() => ({ q, category, provinsi: provNama, kota: kotaNama }), [q, category, provNama, kotaNama]);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.bahanUpahQuery({ ...filters, limit: PAGE, offset: page * PAGE }),
      api.bahanUpahCount(filters),
    ]).then(([r, c]) => { setRows(r); setTotal(c.count); })
      .catch((e) => toast(e instanceof Error ? e.message : 'Gagal', false))
      .finally(() => setLoading(false));
  }, [filters, page, toast]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setPage(0); }, [q, category, provNama, kotaNama]);

  const cols = useMemo<ColDef<BahanUpah>[]>(() => [
    { headerName: 'Nama', field: 'nama', flex: 2, minWidth: 200 },
    { headerName: 'Satuan', field: 'satuan', width: 90 },
    { headerName: 'Harga', field: 'harga', width: 130, type: 'rightAligned',
      valueFormatter: (p) => (p.value > 0 ? rupiah(p.value) : 'belum ada'),
      cellStyle: (p: any) => (p.value > 0 ? null : { color: 'hsl(var(--warning))' }) },
    { headerName: 'Provinsi', field: 'provinsi', width: 150, valueFormatter: (p) => p.value || 'Nasional' },
    { headerName: 'Kota/Kab', field: 'kota', width: 170, valueFormatter: (p) => p.value || '—' },
    { headerName: 'Kategori', field: 'category', width: 100 },
    { headerName: 'Tier', field: 'tier', width: 70 },
    { headerName: 'Sumber', field: 'source_label', flex: 1, minWidth: 160 },
    { headerName: 'Thn', field: 'tahun', width: 70 },
  ], []);

  const maxPage = Math.max(0, Math.ceil(total / PAGE) - 1);

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-3">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative">
          <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
          <input className="input pl-8 w-56" placeholder="Cari nama…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="flex items-center gap-1">
          <MapPin className="h-4 w-4 text-muted" />
          <select className="input w-44" value={provId}
            onChange={(e) => { const id = e.target.value; setProvId(id); const p = provinsi.find((x) => String(x.id) === id); setProvNama(p?.nama || ''); setKotaNama(''); }}>
            <option value="">Semua provinsi</option>
            {provinsi.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}
          </select>
        </div>
        <select className="input w-44" value={kotaNama} disabled={!provId} onChange={(e) => setKotaNama(e.target.value)}>
          <option value="">Semua kota/kab</option>
          {kota.map((k) => <option key={k.id} value={k.nama}>{k.nama}</option>)}
        </select>
        <select className="input w-32" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Semua kategori</option>
          <option value="bahan">bahan</option><option value="upah">upah</option><option value="alat">alat</option>
        </select>
        <div className="ml-auto flex items-center gap-2 text-sm text-muted">
          {loading ? <Spinner /> : <span>{num(total)} baris</span>}
          <button className="btn-ghost h-8 w-8 p-0" disabled={page <= 0} onClick={() => setPage((p) => p - 1)}><ChevronLeft className="h-4 w-4" /></button>
          <span>{page + 1}/{maxPage + 1}</span>
          <button className="btn-ghost h-8 w-8 p-0" disabled={page >= maxPage} onClick={() => setPage((p) => p + 1)}><ChevronRight className="h-4 w-4" /></button>
        </div>
      </div>
      <DataGrid<BahanUpah> rowData={rows} columnDefs={cols} getRowId={(p) => String(p.data.id)} pageSize={PAGE} />
    </div>
  );
}

function useReadList<T>(fetcher: (p: Record<string, string | number>) => Promise<T[]>, toast: Toast) {
  const [rows, setRows] = useState<T[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    setLoading(true);
    fetcher({ q, limit: 300 }).then(setRows)
      .catch((e) => toast(e instanceof Error ? e.message : 'Gagal', false))
      .finally(() => setLoading(false));
  }, [q]); // eslint-disable-line react-hooks/exhaustive-deps
  return { rows, q, setQ, loading };
}

function Toolbar({ q, setQ, loading, count, placeholder }: { q: string; setQ: (v: string) => void; loading: boolean; count: number; placeholder: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="relative">
        <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
        <input className="input pl-8 w-64" placeholder={placeholder} value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <div className="ml-auto text-sm text-muted">{loading ? <Spinner /> : `${num(count)} baris`}</div>
    </div>
  );
}

function Empty({ msg }: { msg: string }) {
  return <div className="card p-8 text-center text-sm text-muted">{msg}</div>;
}

function VendorTab({ toast }: { toast: Toast }) {
  const { rows, q, setQ, loading } = useReadList<VendorRow>(api.pricingVendors, toast);
  const cols = useMemo<ColDef<VendorRow>[]>(() => [
    { headerName: 'Vendor', field: 'name', flex: 1, minWidth: 160 },
    { headerName: 'Domain', field: 'domain', flex: 1, minWidth: 160 },
    { headerName: 'Tipe', field: 'source_type', width: 150 },
    { headerName: 'Reliability', field: 'reliability_score', width: 110, type: 'rightAligned',
      valueFormatter: (p) => `${(p.value * 100).toFixed(0)}%` },
    { headerName: 'Snapshot', field: 'total_snapshots', width: 100, type: 'rightAligned' },
    { headerName: 'Sukses/Gagal', width: 120, valueGetter: (p) => `${p.data?.successful_scrapes}/${p.data?.failed_scrapes}` },
    { headerName: 'Aktif', field: 'is_active', width: 80, valueFormatter: (p) => (p.value ? '✓' : '—') },
  ], []);
  return (
    <div className="flex-1 min-h-0 flex flex-col gap-3">
      <Toolbar q={q} setQ={setQ} loading={loading} count={rows.length} placeholder="Cari vendor / domain…" />
      {rows.length === 0 && !loading ? <Empty msg="Belum ada vendor. Vendor muncul otomatis setelah AI discovery dijalankan (butuh API key + jaringan saat deploy)." />
        : <DataGrid<VendorRow> rowData={rows} columnDefs={cols} getRowId={(p) => String(p.data.id)} pageSize={100} />}
    </div>
  );
}

function SnapshotTab({ toast }: { toast: Toast }) {
  const { rows, q, setQ, loading } = useReadList<SnapshotRow>(api.pricingSnapshots, toast);
  const cols = useMemo<ColDef<SnapshotRow>[]>(() => [
    { headerName: 'Material', field: 'nama_material', flex: 1, minWidth: 180 },
    { headerName: 'Sat', field: 'satuan', width: 70 },
    { headerName: 'Harga', field: 'harga', width: 120, type: 'rightAligned', valueFormatter: (p) => rupiah(p.value) },
    { headerName: 'Vendor', field: 'vendor', width: 150 },
    { headerName: 'Kutipan (page_quote)', field: 'page_quote', flex: 1, minWidth: 200,
      tooltipValueGetter: (p: any) => p.value },
    { headerName: 'Sumber', field: 'source_url', width: 90, sortable: false,
      cellRenderer: (p: any) => p.value
        ? <a href={p.value} target="_blank" rel="noreferrer" className="text-primary inline-flex items-center gap-1"><ExternalLink className="h-3.5 w-3.5" /> buka</a>
        : '—' },
    { headerName: 'Outlier', field: 'is_outlier', width: 90, valueFormatter: (p) => (p.value ? '⚠ ya' : '—') },
    { headerName: 'Thn', field: 'tahun', width: 70 },
  ], []);
  return (
    <div className="flex-1 min-h-0 flex flex-col gap-3">
      <Toolbar q={q} setQ={setQ} loading={loading} count={rows.length} placeholder="Cari material…" />
      {rows.length === 0 && !loading ? <Empty msg="Belum ada snapshot. Snapshot (harga + source_url + kutipan) muncul setelah AI discovery — tiap harga wajib punya bukti sumber." />
        : <DataGrid<SnapshotRow> rowData={rows} columnDefs={cols} getRowId={(p) => String(p.data.id)} pageSize={100} />}
    </div>
  );
}

function KonsensusTab({ toast }: { toast: Toast }) {
  const { rows, q, setQ, loading } = useReadList<ConsensusRow>(api.pricingConsensus, toast);
  const cols = useMemo<ColDef<ConsensusRow>[]>(() => [
    { headerName: 'Material (norm)', field: 'norm_nama', flex: 1, minWidth: 200 },
    { headerName: 'Sat', field: 'satuan', width: 70 },
    { headerName: 'n', field: 'n_sources', width: 70, type: 'rightAligned' },
    { headerName: 'Median', field: 'median_price', width: 120, type: 'rightAligned', valueFormatter: (p) => rupiah(p.value) },
    { headerName: 'Min', field: 'min_price', width: 110, type: 'rightAligned', valueFormatter: (p) => (p.value ? rupiah(p.value) : '—') },
    { headerName: 'Max', field: 'max_price', width: 110, type: 'rightAligned', valueFormatter: (p) => (p.value ? rupiah(p.value) : '—') },
    { headerName: 'Variance', field: 'variance_pct', width: 100, type: 'rightAligned', valueFormatter: (p) => (p.value != null ? `${p.value.toFixed(0)}%` : '—') },
    { headerName: 'Review?', field: 'needs_review', width: 90, valueFormatter: (p) => (p.value ? '⚠' : '—') },
  ], []);
  return (
    <div className="flex-1 min-h-0 flex flex-col gap-3">
      <Toolbar q={q} setQ={setQ} loading={loading} count={rows.length} placeholder="Cari material…" />
      {rows.length === 0 && !loading ? <Empty msg="Belum ada konsensus. Dihitung otomatis dari ≥3 snapshot per material/lokasi setelah discovery." />
        : <DataGrid<ConsensusRow> rowData={rows} columnDefs={cols} getRowId={(p) => String(p.data.id)} pageSize={100} />}
    </div>
  );
}
