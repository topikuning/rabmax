// Shared TypeScript types — selaras dengan app/api/schemas.py (backend).

export type ProjectMode = 'generate' | 'profit_analysis';

export type ProjectStatus =
  | 'draft'
  | 'parsing'
  | 'matching'
  | 'building'
  | 'ready_for_review'
  | 'finalized'
  | 'failed';

export interface Project {
  id: number;
  name: string;
  lokasi: string | null;
  tahun_anggaran: number | null;
  target_value: number | null;
  mode: ProjectMode;
  status: ProjectStatus;
  input_file_path: string | null;
  output_file_path: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaketItem {
  id: number;
  sheet_name: string;
  excel_row: number;
  no_label: string | null;
  uraian: string;
  satuan: string;
  volume: number;
  parent_uraian: string | null;
}

export interface ItemMatch {
  id: number;
  paket_item_id: number;
  match_type: string;
  method: string;
  ahsp_id: number | null;
  lumpsum_price: number | null;
  lumpsum_source: string | null;
  final_hsp: number | null;
  tkdn_factor: number | null;
  confidence: number;
  reviewed_by_user: boolean;
}

export interface ParseSummary {
  project_id: number;
  paket_sheets: number;
  aggregator_sheets: number;
  items_total: number;
  items_unique: number;
  needs_ai_assist: string[];
  warnings: string[];
}

export interface MatchRunSummary {
  project_id: number;
  items_total: number;
  unique_keys: number;
  rule_matched: number;
  llm_matched: number;
  lumpsum: number;
  unresolved: number;
}

export interface PricingSummary {
  project_id: number;
  items_priced: number;
  items_zero_price: number;
  base_total: number;
  calibrated_total: number;
  multiplier: number;
  target_value: number | null;
  warnings: string[];
}

export interface AHSP {
  id: number;
  kode: string;
  uraian: string;
  satuan: string;
  source: string;
  confidence_tier: string;
  work_group: string | null;
}

export interface BahanUpah {
  id: number;
  nama: string;
  satuan: string;
  harga: number;
  category: string;
  tier: string;
  tkdn_factor: number;
  source_label: string;
  provinsi: string | null;
  kota: string | null;
  tahun: number;
}

export interface GenerateResult {
  project_id: number;
  output_file_path: string;
  resume_rows: number;
  items_written: number;
  items_total: number;
  items_unpriced: number;
  download_url: string;
  validation: {
    ok: boolean;
    errors: string[];
    warnings: string[];
    stats: Record<string, unknown>;
  };
}

export interface ProfitAnalysis {
  id: number;
  project_id: number;
  hps_total: number;
  hps_total_incl_ppn: number;
  estimated_cost_total: number;
  estimated_cost_breakdown: Record<string, unknown>;
  gross_profit: number;
  gross_profit_margin_pct: number;
  risk_items: unknown[];
  per_paket_breakdown: unknown[];
  assumptions: Record<string, unknown>;
  confidence: number;
  items_resolved: number;
  items_total: number;
  ai_summary: string | null;
  created_at: string;
}
