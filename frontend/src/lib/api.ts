// API client tipis untuk backend BOQ Generator.
// Semua endpoint selaras dengan app/main.py router prefixes.

import type {
  ItemMatch,
  MatchRunSummary,
  PaketItem,
  ParseSummary,
  PricingSummary,
  ProfitAnalysis,
  Project,
} from '@/types';

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // Projects
  listProjects: () => req<Project[]>('/api/projects'),
  getProject: (id: number) => req<Project>(`/api/projects/${id}`),
  createProject: (data: Partial<Project>) =>
    req<Project>('/api/projects', { method: 'POST', body: JSON.stringify(data) }),
  updateProject: (id: number, data: Partial<Project>) =>
    req<Project>(`/api/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteProject: (id: number) =>
    req<void>(`/api/projects/${id}`, { method: 'DELETE' }),

  // Upload + parse
  upload: async (id: number, file: File, mode = 'generate') => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('mode', mode);
    const res = await fetch(`${API_BASE}/api/upload/${id}`, {
      method: 'POST',
      body: fd,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<ParseSummary>;
  },

  // Items + matches
  listItems: (id: number) => req<PaketItem[]>(`/api/matches/${id}/items`),
  listMatches: (id: number) => req<ItemMatch[]>(`/api/matches/${id}`),
  runMatcher: (id: number) =>
    req<MatchRunSummary>(`/api/matches/${id}/run`, { method: 'POST' }),
  updateMatch: (matchId: number, data: Record<string, unknown>) =>
    req<ItemMatch>(`/api/matches/${matchId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  // Pricing + calibration (Stage 3+5)
  priceProject: (id: number) =>
    req<PricingSummary>(`/api/projects/${id}/price`, { method: 'POST' }),

  // Profit (Mode B)
  runProfit: (id: number) =>
    req<{ analysis_id: number | null }>(`/api/profit/${id}/run`, { method: 'POST' }),
  listAnalyses: (id: number) => req<ProfitAnalysis[]>(`/api/profit/${id}`),
};
