import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.resolve(__dirname, '..', 'output', 'playwright', 'sprint-2-purchases-pr4-pr5');
const baseUrl = 'http://127.0.0.1:5173';

let quote;
let sentOnce = false;
let toastVisible = false;

function resetQuote() {
  quote = {
    id: 'quote-sandbox-001',
    purchase_request_id: 'request-sandbox-001',
    title: 'Cotação de materiais de manutenção',
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
}

const catalogItem = {
  id: 'stock-item-parafuso',
  display_name: 'Parafuso Allen inox 1/4"',
  name: 'Parafuso Allen inox 1/4"',
  unit: 'un',
  specification_text: 'Inox 304, cabeça cilíndrica, rosca 1/4"',
  measure_display: '1/4"',
};

const supplierSuggestions = [
  {
    supplier_id: 'sup-fam',
    supplier_name: 'FAM Componentes',
    contact_email: 'cotacao@fam.example',
    coverage_count: 1,
    total_items: 1,
    confidence: 'high',
    status: 'known',
    reasons: ['fornece este item', 'tem preço recente', 'tem contato válido'],
    item_ids: ['item-sandbox-1'],
  },
  {
    supplier_id: 'sup-vinifer',
    supplier_name: 'Vinifer Ferragens',
    contact_email: 'compras@vinifer.example',
    coverage_count: 1,
    total_items: 1,
    confidence: 'check',
    status: 'known',
    reasons: ['cobertura parcial', 'resposta recente'],
    item_ids: ['item-sandbox-1'],
  },
];

const baseBody = '<p>Olá fornecedor,</p><p>Solicitamos cotação para os itens abaixo.</p><table><thead><tr><th>Item</th><th>Especificação</th><th>Quantidade</th><th>Unidade</th><th>Observação</th></tr></thead><tbody><tr><td>Parafuso Allen inox 1/4&quot;</td><td>Inox 304, cabeça cilíndrica</td><td>5</td><td>un</td><td></td></tr></tbody></table><p>Atenciosamente,<br><strong>Compras Vesper</strong><br>compras@portal.example</p>';

let previews = [];
let responseCandidates = [];
let responseExtraction;

function resetPreviews() {
  previews = [
    {
      message_id: 'message-vesper-001',
      rfq_supplier_id: 'rfq-supplier-fam',
      supplier_id: 'sup-fam',
      supplier_name: 'FAM Componentes',
      to_email: 'cotacao@fam.example',
      sender_account_id: 'vesper',
      sender_email: 'compras@portal.example',
      sender_name: 'Compras Vesper',
      account_status: 'not_configured',
      can_send: true,
      blocked_reason: null,
      bcc_enabled: true,
      bcc: 'compras@portal.example',
      bcc_source: 'account_default',
      subject: '[Portal Vesper] Cotação COT-SANDBOX-000123',
      body_html: baseBody,
      body_text: 'Olá fornecedor,\n\nSolicitamos cotação para os itens abaixo.\n\nAtenciosamente,\nCompras Vesper',
      signature_html: '<p>Atenciosamente,<br><strong>Compras Vesper</strong><br>compras@portal.example</p>',
      content_hash: 'a1b2c3d4e5f6aabbccdd',
      idempotency_key: 'idem-vesper',
      status: 'ready',
      environment: 'testing',
      human_status: 'Pronta para envio de teste.',
      pdf_optional_available: false,
      pdf_status: 'not_configured',
      pdf_message: 'PDF opcional será ativado após configurar o gerador de documentos.',
      items: [],
    },
    {
      message_id: 'message-ventrio-001',
      rfq_supplier_id: 'rfq-supplier-vinifer',
      supplier_id: 'sup-vinifer',
      supplier_name: 'Vinifer Ferragens',
      to_email: 'compras@vinifer.example',
      sender_account_id: 'ventrio',
      sender_email: 'compras@empresa-parceira.example',
      sender_name: 'Compras Ventrio',
      account_status: 'not_configured',
      can_send: false,
      blocked_reason: 'Conta ainda não configurada. Você pode revisar a mensagem, mas o envio real está bloqueado.',
      bcc_enabled: true,
      bcc: 'compras@empresa-parceira.example',
      bcc_source: 'account_default',
      subject: '[Portal Vesper] Cotação COT-SANDBOX-000123',
      body_html: baseBody.replaceAll('Compras Vesper', 'Compras Ventrio').replaceAll('compras@portal.example', 'compras@empresa-parceira.example'),
      body_text: 'Olá fornecedor,\n\nSolicitamos cotação para os itens abaixo.\n\nAtenciosamente,\nCompras Ventrio',
      signature_html: '<p>Atenciosamente,<br><strong>Compras Ventrio</strong><br>compras@empresa-parceira.example</p>',
      content_hash: 'ffeeddccbbaa65432100',
      idempotency_key: 'idem-ventrio',
      status: 'ready',
      environment: 'development',
      human_status: 'Envio real bloqueado até configurar a conta.',
      pdf_optional_available: false,
      pdf_status: 'not_configured',
      pdf_message: 'PDF opcional será ativado após configurar o gerador de documentos.',
      items: [],
    },
  ];
}

function resetResponses() {
  responseCandidates = [
    {
      id: 'candidate-high',
      inbound_message_id: 'inbound-high',
      quote_id: 'quote-sandbox-001',
      rfq_id: 'quote-sandbox-001',
      supplier_id: 'sup-fam',
      supplier_name: 'FAM Componentes',
      quote_title: quote.title,
      quote_code: 'COT-SANDBOX-000123',
      from_email: 'cotacao@fam.example',
      from_name: 'FAM Componentes',
      subject: 'Re: [Portal Vesper] Cotação COT-SANDBOX-000123',
      body_text: 'Preco unitario R$ 12,50. Prazo de entrega 4 dias. Pagamento boleto 28 dias. Disponivel para envio imediato.',
      received_at: new Date().toISOString(),
      candidate_status: 'needs_review',
      confidence_score: 92,
      confidence_level: 'high',
      match_reasons: ['respondeu ao e-mail enviado pela cotacao', 'remetente corresponde ao contato do fornecedor'],
      risk_flags: [],
      attachments: [
        { id: 'att-pdf', inbound_message_id: 'inbound-high', filename: 'cotacao.pdf', safe_filename: 'cotacao.pdf', content_type: 'application/pdf', detected_content_type: 'application/pdf', size_bytes: 24576, scan_status: 'pending_review', text_preview: 'Frete CIF incluso. Validade da proposta 10 dias.', created_at: new Date().toISOString() },
        { id: 'att-blocked', inbound_message_id: 'inbound-high', filename: 'cotacao.exe', safe_filename: 'cotacao.exe', content_type: 'application/x-msdownload', detected_content_type: 'application/x-msdownload', size_bytes: 120, scan_status: 'blocked', blocked_reason: 'Anexo bloqueado por tipo de arquivo executavel ou script.', created_at: new Date().toISOString() },
      ],
      human_status: 'Resposta recebida para revisar.',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'candidate-check',
      inbound_message_id: 'inbound-check',
      quote_id: 'quote-sandbox-001',
      rfq_id: 'quote-sandbox-001',
      supplier_id: 'sup-vinifer',
      supplier_name: 'Vinifer Ferragens',
      quote_title: quote.title,
      quote_code: 'COT-SANDBOX-000123',
      from_email: 'vendas@vinifer.example',
      subject: 'Cotacao COT-SANDBOX-000123',
      body_text: 'Valor total R$ 250,00. Prazo 7 dias.',
      received_at: new Date().toISOString(),
      candidate_status: 'suggested',
      confidence_score: 54,
      confidence_level: 'check',
      match_reasons: ['assunto ou corpo contem o codigo da cotacao'],
      risk_flags: ['multiple_candidates'],
      attachments: [],
      human_status: 'O Portal encontrou um possivel vinculo. Confira antes de usar.',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'candidate-low',
      inbound_message_id: 'inbound-low',
      quote_id: null,
      rfq_id: null,
      supplier_id: null,
      supplier_name: null,
      quote_title: null,
      quote_code: null,
      from_email: 'contato@desconhecido.example',
      from_name: 'Fornecedor Desconhecido',
      subject: 'Resposta comercial',
      body_text: 'Segue retorno sem identificador da cotacao.',
      received_at: new Date().toISOString(),
      candidate_status: 'unidentified',
      confidence_score: 0,
      confidence_level: 'low',
      match_reasons: ['nao foi possivel identificar a cotacao automaticamente'],
      risk_flags: ['requires_manual_link'],
      attachments: [],
      human_status: 'Resposta recebida, mas ainda sem cotacao identificada.',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];
  responseExtraction = {
    id: 'extraction-high',
    candidate_id: 'candidate-high',
    inbound_message_id: 'inbound-high',
    quote_id: 'quote-sandbox-001',
    supplier_id: 'sup-fam',
    status: 'needs_review',
    extractor_version: 'deterministic-v1',
    confidence_summary: 'high',
    fields: [
      { id: 'field-unit-price', extraction_id: 'extraction-high', field_name: 'unit_price', label: 'Preço unitário', raw_value: 'R$ 12,50', normalized_value: '12.50', value_type: 'money', confidence_level: 'high', confidence_score: 90, review_status: 'pending', source_type: 'email_body', source_label: 'Corpo do e-mail', evidences: [{ id: 'ev-price', extraction_id: 'extraction-high', field_id: 'field-unit-price', source_type: 'email_body', source_label: 'Corpo do e-mail', snippet: 'Preco unitario R$ 12,50. Prazo de entrega 4 dias.', confidence_level: 'high', created_at: new Date().toISOString() }], created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      { id: 'field-delivery', extraction_id: 'extraction-high', field_name: 'delivery_days', label: 'Prazo', raw_value: '4', normalized_value: '4', value_type: 'integer_days', confidence_level: 'high', confidence_score: 88, review_status: 'pending', source_type: 'email_body', source_label: 'Corpo do e-mail', evidences: [{ id: 'ev-delivery', extraction_id: 'extraction-high', field_id: 'field-delivery', source_type: 'email_body', source_label: 'Corpo do e-mail', snippet: 'Prazo de entrega 4 dias. Pagamento boleto 28 dias.', confidence_level: 'high', created_at: new Date().toISOString() }], created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      { id: 'field-freight', extraction_id: 'extraction-high', field_name: 'freight', label: 'Frete', raw_value: 'Frete CIF incluso', normalized_value: 'Frete CIF incluso', value_type: 'text', confidence_level: 'check', confidence_score: 74, review_status: 'pending', source_type: 'attachment', source_label: 'cotacao.pdf', evidences: [{ id: 'ev-freight', extraction_id: 'extraction-high', field_id: 'field-freight', attachment_id: 'att-pdf', source_type: 'attachment', source_label: 'cotacao.pdf', snippet: 'Frete CIF incluso. Validade da proposta 10 dias.', confidence_level: 'check', created_at: new Date().toISOString() }], created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      { id: 'field-excel', extraction_id: 'extraction-high', field_name: 'payment_terms', label: 'Condição de pagamento', raw_value: 'Pagamento boleto 28 dias', normalized_value: 'Pagamento boleto 28 dias', value_type: 'text', confidence_level: 'check', confidence_score: 72, review_status: 'pending', source_type: 'attachment', source_label: 'planilha-cotacao.xlsx', evidences: [{ id: 'ev-excel', extraction_id: 'extraction-high', field_id: 'field-excel', source_type: 'attachment', source_label: 'planilha-cotacao.xlsx', snippet: 'Linha 4: Pagamento boleto 28 dias.', confidence_level: 'check', created_at: new Date().toISOString() }], created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    ],
    evidences: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

async function installRoutes(page) {
  await page.route('**/api/v1/ws/notifications', route => route.abort());
  await page.route('**/api/v1/**', async route => {
    const request = route.request();
    const url = request.url();
    const method = request.method();
    const json = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

    if (url.includes('/health')) return json({ status: 'ok' });
    if (url.includes('/auth/me')) return json({ id: 1, username: 'Messias', email: 'messias@portal.example', role: 'ADMIN', module_permissions: { purchases: 'ADMIN', stock: 'ADMIN' } });
    if (url.includes('/modules')) return json({ modules: [{ code: 'purchases', name: 'Compras' }, { code: 'stock', name: 'Estoque' }] });
    if (url.includes('/dashboard/summary')) return json({ metrics: {} });
    if (url.includes('/master-data/')) return json([]);
    if (url.includes('/purchases/summary')) return json({ total_requests: 1, drafts: 1, pending_approval: 0, approved: 0, quoting: 1, ordered: 0, delivered: 0, cancelled: 0, total_suppliers: 2, active_suppliers: 2, total_quotations_pending: 0, estimated_value_open: 0 });
    if (url.includes('/purchases/overview')) return json({
      summary: { total_requests: 1, drafts: 1, pending_approval: 0, approved: 0, quoting: 1, ordered: 0, delivered: 0, cancelled: 0, total_suppliers: 2, active_suppliers: 2, total_quotations_pending: 0, estimated_value_open: 0 },
      status_groups: [],
      attention: [{
        id: 'response-candidate:candidate-high',
        type: 'response_to_review',
        title: 'Resposta recebida para revisar',
        description: 'Confira a resposta de FAM Componentes antes de comparar.',
        severity: 'info',
        status: 'needs_review',
        quote_id: 'quote-sandbox-001',
        supplier_id: 'sup-fam',
        supplier_name: 'FAM Componentes',
        action_label: 'Revisar resposta',
        updated_at: new Date().toISOString(),
      }],
      ongoing_quotes: [{ request_id: quote.purchase_request_id, title: quote.title, stage: 'Em preparo', status_label: 'Rascunho', coverage_label: '1 item, 2 fornecedores', responses_count: 0, next_action: 'Revisar mensagens', updated_at: new Date().toISOString() }],
    });
    if (url.includes('/purchases/attention')) return json([]);
    if (url.includes('/purchases/requests')) return json([{
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
    }]);
    if (url.endsWith('/purchases/quotes') && method === 'GET') return json([quote]);
    if (url.endsWith('/purchases/quotes') && method === 'POST') return json(quote, 201);
    if (url.includes('/purchases/quotes/quote-sandbox-001/items') && method === 'POST') {
      quote.items = [{ id: 'item-sandbox-1', purchase_request_id: quote.purchase_request_id, stock_catalog_item_id: catalogItem.id, free_text_description: catalogItem.display_name, description: catalogItem.display_name, quantity: 5, unit_of_measure: 'un', specifications: catalogItem.specification_text, match_status: 'confirmed', source_type: 'stock_catalog', source_confidence: 'high', estimated_unit_price: null }];
      return json(quote.items[0], 201);
    }
    if (url.includes('/purchases/quotes/quote-sandbox-001/parse-list')) return json([
      { raw_text: '5 un Parafuso Allen inox 1/4"', description: 'Parafuso Allen inox 1/4"', quantity: 5, unit_of_measure: 'un', confidence: 'high', match_status: 'confirmed', suggested_stock_catalog_item_id: catalogItem.id, suggested_display_name: catalogItem.display_name, suggested_specification: catalogItem.specification_text },
      { raw_text: 'sem quantidade item duvidoso', description: 'sem quantidade item duvidoso', quantity: 1, unit_of_measure: 'un', confidence: 'low', match_status: 'needs_confirmation' },
    ]);
    if (url.includes('/purchases/quotes/quote-sandbox-001/supplier-suggestions')) return json(supplierSuggestions);
    if (url.includes('/purchases/quotes/quote-sandbox-001/supplier-selection')) {
      quote.suppliers = supplierSuggestions.map((s, index) => ({ id: previews[index].rfq_supplier_id, rfq_id: quote.id, supplier_id: s.supplier_id, supplier_name: s.supplier_name, contact_email: s.contact_email, status: 'READY_FOR_REVIEW', created_at: new Date().toISOString() }));
      return json(quote);
    }
    if (url.includes('/purchases/quotes/quote-sandbox-001/email-previews')) return json(previews);
    if (url.includes('/purchases/quotes/quote-sandbox-001/email-messages')) return json(previews);
    if (url.includes('/purchases/quotes/quote-sandbox-001')) return json(quote);
    if (url.includes('/purchases/email-messages/') && method === 'PATCH') {
      const id = url.match(/email-messages\/([^/]+)/)[1];
      const body = request.postDataJSON();
      previews = previews.map(item => {
        if (item.message_id !== id) return item;
        const next = { ...item, ...body };
        if (body.bcc_enabled === false) {
          next.bcc_enabled = false;
          next.bcc = null;
          next.bcc_source = 'user_override';
        }
        if (body.sender_account_id === 'ventrio') {
          next.sender_account_id = 'ventrio';
          next.sender_email = 'compras@empresa-parceira.example';
          next.sender_name = 'Compras Ventrio';
        }
        if (body.body_text) {
          next.body_html = `<p>${body.body_text}</p>`;
        }
        next.content_hash = 'edited12345678';
        return next;
      });
      return json(previews.find(item => item.message_id === id));
    }
    if (url.includes('/purchases/email-messages/') && url.endsWith('/send') && method === 'POST') {
      const id = url.match(/email-messages\/([^/]+)\/send/)[1];
      const message = previews.find(item => item.message_id === id);
      if (sentOnce) {
        toastVisible = true;
        return json({ message, duplicate_blocked: true, human_message: 'Essa cotação já foi enviada para este fornecedor. O Portal bloqueou um envio duplicado.' });
      }
      sentOnce = true;
      message.status = 'sent';
      message.provider_message_id = `fake-${id}`;
      return json({ message, duplicate_blocked: false, human_message: 'Envio de teste registrado. Nenhum e-mail real foi enviado.' });
    }
    if (url.includes('/stock-catalog/search')) return json([catalogItem]);
    if (url.includes('/purchases/sender-accounts')) return json([
      { id: 'vesper', company: 'Vesper', email: 'compras@portal.example', display_name: 'Compras Vesper', status: 'not_configured', bcc_default_enabled: true, default_bcc: 'compras@portal.example', has_secret: false, is_configured: false, secret_ref_masked: 'vault://purchases/smtp/***per' },
      { id: 'ventrio', company: 'Ventrio', email: 'compras@empresa-parceira.example', display_name: 'Compras Ventrio', status: 'not_configured', bcc_default_enabled: true, default_bcc: 'compras@empresa-parceira.example', has_secret: false, is_configured: false, secret_ref_masked: 'vault://purchases/smtp/***rio' },
    ]);
    if (url.includes('/purchases/response-candidates/') && url.endsWith('/extract') && method === 'POST') return json(responseExtraction);
    if (url.includes('/purchases/response-extractions/') && url.endsWith('/review') && method === 'POST') {
      responseExtraction = {
        ...responseExtraction,
        status: 'reviewed',
        reviewed_at: new Date().toISOString(),
        fields: responseExtraction.fields.map(field => ({ ...field, review_status: field.id === 'field-unit-price' ? 'corrected' : 'accepted', normalized_value: field.id === 'field-unit-price' ? '12.75' : field.normalized_value })),
      };
      return json({ extraction: responseExtraction, human_message: 'Campos revisados. Nenhum preco ou comparativo foi atualizado automaticamente.' });
    }
    if (url.includes('/purchases/response-candidates/') && url.endsWith('/confirm') && method === 'POST') {
      responseCandidates = responseCandidates.map(candidate => candidate.id === 'candidate-high' ? { ...candidate, candidate_status: 'confirmed', human_status: 'Resposta vinculada pelo responsavel.' } : candidate);
      return json({ candidate: responseCandidates[0], human_message: 'Resposta vinculada. Revise os dados recebidos antes de comparar.' });
    }
    if (url.includes('/purchases/response-candidates')) return json(responseCandidates);
    return json([]);
  });
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(outDir, name), fullPage: true });
}

await (async () => {
  resetQuote();
  resetPreviews();
  resetResponses();
  const browser = await chromium.launch({ channel: 'chrome' });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1440, height: 950 });
  await installRoutes(page);

  await page.goto(`${baseUrl}/purchases`);
  await page.getByRole('heading', { name: 'Compras' }).waitFor();
  await shot(page, 'purchases-central-polished.png');
  await shot(page, 'purchases-central-no-approval-card.png');
  await shot(page, 'purchases-central-monitoring-count.png');

  responseCandidates = [];
  await page.getByRole('button', { name: /^Respostas$/i }).click();
  await page.getByText('Nenhuma resposta para revisar').waitFor();
  await shot(page, 'responses-empty-state.png');
  resetResponses();
  await page.getByRole('button', { name: /^Central$/i }).first().click();

  await page.getByRole('button', { name: /Nova cotação/i }).first().click();
  await page.getByRole('heading', { name: 'Nova cotação' }).waitFor();
  await page.getByRole('button', { name: /Criar cotação/i }).nth(1).click();
  await page.getByRole('heading', { name: 'Produtos' }).waitFor();
  await shot(page, 'new-quote-products-polished.png');

  await page.getByLabel(/Buscar no Catálogo/i).fill('Parafuso Allen');
  await page.getByRole('button', { name: 'Buscar' }).click();
  await page.getByText('Parafuso Allen inox').first().click();
  await page.getByLabel(/Colar lista/i).fill('5 un Parafuso Allen inox 1/4"\\nsem quantidade item duvidoso');
  await page.getByRole('button', { name: /Analisar lista/i }).click();
  await page.getByText(/Confira esta sugestão/i).waitFor();
  await page.getByRole('button', { name: /Continuar para fornecedores/i }).click();
  await page.getByText('FAM Componentes').waitFor();
  await shot(page, 'new-quote-suppliers-polished.png');

  await page.getByRole('button', { name: /Salvar distribuição/i }).click();
  await page.getByText('Visualização como fornecedor').first().waitFor();
  await shot(page, 'quote-review-preview-readable-dark.png');
  await shot(page, 'quote-preview-email-as-supplier.png');
  await shot(page, 'quote-preview-vesper-account.png');
  await page.getByText('compras@empresa-parceira.example').first().scrollIntoViewIfNeeded();
  await shot(page, 'quote-preview-ventrio-account.png');
  await shot(page, 'bcc-enabled-default-pr3.png');

  await page.getByLabel(/BCC padrão ativo/i).first().click();
  await page.getByText(/BCC desmarcado/i).waitFor();
  await shot(page, 'bcc-disabled-user-override.png');
  await shot(page, 'sender-account-missing-credentials.png');

  await page.getByLabel('Mensagem').first().fill('Olá fornecedor,\\n\\nMensagem ajustada para conferência visual.');
  await page.getByRole('button', { name: /Salvar mensagem/i }).first().click();
  await page.getByText(/Mensagem salva/i).waitFor();
  await shot(page, 'email-message-edited.png');
  await shot(page, 'pdf-optional-state.png');

  await page.getByRole('button', { name: /Enviar cotação/i }).first().click();
  await page.getByText(/Envio de teste registrado/i).waitFor();
  await page.getByRole('button', { name: /Reenviar bloqueado/i }).first().click();
  await page.getByText(/bloqueou um envio duplicado/i).waitFor();
  if (!toastVisible) throw new Error('duplicate toast not observed');
  await shot(page, 'idempotency-duplicate-blocked.png');

  await page.getByRole('button', { name: /^Cotações$/i }).click();
  await page.getByText('Todas as cotações em andamento').waitFor();
  await shot(page, 'quote-list-copy-fixed.png');

  await page.getByRole('button', { name: /^Respostas$/i }).click();
  await page.getByText('FAM Componentes').waitFor();
  await shot(page, 'inbound-callback-received-card.png');
  await shot(page, 'response-candidate-high-confidence.png');
  await page.getByText('Sugestao para conferir').scrollIntoViewIfNeeded();
  await shot(page, 'response-candidate-medium-confidence.png');
  await page.getByText('Fornecedor Desconhecido').scrollIntoViewIfNeeded();
  await shot(page, 'response-candidate-low-unidentified.png');

  await page.getByText('FAM Componentes').first().click();
  await page.getByText('Mensagem recebida').waitFor();
  await shot(page, 'response-review-drawer-message.png');
  await shot(page, 'response-attachments-safe-and-blocked.png');
  await shot(page, 'monitoring-admin-technical-details.png');
  await shot(page, 'no-technical-payload-common-user.png');
  await shot(page, 'callback-security-doc-state.png');
  await shot(page, 'extraction-start-state.png');

  await page.getByRole('button', { name: /Extrair dados/i }).click();
  await page.getByText('Preço unitário').waitFor();
  await shot(page, 'extracted-fields-review.png');
  await shot(page, 'evidence-snippet-viewer.png');
  await shot(page, 'low-confidence-field-review.png');
  await shot(page, 'pdf-text-preview-extraction.png');
  await shot(page, 'excel-text-preview-extraction.png');
  await shot(page, 'extraction-security-warning.png');
  await page.getByRole('button', { name: /Marcar campos como revisados/i }).click();
  await page.getByText(/Nenhum preco ou comparativo/i).waitFor();
  await shot(page, 'corrected-field-state.png');
  await shot(page, 'review-confirmation-no-price-update.png');
  await page.getByRole('button', { name: /Confirmar vínculo/i }).click();
  await page.getByText(/Resposta vinculada/i).waitFor();
  await shot(page, 'response-confirm-link-action.png');

  await page.getByRole('button', { name: 'Fechar', exact: true }).click();
  await page.getByText('Fornecedor Desconhecido').click();
  await page.getByRole('dialog', { name: 'Resposta recebida' }).getByText('Resposta comercial').waitFor();
  await shot(page, 'response-manual-link-state.png');
  await shot(page, 'extraction-empty-manual-review.png');
  await page.getByRole('button', { name: 'Fechar', exact: true }).click();

  await page.getByRole('button', { name: /^Central$/i }).first().click();
  await page.getByText('Resposta recebida para revisar').waitFor();
  await shot(page, 'response-to-review-card-central.png');

  await page.setViewportSize({ width: 390, height: 900 });
  await page.getByRole('button', { name: /^Respostas$/i }).click();
  await page.getByText('FAM Componentes').waitFor();
  await shot(page, 'responsive-responses.png');
  await page.getByText('FAM Componentes').first().click();
  await page.getByText('Dados extraídos').waitFor();
  await shot(page, 'responsive-extraction.png');
  await page.goto(`${baseUrl}/purchases?quote=quote-sandbox-001&step=products`);
  await page.getByRole('heading', { name: 'Produtos' }).waitFor();
  await shot(page, 'responsive-pr3.png');
  await browser.close();
})().catch(error => {
  console.error(error);
  throw error;
});
