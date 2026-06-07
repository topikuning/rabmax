import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Search } from 'lucide-react';
import { api, type Project, type Provinsi, type Kota } from '@/lib/api';
import { DataGrid, type ColDef } from '@/components/grid';
import { Button, Field, Modal, StatusChip, useToast } from '@/components/ui';
import { rupiah } from '@/lib/utils';

export default function Projects() {
  const nav = useNavigate();
  const toast = useToast();
  const [rows, setRows] = useState<Project[]>([]);
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: '', lokasi: '', tahun_anggaran: String(new Date().getFullYear()), target_value: '', mode: 'generate', kota_kabupaten_id: '', tahun_pricing: String(new Date().getFullYear()) });
  const [busy, setBusy] = useState(false);
  const [provinsi, setProvinsi] = useState<Provinsi[]>([]);
  const [kota, setKota] = useState<Kota[]>([]);
  const [provId, setProvId] = useState('');

  const load = () => api.projects().then(setRows).catch((e) => toast(e.message, false));
  useEffect(() => { load(); }, []);
  useEffect(() => { if (open && provinsi.length === 0) api.provinsi().then(setProvinsi).catch(() => {}); }, [open]);
  useEffect(() => { if (provId) api.kota(Number(provId)).then(setKota).catch(() => {}); else setKota([]); }, [provId]);

  const cols = useMemo<ColDef<Project>[]>(() => [
    { headerName: 'Nama', field: 'name', flex: 2, minWidth: 200 },
    { headerName: 'Lokasi', field: 'lokasi', flex: 1.5 },
    { headerName: 'Mode', field: 'mode', width: 150, valueFormatter: (p) => p.value === 'generate' ? 'Generate BOQ' : 'Analisa Profit' },
    { headerName: 'Status', field: 'status', width: 160, cellRenderer: (p: any) => <StatusChip status={p.value} /> },
    { headerName: 'Target', field: 'target_value', width: 160, type: 'rightAligned', valueFormatter: (p) => rupiah(p.value) },
  ], []);

  async function create() {
    setBusy(true);
    try {
      const p = await api.createProject({
        name: form.name, lokasi: form.lokasi || null,
        tahun_anggaran: form.tahun_anggaran ? Number(form.tahun_anggaran) : null,
        target_value: form.target_value ? Number(form.target_value) : null,
        mode: form.mode,
        kota_kabupaten_id: form.kota_kabupaten_id ? Number(form.kota_kabupaten_id) : null,
        tahun_pricing: form.tahun_pricing ? Number(form.tahun_pricing) : null,
      });
      setOpen(false); nav('/projects/' + p.id);
    } catch (e) { toast(e instanceof Error ? e.message : 'Gagal', false); setBusy(false); }
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Proyek</h1>
          <p className="text-sm text-muted">Estimasi BOQ &amp; analisa profit.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
            <input className="input pl-8 w-56" placeholder="Cari…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" /> Proyek Baru</Button>
        </div>
      </div>

      <DataGrid<Project>
        rowData={rows} columnDefs={cols} quickFilter={q}
        getRowId={(p) => String(p.data.id)}
        options={{ onRowDoubleClicked: (e) => e.data && nav('/projects/' + e.data.id) }}
      />

      <Modal open={open} onClose={() => setOpen(false)} title="Proyek Baru"
        footer={<>
          <Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
          <Button loading={busy} disabled={!form.name || !form.kota_kabupaten_id} onClick={create}>Buat</Button>
        </>}>
        <div className="space-y-3">
          <Field label="Nama proyek">
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="mis. Pembangunan Gedung…" />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Provinsi" hint="wajib (harga lokasi-aware)">
              <select className="input" value={provId} onChange={(e) => { setProvId(e.target.value); setForm({ ...form, kota_kabupaten_id: '' }); }}>
                <option value="">— pilih —</option>
                {provinsi.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}
              </select>
            </Field>
            <Field label="Kota/Kabupaten">
              <select className="input" value={form.kota_kabupaten_id} disabled={!provId}
                onChange={(e) => setForm({ ...form, kota_kabupaten_id: e.target.value })}>
                <option value="">— pilih —</option>
                {kota.map((k) => <option key={k.id} value={k.id}>{k.nama}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Lokasi detail (opsional)">
            <input className="input" value={form.lokasi} onChange={(e) => setForm({ ...form, lokasi: e.target.value })} placeholder="alamat detail bila jauh dari ibukota" />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Tahun anggaran">
              <input className="input" type="number" value={form.tahun_anggaran} onChange={(e) => setForm({ ...form, tahun_anggaran: e.target.value })} />
            </Field>
            <Field label="Target nilai (Rp)">
              <input className="input" type="number" value={form.target_value} onChange={(e) => setForm({ ...form, target_value: e.target.value })} />
            </Field>
          </div>
          <Field label="Mode">
            <select className="input" value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}>
              <option value="generate">Generate BOQ (RAB kosong)</option>
              <option value="profit_analysis">Analisa Profit (RAB terisi)</option>
            </select>
          </Field>
        </div>
      </Modal>
    </div>
  );
}
