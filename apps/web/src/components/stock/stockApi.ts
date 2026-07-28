export interface StockSummary {
  total_items: number;
  total_suppliers: number;
  total_offers: number;
  items_without_cybersul_code: number;
  items_in_review: number;
  low_stock_items: number;
  last_import_at: string | null;
  total_operational_items?: number;
  total_with_supplier?: number;
  total_with_price?: number;
}

import { humanizeApiError } from '../../lib/apiErrors';

export interface StockImportRun {
  id: string;
  source_type: string;
  source_path: string;
  source_filename: string;
  source_hash: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  total_rows: number;
  total_items: number;
  total_offers: number;
  total_errors: number;
  total_review: number;
  triggered_by_user_id: number | null;
  error_message: string | null;
}

export interface StockTreeNode {
  id: string;
  title: string;
  label: string;
  display_label: string;
  node_type: 'sheet' | 'family' | 'product' | 'variation';
  kind: 'sheet' | 'category' | 'family' | 'product' | 'variation';
  sheet: string;
  path: string;
  children: StockTreeNode[];
  count_families?: number;
  count_products?: number;
  count_variations?: number;
  count_priced?: number;
  count_low_stock?: number;
  has_children?: boolean;
  parent_id?: string | null;
  breadcrumb?: string;
  hidden_for_common_user?: boolean;
  admin_only_reason?: string | null;
}

export interface StockCatalogItem {
  id: string;
  display_name: string;
  base_name: string;
  source_sheet: string;
  variation_label: string | null;
  normalized_measure: string | null;
  measure_display?: string | null;
  measure_kind?: 'complete' | 'partial' | 'none' | string | null;
  specification_text: string | null;
  internal_code: string | null;
  quality_status?: string;
  needs_review: boolean;
  review_reason: string | null;
  family_path: string;
  cybersul_code: string | null;
  cybersul_description: string | null;
  balance_total: number;
  last_price: number | null;
  last_supplier: string | null;
  primary_price?: number | null;
  primary_supplier?: string | null;
  offer_count?: number;
  has_price?: boolean;
  metadata_json?: Record<string, string> | null;
  unit: string;
}

export interface StockOffer {
  id: string;
  supplier_id: string;
  supplier_name: string;
  price: number | null;
  price_raw: string | null;
  final_value: number | null;
  final_value_raw: string | null;
  currency: string;
  unit: string;
  email: string | null;
  phone: string | null;
  source_sheet: string;
  source_row: number;
  created_at: string;
}

export interface StockPriceHistory {
  id: string;
  supplier_name: string;
  old_price: number | null;
  new_price: number;
  source: string;
  source_reference: string | null;
  changed_by: string;
  changed_at: string;
  notes: string | null;
}

export interface StockReviewItem {
  id: string;
  item_id: string;
  item_display_name: string;
  import_run_id: string;
  review_type: string;
  severity: string;
  title: string;
  description: string;
  raw_context_json: any;
  status: string;
}

export async function stockRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/stock-catalog${path}`, {
    credentials: 'include',
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const errMsg = humanizeApiError(detail, 'Nao foi possivel concluir a acao no catalogo.', response.status);
    throw new Error(errMsg);
  }
  return response.json();
}
