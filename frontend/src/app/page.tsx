'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Project {
  id: number;
  name: string;
  lokasi: string | null;
  tahun_anggaran: number | null;
  target_value: number | null;
  mode: string;
  status: string;
  created_at: string;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/projects`)
      .then((r) => r.json())
      .then((data) => setProjects(data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold">Projects</h2>
        <Link
          href="/projects/new"
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm hover:opacity-90"
        >
          + Project Baru
        </Link>
      </div>

      {loading && <p className="text-muted-foreground">Loading...</p>}
      {error && (
        <div className="border border-red-200 bg-red-50 text-red-700 p-4 rounded-md text-sm">
          Error: {error}. Pastikan backend running di {API}.
        </div>
      )}

      {!loading && projects.length === 0 && !error && (
        <div className="border border-dashed border-border p-12 rounded-md text-center">
          <p className="text-muted-foreground mb-4">Belum ada project.</p>
          <Link
            href="/projects/new"
            className="text-primary underline text-sm"
          >
            Buat project pertama →
          </Link>
        </div>
      )}

      {projects.length > 0 && (
        <div className="border rounded-md divide-y">
          {projects.map((p) => (
            <Link
              key={p.id}
              href={`/projects/${p.id}`}
              className="block p-4 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-medium">{p.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {p.lokasi || 'Lokasi tidak tercantum'}
                    {p.tahun_anggaran && ` · TA ${p.tahun_anggaran}`}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs px-2 py-1 rounded bg-muted">
                    {p.status}
                  </span>
                  <p className="text-xs text-muted-foreground mt-1">
                    {p.mode === 'generate' ? 'Generate BOQ' : 'Analisa Profit'}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
