// API client tipis untuk backend BOQ Generator.
// Semua endpoint selaras dengan app/main.py router prefixes.

import type {
  AHSP,
  BahanUpah,
  GenerateResult,
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

const TOKEN_KEY = 'boq_token';

export const auth = {
  getToken: (): string | null =>
    typeof window === 'undefined' ? null : localStorage.getItem(TOKEN_KEY),
  setToken: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
  isAuthed: (): boolean =>
    typeof window !== 'undefined' && !!localStorage.getItem(TOKEN_KEY),

  async login(email: string, password: string): Promise<string> {
    // OAuth2 password flow: form-encoded, username = email.
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    if (!res.ok) throw new Error('Email atau password salah');
    const data = (await res.json()) as { access_token: string };
    auth.setToken(data.access_token);
    return data.access_token;
  },

  async register(email: string, password: string, fullName?: string) {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name: fullName }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  logout: () => auth.clear(),
};

class UnauthorizedError extends Error {}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const token = auth.getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (res.status === 401) {
    auth.clear();
    if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
    throw new UnauthorizedError('Sesi berakhir, silakan login lagi');
  }
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
    const token = auth.getToken();
    const res = await fetch(`${API_BASE}/api/upload/${id}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
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

  // Generate BOQ (Stage 4)
  generate: (id: number) =>
    req<GenerateResult>(`/api/projects/${id}/generate`, { method: 'POST' }),
  fileUrl: (outputPath: string) => `${API_BASE}/files/${outputPath}`,

  // Profit (Mode B)
  runProfit: (id: number) =>
    req<{ analysis_id: number | null }>(`/api/profit/${id}/run`, { method: 'POST' }),
  listAnalyses: (id: number) => req<ProfitAnalysis[]>(`/api/profit/${id}`),

  // Katalog
  listAhsp: (q = '', limit = 50) =>
    req<AHSP[]>(`/api/ahsp?limit=${limit}${q ? `&q=${encodeURIComponent(q)}` : ''}`),
  listBahanUpah: (q = '', limit = 50) =>
    req<BahanUpah[]>(
      `/api/bahan-upah?limit=${limit}${q ? `&q=${encodeURIComponent(q)}` : ''}`,
    ),
};
