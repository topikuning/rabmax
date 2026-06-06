'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Sparkles, TrendingUp } from 'lucide-react';
import { api, auth } from '@/lib/api';
import { Button, Card, Field, Input } from '@/components/ui';
import { cn } from '@/lib/utils';
import type { ProjectMode } from '@/types';

export default function NewProjectPage() {
  const router = useRouter();
  const [mode, setMode] = useState<ProjectMode>('generate');
  const [form, setForm] = useState({
    name: '',
    lokasi: '',
    tahun_anggaran: '',
    target_value: '',
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.isAuthed()) router.replace('/login');
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const project = await api.createProject({
        name: form.name,
        lokasi: form.lokasi || null,
        tahun_anggaran: form.tahun_anggaran ? Number(form.tahun_anggaran) : null,
        target_value: form.target_value ? Number(form.target_value) : null,
        mode,
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal membuat proyek');
      setBusy(false);
    }
  }

  const modes: { id: ProjectMode; title: string; desc: string; icon: typeof Sparkles }[] = [
    { id: 'generate', title: 'Generate BOQ', desc: 'RAB kosong → BOQ lengkap otomatis', icon: Sparkles },
    { id: 'profit_analysis', title: 'Analisa Profit', desc: 'RAB terisi (HPS) → margin profit', icon: TrendingUp },
  ];

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <Link href="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Kembali
      </Link>

      <div>
        <h1 className="text-2xl font-bold tracking-tight">Proyek Baru</h1>
        <p className="text-sm text-muted-foreground">Pilih mode dan isi detail proyek.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {modes.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => setMode(m.id)}
            className={cn(
              'text-left rounded-2xl border p-4 transition-all',
              mode === m.id
                ? 'border-primary ring-2 ring-primary/30 bg-accent'
                : 'border-border bg-card hover:border-primary/40',
            )}
          >
            <m.icon className={cn('h-5 w-5 mb-2', mode === m.id ? 'text-primary' : 'text-muted-foreground')} />
            <div className="font-medium text-sm">{m.title}</div>
            <div className="text-xs text-muted-foreground mt-0.5">{m.desc}</div>
          </button>
        ))}
      </div>

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-4">
          <Field label="Nama proyek">
            <Input
              required
              placeholder="mis. Pembangunan Gedung Serbaguna"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </Field>
          <Field label="Lokasi">
            <Input
              placeholder="mis. Kota Mataram, NTB"
              value={form.lokasi}
              onChange={(e) => setForm({ ...form, lokasi: e.target.value })}
            />
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Tahun anggaran">
              <Input
                type="number"
                placeholder="2026"
                value={form.tahun_anggaran}
                onChange={(e) => setForm({ ...form, tahun_anggaran: e.target.value })}
              />
            </Field>
            <Field label="Target nilai (Rp)" hint="Opsional — untuk kalibrasi">
              <Input
                type="number"
                placeholder="0"
                value={form.target_value}
                onChange={(e) => setForm({ ...form, target_value: e.target.value })}
              />
            </Field>
          </div>

          {error && (
            <div className="rounded-lg border border-destructive/40 bg-destructive/10 text-destructive text-sm p-3">
              {error}
            </div>
          )}

          <Button type="submit" loading={busy} className="w-full">
            Buat &amp; lanjut upload
          </Button>
        </form>
      </Card>
    </div>
  );
}
