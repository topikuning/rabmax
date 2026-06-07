import { useEffect, useMemo, useState } from 'react';
import { Search, Plus, Sparkles, Trash2, MapPin } from 'lucide-react';
import { api, type BahanUpah, type Provinsi, type Kota } from '@/lib/api';
import { DataGrid, type ColDef } from '@/components/grid';
import { Button, Field, Modal, Spinner, useToast } from '@/components/ui';
import { rupiah, num } from '@/lib/utils';
import type { CellValueChangedEvent } from 'ag-grid-community';

export default function BahanUpahPage() {
  const toast = useToast();
  const [rows, setRows] = useState<BahanUpah[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    nama: '', satuan: '', harga: '', category: 'bahan', tier: 'A',
    tahun: String(new Date().getFullYear()), provinsi: '', kota: '',
  });
  // geografi untuk dropdown lokasi
  const [provinsi, setProvinsi] = useState<Provinsi[]>([]);
  const [kota, setKota] = useState<Kota[]>([]);
  const [provId, setProvId] = useState('');
  // filter lokasi (client-side)
  const [filterProv, setFilterProv] = useState('');

  const load = () => { setLoading(true); api.bahanUpah().then(setRows).catch((e) => toast(e.message, false)).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, []);
  useEffect(() => { if (provinsi.length === 0) api.provinsi().then(setProvinsi).catch(() => {}); }, []);
  useEffect(() => { if (provId) api.kota(Number(provId)).then(setKota).catch(() => {}); else setKota([]); }, [provId]);

  async function onCell(e: CellValueChangedEvent<BahanUpah>) {
    const field = e.colDef.field!;
    try {
      const updated = await api.updateBahanUpah(e.data.id, { [field]: e.newValue });
      e.data.ai_generated = updated.ai_generated;
      e.api.refreshCells({ rowNodes: [e.node!], force: true });
      toast('Tersimpan');
    } catch (err) {
      (e.data as any)[field] = e.oldValue;
      e.api.refreshCells({ rowNodes: [e.node!], force: true });
      toast(err instanceof Error ? err.message : 'Gagal', false);
    }
  }

  async function del(id: number) {
    try { await api.deleteBahanUpah(id); setRows((r) => r.filter((x) => x.id !== id)); toast('Dihapus'); }
    catch (e) { toast(e instanceof Error ? e.message : 'Gagal', false); }
  }

  async function create() {
    try {
      const it = await api.createBahanUpah({
        nama: form.nama, satuan: form.satuan, harga: Number(form.harga),
        category: form.category, tier: form.tier, tahun: Number(form.tahun),
        provinsi: form.provinsi || null, kota: form.kota || null,
      });
      setRows((r) => [it, ...r]); setOpen(false);
      setForm({ nama: '', satuan: '', harga: '', category: 'bahan', tier: 'A', tahun: String(new Date().getFullYear()), provinsi: '', kota: '' });
      setProvId('');
      toast('Ditambahkan');
    } catch (e) { toast(e instanceof Error ? e.message : 'Gagal', false); }
  }

  const filtered = useMemo(
    () => (filterProv ? rows.filter((r) => (r.provinsi || '') === filterProv) : rows),
    [rows, filterProv],
  );
  const aiCount = filtered.filter((r) => r.ai_generated).length;
  const belumCount = filtered.filter((r) => !(r.harga > 0)).length;

  const cols = useMemo<ColDef<BahanUpah>[]>(() => [
    { headerName: 'Nama', field: 'nama', flex: 2, minWidth: 180, editable: true },
    { headerName: 'Satuan', field: 'satuan', width: 80, editable: true },
    { headerName: 'Harga', field: 'harga', width: 130, type: 'rightAligned', editable: true,
      cellEditor: 'agNumberCellEditor',
      cellStyle: (p: any) => (p.value > 0 ? null : { color: 'hsl(var(--warning))' }),
      valueFormatter: (p) => (p.value > 0 ? rupiah(p.value) : 'belum ada') },
    { headerName: 'Provinsi', field: 'provinsi', width: 140, editable: true,
      valueFormatter: (p) => p.value || 'Nasional',
      cellStyle: (p: any) => (p.value ? null : { color: 'hsl(var(--muted))' }) },
    { headerName: 'Kota/Kab', field: 'kota', width: 150, editable: true,
      valueFormatter: (p) => p.value || '—' },
    { headerName: 'Kategori', field: 'category', width: 100, editable: true,
      cellEditor: 'agSelectCellEditor', cellEditorParams: { values: ['bahan', 'upah', 'alat'] } },
    { headerName: 'Tier', field: 'tier', width: 70, editable: true,
      cellEditor: 'agSelectCellEditor', cellEditorParams: { values: ['A', 'B', 'C', 'D'] } },
    { headerName: 'TKDN', field: 'tkdn_factor', width: 80, editable: true, cellEditor: 'agNumberCellEditor',
      valueFormatter: (p) => p.value != null ? `${(p.value * 100).toFixed(0)}%` : '-' },
    { headerName: 'Sumber', field: 'ai_generated', width: 120, editable: false,
      cellRenderer: (p: any) => p.value
        ? <span className="chip bg-warning/15 text-warning"><Sparkles className="h-3 w-3" /> AI</span>
        : <span className="chip bg-success/15 text-success">terverifikasi</span> },
    { headerName: 'Thn', field: 'tahun', width: 70, editable: true },
    { headerName: '', width: 56, pinned: 'right', sortable: false, filter: false,
      cellRenderer: (p: any) => (
        <button className="btn-ghost h-7 w-7 p-0 text-danger" title="Hapus" onClick={() => del(p.data.id)}>
          <Trash2 className="h-3.5 w-3.5" />
        </button>) },
  ], []);

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Bahan &amp; Upah</h1>
          <p className="text-sm text-muted">
            {loading ? <Spinner /> : <>{num(filtered.length)} item · <b>{num(belumCount)} belum ada harga</b> · {aiCount} dari AI · harga bisa beda per lokasi</>}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1">
            <MapPin className="h-4 w-4 text-muted" />
            <select className="input w-44" value={filterProv} onChange={(e) => setFilterProv(e.target.value)}>
              <option value="">Semua lokasi</option>
              <option value="">— Nasional —</option>
              {provinsi.map((p) => <option key={p.id} value={p.nama}>{p.nama}</option>)}
            </select>
          </div>
          <div className="relative">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
            <input className="input pl-8 w-56" placeholder="Cari nama / kota…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> Tambah</Button>
        </div>
      </div>

      <DataGrid<BahanUpah> rowData={filtered} columnDefs={cols} quickFilter={q} getRowId={(p) => String(p.data.id)}
        pageSize={100} options={{ onCellValueChanged: onCell, singleClickEdit: false }} />

      <Modal open={open} onClose={() => setOpen(false)} title="Tambah Harga (per lokasi)"
        footer={<><Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
          <Button disabled={!form.nama || !form.harga} onClick={create}>Simpan</Button></>}>
        <div className="space-y-3">
          <Field label="Nama"><input className="input" value={form.nama} onChange={(e) => setForm({ ...form, nama: e.target.value })} placeholder="mis. Upah Pekerja / Semen Portland" /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Satuan"><input className="input" value={form.satuan} onChange={(e) => setForm({ ...form, satuan: e.target.value })} placeholder="OH / kg / m3" /></Field>
            <Field label="Harga (Rp)"><input className="input" type="number" value={form.harga} onChange={(e) => setForm({ ...form, harga: e.target.value })} /></Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Provinsi" hint="kosong = berlaku nasional">
              <select className="input" value={provId}
                onChange={(e) => { const id = e.target.value; setProvId(id); const p = provinsi.find((x) => String(x.id) === id); setForm({ ...form, provinsi: p?.nama || '', kota: '' }); }}>
                <option value="">— Nasional —</option>
                {provinsi.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}
              </select>
            </Field>
            <Field label="Kota/Kabupaten">
              <select className="input" value={form.kota} disabled={!provId}
                onChange={(e) => setForm({ ...form, kota: e.target.value })}>
                <option value="">— semua di provinsi —</option>
                {kota.map((k) => <option key={k.id} value={k.nama}>{k.nama}</option>)}
              </select>
            </Field>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Kategori"><select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}><option value="bahan">bahan</option><option value="upah">upah</option><option value="alat">alat</option></select></Field>
            <Field label="Tier"><select className="input" value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })}><option>A</option><option>B</option><option>C</option><option>D</option></select></Field>
            <Field label="Tahun"><input className="input" type="number" value={form.tahun} onChange={(e) => setForm({ ...form, tahun: e.target.value })} /></Field>
          </div>
          <p className="text-xs text-muted">Material/upah yang sama bisa punya harga berbeda per provinsi/kota (mis. Malang vs Surabaya) — tambahkan baris terpisah per lokasi.</p>
        </div>
      </Modal>
    </div>
  );
}
