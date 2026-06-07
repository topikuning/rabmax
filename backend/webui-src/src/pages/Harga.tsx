import { useEffect, useState } from 'react';
import { Search, Sparkles } from 'lucide-react';
import { api, type Provinsi, type Kota, type ResolveResult } from '@/lib/api';
import { Button, Field, Spinner, useToast } from '@/components/ui';
import { rupiah } from '@/lib/utils';

const TIER_LABEL: Record<string, string> = {
  kota_lokal: 'Kota (lokal)', provinsi_lokal: 'Provinsi + transport',
  provinsi_tetangga: 'Provinsi tetangga + transport', nasional_markup: 'Nasional + markup',
  discovery: 'Discovery', manual: 'Manual', unresolved: 'Belum ketemu',
};
const TIER_TONE: Record<string, string> = {
  kota_lokal: 'bg-success/15 text-success', provinsi_lokal: 'bg-primary/15 text-primary',
  provinsi_tetangga: 'bg-primary/15 text-primary', nasional_markup: 'bg-warning/15 text-warning',
  manual: 'bg-muted/20 text-muted', unresolved: 'bg-danger/15 text-danger',
};

interface Row extends ResolveResult { _key: string; nama: string; lokasi: string; }

export default function Harga() {
  const toast = useToast();
  const [form, setForm] = useState({ nama: '', satuan: '' });
  const [provinsi, setProvinsi] = useState<Provinsi[]>([]);
  const [kota, setKota] = useState<Kota[]>([]);
  const [provId, setProvId] = useState('');
  const [kotaId, setKotaId] = useState('');
  const [discover, setDiscover] = useState(true);
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<Row[]>([]);

  useEffect(() => { api.provinsi().then(setProvinsi).catch(() => {}); }, []);
  useEffect(() => { if (provId) api.kota(Number(provId)).then(setKota).catch(() => {}); else setKota([]); }, [provId]);

  async function cari() {
    if (!form.nama || !form.satuan) { toast('Isi nama material & satuan', false); return; }
    setBusy(true);
    try {
      const r = await api.resolvePrice({
        nama_material: form.nama, satuan: form.satuan,
        kota_kabupaten_id: kotaId ? Number(kotaId) : null,
        provinsi_id: provId ? Number(provId) : null,
        discover,
      });
      const lok = (kota.find((k) => String(k.id) === kotaId)?.nama)
        || (provinsi.find((p) => String(p.id) === provId)?.nama) || 'Nasional';
      setResults((rs) => [{ ...r, _key: Date.now() + '', nama: form.nama, lokasi: lok }, ...rs]);
    } catch (e) { toast(e instanceof Error ? e.message : 'Gagal', false); }
    finally { setBusy(false); }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Cek Harga (lokasi-aware)</h1>
        <p className="text-sm text-muted">Cari harga material/upah per kota → cross-validate dari web (Tier 1-6). Ganti kota untuk membandingkan (mis. Malang vs Surabaya).</p>
      </div>

      <div className="card p-5 space-y-4">
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Nama material / upah"><input className="input" value={form.nama} onChange={(e) => setForm({ ...form, nama: e.target.value })} placeholder="mis. Upah Tukang Batu / Semen Portland" /></Field>
          <Field label="Satuan"><input className="input" value={form.satuan} onChange={(e) => setForm({ ...form, satuan: e.target.value })} placeholder="OH / kg / m3" /></Field>
        </div>
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Provinsi">
            <select className="input" value={provId} onChange={(e) => { setProvId(e.target.value); setKotaId(''); }}>
              <option value="">— pilih —</option>
              {provinsi.map((p) => <option key={p.id} value={p.id}>{p.nama}</option>)}
            </select>
          </Field>
          <Field label="Kota/Kabupaten">
            <select className="input" value={kotaId} disabled={!provId} onChange={(e) => setKotaId(e.target.value)}>
              <option value="">— seluruh provinsi —</option>
              {kota.map((k) => <option key={k.id} value={k.id}>{k.nama}</option>)}
            </select>
          </Field>
        </div>
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={discover} onChange={(e) => setDiscover(e.target.checked)} />
            <Sparkles className="h-4 w-4 text-warning" /> Cari ke web bila belum ada (discovery — butuh API key AI)
          </label>
          <Button loading={busy} onClick={cari}><Search className="h-4 w-4" /> Cari Harga</Button>
        </div>
        {busy && discover && <p className="text-xs text-muted flex items-center gap-1"><Spinner /> Mencari ke web &amp; cross-validate… (bisa beberapa detik)</p>}
      </div>

      {results.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-medium text-muted">Hasil (terbaru di atas — bandingkan antar lokasi)</div>
          {results.map((r) => (
            <div key={r._key} className="card p-4">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div>
                  <div className="font-medium">{r.nama} <span className="text-muted">· {r.lokasi}</span></div>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <span className={'chip ' + (TIER_TONE[r.tier_used] || 'bg-muted/20 text-muted')}>{TIER_LABEL[r.tier_used] || r.tier_used}</span>
                    {r.n_sources > 0 && <span className="text-xs text-muted">{r.n_sources} sumber · conf {(r.confidence * 100).toFixed(0)}%</span>}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold">{r.harga_final != null ? rupiah(r.harga_final) : '—'}</div>
                  {r.markup_transport > 0 && (
                    <div className="text-xs text-muted">base {rupiah(r.harga_base)} + transport {rupiah(r.markup_transport)}</div>
                  )}
                </div>
              </div>
              {r.sources?.length > 0 && (
                <div className="text-xs text-muted mt-2">Sumber: {r.sources.slice(0, 6).join(', ')}{r.sources.length > 6 ? '…' : ''}</div>
              )}
              {r.warning_messages?.map((w, i) => <div key={i} className="text-xs text-warning mt-1">⚠ {w}</div>)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
