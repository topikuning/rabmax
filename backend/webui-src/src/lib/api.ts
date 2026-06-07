// API client — same-origin (UI di-serve backend). Token Bearer di localStorage.

const TOKEN_KEY = 'boq_token';

export const auth = {
  token: () => localStorage.getItem(TOKEN_KEY),
  isAuthed: () => !!localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const t = auth.token();
  const res = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(t ? { Authorization: `Bearer ${t}` } : {}),
      ...(init?.headers || {}),
    },
  });
  if (res.status === 401) {
    auth.clear();
    if (location.pathname !== '/login') location.assign('/login');
    throw new Error('Sesi berakhir');
  }
  if (!res.ok) throw new Error(await res.text());
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get('content-type') || '';
  return (ct.includes('json') ? res.json() : res.text()) as Promise<T>;
}

async function upload<T>(path: string, file: File, extra?: Record<string, string>) {
  const fd = new FormData();
  fd.append('file', file);
  if (extra) Object.entries(extra).forEach(([k, v]) => fd.append(k, v));
  const t = auth.token();
  const res = await fetch(path, {
    method: 'POST',
    headers: t ? { Authorization: `Bearer ${t}` } : {},
    body: fd,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

export interface Project {
  id: number; name: string; lokasi: string | null; tahun_anggaran: number | null;
  target_value: number | null; mode: string; status: string; created_at: string;
  kota_kabupaten_id?: number | null; provinsi_id?: number | null; tahun_pricing?: number | null;
}
export interface Provinsi { id: number; kode: string; nama: string; nama_singkat: string | null; pulau: string | null; }
export interface Kota { id: number; provinsi_id: number; kode: string; nama: string; tipe: string; }
export interface AHSP {
  id: number; kode: string; uraian: string; satuan: string; source: string;
  confidence_tier: string; work_group: string | null;
}
export interface BahanUpah {
  id: number; nama: string; satuan: string; harga: number; category: string;
  tier: string; tkdn_factor: number; source_label: string; provinsi: string | null;
  tahun: number; ai_generated: boolean;
}
export interface AhspComponent {
  kategori: string; nama_material: string; koefisien: number; satuan: string;
  harga: number; subtotal: number; tkdn_factor: number; harga_tersedia: boolean;
}
export interface AhspDetail {
  id: number; kode: string; uraian: string; satuan: string; source: string;
  work_group: string | null; confidence_tier: string; notes: string | null;
  components: AhspComponent[]; components_total: number; components_missing_price: number;
  hsp: { bahan: number; upah: number; alat: number; subtotal: number; op: number; hsp: number; tkdn_factor: number };
}

export interface PaketItem {
  id: number; sheet_name: string; uraian: string; satuan: string; volume: number;
}
export interface ItemMatch {
  id: number; paket_item_id: number; match_type: string; ahsp_id: number | null;
  lumpsum_price: number | null; final_hsp: number | null; confidence: number; reviewed_by_user: boolean;
}

export const api = {
  login: async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    if (!res.ok) throw new Error('Email atau password salah');
    const d = await res.json();
    auth.set(d.access_token);
  },
  register: (email: string, password: string, full_name?: string) =>
    req('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password, full_name }) }),
  me: () => req<{ id: number; email: string; is_superuser: boolean }>('/api/auth/me'),

  provinsi: () => req<Provinsi[]>('/api/geografi/provinsi'),
  kota: (provinsiId: number) => req<Kota[]>('/api/geografi/kota?provinsi_id=' + provinsiId),

  projects: () => req<Project[]>('/api/projects'),
  createProject: (d: Partial<Project>) =>
    req<Project>('/api/projects', { method: 'POST', body: JSON.stringify(d) }),
  priceProject: (id: number) => req('/api/projects/' + id + '/price', { method: 'POST' }),
  generate: (id: number) => req<any>('/api/projects/' + id + '/generate', { method: 'POST' }),

  uploadRab: (id: number, f: File, mode: string) =>
    upload('/api/upload/' + id, f, { mode }),
  items: (id: number) => req<PaketItem[]>('/api/matches/' + id + '/items'),
  matches: (id: number) => req<ItemMatch[]>('/api/matches/' + id),
  runMatcher: (id: number) => req<any>('/api/matches/' + id + '/run', { method: 'POST' }),
  updateMatch: (mid: number, d: Record<string, unknown>) =>
    req<ItemMatch>('/api/matches/' + mid, { method: 'PATCH', body: JSON.stringify(d) }),
  runProfit: (id: number) => req<any>('/api/profit/' + id + '/run', { method: 'POST' }),

  ahsp: (limit = 8000) => req<AHSP[]>('/api/ahsp?limit=' + limit),
  ahspDetail: (id: number) => req<AhspDetail>('/api/ahsp/' + id + '/detail'),
  ahspSourcePrices: (id: number) => req<AhspDetail>('/api/ahsp/' + id + '/source-prices', { method: 'POST' }),

  bahanUpah: (limit = 8000) => req<BahanUpah[]>('/api/bahan-upah?limit=' + limit),
  createBahanUpah: (d: Partial<BahanUpah>) =>
    req<BahanUpah>('/api/bahan-upah', { method: 'POST', body: JSON.stringify(d) }),
  updateBahanUpah: (id: number, d: Record<string, unknown>) =>
    req<BahanUpah>('/api/bahan-upah/' + id, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteBahanUpah: (id: number) => req<void>('/api/bahan-upah/' + id, { method: 'DELETE' }),

  adminStats: () => req<{ ahsp_count: number; bahan_upah_count: number; bundled_ahsp_available: boolean }>('/api/admin/stats'),
  seedBundled: () => req<any>('/api/admin/seed/ahsp/bundled', { method: 'POST' }),
  seedUpload: (kind: 'ahsp' | 'bahan-upah', f: File) => upload<any>('/api/admin/seed/' + kind, f),
};
