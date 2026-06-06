'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Plus, FolderOpen, MapPin, Calendar, ChevronRight } from 'lucide-react';
import { api, auth } from '@/lib/api';
import { Button, Card, EmptyState, ModeBadge, Spinner, StatusBadge } from '@/components/ui';
import { formatDate, formatRupiah } from '@/lib/utils';
import type { Project } from '@/types';

export default function HomePage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.isAuthed()) {
      router.replace('/login');
      return;
    }
    api
      .listProjects()
      .then(setProjects)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [router]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Proyek</h1>
          <p className="text-sm text-muted-foreground">
            Kelola proyek estimasi BOQ &amp; analisa profit.
          </p>
        </div>
        <Link href="/projects/new">
          <Button>
            <Plus className="h-4 w-4" /> Proyek Baru
          </Button>
        </Link>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-muted-foreground text-sm py-12 justify-center">
          <Spinner /> Memuat…
        </div>
      )}

      {error && (
        <Card className="p-4 border-destructive/40 text-destructive text-sm">
          {error}
        </Card>
      )}

      {!loading && !error && projects.length === 0 && (
        <EmptyState
          title="Belum ada proyek"
          desc="Mulai dengan membuat proyek pertama lalu upload file RAB."
          action={
            <Link href="/projects/new">
              <Button>
                <Plus className="h-4 w-4" /> Buat Proyek
              </Button>
            </Link>
          }
        />
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {projects.map((p) => (
          <Link key={p.id} href={`/projects/${p.id}`}>
            <Card className="p-4 hover:border-primary/50 transition-colors group cursor-pointer h-full">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="h-9 w-9 rounded-lg bg-accent text-accent-foreground flex items-center justify-center shrink-0">
                    <FolderOpen className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-medium truncate">{p.name}</h3>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3" />
                      <span className="truncate">{p.lokasi || 'Lokasi -'}</span>
                    </div>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors shrink-0" />
              </div>
              <div className="flex items-center gap-2 mt-3 flex-wrap">
                <StatusBadge status={p.status} />
                <ModeBadge mode={p.mode} />
                {p.target_value != null && (
                  <span className="text-xs text-muted-foreground">
                    Target {formatRupiah(p.target_value)}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground mt-2">
                <Calendar className="h-3 w-3" />
                {formatDate(p.created_at)}
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
