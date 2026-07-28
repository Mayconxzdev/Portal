import React from 'react';

export interface MasterSupplier {
  id: string;
  person: { id: string; name: string; document_number?: string; email?: string; phone?: string };
  categories: string[];
  preferred_contact_email?: string;
  status: string;
}

export interface MasterItem {
  id: string;
  name: string;
  sku?: string;
  unit_of_measure: string;
  description?: string;
  category?: string;
}

export interface MasterService {
  id: string;
  name: string;
  description?: string;
  category?: string;
}

export interface PurchaseItemOptionResponse {
  id: string;
  purchase_item_id: string;
  source_type: string;
  supplier_id?: string;
  store_name?: string;
  seller_name?: string;
  title: string;
  brand?: string;
  model?: string;
  image_url?: string;
  product_url?: string;
  unit_price: number;
  shipping_price?: number;
  total_price: number;
  delivery_estimate?: string;
  availability: boolean;
  rating?: number;
  review_count?: number;
  specifications?: string;
  captured_at?: string;
  raw_source_metadata?: any;
  status?: string;
  selected: boolean;
  rejection_reason?: string;
  search_session_id?: string;
  canonical_product_id?: string;
  source_domain?: string;
  source_rank?: number;
  compatibility_score?: number;
  confidence_score?: number;
  evidence_level?: string;
  shipping_destination?: string;
  invoice_available?: boolean;
  payment_summary?: string;
  warranty_summary?: string;
  captured_method?: string;
  verification_status?: string;
  verification_summary?: string;
  price_conditions?: {
    id: string;
    condition_type: string;
    amount: number;
    currency?: string;
    installments?: number;
    installment_amount?: number;
    discount_percent?: number;
    is_recommended?: boolean;
    source_label?: string;
    evidence_status?: string;
    captured_at?: string;
  }[];
}

export interface PurchaseResearchSession {
  id: string;
  purchase_request_id: string;
  purchase_item_id: string;
  query: string;
  category: string;
  status: string;
  progress_percent: number;
  current_step: string;
  destination?: string;
  shipping_postal_code: string;
  budget_limit?: number;
  planner_summary: Record<string, any>;
  recommendation_summary: {
    summary?: string;
    highlights?: Record<string, any>;
    why?: string[];
    pending?: Record<string, any>[];
  };
  missing_questions: Record<string, any>[];
  sources: Record<string, any>[];
  tasks: Record<string, any>[];
  canonical_products: {
    id: string;
    title?: string;
    name?: string;
    brand?: string;
    model?: string;
    compatibility_score?: number;
    confidence_score?: number;
    best_total_price?: number;
    offers: PurchaseItemOptionResponse[];
  }[];
  options: PurchaseItemOptionResponse[];
  created_at?: string;
  updated_at?: string;
}

export interface PurchaseItemResponse {
  id: string;
  purchase_request_id: string;
  item_id?: string;
  service_id?: string;
  stock_catalog_item_id?: string;
  free_text_description?: string;
  quantity: number;
  unit_of_measure: string;
  specifications?: string;
  estimated_unit_price?: number;
  source_type?: string;
  source_ref_id?: string;
  source_confidence?: string;
  match_status?: string;
  source_snapshot_json?: Record<string, any>;
  description: string; // alias do backend
  unit: string;
  normalized_name?: string;
  destination?: string;
  department?: string;
  budget_limit?: number;
  classification?: string;
  classification_confidence?: number;
  selected_option_id?: string;
  requires_approval?: boolean;
  approval_status?: string;
  purchasing_status?: string;
  delivery_status?: string;
  options?: PurchaseItemOptionResponse[];
}

export interface PurchaseRFQ {
  id: string;
  purchase_request_id: string;
  title: string;
  status: string;
  deadline?: string;
  message_template?: string;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface PurchaseRFQSupplier {
  id: string;
  rfq_id: string;
  supplier_id: string;
  supplier_name?: string;
  contact_email?: string;
  status: string;
  message_subject?: string;
  message_body?: string;
  sent_at?: string;
  response_received_at?: string;
  created_at: string;
}

export interface PurchaseQuoteDetail {
  id: string;
  purchase_request_id: string;
  title: string;
  description?: string;
  status: string;
  origin_type?: string;
  origin_ref_id?: string;
  origin_snapshot_json?: Record<string, any>;
  items: PurchaseItemResponse[];
  suppliers: PurchaseRFQSupplier[];
  created_at: string;
  updated_at: string;
}

export interface ParsedQuoteLine {
  raw_text: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  confidence: 'high' | 'check' | 'low' | string;
  match_status: 'confirmed' | 'needs_confirmation' | string;
  purchase_type?: 'internal' | 'external' | 'ambiguous' | string;
  requires_approval?: boolean;
  classification_message?: string;
  match_score?: number;
  suggested_stock_catalog_item_id?: string;
  suggested_display_name?: string;
  suggested_specification?: string;
  budget_limit?: number;
  destination?: string;
  department?: string;
}

export interface PurchaseSuggestion {
  id?: string;
  label: string;
  kind: string;
  subtitle?: string;
  confidence: number;
  stock_catalog_item_id?: string;
  source: string;
  metadata?: Record<string, any>;
}

export interface SupplierSuggestion {
  supplier_id?: string;
  supplier_name: string;
  contact_email?: string;
  coverage_count: number;
  total_items: number;
  confidence: string;
  status: string;
  reasons: string[];
  item_ids: string[];
}

export interface EmailPreview {
  message_id: string;
  rfq_supplier_id: string;
  supplier_id: string;
  supplier_name: string;
  to_email?: string;
  sender_account_id: string;
  sender_email: string;
  sender_name?: string;
  account_status?: string;
  can_send?: boolean;
  blocked_reason?: string;
  bcc_enabled: boolean;
  bcc?: string;
  bcc_source?: string;
  subject: string;
  body_html: string;
  body_text?: string;
  signature_html?: string;
  content_hash: string;
  idempotency_key?: string;
  status: string;
  environment?: string;
  provider_message_id?: string;
  human_status?: string;
  pdf_optional_available?: boolean;
  pdf_status?: string;
  pdf_message?: string;
  items: {
    purchase_item_id: string;
    description: string;
    specifications?: string;
    quantity: number;
    unit_of_measure: string;
  }[];
}

export interface InboundAttachment {
  id: string;
  inbound_message_id: string;
  filename?: string;
  safe_filename: string;
  content_type?: string;
  detected_content_type?: string;
  size_bytes: number;
  sha256?: string;
  storage_key?: string;
  scan_status: string;
  blocked_reason?: string;
  text_preview?: string;
  created_at: string;
}

export interface ResponseCandidate {
  id: string;
  inbound_message_id: string;
  quote_id?: string;
  rfq_id?: string;
  supplier_id?: string;
  supplier_name?: string;
  quote_title?: string;
  quote_code?: string;
  from_email: string;
  from_name?: string;
  subject?: string;
  body_text?: string;
  received_at: string;
  candidate_status: string;
  confidence_score: number;
  confidence_level: 'high' | 'check' | 'low' | string;
  match_reasons: string[];
  risk_flags: string[];
  attachments: InboundAttachment[];
  human_status: string;
  created_at: string;
  updated_at: string;
}

export interface ResponseEvidence {
  id: string;
  extraction_id: string;
  field_id?: string;
  attachment_id?: string;
  source_type: string;
  source_label?: string;
  snippet: string;
  confidence_level: string;
  created_at: string;
}

export interface ResponseExtractedField {
  id: string;
  extraction_id: string;
  field_name: string;
  label: string;
  raw_value?: string;
  normalized_value?: string;
  value_type: string;
  confidence_level: string;
  confidence_score: number;
  review_status: string;
  source_type: string;
  source_label?: string;
  evidences: ResponseEvidence[];
}

export interface ResponseExtraction {
  id: string;
  candidate_id: string;
  inbound_message_id: string;
  quote_id?: string;
  supplier_id?: string;
  status: string;
  extractor_version: string;
  confidence_summary: string;
  fields: ResponseExtractedField[];
  evidences: ResponseEvidence[];
  created_at: string;
  updated_at: string;
  reviewed_at?: string;
}

export interface RFQDraft {
  supplier_id: string;
  supplier_name: string;
  contact_email?: string;
  subject: string;
  body: string;
}

export interface QuoteResponseLine {
  id: string;
  quote_response_id: string;
  request_item_id?: string;
  description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  delivery_days?: number;
  notes?: string;
}

export interface QuoteResponse {
  id: string;
  rfq_supplier_id?: string;
  supplier_id: string;
  supplier_name?: string;
  total_amount?: number;
  currency: string;
  delivery_days?: number;
  payment_terms?: string;
  validity_date?: string;
  status: string;
  created_at: string;
  lines: QuoteResponseLine[];
}

export interface CompareSupplierSummary {
  supplier_id: string;
  supplier_name: string;
  total_amount: number;
  quote_response_id?: string;
  average_delivery_days?: number;
  payment_terms?: string;
  is_best_price: boolean;
  is_best_delivery: boolean;
}

export interface CompareItemOffer {
  supplier_id: string;
  supplier_name: string;
  unit_price: number;
  total_price: number;
  delivery_days?: number;
}

export interface CompareItemRow {
  request_item_id?: string;
  description: string;
  requested_quantity: number;
  offers: CompareItemOffer[];
}

export interface PurchaseComparison {
  rfq_id: string;
  best_supplier_id?: string;
  best_supplier_name?: string;
  recommendation_summary?: string;
  created_at: string;
  items_comparison: CompareItemRow[];
  suppliers_summary: CompareSupplierSummary[];
}

export interface PurchasesSummary {
  total_requests: number;
  drafts: number;
  pending_approval: number;
  approved: number;
  quoting: number;
  ordered: number;
  delivered: number;
  cancelled: number;
  total_suppliers: number;
  active_suppliers: number;
  total_quotations_pending: number;
  estimated_value_open: number;
}

export interface PurchaseAttentionItem {
  id: string;
  type: string;
  title: string;
  description: string;
  severity: 'info' | 'warning' | 'danger' | string;
  status: string;
  quote_id?: string;
  request_id?: string;
  supplier_id?: string;
  supplier_name?: string;
  action_label: string;
  updated_at?: string;
}

export interface PurchaseStatusGroup {
  key: string;
  label: string;
  count: number;
}

export interface PurchaseOngoingQuote {
  request_id: string;
  title: string;
  status: string;
  status_label: string;
  stage: string;
  items_count: number;
  suppliers_count: number;
  responses_count: number;
  coverage_label: string;
  next_action: string;
  responsible?: string;
  updated_at: string;
}

export interface PurchasesOverview {
  summary: PurchasesSummary;
  queue_counts?: Record<string, number>;
  status_groups: PurchaseStatusGroup[];
  attention: PurchaseAttentionItem[];
  ongoing_quotes: PurchaseOngoingQuote[];
}

export interface NewItemForm {
  item_id?: string;
  service_id?: string;
  stock_catalog_item_id?: string;
  free_text_description: string;
  quantity: number;
  unit_of_measure: string;
  specifications: string;
  estimated_unit_price: number;
  itemType: 'product' | 'service' | 'freetext';
}

export interface PurchaseRequest {
  id: string;
  title: string;
  description?: string;
  justification?: string;
  requester_user_id: number;
  requester_username?: string;
  status: string;
  priority: string;
  urgency: string;
  category?: string;
  department?: string;
  estimated_total?: number;
  approved_total?: number;
  needed_by?: string;
  origin_type?: string;
  origin_ref_id?: string;
  origin_snapshot_json?: Record<string, any>;
  notes?: string;
  approval_id?: number;
  items: PurchaseItemResponse[];
  rfqs?: PurchaseRFQ[];
  created_at: string;
  updated_at: string;
}
