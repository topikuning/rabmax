import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Upload, Wand2, Calculator, FileSpreadsheet, TrendingUp, Pencil,
} from 'lucide-react';
import { api, type AHSP, type Project } from '@/lib/api';
import { DataGrid, type ColDef } from '@/components/grid';
import { Button, Field, Modal, Spinner, StatusChip, useToast } from '@/components/ui';
import { rupiah } from '@/lib/utils';

interface Row {
  paket_item_id: number; sheet_name: string; uraian: string; satuan: string; volume: number;
  match_id: number | null; match_type: string; ahsp_id: number | null;
  lumpsum_price: number | null; final_hsp: number | null; confidence: number; reviewed_by_user: boolean;
}

function AhspPicker({ value, ahsp, onChange }: { value: number | null; ahsp: AHSP[]; onChange: (id: number | null) => void }) {
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const cur = value ? ahsp.find((a) => a.id === value) : null;
  const hits = useMemo(() => {
    if (!q) return ahsp.slice(0, 30);
    const s = q.toLowerCase();
    return ahsp.filter((a) => (a.kode + ' ' + a.uraian).toLowerCase().includes(s)).slice(0, 30);
  }, [q, ahsp]);
  return (
    <div className="relative">
      <input className="input" placeholder={cur ? `${cur.kode} — ${cur.uraian.slice(0, 40)}` : 'Cari AHSP…'}
        value={q} onFocus={() => setOpen(true)} onChange={(e) => { setQ(e.target.value); setOpen(true); }} />
      {open && (
        <div className="absolute z-10 mt-1 w-full max-h-60 overflow-auto card p-1">
          {hits.map((a) => (
            <button key={a.id} type="button"
              className="block w-full text-left px-2 py-1.5 rounded hover:bg-bg text-sm"
              onClick={() => { onChange(a.id); setQ(''); setOpen(false); }}>
              <span className="font-mono text-xs text-primary">{a.kode}</span> — {a.uraian.slice(0, 60)}
            </button>
          ))}
          {hits.length === 0 && <div className="px-2 py-2 text-sm text-muted">Tidak ada hasil</div>}
        </div>
      )}
    </div>
  );
}

export default function Workspace() {
  const { id } = useParams();
  const pid = Number(id);
  const nav = useNavigate();
  const toast = useToast();
  const [project, setProject] = useState<Project | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [ahsp, setAhsp] = useState<AHSP[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [edit, setEdit] = useState<Row | null>(null);

  const ahspMap = useMemo(() => { const m = new Map<number, string>(); ahsp.forEach((a) => m.set(a.id, a.kode)); return m; }, [ahsp]);

  async function load() {
    const [items, matches] = await Promise.all([api.items(pid), api.matches(pid)]);
    const byItem = new Map(matches.map((m) => [m.paket_item_id, m]));
    setRows(items.map((it) => {
      const m = byItem.get(it.id);
      return {
        paket_item_id: it.id, sheet_name: it.sheet_name, uraian: it.uraian, satuan: it.satuan, volume: it.volume,
        match_id: m?.id ?? null, match_type: m?.match_type ?? 'unresolved', ahsp_id: m?.ahsp_id ?? null,
        lumpsum_price: m?.lumpsum_price ?? null, final_hsp: m?.final_hsp ?? null,
        confidence: m?.confidence ?? 0, reviewed_by_user: m?.reviewed_by_user ?? false,
      };
    }));
  }

  useEffect(() => {
    api.projects().then((ps) => setProject(ps.find((p) => p.id === pid) || null));
    api.ahsp().then(setAhsp).catch(() => {});
    load().catch((e) => toast(e.message, false)).finally(() => setLoading(false));
  }, [pid]);

  async function act(key: string, fn: () => Promise<any>, isGen = false) {
    setBusy(key);
    try {
      const r = await fn();
      toast(`${key} selesai`);
      if (isGen && r?.download_url) window.open(r.download_url, '_blank');
      await load();
      api.projects().then((ps) => setProject(ps.find((p) => p.id === pid) || null));
    } catch (e) { toast(e instanceof Error ? e.message : 'Gagal', false); }
    finally { setBusy(null); }
  }

  function doUpload() {
    const inp = document.createElement('input');
    inp.type = 'file'; inp.accept = '.xlsx,.xlsm';
    inp.onchange = async () => {
      const f = inp.files?.[0]; if (!f || !project) return;
      setBusy('upload');
      try { const s: any = await api.uploadRab(pid, f, project.mode); toast(`Parse: ${s.items_total} item`); await load(); }
      catch (e) { toast(e instanceof Error ? e.message : 'Gagal', false); }
      finally { setBusy(null); }
    };
    inp.click();
  }

  async function saveEdit() {
    if (!edit?.match_id) { toast('Item belum punya match (jalankan match).', false); return; }
    try {
      await api.updateMatch(edit.match_id, {
        match_type: edit.match_type, ahsp_id: edit.ahsp_id || null, lumpsum_price: edit.lumpsum_price || null,
      });
      toast('Match disimpan'); setEdit(null); await load();
    } catch (e) { toast(e instanceof Error ? e.message : 'Gagal', false); }
  }

  const cols = useMemo<ColDef<Row>[]>(() => [
    { headerName: 'Sheet', field: 'sheet_name', width: 130 },
    { headerName: 'Uraian', field: 'uraian', flex: 2, minWidth: 240 },
    { headerName: 'Sat', field: 'satuan', width: 70 },
    { headerName: 'Volume', field: 'volume', width: 100, type: 'rightAligned' },
    { headerName: 'Tipe', field: 'match_type', width: 110 },
    { headerName: 'AHSP', field: 'ahsp_id', width: 150, valueFormatter: (p) => p.value ? (ahspMap.get(p.value) || String(p.value)) : '' },
    { headerName: 'Lumpsum', field: 'lumpsum_price', width: 120, type: 'rightAligned', valueFormatter: (p) => p.value ? rupiah(p.value) : '' },
    { headerName: 'HSP final', field: 'final_hsp', width: 140, type: 'rightAligned', valueFormatter: (p) => rupiah(p.value) },
    { headerName: 'Conf', field: 'confidence', width: 80, valueFormatter: (p) => p.value != null ? `${(p.value * 100).toFixed(0)}%` : '' },
    { headerName: '✓', field: 'reviewed_by_user', width: 60, valueFormatter: (p) => p.value ? '✓' : '' },
    {
      headerName: '', width: 80, pinned: 'right', sortable: false, filter: false,
      cellRenderer: (p: any) => (
        <button className="btn-ghost h-7 px-2 text-xs" onClick={() => setEdit(p.data)}>
          <Pencil className="h-3.5 w-3.5" /> Ubah
        </button>
      ),
    },
  ], [ahspMap]);

  if (loading) return <div className="flex-1 flex items-center justify-center text-muted"><Spinner /></div>;
  if (!project) return <div className="flex-1 flex items-center justify-center text-muted">Proyek tidak ditemukan</div>;

  const isGen = project.mode === 'generate';

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-4">
      <button onClick={() => nav('/')} className="inline-flex items-center gap-1 text-sm text-muted hover:text-fg w-fit">
        <ArrowLeft className="h-4 w-4" /> Semua proyek
      </button>

      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-bold tracking-tight">{project.name}</h1>
          <div className="text-sm text-muted">{project.lokasi || 'Lokasi -'} {project.target_value ? `· Target ${rupiah(project.target_value)}` : ''}</div>
        </div>
        <StatusChip status={project.status} />
      </div>

      {/* Pipeline */}
      <div className="card p-2 flex items-center gap-2 flex-wrap">
        <Button variant="outline" loading={busy === 'upload'} onClick={doUpload}><Upload className="h-4 w-4" /> Upload RAB</Button>
        <div className="w-px h-6 bg-border mx-1" />
        {isGen ? (
          <>
            <Button variant="outline" loading={busy === 'Match'} onClick={() => act('Match', () => api.runMatcher(pid))}><Wand2 className="h-4 w-4" /> Match</Button>
            <Button variant="outline" loading={busy === 'Pricing'} onClick={() => act('Pricing', () => api.priceProject(pid))}><Calculator className="h-4 w-4" /> Harga + Kalibrasi</Button>
            <Button loading={busy === 'Generate'} onClick={() => act('Generate', () => api.generate(pid), true)}><FileSpreadsheet className="h-4 w-4" /> Generate</Button>
          </>
        ) : (
          <Button loading={busy === 'Profit'} onClick={() => act('Profit', () => api.runProfit(pid))}><TrendingUp className="h-4 w-4" /> Analisa Profit</Button>
        )}
        <div className="ml-auto text-sm text-muted">{rows.length} item</div>
      </div>

      <DataGrid<Row> rowData={rows} columnDefs={cols} getRowId={(p) => String(p.data.paket_item_id)} pageSize={100} />

      <Modal open={!!edit} onClose={() => setEdit(null)} title="Override Match"
        footer={<><Button variant="outline" onClick={() => setEdit(null)}>Batal</Button><Button onClick={saveEdit}>Simpan</Button></>}>
        {edit && (
          <div className="space-y-3">
            <div className="text-sm"><span className="text-muted">Item:</span> {edit.uraian} <span className="text-muted">({edit.satuan})</span></div>
            <Field label="Tipe match">
              <select className="input" value={edit.match_type} onChange={(e) => setEdit({ ...edit, match_type: e.target.value })}>
                <option value="ahsp">AHSP</option>
                <option value="lumpsum">Lumpsum</option>
                <option value="unresolved">Belum ditentukan</option>
              </select>
            </Field>
            {edit.match_type === 'ahsp' && (
              <Field label="Pilih AHSP">
                <AhspPicker value={edit.ahsp_id} ahsp={ahsp} onChange={(id) => setEdit({ ...edit, ahsp_id: id })} />
              </Field>
            )}
            {edit.match_type === 'lumpsum' && (
              <Field label="Harga lumpsum (Rp)">
                <input className="input" type="number" value={edit.lumpsum_price ?? ''} onChange={(e) => setEdit({ ...edit, lumpsum_price: e.target.value ? Number(e.target.value) : null })} />
              </Field>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
