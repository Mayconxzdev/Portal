import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import StockPage from './StockPage';

const adminUser = {
  id: 1,
  username: 'vesper_admin',
  role: 'ADMIN',
  module_permissions: { stock: 'ADMIN' },
};

const commonUser = {
  id: 2,
  username: 'vesper_user',
  role: 'USER',
  module_permissions: { stock: 'READ_ONLY' },
};

const mockSummary = {
  total_items: 120,
  total_suppliers: 10,
  total_offers: 300,
  items_without_cybersul_code: 15,
  items_in_review: 5,
  low_stock_items: 3,
  last_import_at: '2026-06-11T12:00:00Z',
};

const mockImportRuns = [
  {
    id: 'run-1',
    source_type: 'COMPRAS_NOVA',
    source_path: 'C:\\Users\\UsuarioDemo\\Desktop\\Compras Nova .xlsx',
    source_filename: 'Compras Nova .xlsx',
    source_hash: 'hash123',
    status: 'SUCCESS',
    started_at: '2026-06-11T12:00:00Z',
    finished_at: '2026-06-11T12:05:00Z',
    total_rows: 1000,
    total_items: 120,
    total_offers: 300,
    total_errors: 0,
    total_review: 5,
    triggered_by_user_id: 1,
    error_message: null,
  }
];

const mockTreeNodes = [
  {
    id: 'node-sheet-1',
    title: 'Chapa e Tubo Inox',
    label: 'Chapa e Tubo Inox',
    display_label: 'Chapa e Tubo Inox',
    node_type: 'sheet',
    kind: 'sheet',
    sheet: 'Chapa e Tubo Inox',
    path: 'Chapa e Tubo Inox',
    children: [
      {
        id: 'node-family-1',
        title: 'INOX',
        label: 'INOX',
        display_label: 'INOX',
        node_type: 'family',
        kind: 'family',
        sheet: 'Chapa e Tubo Inox',
        path: 'Chapa e Tubo Inox > INOX',
        children: [
          {
            id: 'node-prod-1',
            title: 'Chapa Aço Inox 316 L',
            label: 'Chapa Aço Inox 316 L',
            display_label: 'Chapa Aço Inox 316 L',
            node_type: 'product',
            kind: 'product',
            sheet: 'Chapa e Tubo Inox',
            path: 'Chapa e Tubo Inox > INOX > Chapa Aço Inox 316 L',
            count_variations: 3,
            children: [],
          },
          {
            id: 'node-prod-2',
            title: 'Tubo Aço Inox Redondo 304',
            label: 'Tubo Aço Inox Redondo 304',
            display_label: 'Tubo Aço Inox Redondo 304',
            node_type: 'product',
            kind: 'product',
            sheet: 'Chapa e Tubo Inox',
            path: 'Chapa e Tubo Inox > INOX > Tubo Aço Inox Redondo 304',
            count_variations: 2,
            children: [],
          },
        ],
      },
    ],
  },
  {
    id: 'node-sheet-2',
    title: 'Tubo e Tarugo - Flange',
    label: 'Tubo e Tarugo - Flange',
    display_label: 'Tubo e Tarugo - Flange',
    node_type: 'sheet',
    kind: 'sheet',
    sheet: 'Tubo e Tarugo - Flange',
    path: 'Tubo e Tarugo - Flange',
    children: [],
  },
];

const mockCategoryNodes = mockTreeNodes.map(({ children: _children, ...node }) => ({
  ...node,
  children: [],
}));

const mockChapaFamilies = mockTreeNodes[0].children;

const mockReviewQueue = [
  {
    id: 'rev-1',
    item_id: 'item-3-8',
    item_display_name: 'Tubo Aco Redondo Polido 1020 c/ Costura - 3/8"',
    import_run_id: 'run-1',
    review_type: 'MISSING_EMAIL',
    severity: 'MEDIUM',
    title: 'Revisar item: Tubo Aco Redondo Polido 1020 c/ Costura - 3/8"',
    description: 'Fornecedor sem e-mail cadastrado.',
    raw_context_json: null,
    status: 'PENDING'
  }
];

const mockSearchResults = [
  {
    id: 'item-3-8',
    display_name: 'Tubo Aco Redondo Polido 1020 c/ Costura - 3/8" - (9,53 mm)',
    base_name: 'Tubo Aco Redondo Polido 1020 c/ Costura',
    source_sheet: 'Tubo e Tarugo - Flange',
    variation_label: '3/8"',
    normalized_measure: '9,53 mm',
    specification_text: '9,53 mm',
    internal_code: 'VPC1001',
    needs_review: true,
    review_reason: 'Fornecedor sem e-mail cadastrado.',
    family_path: 'Tubo e Tarugo - Flange > TUBO ACO REDONDO',
    cybersul_code: null,
    cybersul_description: null,
    balance_total: 0,
    last_price: 30.69,
    last_supplier: 'FAM',
    unit: 'm'
  },
  {
    id: 'item-1-1-2',
    display_name: 'Tubo Aco Redondo Polido 1020 c/ Costura - 1.1/2" - (38,1 mm)',
    base_name: 'Tubo Aco Redondo Polido 1020 c/ Costura',
    source_sheet: 'Tubo e Tarugo - Flange',
    variation_label: '1.1/2"',
    normalized_measure: '38,1 mm',
    specification_text: '38,1 mm',
    internal_code: 'VPC1002',
    needs_review: false,
    review_reason: null,
    family_path: 'Tubo e Tarugo - Flange > TUBO ACO REDONDO',
    cybersul_code: 'VPC31016',
    cybersul_description: 'TUBO ACO POLIDO 1020 NBR 8261',
    balance_total: 10,
    last_price: 70.50,
    last_supplier: 'FAM',
    unit: 'm'
  }
];

const mockItemDetails3_8 = {
  id: 'item-3-8',
  display_name: 'Tubo Aco Redondo Polido 1020 c/ Costura - 3/8" - (9,53 mm)',
  base_name: 'Tubo Aco Redondo Polido 1020 c/ Costura',
  variation_label: '3/8"',
  normalized_measure: '9,53 mm',
  specification_text: '9,53 mm',
  internal_code: 'VPC1001',
  source_sheet: 'Tubo e Tarugo - Flange',
  family_path: 'Tubo e Tarugo - Flange > TUBO ACO REDONDO',
  needs_review: true,
  review_reason: 'Fornecedor sem e-mail cadastrado.',
  created_at: '2026-06-11T12:00:00Z',
  updated_at: '2026-06-11T12:00:00Z',
  cybersul_product_id: null,
  cybersul_code: null,
  cybersul_description: null,
  balance_vesper: 0,
  balance_ventrio: 0,
  balance_total: 0,
  cost_price: null,
  ncm: null,
  group_name: null,
  specs: [{ key: 'medida', value: '9,53 mm' }],
  current_price: 30.69,
  current_supplier: 'FAM',
  unit: 'm',
  identity_hash: 'hash_3_8_secret_technical_hash_value',
  source_row: 12
};

const mockItemOffers3_8 = [
  {
    id: 'off-1',
    supplier_id: 'supp-fam',
    supplier_name: 'FAM',
    price: 30.69,
    price_raw: '30.69',
    final_value: 30.69,
    final_value_raw: '30.69',
    currency: 'BRL',
    unit: 'm',
    email: 'compras@fornecedor-alfa.example',
    phone: '1199999999',
    source_sheet: 'Tubo e Tarugo - Flange',
    source_row: 12,
    created_at: '2026-06-11T12:00:00Z'
  }
];

const mockItemHistory3_8 = [
  {
    id: 'hist-1',
    supplier_name: 'FAM',
    old_price: 28.50,
    new_price: 30.69,
    source: 'MANUAL',
    source_reference: 'Portal Vesper UI',
    changed_by: 'vesper_admin',
    changed_at: '2026-06-11T12:00:00Z',
    notes: 'Reajuste anual'
  }
];

function installFetchMock() {
  const fetchMock = vi.fn(async (url: string, init?: any) => {
    if (url.includes('/summary')) {
      return new Response(JSON.stringify(mockSummary), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/import-runs')) {
      return new Response(JSON.stringify(mockImportRuns), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/navigation/categories')) {
      return new Response(JSON.stringify(mockCategoryNodes), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/navigation/families')) {
      return new Response(JSON.stringify(mockChapaFamilies), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/review-queue/grouped')) {
      return new Response(JSON.stringify({
        inactive: { count: 0, label: 'Inativos ocultados', description: 'Itens inativos' },
        missing_code: { count: 0, label: 'Sem codigo Cybersul', description: 'Sem codigo' },
        incomplete_offers: { count: 0, label: 'Ofertas sem preco', description: 'Sem preco' },
        missing_email: { count: 0, label: 'Fornecedores sem e-mail', description: 'Sem email' },
        duplicates: { count: 0, label: 'Possiveis duplicados', description: 'Duplicados' },
        quarantine: { count: 0, label: 'Quarentena', description: 'Quarentena' },
        high_confidence: { count: 0, label: 'Vinculos de confianca alta', description: 'Confianca alta' },
        human_review: { count: 1, label: 'Revisao humana real', description: 'Revisao humana' }
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/review-queue/group/')) {
      return new Response(JSON.stringify([
        {
          id: 'rev-1',
          display_name: 'Tubo Aco Redondo Polido 1020 c/ Costura - 3/8"',
          reason: 'Fornecedor sem e-mail cadastrado.'
        }
      ]), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/review-queue')) {
      return new Response(JSON.stringify(mockReviewQueue), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/search')) {
      return new Response(JSON.stringify(mockSearchResults), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/price-update')) {
      const body = JSON.parse(init.body);
      return new Response(JSON.stringify({
        item_id: 'item-3-8',
        item_display_name: 'Tubo Aco Redondo Polido 1020 c/ Costura - 3/8"',
        supplier_id: body.supplier_id,
        supplier_name: 'FAM',
        old_price: 30.69,
        new_price: body.new_price,
        difference_amount: body.new_price - 30.69,
        difference_percent: ((body.new_price - 30.69) / 30.69) * 100,
        notes: body.notes,
        message: 'Preco atualizado de R$ 30,69 para R$ 35,00 para o fornecedor FAM.'
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/quote-draft')) {
      return new Response(JSON.stringify({
        quote_id: 'rfq-stock-1',
        action_url: '/purchases?quote=rfq-stock-1&step=products',
        product_item_id: 'item-3-8',
        display_name: 'Tubo Aco Redondo Polido 1020 c/ Costura - 3/8"',
        cybersul_code: null,
        variation: '3/8"',
        description: 'Tubo Aco Redondo Polido 1020 c/ Costura',
        suggested_suppliers: [
          {
            supplier_id: 'supp-fam',
            supplier_name: 'FAM',
            last_price: 30.69,
            email: 'compras@fornecedor-alfa.example',
            phone: '1199999999'
          }
        ],
        quantity: 1,
        observations: 'Rascunho gerado a partir do Catalogo. Medida: 9,53 mm'
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/items/item-3-8/offers')) {
      return new Response(JSON.stringify(mockItemOffers3_8), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/items/item-3-8/history')) {
      return new Response(JSON.stringify(mockItemHistory3_8), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/items/item-3-8')) {
      return new Response(JSON.stringify(mockItemDetails3_8), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('StockPage Component Tests', () => {
  it('renderiza catalogo sem hero e com busca lateral unica', async () => {
    installFetchMock();
    render(<StockPage currentUser={adminUser} />);

    expect(screen.getByRole('heading', { name: 'Estoque & Catálogo' })).toBeInTheDocument();
    expect(screen.getByText(/Consulte produtos, códigos, preços e fornecedores/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Buscar no catálogo/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Buscar na navegação/i)).toBeInTheDocument();
    expect(await screen.findByLabelText(/Abas do Cat/i)).toBeInTheDocument();
    expect((await screen.findAllByText('Tubo e Tarugo - Flange')).length).toBeGreaterThan(0);
    expect(screen.queryByText('Saneamento interno')).not.toBeInTheDocument();
    
    vi.unstubAllGlobals();
  });

  it('exibe autocomplete com sugestoes de busca, e clicar abre o drawer do item', async () => {
    installFetchMock();
    render(<StockPage currentUser={adminUser} />);

    const searchInput = screen.getByPlaceholderText(/Buscar no catálogo/i);
    await userEvent.type(searchInput, 'Tubo');

    // Autocomplete deve disparar sugestoes e renderizar
    expect(await screen.findByText(/Sugest/i)).toBeInTheDocument();
    
    // Deve listar a sugestao do Tubo 3/8"
    const suggestion = screen.getByText(/Tubo Aco Redondo Polido 1020 c\/ Costura - 3\/8"/i);
    expect(suggestion).toBeInTheDocument();

    // Clicar na sugestao deve abrir o drawer lateral e esconder sugestoes
    await userEvent.click(suggestion);
    expect(screen.queryByText(/Sugest/i)).not.toBeInTheDocument();
    
    // Drawer deve mostrar o display_name do item no topo
    expect((await screen.findAllByRole('heading', { level: 2, name: /Tubo Aco Redondo Polido 1020 c\/ Costura - 3\/8" - \(9,53 mm\)/i })).length).toBeGreaterThan(0);

    vi.unstubAllGlobals();
  });

  it('mostra precos e fornecedores especificos do item no drawer e atualiza preco com preview', async () => {
    installFetchMock();
    render(<StockPage currentUser={adminUser} />);

    // Buscar e abrir detalhes
    const searchInput = screen.getByPlaceholderText(/Buscar no catálogo/i);
    await userEvent.type(searchInput, 'Tubo');
    const suggestion = await screen.findByText(/Tubo Aco Redondo Polido 1020 c\/ Costura - 3\/8"/i);
    await userEvent.click(suggestion);

    // Navegar para a aba Fornecedores no Drawer
    const precosTab = await screen.findByRole('button', { name: /Fornecedores \(1\)/i });
    await userEvent.click(precosTab);

    // Deve exibir o fornecedor mockado FAM com o preco
    expect((await screen.findAllByText('FAM')).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/R\$\s*30,69/).length).toBeGreaterThan(0);

    // Clicar em Atualizar Preco abre o Modal
    const updateBtn = screen.getByRole('button', { name: 'Atualizar Preco' });
    await userEvent.click(updateBtn);

    // O modal deve ser exibido
    expect(await screen.findByText('Atualizar Preco do Fornecedor')).toBeInTheDocument();

    // Alterar o preco no input para disparar o preview
    const priceInput = screen.getByLabelText('Novo Preco (R$)');
    await userEvent.clear(priceInput);
    await userEvent.type(priceInput, '35.00');

    // Deve renderizar comparativo e diferenca no preview
    expect(await screen.findByText('Comparativo de Reajuste')).toBeInTheDocument();
    expect(screen.getByText(/\+R\$\s*4,31 \(\+14.0%\)/)).toBeInTheDocument();

    // Confirmar atualizacao
    const confirmBtn = screen.getByRole('button', { name: 'Confirmar Preco' });
    await userEvent.click(confirmBtn);

    // Deve mostrar mensagem de sucesso
    expect(await screen.findByText(/Preco atualizado de R\$ 30,69 para R\$ 35,00 para o fornecedor FAM/i)).toBeInTheDocument();

    vi.unstubAllGlobals();
  }, 15000);

  it('cria cotacao real em Compras com botao Cotar sem envios externos', async () => {
    installFetchMock();
    render(<StockPage currentUser={adminUser} />);

    // Buscar e clicar no botao Cotar na linha de resultados
    const searchInput = screen.getByPlaceholderText(/Buscar no catálogo/i);
    await userEvent.type(searchInput, 'Tubo{enter}');

    const cotarButtons = await screen.findAllByRole('button', { name: 'Cotar' });
    await userEvent.click(cotarButtons[0]);

    expect(await screen.findByText(/Cotacao criada em Compras/i)).toBeInTheDocument();
    expect(window.location.pathname).toBe('/purchases');
    expect(window.location.search).toContain('quote=rfq-stock-1');
    expect(window.location.search).toContain('step=products');

    vi.unstubAllGlobals();
  });

  it('permite acessar central de saneamento e resolver pendencias', async () => {
    installFetchMock();
    render(<StockPage currentUser={adminUser} />);

    // Clicar no botao discreto de saneamento
    const saneamentoBtn = screen.getByRole('button', { name: /Saneamento da Base/i });
    await userEvent.click(saneamentoBtn);

    // Deve exibir o cabecalho correspondente
    expect(await screen.findByRole('heading', { name: 'Central de Saneamento da Base', level: 3 })).toBeInTheDocument();

    // Novo fluxo: Clicar em "Ver detalhes" do card de revisao humana
    const verDetalhesButtons = await screen.findAllByRole('button', { name: 'Ver detalhes' });
    await userEvent.click(verDetalhesButtons[verDetalhesButtons.length - 1]); // O ultimo card e "Revisao humana real"

    // Deve listar a pendencia da fila de revisao
    expect(await screen.findByText('Tubo Aco Redondo Polido 1020 c/ Costura - 3/8"')).toBeInTheDocument();
    expect(await screen.findByText('Motivo: Fornecedor sem e-mail cadastrado.')).toBeInTheDocument();

    // Resolver a pendencia clicando em Aprovar
    const approveBtn = await screen.findByRole('button', { name: 'Aprovar para catalogo' });
    await userEvent.click(approveBtn);

    // Deve disparar a requisicao resolve e mostrar mensagem de sucesso
    expect(await screen.findByText('Aprovado para o catalogo operacional.')).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it('exibe aba tecnica apenas para Admin ou Messias', async () => {
    installFetchMock();
    
    // 1. Caso Usuario Comum
    const { unmount } = render(<StockPage currentUser={commonUser} />);
    const searchInputCommon = screen.getByPlaceholderText(/Buscar no catálogo/i);
    await userEvent.type(searchInputCommon, 'Tubo');
    const suggestionCommon = await screen.findByText(/Tubo Aco Redondo Polido 1020 c\/ Costura - 3\/8"/i);
    await userEvent.click(suggestionCommon);

    // Aba tecnica nao deve ser visivel para usuario comum
    expect(screen.queryByRole('button', { name: 'Tecnico (Admin)' })).not.toBeInTheDocument();
    unmount();

    // 2. Caso Usuario Admin
    render(<StockPage currentUser={adminUser} />);
    const searchInputAdmin = screen.getByPlaceholderText(/Buscar no catálogo/i);
    await userEvent.type(searchInputAdmin, 'Tubo');
    const suggestionAdmin = await screen.findByText(/Tubo Aco Redondo Polido 1020 c\/ Costura - 3\/8"/i);
    await userEvent.click(suggestionAdmin);

    // Aba tecnica deve ser visivel para Admin
    const tecnicoTab = await screen.findByRole('button', { name: 'Tecnico (Admin)' });
    expect(tecnicoTab).toBeInTheDocument();

    // Clicar na aba tecnica exibe metadados secretos (ex: identity_hash)
    await userEvent.click(tecnicoTab);
    expect(screen.getByText('hash_3_8_secret_technical_hash_value')).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it('painel esquerdo mostra produtos validos e oculta atributos isolados', async () => {
    installFetchMock();
    render(<StockPage currentUser={adminUser} />);

    const navPanel = await screen.findByLabelText('Abas do Catálogo');
    expect(navPanel).toBeInTheDocument();
    expect(screen.getAllByText('Chapa e Tubo Inox').length).toBeGreaterThan(0);

    const abaButton = screen.getAllByText('Chapa e Tubo Inox')[0];
    await userEvent.click(abaButton);

    expect(screen.getAllByText('Chapa Aço Inox 316 L').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Tubo Aço Inox Redondo 304').length).toBeGreaterThan(0);
    expect(screen.queryByText('39,65 kg/m')).not.toBeInTheDocument();
    expect(screen.queryByText('F304')).not.toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it('formata preco em pt-BR no resultado de busca', async () => {
    installFetchMock();
    render(<StockPage currentUser={adminUser} />);

    const searchInput = screen.getByPlaceholderText(/Buscar no catálogo/i);
    await userEvent.type(searchInput, 'Tubo');
    await userEvent.keyboard('{Enter}');

    expect(await screen.findByText('R$ 30,69')).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
