const { chromium } = require('playwright');
const path = require('path');

const outDir = path.resolve(__dirname, '..', 'output', 'playwright', 'sprint-2-purchases-pr2');
const baseUrl = 'http://127.0.0.1:5177';

let quote;

const resetQuote = () => {
  quote = {
    id: 'rfq-pr2-demo',
    purchase_request_id: 'req-pr2-demo',
    title: 'Cotacao de materiais de manutencao',
    description: 'Fixture sanitizada para QA visual',
    status: 'DRAFT',
    origin_type: 'manual',
    origin_ref_id: null,
    origin_snapshot_json: null,
    items: [],
    suppliers: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
};

const catalogItem = {
  id: 'stock-item-parafuso',
  display_name: 'Parafuso Allen inox 1/4"',
  name: 'Parafuso Allen inox 1/4"',
  unit: 'un',
  specification_text: 'Inox 304, cabeca cilindrica, rosca 1/4"',
  measure_display: '1/4"',
  primary_price: 12.5,
};

const suppliers = [
  { supplier_id: 'sup-fam', supplier_name: 'FAM Componentes', contact_email: 'cotacao@fam.example', coverage_count: 1, total_items: 1, confidence: 'high', status: 'known', reasons: ['fornece este item', 'tem preco recente', 'tem contato valido'], item_ids: ['item-pr2-1'] },
  { supplier_id: 'sup-vinifer', supplier_name: 'Vinifer Ferragens', contact_email: 'compras@vinifer.example', coverage_count: 1, total_items: 1, confidence: 'check', status: 'known', reasons: ['cobertura parcial', 'resposta recente'], item_ids: ['item-pr2-1'] },
];

const previews = [
  { rfq_supplier_id: 'rfq-supplier-fam', supplier_id: 'sup-fam', supplier_name: 'FAM Componentes', to_email: 'cotacao@fam.example', sender_account_id: 'vesper', sender_email: 'compras@portal.example', bcc_enabled: true, bcc: 'compras@portal.example', subject: '[Portal Vesper] Cotacao PR2 rfq-pr2-demo', body_html: '<p>Prezados, solicitamos cotacao dos itens abaixo.</p><table><thead><tr><th>Item</th><th>Especificacao</th><th>Qtd</th><th>Un</th></tr></thead><tbody><tr><td>Parafuso Allen inox 1/4&quot;</td><td>Inox 304, cabeca cilindrica</td><td>5</td><td>un</td></tr></tbody></table><p>Atenciosamente,<br>Compras Vesper</p>', content_hash: 'a1b2c3d4e5f6aabbccdd', status: 'READY_FOR_SEND', items: [] },
  { rfq_supplier_id: 'rfq-supplier-vinifer', supplier_id: 'sup-vinifer', supplier_name: 'Vinifer Ferragens', to_email: 'compras@vinifer.example', sender_account_id: 'ventrio', sender_email: 'compras@empresa-parceira.example', bcc_enabled: true, bcc: 'compras@empresa-parceira.example', subject: '[Portal Ventrio] Cotacao PR2 rfq-pr2-demo', body_html: '<p>Prezados, solicitamos cotacao dos itens abaixo.</p><table><thead><tr><th>Item</th><th>Especificacao</th><th>Qtd</th><th>Un</th></tr></thead><tbody><tr><td>Parafuso Allen inox 1/4&quot;</td><td>Inox 304, cabeca cilindrica</td><td>5</td><td>un</td></tr></tbody></table><p>Atenciosamente,<br>Compras Ventrio</p>', content_hash: 'ffeeddccbbaa65432100', status: 'READY_FOR_SEND', items: [] },
];

async function installRoutes(page) {
  await page.route('**/api/v1/ws/notifications', route => route.abort());
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = request.url();
    const method = request.method();
    const json = body => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });

    if (url.includes('/health')) return json({ status: 'ok' });
    if (url.includes('/auth/me')) return json({ id: 1, username: 'Messias', email: 'messias@portal.example', role: 'ADMIN', module_permissions: { purchases: 'ADMIN', stock: 'ADMIN' } });
    if (url.includes('/modules')) return json({ modules: [{ code: 'purchases', name: 'Compras' }, { code: 'stock', name: 'Estoque' }] });
    if (url.includes('/dashboard/summary')) return json({ metrics: {} });
    if (url.includes('/master-data/')) return json([]);
    if (url.includes('/purchases/summary')) return json({ total_requests: 1, drafts: 1, pending_approval: 0, approved: 0, quoting: 1, ordered: 0, delivered: 0, cancelled: 0, total_suppliers: 2, active_suppliers: 2, total_quotations_pending: 0, estimated_value_open: 0 });
    if (url.includes('/purchases/overview')) return json({
      summary: { total_requests: 1, drafts: 1, pending_approval: 0, approved: 0, quoting: 1, ordered: 0, delivered: 0, cancelled: 0, total_suppliers: 2, active_suppliers: 2, total_quotations_pending: 0, estimated_value_open: 0 },
      status_groups: [
        { key: 'preparation', label: 'Em preparo', count: 1 },
        { key: 'waiting', label: 'Aguardando respostas', count: 1 },
        { key: 'review', label: 'Respostas para revisar', count: 0 },
        { key: 'compare', label: 'Prontas para comparar', count: 0 },
        { key: 'delivery', label: 'Pedidos aguardando entrega', count: 0 },
      ],
      attention: [],
      ongoing_quotes: [{ request_id: 'req-pr2-demo', title: quote.title, stage: 'Em preparacao', status_label: 'Rascunho', coverage_label: '1 item, 2 fornecedores', responses_count: 0, next_action: 'Revisar preview', updated_at: new Date().toISOString() }],
    });
    if (url.includes('/purchases/attention')) return json([]);
    if (url.includes('/purchases/requests')) return json([
      {
        id: quote.purchase_request_id,
        title: quote.title,
        description: quote.description,
        requester_user_id: 1,
        requester_username: 'Messias',
        status: 'RFQ_PREPARING',
        priority: 'NORMAL',
        urgency: 'NORMAL',
        department: 'Compras',
        estimated_total: 0,
        items: quote.items,
        rfqs: [{ id: quote.id, purchase_request_id: quote.purchase_request_id, title: quote.title, status: quote.status, deadline: null, created_by_user_id: 1, created_at: quote.created_at, updated_at: quote.updated_at }],
        created_at: quote.created_at,
        updated_at: quote.updated_at,
      },
    ]);
    if (url.endsWith('/purchases/quotes') && method === 'GET') return json([quote]);
    if (url.endsWith('/purchases/quotes') && method === 'POST') return json(quote);
    if (url.includes('/purchases/quotes/rfq-pr2-demo/items') && method === 'POST') {
      quote.items = [{ id: 'item-pr2-1', purchase_request_id: quote.purchase_request_id, stock_catalog_item_id: catalogItem.id, free_text_description: catalogItem.display_name, description: catalogItem.display_name, quantity: 5, unit_of_measure: 'un', specifications: catalogItem.specification_text, match_status: 'confirmed', source_type: 'stock_catalog', source_confidence: 'high', estimated_unit_price: null }];
      return json(quote.items[0]);
    }
    if (url.includes('/purchases/quotes/rfq-pr2-demo/parse-list')) return json([
      { raw_text: '5 un Parafuso Allen inox 1/4"', description: 'Parafuso Allen inox 1/4"', quantity: 5, unit_of_measure: 'un', confidence: 'high', match_status: 'confirmed', suggested_stock_catalog_item_id: catalogItem.id, suggested_display_name: catalogItem.display_name, suggested_specification: catalogItem.specification_text },
      { raw_text: 'sem quantidade item duvidoso', description: 'sem quantidade item duvidoso', quantity: 1, unit_of_measure: 'un', confidence: 'low', match_status: 'needs_confirmation' },
    ]);
    if (url.includes('/purchases/quotes/rfq-pr2-demo/supplier-suggestions')) return json(suppliers);
    if (url.includes('/purchases/quotes/rfq-pr2-demo/supplier-selection')) {
      quote.suppliers = suppliers.map((s, index) => ({ id: previews[index].rfq_supplier_id, rfq_id: quote.id, supplier_id: s.supplier_id, supplier_name: s.supplier_name, contact_email: s.contact_email, status: 'READY_FOR_REVIEW', created_at: new Date().toISOString() }));
      return json(quote);
    }
    if (url.includes('/purchases/quotes/rfq-pr2-demo/email-previews')) return json(previews);
    if (url.includes('/purchases/quotes/rfq-pr2-demo')) return json(quote);
    if (url.includes('/stock-catalog/search')) return json([catalogItem]);
    if (url.includes('/purchases/sender-accounts')) return json([
      { id: 'vesper', email: 'compras@portal.example', display_name: 'Compras Vesper', bcc_default_enabled: true, default_bcc: 'compras@portal.example', is_configured: false, provider: 'sandbox' },
      { id: 'ventrio', email: 'compras@empresa-parceira.example', display_name: 'Compras Ventrio', bcc_default_enabled: true, default_bcc: 'compras@empresa-parceira.example', is_configured: false, provider: 'sandbox' },
    ]);
    return json([]);
  });
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(outDir, name), fullPage: true });
}

(async () => {
  resetQuote();
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 950 });
  await installRoutes(page);

  await page.goto(`${baseUrl}/purchases`);
  await page.getByRole('heading', { name: 'Compras' }).waitFor();
  await shot(page, 'purchases-central-clean.png');
  await shot(page, 'purchases-central-no-technical-tabs.png');

  await page.getByRole('button', { name: /Nova cotacao/i }).first().click();
  await page.getByRole('heading', { name: 'Nova cotacao' }).waitFor();
  await shot(page, 'new-quote-step-products-empty.png');

  await page.getByRole('button', { name: /Criar cotacao/i }).click();
  await page.getByLabel(/Buscar no Catalogo/i).fill('Parafuso Allen');
  await page.getByRole('button', { name: 'Buscar' }).click();
  await page.getByText('Parafuso Allen inox').first().click();
  await page.getByText('Produto adicionado').waitFor();
  await shot(page, 'new-quote-product-from-catalog.png');

  await page.getByLabel(/Colar lista/i).fill('5 un Parafuso Allen inox 1/4"\\nsem quantidade item duvidoso');
  await shot(page, 'new-quote-pasted-list.png');
  await page.getByRole('button', { name: /Analisar lista/i }).click();
  await page.getByText(/Confira esta sugestao/i).waitFor();
  await shot(page, 'new-quote-pasted-list-review.png');

  await page.getByRole('button', { name: /Continuar para fornecedores/i }).click();
  await page.getByText('FAM Componentes').waitFor();
  await shot(page, 'new-quote-supplier-suggestions.png');
  await shot(page, 'supplier-coverage-details.png');

  await page.getByRole('button', { name: /Salvar distribuicao/i }).click();
  await page.getByText('FAM Componentes').waitFor();
  await shot(page, 'quote-review-preview-list.png');
  await shot(page, 'quote-email-preview-vesper.png');
  await page.getByText('compras@empresa-parceira.example').first().scrollIntoViewIfNeeded();
  await shot(page, 'quote-email-preview-ventrio.png');
  await shot(page, 'bcc-enabled-default.png');
  await shot(page, 'quote-ready-to-send.png');

  await page.getByRole('button', { name: /^Cotacoes$/i }).click();
  await page.getByText('Cotacao de materiais de manutencao').first().waitFor();
  await shot(page, 'quote-created-in-list.png');

  await page.setViewportSize({ width: 390, height: 900 });
  await page.goto(`${baseUrl}/purchases?quote=rfq-pr2-demo&step=products`);
  await page.getByRole('heading', { name: 'Produtos' }).waitFor();
  await shot(page, 'responsive-narrow.png');
  await browser.close();
})().catch(error => {
  console.error(error);
  process.exit(1);
});
