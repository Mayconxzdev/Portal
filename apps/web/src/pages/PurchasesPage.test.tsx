import { render, screen, waitFor, within, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { PurchasesPage } from './PurchasesPage';
// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------
const mockSummary = {
  total_requests: 3, drafts: 1, pending_approval: 1, approved: 1,
  quoting: 0, ordered: 0, delivered: 0, cancelled: 0,
  total_suppliers: 2, active_suppliers: 2, total_quotations_pending: 0,
  estimated_value_open: 5000
};

const mockSupplier = {
  id: 'sup-uuid-1',
  person: { id: 'person-uuid-1', name: 'Fornecedor Alfa Ltda', document_number: '11111111000111', email: 'comercial@fornecedor-hardware.example' },
  categories: ['TI', 'Hardware'],
  preferred_contact_email: 'vendas@fornecedor-alfa.example',
  status: 'ACTIVE'
};

const mockSupplierReviewResponse = {
  items: [
    {
      supplier_id: 'sup-uuid-1',
      name: 'Fornecedor Alfa Ltda',
      legal_name: null,
      email: 'vendas@fornecedor-alfa.example',
      phone: null,
      categories: ['TI', 'Hardware'],
      sheets: ['Compras Nova.xlsx'],
      ready_for_quote: true,
      status_label: 'Pronto',
      possible_duplicate_names: [],
    },
  ],
  summary: {
    ready_for_quote: 1,
    missing_email: 0,
    missing_phone: 1,
    possible_duplicates: 0,
    needs_review: 0,
  },
};

const mockMasterItem = {
  id: 'item-uuid-1', name: 'Monitor Full HD 27"', sku: 'MON-27FHD',
  unit_of_measure: 'un', description: 'Monitor LG 27 polegadas Full HD', category: 'Periféricos'
};

const mockMasterService = {
  id: 'svc-uuid-1', name: 'Manutenção de TI', description: 'Suporte técnico especializado', category: 'TI'
};

const mockRequest: any = {
  id: 'req-uuid-1',
  title: 'Compra de monitores para TI',
  description: 'Precisamos de 5 monitores novos',
  justification: 'Monitores atuais com defeito',
  requester_user_id: 1,
  requester_username: 'admin_vesper',
  status: 'DRAFT',
  priority: 'HIGH',
  urgency: 'HIGH',
  department: 'TI',
  estimated_total: 5000,
  needed_by: '2026-07-01T00:00:00Z',
  items: [
    { id: 'item-line-1', purchase_request_id: 'req-uuid-1', description: 'Monitor Dell 27"', free_text_description: null, item_id: 'item-uuid-1', service_id: null, quantity: 5, unit_of_measure: 'un', estimated_unit_price: 1000 }
  ],
  rfqs: [],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString()
};

const mockApprovedRequest: any = {
  ...mockRequest,
  id: 'req-uuid-2',
  title: 'Nobreaks para servidor',
  status: 'APPROVED',
  priority: 'URGENT',
  rfqs: []
};

const mockRFQ = {
  id: 'rfq-uuid-1', purchase_request_id: 'req-uuid-2',
  title: 'Cotacao - Nobreaks para servidor', status: 'RFQ_PREPARING',
  deadline: '2026-07-15T00:00:00Z', message_template: null,
  created_by_user_id: 1, created_at: new Date().toISOString(), updated_at: new Date().toISOString()
};

const mockApprovedRequestWithRFQ = { ...mockApprovedRequest, rfqs: [mockRFQ] };

const mockDrafts = [
  {
    supplier_id: 'sup-uuid-1',
    supplier_name: 'Fornecedor Alfa Ltda',
    contact_email: 'vendas@fornecedor-alfa.example',
    subject: 'Solicitação de Cotação — Nobreaks para servidor',
    body: 'Prezados,\n\nSolicitamos cotação para os itens.\n\nAtenciosamente,\nPortal Vesper'
  }
];

const mockComparison = {
  rfq_id: 'rfq-uuid-1',
  best_supplier_id: 'sup-uuid-1',
  best_supplier_name: 'Fornecedor Alfa Ltda',
  recommendation_summary: 'Dell apresentou o melhor custo-benefício com menor prazo.',
  created_at: new Date().toISOString(),
  items_comparison: [],
  suppliers_summary: [
    {
      supplier_id: 'sup-uuid-1', supplier_name: 'Fornecedor Alfa Ltda',
      total_amount: 4500, average_delivery_days: 7,
      payment_terms: 'Boleto 30 dias', is_best_price: true, is_best_delivery: true
    }
  ]
};

const emptyComparison = {
  rfq_id: 'rfq-uuid-1', items_comparison: [], suppliers_summary: [],
  created_at: new Date().toISOString()
};

const mockPriceReference = {
  id: 'ref-uuid-1',
  product_item_id: 'item-uuid-1',
  product_item_name: 'Monitor Full HD 27"',
  product_item_sku: 'MON-27FHD',
  supplier_id: 'sup-uuid-1',
  supplier_name: 'Fornecedor Alfa Ltda',
  current_unit_price: 1200.00,
  currency: 'BRL',
  unit_of_measure: 'un',
  is_active: true,
  approved_at: new Date().toISOString(),
  approved_by_user_id: 1,
  notes: 'Preço negociado anual'
};

const mockPriceSuggestion = {
  id: 'sug-uuid-1',
  product_item_id: 'item-uuid-1',
  product_item_name: 'Monitor Full HD 27"',
  product_item_sku: 'MON-27FHD',
  supplier_id: 'sup-uuid-1',
  supplier_name: 'Fornecedor Alfa Ltda',
  evidence_id: 'ev-uuid-1',
  old_unit_price: 1200.00,
  new_unit_price: 1380.00,
  pct_variation: 15.00,
  variation_direction: 'INCREASE',
  status: 'PENDING',
  reason: 'Aumento nos custos de logística',
  created_by_user_id: 2,
  created_by_username: 'comprador_1',
  created_at: new Date().toISOString(),
  evidence_document_number: 'NF-9928'
};

const mockPriceHistory = {
  id: 'hist-uuid-1',
  product_item_id: 'item-uuid-1',
  product_item_name: 'Monitor Full HD 27"',
  supplier_id: 'sup-uuid-1',
  supplier_name: 'Fornecedor Alfa Ltda',
  unit_price: 1380.00,
  quantity: 5,
  total_amount: 6900.00,
  currency: 'BRL',
  observed_at: new Date().toISOString(),
  source_type: 'NF',
  source_id: 'NF-100223'
};

const mockProductsPrices = {
  items: [
    {
      family_id: 'family-chapa',
      family_name: 'CHAPA GALVANIZADA',
      description: 'Familia de chapas galvanizadas',
      variations_count: 2,
      suppliers_count: 1,
      min_price: 1200,
      max_price: 1380,
      last_updated_at: new Date().toISOString(),
      variations: [
        {
          id: 'item-uuid-1',
          family_id: 'family-chapa',
          family_name: 'CHAPA GALVANIZADA',
          name: 'Ch. Galv. 3/16 - 4,75 mm | 3 x 1,2 m | 136,8 kg/m',
          short_name: '3/16 - 4,75 mm | 3 x 1,2 m | 136,8 kg/m',
          variation_name: '3/16 - 4,75 mm | 3 x 1,2 m | 136,8 kg/m',
          attributes: { medida: '3 x 1,2 m', espessura: '4,75 mm' },
          unit_of_measure: 'un',
          current_price: 1200,
          currency: 'BRL',
          supplier_id: 'sup-uuid-1',
          supplier_name: 'Fornecedor Alfa Ltda',
          last_updated_at: new Date().toISOString(),
          history_count: 1,
          suppliers_count: 1,
          description: 'Chapa galvanizada compravel',
          technical_details: { id: 'item-uuid-1', sku: 'CH-GALV-316-3X12' }
        },
        {
          id: 'item-uuid-2',
          family_id: 'family-chapa',
          family_name: 'CHAPA GALVANIZADA',
          name: 'Ch. Galv. 3/16 - 4,75 mm | 6 x 1,2 m | 273,6 kg/m',
          short_name: '3/16 - 4,75 mm | 6 x 1,2 m | 273,6 kg/m',
          variation_name: '3/16 - 4,75 mm | 6 x 1,2 m | 273,6 kg/m',
          attributes: { medida: '6 x 1,2 m', espessura: '4,75 mm' },
          unit_of_measure: 'un',
          current_price: 1380,
          currency: 'BRL',
          supplier_id: 'sup-uuid-1',
          supplier_name: 'Fornecedor Alfa Ltda',
          last_updated_at: new Date().toISOString(),
          history_count: 0,
          suppliers_count: 1,
          description: 'Chapa galvanizada compravel',
          technical_details: { id: 'item-uuid-2', sku: 'CH-GALV-316-6X12' }
        }
      ]
    }
  ],
  total_variations: 2,
  limit: 80,
  offset: 0,
  has_more: false,
  summary: {
    products_count: 2,
    families_count: 1,
    current_prices_count: 2,
    recently_updated_count: 2
  }
};

const mockXlsxReconciliation = {
  source_path: '\\\\fileserver.local\\suporte\\$  - TABELA COMPRA\\Compras Nova .xlsx',
  file_updated_at: '2026-06-03T16:42:22',
  sheets_read: ['Chapas', 'Hélice FM'],
  sheets_ignored: ['ÍNDICE ', 'Planilha1'],
  layouts: { metais_blocos: 1, helices: 1 },
  summary: {
    sheets_read: 2,
    suppliers_found: 3,
    suppliers_with_email: 2,
    suppliers_with_phone: 2,
    suppliers_in_portal: 1,
    suppliers_missing: 1,
    products_found: 2,
    families_found: 2,
    variations_found: 2,
    ambiguous_items: 1,
    prices_detected: 2,
    prices_using_final_value: 2,
    prices_matching_portal: 0,
    prices_divergent: 1,
    needs_review: 1,
    suppliers_without_email: 1
  },
  items: [
    {
      row_key: 'Chapas:4:abc',
      sheet: 'Chapas',
      row_number: 4,
      category: 'Chapas',
      family: 'CHAPA GALVANIZADA',
      subfamily: 'Ch. Galv. 3/16',
      variation: 'Ch. Galv. 3/16 - 4,75 mm | 3 x 1,2 m',
      display_name: 'CHAPA GALVANIZADA | Ch. Galv. 3/16 - 4,75 mm | 3 x 1,2 m',
      supplier_name: 'CALINOX',
      company_name: 'Calinox',
      email: 'vendas@fornecedor-inox.example',
      phone: '21999990000',
      spreadsheet_price: 120,
      raw_price: 100,
      final_value: 120,
      portal_price: 100,
      difference_amount: 20,
      difference_percent: 20,
      price_type: 'chapa',
      unit: 'chapa',
      updated_at: '03/06/2026',
      situation: 'Preço diferente',
      issues: ['Preço diferente'],
      portal_item_id: 'item-uuid-1',
      portal_supplier_id: 'sup-uuid-1',
      portal_item_name: 'Ch. Galv. 3/16 - 4,75 mm | 3 x 1,2 m',
      portal_supplier_name: 'CALINOX',
      ready_for_quote: true
    },
    {
      row_key: 'Chapas:5:def',
      sheet: 'Chapas',
      row_number: 5,
      category: 'Chapas',
      family: 'CANTONEIRA',
      variation: '1/4" x 1/8"',
      display_name: 'CANTONEIRA | 1/4" x 1/8"',
      supplier_name: 'SERFER',
      email: null,
      phone: null,
      spreadsheet_price: 80,
      portal_price: null,
      price_type: 'barra',
      unit: 'barra',
      situation: 'Sem e-mail',
      issues: ['Fornecedor sem e-mail', 'Variação ambígua'],
      portal_item_id: null,
      portal_supplier_id: null,
      ready_for_quote: false
    }
  ],
  total: 2,
  limit: 80,
  offset: 0,
  has_more: false
};

// ---------------------------------------------------------------------------
// Helper: instalação do fetch mock
// ---------------------------------------------------------------------------
function installFetchMock(opts: {
  requests?: any[];
  summaryData?: any;
  suppliers?: any[];
  supplierReview?: any;
  items?: any[];
  services?: any[];
  detailById?: Record<string, any>;
  drafts?: any[];
  comparison?: any;
  failCreate?: boolean;
} = {}) {
  const {
    requests = [mockRequest, mockApprovedRequest],
    summaryData = mockSummary,
    suppliers = [mockSupplier],
    supplierReview = mockSupplierReviewResponse,
    items = [mockMasterItem],
    services = [mockMasterService],
    detailById = {},
    drafts = [],
    comparison = emptyComparison,
    failCreate = false
  } = opts;

  const fetchMock = vi.fn(async (url: string, init?: any) => {
    const method = (init?.method || 'GET').toUpperCase();
    const json = (body: any, status = 200) =>
      new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

    // Produtos e preços
    if (url.includes('/purchases/xlsx-reconciliation/update-price') && method === 'POST') {
      return json({
        item_id: 'item-uuid-1',
        family_name: 'CHAPA GALVANIZADA',
        variation_name: 'Ch. Galv. 3/16 - 4,75 mm | 3 x 1,2 m',
        old_price: 100,
        new_price: 120,
        difference_amount: 20,
        difference_percent: 20,
        supplier_id: 'sup-uuid-1',
        supplier_name: 'CALINOX',
        history_id: 'hist-xlsx',
        reference_id: 'ref-xlsx',
        updated_at: new Date().toISOString()
      });
    }
    if (url.includes('/purchases/xlsx-reconciliation/supplier-contact') && method === 'POST') return json(mockSupplier);
    if (url.includes('/purchases/xlsx-reconciliation/export') && method === 'POST') return json({ path: 'K:\\Maycon\\Portal-Vesper-Dados\\compras_conferencia_planilha.csv', rows: 2 });
    if (url.includes('/purchases/xlsx-reconciliation')) return json(mockXlsxReconciliation);

    if (url.includes('/purchases/products-prices/items/item-uuid-1/price') && method === 'POST') {
      return json({
        item_id: 'item-uuid-1',
        family_name: 'CHAPA GALVANIZADA',
        variation_name: '3/16 - 4,75 mm | 3 x 1,2 m | 136,8 kg/m',
        old_price: 1200,
        new_price: 1300,
        difference_amount: 100,
        difference_percent: 8.33,
        supplier_id: 'sup-uuid-1',
        supplier_name: 'Fornecedor Alfa Ltda',
        history_id: 'hist-uuid-new',
        reference_id: 'ref-uuid-new',
        updated_at: new Date().toISOString()
      });
    }
    if (url.includes('/purchases/catalog/items/item-uuid-1/supplier-offers')) {
      return json({ items: [], total: 0 });
    }
    if (url.includes('/purchases/catalog/families/family-chapa/variations')) return json(mockProductsPrices.items[0]);
    if (url.includes('/purchases/catalog/families')) return json(mockProductsPrices);
    if (url.includes('/purchases/catalog/sync-from-xlsx') && method === 'POST') {
      return json({
        status: 'success',
        message: 'Catalogo atualizado da planilha.',
        run_id: 'run-uuid-1',
        source_path: 'Compras Nova.xlsx',
        started_at: new Date().toISOString(),
        finished_at: new Date().toISOString(),
        metrics: {},
        summary: {
          families_count: 1,
          variations_count: 2,
          catalog_rows_count: 2,
          supplier_offers_count: 2,
          current_prices_count: 2,
          needs_review_count: 0,
          suppliers_without_email_count: 0,
          last_sync_status: 'success',
        },
      });
    }
    if (url.includes('/purchases/products-prices')) return json(mockProductsPrices);

    // Rastreabilidade de preços de compras
    if (url.includes('/purchases/prices/references')) return json([mockPriceReference]);
    if (url.includes('/purchases/prices/history')) return json([mockPriceHistory]);
    if (url.includes('/purchases/prices/suggestions')) {
      const sugMatch = url.match(/\/suggestions\/([^/]+)\/(approve|reject)$/);
      if (sugMatch && method === 'POST') {
        const action = sugMatch[2];
        const statusVal = action === 'approve' ? 'APPROVED' : 'REJECTED';
        return json({ ...mockPriceSuggestion, status: statusVal });
      }
      return json([mockPriceSuggestion]);
    }
    if (url.includes('/purchases/prices/evidences') && method === 'POST') {
      return json({
        id: 'ev-uuid-new',
        source_type: 'BOLETO',
        supplier_id: 'sup-uuid-1',
        product_item_id: 'item-uuid-1',
        unit_price: 1380.00,
        quantity: 5,
        total_amount: 6900.00
      }, 201);
    }
    if (url.match(/\/purchases\/prices\/items\/[^/]+\/timeline/)) {
      return json([mockPriceHistory]);
    }

    // Master data
    if (url.includes('/master-data/suppliers')) return json(suppliers);
    if (url.includes('/master-data/items')) return json(items);
    if (url.includes('/master-data/services')) return json(services);

    // Summary
    if (url.includes('/purchases/summary')) return json(summaryData);

    // Suppliers review queue
    if (url.includes('/purchases/suppliers/review')) return json(supplierReview);

    // RFQ drafts
    if (url.match(/\/rfqs\/[^/]+\/drafts/)) return json(drafts);

    // RFQ comparison
    if (url.match(/\/rfqs\/[^/]+\/comparison/)) return json(comparison);

    // RFQ generate-drafts
    if (url.includes('/generate-drafts') && method === 'POST') return json(mockDrafts);

    // RFQ request-send-approval
    if (url.includes('/request-send-approval') && method === 'POST')
      return json({ status: 'no_approval_required', message: 'Cotacao liberada para envio direto.', rfq_id: 'rfq-uuid-1' });

    // RFQ suppliers POST
    if (url.match(/\/rfqs\/[^/]+\/suppliers/) && method === 'POST')
      return json({ id: 'rfqs-sup-1', supplier_id: 'sup-uuid-1', status: 'PENDING' }, 201);

    // RFQ create (POST /requests/:id/rfqs)
    if (url.match(/\/requests\/[^/]+\/rfqs/) && method === 'POST') return json(mockRFQ, 201);

    // RFQ detail GET
    if (url.match(/\/rfqs\/[^/]+$/) && method === 'GET') return json(mockRFQ);

    // Request send-to-approval
    if (url.includes('/send-to-approval') && method === 'POST')
      return json({ ...mockRequest, status: 'PENDING_APPROVAL' });

    // Request cancel
    if (url.includes('/cancel') && method === 'POST')
      return json({ ...mockRequest, status: 'CANCELLED' });

    // Request create POST
    if (url.match(/\/purchases\/requests$/) && method === 'POST') {
      if (failCreate) return json({ detail: 'Erro interno ao criar requisição.' }, 500);
      return json({ ...mockRequest, id: 'req-uuid-new' }, 201);
    }

    // Request detail GET
    const detailMatch = url.match(/\/purchases\/requests\/([^/]+)$/);
    if (detailMatch && method === 'GET') {
      const id = detailMatch[1];
      if (detailById[id]) return json(detailById[id]);
      if (id === 'req-uuid-2') return json(mockApprovedRequestWithRFQ);
      if (id === 'req-uuid-new') return json({ ...mockRequest, id: 'req-uuid-new' });
      return json(mockRequest);
    }

    // Requests list GET
    if (url.match(/\/purchases\/requests$/) && method === 'GET') return json(requests);

    return json([]);
  });

  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

// ---------------------------------------------------------------------------
// Testes consolidados do fluxo principal de Compras
// ---------------------------------------------------------------------------
const consolidatedExternalRequest: any = {
  id: 'need-external-1',
  title: 'Memoria RAM DDR4',
  description: 'Compra externa para TI',
  justification: null,
  requester_user_id: 1,
  requester_username: 'admin_vesper',
  status: 'DRAFT',
  priority: 'NORMAL',
  urgency: 'NORMAL',
  department: 'TI',
  estimated_total: 1200,
  needed_by: null,
  rfqs: [],
  items: [
    {
      id: 'item-external-1',
      purchase_request_id: 'need-external-1',
      description: 'Memoria RAM DDR4',
      free_text_description: 'Memoria RAM DDR4',
      stock_catalog_item_id: null,
      item_id: null,
      service_id: null,
      quantity: 2,
      unit_of_measure: 'un',
      estimated_unit_price: 600,
      budget_limit: 1200,
      destination: 'TI',
      department: 'TI',
      classification: 'EXTERNAL',
      classification_confidence: 0.12,
      requires_approval: true,
      options: [],
      selected_option_id: null,
    },
  ],
  created_at: '2026-06-18T10:00:00Z',
  updated_at: '2026-06-18T10:00:00Z',
};

const consolidatedInternalRequest: any = {
  id: 'need-internal-1',
  title: 'Arame BTC CL 1,5 mm',
  description: 'Reposicao de item do Estoque',
  justification: null,
  requester_user_id: 1,
  requester_username: 'admin_vesper',
  status: 'RFQ_SENT',
  priority: 'HIGH',
  urgency: 'HIGH',
  department: 'Producao',
  estimated_total: 180,
  needed_by: null,
  rfqs: [{ id: 'rfq-internal-1', status: 'RFQ_SENT', title: 'Cotacao de arame' }],
  items: [
    {
      id: 'item-internal-1',
      purchase_request_id: 'need-internal-1',
      description: 'Arame BTC CL 1,5 mm',
      free_text_description: 'Arame BTC CL 1,5 mm',
      stock_catalog_item_id: 'stock-arame-1',
      quantity: 10,
      unit_of_measure: 'kg',
      estimated_unit_price: 18,
      budget_limit: null,
      department: 'Producao',
      classification: 'INTERNAL',
      classification_confidence: 0.94,
      requires_approval: false,
      options: [],
      selected_option_id: null,
    },
  ],
  created_at: '2026-06-17T10:00:00Z',
  updated_at: '2026-06-17T10:00:00Z',
};

const consolidatedReadyRequest: any = {
  ...consolidatedExternalRequest,
  id: 'need-ready-1',
  title: 'Notebook para engenharia',
  status: 'APPROVED',
  estimated_total: 3650,
  items: [
    {
      ...consolidatedExternalRequest.items[0],
      id: 'item-ready-1',
      purchase_request_id: 'need-ready-1',
      description: 'Notebook para engenharia',
      free_text_description: 'Notebook para engenharia',
      selected_option_id: 'option-ready-1',
      options: [
        {
          id: 'option-ready-1',
          supplier_name: 'Loja autorizada',
          title: 'Notebook 16 GB',
          unit_price: 3650,
          shipping_price: 0,
          total_price: 3650,
          product_url: 'https://example.com/notebook',
          selected: true,
        },
      ],
    },
  ],
};

const consolidatedAllRequests = [
  consolidatedExternalRequest,
  consolidatedInternalRequest,
  consolidatedReadyRequest,
];

const consolidatedQueues: Record<string, any[]> = {
  all: consolidatedAllRequests,
  attention: consolidatedAllRequests,
  suppliers: [consolidatedInternalRequest],
  approval: [consolidatedExternalRequest],
  ready: [consolidatedReadyRequest],
  delivery: [],
};

type ConsolidatedParsedNeed = {
  raw_text: string;
  description: string;
  quantity: number;
  unit_of_measure: string;
  confidence: string;
  purchase_type: 'internal' | 'external' | 'ambiguous' | 'mixed';
  classification_message: string;
  match_score: number;
  suggested_stock_catalog_item_id?: string;
  suggested_display_name?: string;
  suggested_specification?: string;
  budget_limit?: number;
  destination?: string;
  department?: string;
  requires_approval: boolean;
};

function consolidatedParseNeed(text: string): ConsolidatedParsedNeed[] {
  if (text.toLowerCase().includes('arame')) {
    return [
      {
        raw_text: text,
        description: 'Arame BTC CL 1,5 mm',
        quantity: 10,
        unit_of_measure: 'kg',
        confidence: 'high',
        purchase_type: 'internal',
        classification_message: 'Item interno encontrado no Estoque.',
        match_score: 0.94,
        suggested_stock_catalog_item_id: 'stock-arame-1',
        suggested_display_name: 'Arame BTC CL 1,5 mm',
        suggested_specification: '1,5 mm',
        requires_approval: false,
      },
    ];
  }
  return [
    {
      raw_text: text,
      description: 'Memoria RAM DDR4',
      quantity: 2,
      unit_of_measure: 'un',
      confidence: 'high',
      purchase_type: 'external',
      classification_message: 'Nenhum item interno compativel foi encontrado. Vou tratar como compra externa.',
      match_score: 0.12,
      budget_limit: 1200,
      destination: 'TI',
      department: 'TI',
      requires_approval: false,
    },
  ];
}

function consolidatedAnalyzeNeed(text: string) {
  const parsed = consolidatedParseNeed(text);
  return {
    draft_id: 'draft-test-1',
    status: 'reviewing',
    raw_input: text,
    analysis_summary: {
      total_items: parsed.length,
      message: 'Revise os itens interpretados antes de criar a compra.',
    },
    items: parsed.map((item, index) => ({
      id: `draft-item-${index}`,
      draft_id: 'draft-test-1',
      position: index,
      item_type: item.purchase_type,
      description: item.description,
      quantity: item.quantity,
      unit_of_measure: item.unit_of_measure,
      budget_limit: item.budget_limit ?? null,
      destination: item.destination ?? null,
      department: item.department ?? null,
      confidence_score: item.match_score ?? 0.5,
      classification_reason: item.classification_message,
      stock_catalog_item_id: item.suggested_stock_catalog_item_id ?? null,
      missing_question_json: item.purchase_type === 'ambiguous' ? { question: 'Este item e interno ou externo?' } : null,
      metadata_json: item,
    })),
  };
}

function installConsolidatedFetchMock() {
  const calls: Array<{ url: string; init?: RequestInit; body?: any }> = [];
  const consolidatedOverview = {
    summary: {
      total_requests: 3,
      drafts: 1,
      pending_approval: 1,
      approved: 1,
      quoting: 1,
      ordered: 0,
      delivered: 0,
      cancelled: 0,
      total_suppliers: 2,
      active_suppliers: 2,
      total_quotations_pending: 1,
      estimated_value_open: 4850,
    },
    queue_counts: {
      all: 3,
      attention: 2,
      suppliers: 1,
      approval: 1,
      ready: 1,
      delivery: 0,
    },
    attention: [],
    recent_requests: consolidatedAllRequests,
    recent_quotes: [],
  };

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
    const body = init?.body ? JSON.parse(init.body as string) : undefined;
    calls.push({ url, init, body });
    const json = (payload: any, status = 200) =>
      new Response(JSON.stringify(payload), { status, headers: { 'Content-Type': 'application/json' } });

    if (url.includes('/api/v1/purchases/overview')) return json(consolidatedOverview);
    if (url.includes('/api/v1/purchases/summary')) return json(consolidatedOverview.summary);
    if (url.includes('/api/v1/master-data/suppliers')) return json([]);
    if (url.includes('/api/v1/master-data/items')) return json([]);
    if (url.includes('/api/v1/master-data/services')) return json([]);
    if (url.includes('/api/v1/purchases/analyze')) return json(consolidatedAnalyzeNeed(String(body?.text || '')));
    if (url.includes('/api/v1/purchases/suggestions')) return json([]);
    if (url.includes('/api/v1/purchases/needs/parse-text')) return json(consolidatedParseNeed(String(body?.text || '')));
    if (url.includes('/api/v1/purchases/external-search')) {
      return json({
        status: 'credentials_missing',
        results: [],
        classifications: {},
        message: 'Pesquisa automatica de mercado ainda nao esta configurada. Adicione links ou opcoes manualmente.',
      });
    }
    if (url.match(/\/api\/v1\/purchases\/items\/[^/]+\/research-sessions$/)) {
      return json({
        id: 'research-session-1',
        purchase_request_id: 'need-external-1',
        purchase_item_id: 'item-external-1',
        query: body?.query || 'Memoria RAM DDR4',
        category: 'informatica_memoria',
        status: 'completed_with_pending',
        progress_percent: 70,
        current_step: 'Pesquisa automatica indisponivel',
        shipping_postal_code: '21043-030',
        planner_summary: {},
        recommendation_summary: {
          summary: 'Pesquisa automatica de mercado ainda nao esta configurada. Adicione links ou opcoes manualmente.',
          highlights: {},
          why: [],
          pending: [],
        },
        missing_questions: [],
        sources: [
          {
            source_label: 'Pesquisa de mercado',
            status: 'skipped',
            error_message: 'Pesquisa automatica de mercado ainda nao esta configurada.',
          },
        ],
        tasks: [],
        canonical_products: [],
        options: [],
      });
    }
    if (url.match(/\/api\/v1\/purchases\/requests\/[^/]+$/) && init?.method === 'PATCH') {
      return json({
        ...consolidatedExternalRequest,
        items: consolidatedExternalRequest.items.map((item: any) => ({
          ...item,
          classification: body?.items?.[0]?.classification || item.classification,
          match_status: body?.items?.[0]?.match_status || item.match_status,
        })),
      });
    }
    if (url.match(/\/api\/v1\/purchases\/requests\/[^/]+$/)) {
      return json(consolidatedExternalRequest);
    }
    if (url.match(/\/api\/v1\/purchases\/items\/[^/]+\/options$/) && init?.method === 'POST') {
      return json({
        id: 'manual-option-1',
        purchase_item_id: 'need-external-item-1',
        selected: false,
        availability: true,
        captured_at: new Date().toISOString(),
        ...body,
      }, 201);
    }
    if (url.match(/\/api\/v1\/purchases\/items\/[^/]+\/options\/[^/]+\/select$/) && init?.method === 'POST') {
      return json({
        ...consolidatedExternalRequest.items[0],
        selected_option_id: 'manual-option-1',
        options: [{
          id: 'manual-option-1',
          purchase_item_id: 'need-external-item-1',
          source_type: 'EXTERNAL_MARKET',
          store_name: 'Loja teste',
          title: 'Memoria RAM DDR4 16GB',
          unit_price: 220,
          shipping_price: 20,
          total_price: 240,
          availability: true,
          selected: true,
        }],
      });
    }
    if (url.includes('/api/v1/purchases/needs') && init?.method === 'POST') {
      return json({
        ...consolidatedExternalRequest,
        id: 'need-created-1',
        title: body?.title || 'Memoria RAM DDR4',
        items: (body?.items || []).map((item: any, index: number) => ({
          ...consolidatedExternalRequest.items[0],
          ...item,
          id: `created-item-${index}`,
          purchase_request_id: 'need-created-1',
          description: item.free_text_description,
        })),
      });
    }
    if (url.includes('/api/v1/purchases/needs')) {
      const query = url.includes('?') ? new URLSearchParams(url.split('?')[1]) : new URLSearchParams();
      const filter = query.get('queue_filter') || 'all';
      return json(consolidatedQueues[filter] || []);
    }
    return json({});
  });

  vi.stubGlobal('fetch', fetchMock);
  return { calls, fetchMock };
}

async function waitForConsolidatedCentral() {
  await screen.findByRole('heading', { name: 'Compras' }, { timeout: 5000 });
  await screen.findByText('Central inteligente para pesquisar, comparar, aprovar e acompanhar compras.');
  await waitFor(() => expect(screen.getAllByText('Memoria RAM DDR4').length).toBeGreaterThan(0));
}

async function openConsolidatedNewPurchase() {
  fireEvent.click(await screen.findByRole('button', { name: /Nova compra/i }));
  return screen.findByLabelText(/O que voc/i);
}

describe('PurchasesPage - Central de Compras consolidada', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState({}, '', '/purchases');
  });

  it('renderiza indicadores da Central e remove abas antigas do fluxo principal', async () => {
    installConsolidatedFetchMock();
    render(<PurchasesPage />);

    await waitForConsolidatedCentral();

    expect(screen.getByRole('button', { name: /Precisa da sua aten/i })).toHaveTextContent('2');
    expect(screen.getByRole('button', { name: /Aguardando fornecedores/i })).toHaveTextContent('1');
    expect(screen.getByRole('button', { name: /Aguardando aprova/i })).toHaveTextContent('1');
    expect(screen.getByRole('button', { name: /Prontas para comprar/i })).toHaveTextContent('1');
    expect(screen.getByRole('button', { name: /Entregas pendentes/i })).toHaveTextContent('0');

    expect(document.getElementById('tab-requests')).not.toBeInTheDocument();
    expect(document.getElementById('tab-product-prices')).not.toBeInTheDocument();
    expect(screen.queryByText('Produtos e Precos')).not.toBeInTheDocument();
    expect(screen.queryByText('Conferencia da Planilha')).not.toBeInTheDocument();
  });

  it('usa filtro real do backend ao clicar nos indicadores', async () => {
    const { fetchMock } = installConsolidatedFetchMock();
    render(<PurchasesPage />);

    await waitForConsolidatedCentral();
    fireEvent.click(screen.getByRole('button', { name: /Aguardando aprova/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/purchases/needs?queue_filter=approval'),
        expect.any(Object),
      );
    });
    await waitFor(() => expect(screen.getAllByText('Memoria RAM DDR4').length).toBeGreaterThan(0));
  });

  it('classifica Memoria RAM DDR4 como compra externa sem vincular a Arame', async () => {
    installConsolidatedFetchMock();
    render(<PurchasesPage />);

    await waitForConsolidatedCentral();
    const textarea = await openConsolidatedNewPurchase();
    fireEvent.change(textarea, { target: { value: 'Memoria RAM DDR4' } });
    fireEvent.click(screen.getByRole('button', { name: /Analisar antes de criar/i }));

    expect((await screen.findAllByText(/Compra externa/i)).length).toBeGreaterThan(0);
    expect(screen.getByText(/Nenhum item interno compativel foi encontrado/i)).toBeInTheDocument();
    expect(screen.queryByText(/Arame BTC CL 1,5 mm/i)).not.toBeInTheDocument();
  });

  it('classifica Arame BTC CL 1,5 mm como item interno com match forte', async () => {
    installConsolidatedFetchMock();
    render(<PurchasesPage />);

    await waitForConsolidatedCentral();
    const textarea = await openConsolidatedNewPurchase();
    fireEvent.change(textarea, { target: { value: 'Arame BTC CL 1,5 mm' } });
    fireEvent.click(screen.getByRole('button', { name: /Analisar antes de criar/i }));

    expect((await screen.findAllByText(/Item do Estoque/i)).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Arame BTC CL 1,5 mm').length).toBeGreaterThan(0);
    expect(screen.getByText(/Item interno encontrado no Estoque/i)).toBeInTheDocument();
  });

  it('envia aprovacao opcional por item ao criar compra inteligente', async () => {
    const { calls } = installConsolidatedFetchMock();
    render(<PurchasesPage />);

    await waitForConsolidatedCentral();
    const textarea = await openConsolidatedNewPurchase();
    fireEvent.change(textarea, { target: { value: 'Memoria RAM DDR4' } });
    fireEvent.click(screen.getByRole('button', { name: /Analisar antes de criar/i }));

    const checkbox = await screen.findByLabelText(/Pedir aprov/i);
    fireEvent.click(checkbox);
    fireEvent.click(screen.getByRole('button', { name: /Criar compra/i }));

    await waitFor(() => {
      const createCall = calls.find(call => call.url.endsWith('/api/v1/purchases/needs') && call.init?.method === 'POST');
      expect(createCall?.body?.title).toBe('Memoria RAM DDR4');
      expect(createCall?.body?.items?.[0]?.classification).toBe('EXTERNAL');
      expect(createCall?.body?.items?.[0]?.requires_approval).toBe(true);
    });
  });

  it('recupera compra criada quando o submit sofre erro de rede apos persistir', async () => {
    const { calls, fetchMock } = installConsolidatedFetchMock();
    let failCreateOnce = true;
    const resilientFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
      const body = init?.body ? JSON.parse(init.body as string) : undefined;
      if (url.endsWith('/api/v1/purchases/needs') && init?.method === 'POST' && failCreateOnce) {
        failCreateOnce = false;
        calls.push({ url, init, body });
        throw new TypeError('network down after commit');
      }
      if (url.includes('/api/v1/purchases/requests/by-idempotency/')) {
        calls.push({ url, init, body });
        return new Response(JSON.stringify({
          status: 'completed',
          request: {
            ...consolidatedExternalRequest,
            id: 'need-created-after-timeout',
            title: body?.title || 'Memoria RAM DDR4',
          },
          error_message: null,
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return fetchMock(input, init);
    });
    vi.stubGlobal('fetch', resilientFetch);
    render(<PurchasesPage />);

    await waitForConsolidatedCentral();
    const textarea = await openConsolidatedNewPurchase();
    fireEvent.change(textarea, { target: { value: 'Memoria RAM DDR4' } });
    fireEvent.click(screen.getByRole('button', { name: /Analisar antes de criar/i }));
    await screen.findAllByText(/Compra externa/i);
    fireEvent.click(screen.getByRole('button', { name: /Criar compra/i }));

    await waitFor(() => {
      expect(calls.some(call => call.url.includes('/api/v1/purchases/requests/by-idempotency/'))).toBe(true);
      expect(screen.getByText(/Compra inteligente criada com sucesso/i)).toBeInTheDocument();
    });
    expect(document.body.textContent || '').not.toMatch(/Erro ao criar compra inteligente/i);
  });

  it('mostra mensagem humana quando pesquisa externa automatica nao esta configurada', async () => {
    installConsolidatedFetchMock();
    render(<PurchasesPage />);

    await waitForConsolidatedCentral();
    fireEvent.click(screen.getAllByText('Memoria RAM DDR4')[0].closest('button') as HTMLButtonElement);
    fireEvent.click(await screen.findByRole('button', { name: 'Pesquisar' }));
    const input = await screen.findByPlaceholderText(/memoria ram/i);
    fireEvent.change(input, { target: { value: 'Memoria RAM DDR4' } });
    fireEvent.click(screen.getByRole('button', { name: /Buscar online/i }));

    expect((await screen.findAllByText(/Pesquisa automatica de mercado ainda nao esta configurada/i)).length).toBeGreaterThan(0);
    expect(document.body.textContent || '').not.toMatch(/SERPAPI|API_KEY|provider|missing_keys/i);
  });

  it('abre compra exata por deep link de request', async () => {
    const { fetchMock } = installConsolidatedFetchMock();
    window.history.replaceState({}, '', '/purchases?request=need-external-1');
    render(<PurchasesPage />);

    await waitFor(() => expect(screen.getAllByText(/Analisar opções externas/i).length).toBeGreaterThan(0));
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/purchases/requests/need-external-1'),
      );
    });
  });

  it('permite cadastrar opcao externa manual sem pesquisa automatica', async () => {
    const { calls } = installConsolidatedFetchMock();
    render(<PurchasesPage />);

    await waitForConsolidatedCentral();
    fireEvent.click(screen.getAllByText('Memoria RAM DDR4')[0].closest('button') as HTMLButtonElement);
    fireEvent.click(await screen.findByRole('button', { name: 'Pesquisar' }));

    const storeInput = await screen.findByPlaceholderText('Loja ou fornecedor');
    const titleInput = screen.getByPlaceholderText('Produto ofertado');
    const priceInput = screen.getByPlaceholderText('Preco');
    const shippingInput = screen.getByPlaceholderText('Frete');
    await userEvent.type(storeInput, 'Loja teste');
    await userEvent.type(titleInput, 'Memoria RAM DDR4 16GB');
    await userEvent.type(priceInput, '220');
    await userEvent.type(shippingInput, '20');
    fireEvent.click(screen.getByRole('button', { name: /Salvar opcao/i }));

    await waitFor(() => {
      const createOption = calls.find(call => /\/api\/v1\/purchases\/items\/[^/]+\/options$/.test(call.url) && call.init?.method === 'POST');
      expect(createOption?.body?.store_name).toBe('Loja teste');
      expect(createOption?.body?.total_price).toBe(240);
    });
  });

  it('mantem texto legivel e sem termos tecnicos no fluxo comum', async () => {
    installConsolidatedFetchMock();
    render(<PurchasesPage />);

    await waitForConsolidatedCentral();
    const text = document.body.textContent || '';

    expect(text).not.toMatch(/[ÃÂ�]/);
    expect(text).not.toMatch(/payload|event_log|ActionIntent|dedup|UUID|source_sheet/i);
    expect(text).toContain('Prontas para comprar');
  });
});
