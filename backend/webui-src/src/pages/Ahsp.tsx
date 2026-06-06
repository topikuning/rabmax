import { useEffect, useMemo, useState } from 'react';
import { Search, AlertTriangle, Eye, Sparkles } from 'lucide-react';
import { api, type AHSP, type AhspDetail } from '@/lib/api';
import { DataGrid, type ColDef } from '@/components/grid';
import { Button, Modal, Spinner, useToast } from '@/components/ui';
import { rupiah, num } from '@/lib/utils';

function Detail({ id, onClose }: { id: number; onClose: () => void }) {
  const toast = useToast();
  const [d, setD] = useState<AhspDetail | null>(null);
  const [sourcing, setSourcing] = useState(false);
  useEffect(() => { api.ahspDetail(id).then(setD).catch((e) => { toast(e.message, false); onClose(); }); }, [id]);

  async function sourceAI() {
    setSourcing(true);
    try { const r = await api.ahspSourcePrices(id); setD(r); toast(`Harga AI: ${r.components_total - r.components_missing_price}/${r.components_total} terisi`); }
    catch (e) { toast((e instanceof Error ? e.message : 'Gagal') + ' (cek API key AI di server)', false); }
    finally { setSourcing(false); }
  }

  return (
    <Modal open onClose={onClose} width={760} title={d ? d.kode : 'Memuat…'}>
      {!d ? <div className="flex justify-center py-10 text-muted"><Spinner /></div> : (
        <div className="space-y-4">
          <div>
            <div className="text-sm">{d.uraian}</div>
            <div className="text-xs text-muted mt-0.5">Satuan: {d.satuan} · {d.work_group || 'tanpa work group'} · {d.source}</div>
          </div>

          {/* HSP summary */}
          <div className="grid grid-cols-4 gap-2">
            {[['Bahan', d.hsp.bahan], ['Upah', d.hsp.upah], ['Alat', d.hsp.alat], ['O&P', d.hsp.op]].map(([k, v]) => (
              <div key={k as string} className="rounded-lg bg-bg p-2.5">
                <div className="text-xs text-muted">{k}</div>
                <div className="text-sm font-semibold">{rupiah(v as number)}</div>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between rounded-lg bg-primary/10 text-primary px-4 py-3">
            <div>
              <div className="text-xs">HSP (per {d.satuan}, incl O&amp;P)</div>
              <div className="text-2xl font-bold">{rupiah(d.hsp.hsp)}</div>
            </div>
            <div className="text-right text-xs">TKDN<br /><span className="text-lg font-semibold">{(d.hsp.tkdn_factor * 100).toFixed(0)}%</span></div>
          </div>

          {d.components_missing_price > 0 && (
            <div className="rounded-lg bg-warning/10 text-warning text-sm p-3 space-y-2">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                <span><b>{d.components_missing_price}</b> dari {d.components_total} komponen belum ada harga →
                  HSP belum akurat. Isi harga di menu <b>Bahan &amp; Upah</b>, atau estimasi via AI:</span>
              </div>
              <Button loading={sourcing} onClick={sourceAI} className="h-8">
                <Sparkles className="h-3.5 w-3.5" /> Lengkapi harga via AI
              </Button>
            </div>
          )}

          {/* Components table */}
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="max-h-72 overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-elevated text-muted text-xs">
                  <tr className="text-left">
                    <th className="px-3 py-2 font-medium">Kategori</th>
                    <th className="px-3 py-2 font-medium">Material / Tenaga / Alat</th>
                    <th className="px-3 py-2 font-medium text-right">Koef</th>
                    <th className="px-3 py-2 font-medium">Sat</th>
                    <th className="px-3 py-2 font-medium text-right">Harga</th>
                    <th className="px-3 py-2 font-medium text-right">Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  {d.components.map((c, i) => (
                    <tr key={i} className="border-t border-border">
                      <td className="px-3 py-1.5 capitalize text-muted">{c.kategori}</td>
                      <td className="px-3 py-1.5">{c.nama_material}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{c.koefisien}</td>
                      <td className="px-3 py-1.5">{c.satuan}</td>
                      <td className={'px-3 py-1.5 text-right tabular-nums ' + (c.harga_tersedia ? '' : 'text-warning')}>
                        {c.harga_tersedia ? rupiah(c.harga) : 'belum ada'}
                      </td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{rupiah(c.subtotal)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}

export default function Ahsp() {
  const toast = useToast();
  const [rows, setRows] = useState<AHSP[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);
  const [detailId, setDetailId] = useState<number | null>(null);

  const load = () => { setLoading(true); api.ahsp().then(setRows).catch((e) => toast(e.message, false)).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, []);

  const cols = useMemo<ColDef<AHSP>[]>(() => [
    { headerName: 'Kode', field: 'kode', width: 170, cellClass: 'font-mono text-[12px]' },
    { headerName: 'Uraian', field: 'uraian', flex: 3, minWidth: 280 },
    { headerName: 'Satuan', field: 'satuan', width: 90 },
    { headerName: 'Work Group', field: 'work_group', width: 140 },
    { headerName: 'Sumber', field: 'source', width: 160 },
    { headerName: 'Tier', field: 'confidence_tier', width: 130 },
    {
      headerName: '', width: 110, pinned: 'right', sortable: false, filter: false,
      cellRenderer: (p: any) => (
        <button className="btn-ghost h-7 px-2 text-xs" onClick={() => setDetailId(p.data.id)}>
          <Eye className="h-3.5 w-3.5" /> Rincian
        </button>
      ),
    },
  ], []);

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Katalog AHSP</h1>
          <p className="text-sm text-muted">{loading ? <Spinner /> : `${num(rows.length)} item · klik "Rincian" untuk komponen & HSP`}</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="h-4 w-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
            <input className="input pl-8 w-72" placeholder="Cari kode / uraian / work group…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <Button variant="outline" onClick={load}>Muat ulang</Button>
        </div>
      </div>
      <DataGrid<AHSP>
        rowData={rows} columnDefs={cols} quickFilter={q} getRowId={(p) => String(p.data.id)} pageSize={100}
        options={{ onRowDoubleClicked: (e) => e.data && setDetailId(e.data.id) }}
      />
      {detailId != null && <Detail id={detailId} onClose={() => setDetailId(null)} />}
    </div>
  );
}
