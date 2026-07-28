import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import LegacyImportPage from './LegacyImportPage';

const adminUser = {
  role: 'ADMIN',
  username: 'vesper_admin',
};

const mockSummary = {
  total_batches: 2,
  total_rows: 15,
  status_counts: {
    PENDING_REVIEW: 10,
    DUPLICATE_CANDIDATE: 3,
    READY: 1,
    REJECTED: 1,
  },
  module_counts: {
    purchases: 12,
    it: 3,
  },
};

const mockBatches = [
  {
    id: 'b819f71c-42b7-4c4c-8ab5-3c0f4f9f1201',
    source_app: 'COMPRASAPP2',
    source_name: 'Compras Nova.xlsx',
    source_path_masked: 'C:\\...\\Compras Nova.xlsx',
    module_target: 'purchases',
    status: 'NEEDS_REVIEW',
    total_rows: 12,
    valid_rows: 8,
    duplicate_rows: 3,
    error_rows: 1,
    created_at: '2026-06-05T10:00:00Z',
    notes: 'Importacao inicial de fornecedores antigos',
  },
  {
    id: 'db29f71c-42b7-4c4c-8ab5-3c0f4f9f1202',
    source_app: 'HELPDESK',
    source_name: 'suporte.db',
    source_path_masked: '\\\\fileserver.local\\...\\suporte.db',
    module_target: 'it',
    status: 'READY_TO_IMPORT',
    total_rows: 3,
    valid_rows: 3,
    duplicate_rows: 0,
    error_rows: 0,
    created_at: '2026-06-05T11:00:00Z',
    notes: 'Importacao de chamados',
  },
];

const mockRows = [
  {
    id: 'r919f71c-42b7-4c4c-8ab5-3c0f4f9f1301',
    batch_id: 'b819f71c-42b7-4c4c-8ab5-3c0f4f9f1201',
    source_app: 'COMPRASAPP2',
    source_table_or_sheet: 'Fornecedores',
    source_row_id: '101',
    module_target: 'purchases',
    entity_target: 'SUPPLIER',
    raw_data_json: {
      razao_social: 'Fornecedor Antigo Ltda',
      cnpj: '12.345.678/0001-90',
      email: 'contato@fornecedor.com.br',
      db_password: '******',
    },
    normalized_data_json: {
      name: 'Fornecedor Antigo Ltda',
      cnpj: '12345678000190',
      email: 'contato@fornecedor.com.br',
      db_password: '******',
    },
    confidence_score: 0.95,
    status: 'PENDING_REVIEW',
    created_at: '2026-06-05T10:05:00Z',
  },
  {
    id: 'r919f71c-42b7-4c4c-8ab5-3c0f4f9f1302',
    batch_id: 'b819f71c-42b7-4c4c-8ab5-3c0f4f9f1201',
    source_app: 'COMPRASAPP2',
    source_table_or_sheet: 'Fornecedores',
    source_row_id: '102',
    module_target: 'purchases',
    entity_target: 'SUPPLIER',
    raw_data_json: {
      razao_social: 'Fornecedor Duplicado SA',
      cnpj: '98.765.432/0001-10',
    },
    normalized_data_json: {
      name: 'Fornecedor Duplicado SA',
      cnpj: '98765432000110',
    },
    detected_duplicates_json: {
      candidates: [
        {
          target_id: 'p019f71c-42b7-4c4c-8ab5-3c0f4f9f1401',
          match_type: 'DOCUMENT',
          score: 1.0,
        },
      ],
    },
    confidence_score: 0.8,
    status: 'DUPLICATE_CANDIDATE',
    created_at: '2026-06-05T10:06:00Z',
  },
];

function installFetchMock() {
  const fetchMock = vi.fn(async (url: string, options?: any) => {
    if (url.includes('/summary')) {
      return new Response(JSON.stringify(mockSummary), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/batches') && url.includes('/rows')) {
      return new Response(JSON.stringify(mockRows), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/batches')) {
      return new Response(JSON.stringify(mockBatches), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/decision')) {
      const body = JSON.parse(options.body);
      return new Response(JSON.stringify({
        id: 'd019f71c-42b7-4c4c-8ab5-3c0f4f9f1501',
        row_id: 'r919f71c-42b7-4c4c-8ab5-3c0f4f9f1301',
        decision: body.decision,
        reason: body.reason,
        decided_by_user_id: 1,
        decided_at: new Date().toISOString(),
      }), { status: 201, headers: { 'Content-Type': 'application/json' } });
    }
    return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('LegacyImportPage', () => {
  it('renderiza resumo de staging, lotes de origem e abre detalhe com linhas', async () => {
    const fetchMock = installFetchMock();
    const handleBack = vi.fn();
    render(<LegacyImportPage currentUser={adminUser} onBack={handleBack} />);

    // 1. Verifica renderização do ModuleHero e cards de métricas
    expect(await screen.findByRole('heading', { name: /Importação Legada/i })).toBeInTheDocument();
    expect(screen.getByText('Lotes de Origem')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument(); // total_batches

    // 2. Verifica listagem de lotes
    expect(screen.getByText('Compras Nova.xlsx')).toBeInTheDocument();
    expect(screen.getByText('suporte.db')).toBeInTheDocument();

    // 3. Abre um lote de staging clicando sobre ele
    const batchCard = screen.getByText('Compras Nova.xlsx');
    await userEvent.click(batchCard);

    // 4. Verifica listagem de linhas do lote
    expect(await screen.findByText('Fornecedor Antigo Ltda')).toBeInTheDocument();
    expect(screen.getByText('Fornecedor Duplicado SA')).toBeInTheDocument();

    // 5. Abre o drawer de revisão ao clicar no botão "Revisar"
    const reviewButtons = screen.getAllByRole('button', { name: /Revisar/i });
    await userEvent.click(reviewButtons[0]);

    // 6. Verifica se o Drawer de detalhe abre e mostra dados
    expect(await screen.findByText('Revisão de Staging Legado')).toBeInTheDocument();
    expect(screen.getByText('Campos Normalizados')).toBeInTheDocument();

    // 7. Garante mascaramento visual do segredo
    expect(screen.getByText('Protegido')).toBeInTheDocument();

    // 8. O JSON de dados brutos fica oculto em <details> fechado por padrão
    const detailsSummary = screen.getByText('Dados Brutos de Origem (JSON)');
    expect(detailsSummary).toBeInTheDocument();
    
    // 9. Não deve existir nenhum botão ou ação de "Importar agora" oficial direto nas tabelas principais
    expect(screen.queryByRole('button', { name: /Importar Agora/i })).not.toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it('permite registrar uma decisao administrativa com justificativa', async () => {
    const fetchMock = installFetchMock();
    render(<LegacyImportPage currentUser={adminUser} onBack={vi.fn()} />);

    // Abre o lote e a primeira linha
    await userEvent.click(await screen.findByText('Compras Nova.xlsx'));
    const reviewButtons = await screen.findAllByRole('button', { name: /Revisar/i });
    await userEvent.click(reviewButtons[0]);

    // Preenche a justificativa/motivo
    const textarea = screen.getByPlaceholderText(/Escreva a justificativa para essa decisão/i);
    await userEvent.type(textarea, 'Fornecedor valido para rfq futura');

    // Clica no botão Aceitar Dados
    const acceptButton = screen.getByRole('button', { name: /Aceitar Dados/i });
    await userEvent.click(acceptButton);

    // Verifica que enviou a chamada POST com o payload correto
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/rows/r919f71c-42b7-4c4c-8ab5-3c0f4f9f1301/decision'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            decision: 'ACCEPT',
            reason: 'Fornecedor valido para rfq futura',
          }),
        })
      );
    });

    vi.unstubAllGlobals();
  });

  it('exibe duplicidade candidata com match_type', async () => {
    installFetchMock();
    render(<LegacyImportPage currentUser={adminUser} onBack={vi.fn()} />);

    // Abre o lote e a segunda linha (que tem duplicados)
    await userEvent.click(await screen.findByText('Compras Nova.xlsx'));
    const reviewButtons = await screen.findAllByRole('button', { name: /Revisar/i });
    await userEvent.click(reviewButtons[1]); // segunda linha

    // Verifica se exibe informações de colisão de duplicados
    expect(await screen.findByText('Duplicados Potenciais no Portal')).toBeInTheDocument();
    expect(screen.getByText(/Tipo de Colisão:/i)).toBeInTheDocument();
    expect(screen.getByText(/DOCUMENT/i)).toBeInTheDocument();

    vi.unstubAllGlobals();
  });
});
