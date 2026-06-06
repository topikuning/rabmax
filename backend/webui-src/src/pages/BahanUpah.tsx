import { useEffect, useMemo, useState } from 'react';
import { Search, Plus, Sparkles, Trash2 } from 'lucide-react';
import { api, type BahanUpah } from '@/lib/api';
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
  const [form, setForm] = useState({ nama: '', satuan: '', harga: '', category: 'bahan', tier: 'A', tahun: '2025' });

  const load = () => { setLoading(true); api.bahanUpah().then(setRows).catch((e) => toast(e.message, false)).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, []);

  async function onCell(e: CellValueChangedEvent<BahanUpah>) {
    const field = e.colDef.field!;
    try {
      const updated = await api.updateBahanUpah(e.data.id, { [field]: e.newValue });
      e.data.ai_generated = updated.ai_generated; // jadi false setelah diedit
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
      });
      setRows((r) => [it, ...r]); setOpen(false);
      setForm({ nama: '', satuan: '', harga: '', category: 'bahan', tier: 'A', tahun: '2025' });
      toast('Ditambahkan');
    } catch (e) { toast(e instanceof Error ? e.message : 'Gagal', false); }
  }

  const aiCount = rows.filter((r) => r.ai_generated).length;

  const cols = useMemo<ColDef<BahanUpah>[]>(() => [
    { headerName: 'Nama', field: 'nama', flex: 2, minWidth: 200, editable: true },
    { headerName: 'Satuan', field: 'satuan', width: 90, editable: true },
    { headerName: 'Harga', field: 'harga', width: 150, type: 'rightAligned', editable: true,
      cellEditor: 'agNumberCellEditor', valueFormatter: (p) => rupiah(p.value) },
    { headerName: 'Kategori', field: 'category', width: 110, editable: true,
      cellEditor: 'agSelectCellEditor', cellEditorParams: { values: ['bahan', 'upah', 'alat'] } },
    { headerName: 'Tier', field: 'tier', width: 80, editable: true,
      cellEditor: 'agSelectCellEditor', cellEditorParams: { values: ['A', 'B', 'C', 'D'] } },
    { headerName: 'TKDN', field: 'tkdn_factor', width: 90, editable: true, cellEditor: 'agNumberCellEditor',
      valueFormatter: (p) => p.value != null ? `${(p.value * 100).toFixed(0)}%` : '-' },
    { headerName: 'Sumber', field: 'ai_generated', width: 120, editable: false,
      cellRenderer: (p: any) => p.value
        ? <span className="chip bg-warning/15 text-warning"><Sparkles className="h-3 w-3" /> AI</span>
        : <span className="chip bg-success/15 text-success">terverifikasi</span> },
    { headerName: 'Tahun', field: 'tahun', width: 80, editable: true },
    { headerName: '', width: 60, pinned: 'right', sortable: false, filter: false,
      cellRenderer: (p: any) => (
        <button className="btn-ghost h-7 w-7 p-0 text-danger" title="Hapus" onClick={() => del(p.data.id)}>
          <Trash2 className="h-3.5 w-3.5" />
        </button>) },
  ], []);

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Bahan &amp; Upah</h1>
          <p className="text-sm text-muted">
            {loading ? <Spinner /> : <>{num(rows.length)} item · {aiCount} dari AI (perlu verifikasi) · klik sel untuk edit</>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
            <input className="input pl-8 w-64" placeholder="Cari nama…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> Tambah</Button>
        </div>
      </div>

      <DataGrid<BahanUpah> rowData={rows} columnDefs={cols} quickFilter={q} getRowId={(p) => String(p.data.id)}
        pageSize={100} options={{ onCellValueChanged: onCell, singleClickEdit: false }} />

      <Modal open={open} onClose={() => setOpen(false)} title="Tambah Harga"
        footer={<><Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
          <Button disabled={!form.nama || !form.harga} onClick={create}>Simpan</Button></>}>
        <div className="space-y-3">
          <Field label="Nama"><input className="input" value={form.nama} onChange={(e) => setForm({ ...form, nama: e.target.value })} placeholder="mis. Semen Portland / Pekerja" /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Satuan"><input className="input" value={form.satuan} onChange={(e) => setForm({ ...form, satuan: e.target.value })} placeholder="kg / m3 / OH" /></Field>
            <Field label="Harga (Rp)"><input className="input" type="number" value={form.harga} onChange={(e) => setForm({ ...form, harga: e.target.value })} /></Field>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Field label="Kategori"><select className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}><option value="bahan">bahan</option><option value="upah">upah</option><option value="alat">alat</option></select></Field>
            <Field label="Tier"><select className="input" value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })}><option>A</option><option>B</option><option>C</option><option>D</option></select></Field>
            <Field label="Tahun"><input className="input" type="number" value={form.tahun} onChange={(e) => setForm({ ...form, tahun: e.target.value })} /></Field>
          </div>
        </div>
      </Modal>
    </div>
  );
}
