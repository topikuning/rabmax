'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, Upload, Wand2, Calculator, FileSpreadsheet, Download,
  TrendingUp, CheckCircle2, AlertTriangle, MapPin,
} from 'lucide-react';
import { api, auth } from '@/lib/api';
import {
  Button, Card, ModeBadge, Spinner, StatusBadge, EmptyState,
} from '@/components/ui';
import { formatRupiah } from '@/lib/utils';
import type {
  GenerateResult, MatchRunSummary, ParseSummary, PricingSummary, Project,
} from '@/types';

export default function ProjectWorkspace() {
  const router = useRouter();
  const params = useParams();
  const id = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [itemCount, setItemCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  // pipeline state
  const [file, setFile] = useState<File | null>(null);
  const [parse, setParse] = useState<ParseSummary | null>(null);
  const [match, setMatch] = useState<MatchRunSummary | null>(null);
  const [price, setPrice] = useState<PricingSummary | null>(null);
  const [gen, setGen] = useState<GenerateResult | null>(null);
  const [profitMsg, setProfitMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [p, items] = await Promise.all([api.getProject(id), api.listItems(id)]);
    setProject(p);
    setItemCount(items.length);
  }, [id]);

  useEffect(() => {
    if (!auth.isAuthed()) {
      router.replace('/login');
      return;
    }
    refresh()
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [id, router, refresh]);

  async function run(key: string, fn: () => Promise<void>) {
    setErr(null);
    setBusy(key);
    try {
      await fn();
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Terjadi kesalahan');
    } finally {
      setBusy(null);
    }
  }

  if (loading)
    return (
      <div className="flex items-center gap-2 text-muted-foreground text-sm py-16 justify-center">
        <Spinner /> Memuat proyek…
      </div>
    );

  if (!project)
    return <EmptyState title="Proyek tidak ditemukan" desc={err ?? undefined} />;

  const isGenerate = project.mode === 'generate';
  const hasItems = (itemCount ?? 0) > 0;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Semua proyek
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{project.name}</h1>
          <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
            <span className="flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" />
              {project.lokasi || 'Lokasi -'}
            </span>
            {project.target_value != null && (
              <span>Target {formatRupiah(project.target_value)}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={project.status} />
          <ModeBadge mode={project.mode} />
        </div>
      </div>

      {err && (
        <Card className="p-4 border-destructive/40 bg-destructive/10 text-destructive text-sm flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{err}</span>
        </Card>
      )}

      {/* Step 1 — Upload */}
      <Step n={1} title="Upload file RAB" icon={Upload} done={hasItems}>
        <p className="text-sm text-muted-foreground">
          {isGenerate
            ? 'Upload file RAB kosong (template lelang). Item, satuan, volume jadi acuan.'
            : 'Upload file RAB terisi (HPS) untuk analisa profit.'}
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <label className="flex-1 min-w-[200px]">
            <input
              type="file"
              accept=".xlsx,.xlsm"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-muted-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-muted file:px-3 file:py-2 file:text-sm file:font-medium hover:file:bg-muted/70 cursor-pointer"
            />
          </label>
          <Button
            disabled={!file}
            loading={busy === 'upload'}
            onClick={() =>
              run('upload', async () => {
                const s = await api.upload(id, file!, project.mode);
                setParse(s);
              })
            }
          >
            Upload &amp; Parse
          </Button>
        </div>
        {parse && (
          <div className="grid grid-cols-3 gap-2 text-center">
            <Stat label="Paket sheet" value={parse.paket_sheets} />
            <Stat label="Item" value={parse.items_total} />
            <Stat label="Item unik" value={parse.items_unique} />
          </div>
        )}
        {hasItems && !parse && (
          <p className="text-sm text-success flex items-center gap-1">
            <CheckCircle2 className="h-4 w-4" /> {itemCount} item sudah ter-parse.
          </p>
        )}
        {parse?.warnings?.length ? (
          <Warnings items={parse.warnings} />
        ) : null}
      </Step>

      {isGenerate ? (
        <>
          {/* Step 2 — Match */}
          <Step n={2} title="Pencocokan AHSP" icon={Wand2} disabled={!hasItems}>
            <p className="text-sm text-muted-foreground">
              Cocokkan tiap item ke AHSP (rule + AI), bisa di-override manual nanti.
            </p>
            <Button
              variant="outline"
              disabled={!hasItems}
              loading={busy === 'match'}
              onClick={() => run('match', async () => setMatch(await api.runMatcher(id)))}
            >
              <Wand2 className="h-4 w-4" /> Jalankan Matcher
            </Button>
            {match && (
              <div className="grid grid-cols-4 gap-2 text-center">
                <Stat label="Rule" value={match.rule_matched} />
                <Stat label="AI" value={match.llm_matched} />
                <Stat label="Lumpsum" value={match.lumpsum} />
                <Stat label="Belum" value={match.unresolved} tone={match.unresolved ? 'warn' : undefined} />
              </div>
            )}
          </Step>

          {/* Step 3 — Price */}
          <Step n={3} title="Harga &amp; kalibrasi" icon={Calculator} disabled={!hasItems}>
            <p className="text-sm text-muted-foreground">
              Hitung HSP per item lalu kalibrasi total ke target nilai penawaran.
            </p>
            <Button
              variant="outline"
              disabled={!hasItems}
              loading={busy === 'price'}
              onClick={() => run('price', async () => setPrice(await api.priceProject(id)))}
            >
              <Calculator className="h-4 w-4" /> Hitung &amp; Kalibrasi
            </Button>
            {price && (
              <div className="space-y-2">
                <div className="grid grid-cols-3 gap-2 text-center">
                  <Stat label="Item berharga" value={price.items_priced} />
                  <Stat label="Subtotal" value={formatRupiah(price.base_total)} small />
                  <Stat label="Setelah kalibrasi" value={formatRupiah(price.calibrated_total)} small />
                </div>
                {price.warnings?.length ? <Warnings items={price.warnings} /> : null}
              </div>
            )}
          </Step>

          {/* Step 4 — Generate */}
          <Step n={4} title="Generate BOQ Excel" icon={FileSpreadsheet} disabled={!hasItems}>
            <p className="text-sm text-muted-foreground">
              Tulis harga &amp; formula ke salinan file, buat sheet Resume Analisa.
            </p>
            <Button
              disabled={!hasItems}
              loading={busy === 'gen'}
              onClick={() => run('gen', async () => setGen(await api.generate(id)))}
            >
              <FileSpreadsheet className="h-4 w-4" /> Generate
            </Button>
            {gen && (
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-2 text-center">
                  <Stat label="Baris Resume" value={gen.resume_rows} />
                  <Stat label="Item ditulis" value={gen.items_written} />
                  <Stat label="Belum berharga" value={gen.items_unpriced} tone={gen.items_unpriced ? 'warn' : undefined} />
                </div>
                <a href={api.fileUrl(gen.output_file_path)} target="_blank" rel="noreferrer">
                  <Button className="w-full">
                    <Download className="h-4 w-4" /> Unduh BOQ (.xlsx)
                  </Button>
                </a>
                {gen.validation.warnings?.length ? <Warnings items={gen.validation.warnings} /> : null}
                {gen.validation.errors?.length ? (
                  <Warnings items={gen.validation.errors} danger />
                ) : null}
              </div>
            )}
          </Step>
        </>
      ) : (
        /* Mode B — Profit */
        <Step n={2} title="Analisa Profit" icon={TrendingUp} disabled={!hasItems}>
          <p className="text-sm text-muted-foreground">
            Hitung estimasi biaya real vs HPS → margin profit per paket.
          </p>
          <Button
            disabled={!hasItems}
            loading={busy === 'profit'}
            onClick={() =>
              run('profit', async () => {
                const r = await api.runProfit(id);
                setProfitMsg(`Analisa selesai (#${r.analysis_id ?? '-'}). Lihat hasil di laporan.`);
              })
            }
          >
            <TrendingUp className="h-4 w-4" /> Jalankan Analisa
          </Button>
          {profitMsg && (
            <p className="text-sm text-success flex items-center gap-1">
              <CheckCircle2 className="h-4 w-4" /> {profitMsg}
            </p>
          )}
        </Step>
      )}
    </div>
  );
}

// === small building blocks ===
function Step({
  n, title, icon: Icon, children, done, disabled,
}: {
  n: number;
  title: string;
  icon: typeof Upload;
  children: React.ReactNode;
  done?: boolean;
  disabled?: boolean;
}) {
  return (
    <Card className={`p-5 ${disabled ? 'opacity-60' : ''}`}>
      <div className="flex items-center gap-3 mb-3">
        <div className={`h-8 w-8 rounded-lg flex items-center justify-center text-sm font-semibold ${done ? 'bg-success/15 text-success' : 'bg-accent text-accent-foreground'}`}>
          {done ? <CheckCircle2 className="h-4 w-4" /> : n}
        </div>
        <h2 className="font-semibold flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" /> {title}
        </h2>
      </div>
      <div className="space-y-3 pl-11">{children}</div>
    </Card>
  );
}

function Stat({
  label, value, small, tone,
}: {
  label: string;
  value: string | number;
  small?: boolean;
  tone?: 'warn';
}) {
  return (
    <div className="rounded-lg bg-muted/50 p-2.5">
      <div className={`font-semibold ${small ? 'text-sm' : 'text-lg'} ${tone === 'warn' ? 'text-warning' : ''}`}>
        {value}
      </div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

function Warnings({ items, danger }: { items: string[]; danger?: boolean }) {
  return (
    <ul className={`text-xs rounded-lg p-3 space-y-1 ${danger ? 'bg-destructive/10 text-destructive' : 'bg-warning/10 text-warning'}`}>
      {items.map((w, i) => (
        <li key={i} className="flex items-start gap-1.5">
          <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>{w}</span>
        </li>
      ))}
    </ul>
  );
}
