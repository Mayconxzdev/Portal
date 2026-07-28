import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import AutomationsPage from './AutomationsPage';

const mockIntents = [
  {
    id: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    source: 'n8n',
    source_ref_type: 'automation_callback_log',
    source_ref_id: 'a8c4f2d9-e6b1-4f11-9988-123456789012',
    proposed_action: 'update_stock',
    target_module: 'stock',
    title: 'Atualização de Estoque Automática',
    summary: 'Callback do n8n solicitou atualizar quantidade do item 10.',
    risk_level: 'HIGH',
    status: 'PENDING_REVIEW',
    action_payload: {
      action: 'update_stock',
      stock_item_id: 10,
      quantity: 5,
      secret_token: 'should_be_masked'
    },
    created_at: new Date().toISOString()
  },
  {
    id: 'b081c2bf-02dd-4e61-b527-c4b60735b50e',
    source: 'koda',
    proposed_action: 'create_draft',
    target_module: 'proposals',
    title: 'Sugestão de Rascunho',
    summary: 'Koda propôs criar rascunho de proposta comercial.',
    risk_level: 'LOW',
    status: 'APPROVED',
    action_payload: {
      proposal_id: 1
    },
    created_at: new Date().toISOString()
  }
];

function installFetchMock(intents = mockIntents) {
  const fetchMock = vi.fn(async (url: string, init?: any) => {
    if (url.includes('/reject')) {
      return new Response(JSON.stringify({ ...mockIntents[0], status: 'REJECTED', reason: 'Rejeitado por teste' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    if (url.includes('/mark-reviewed')) {
      return new Response(JSON.stringify({ ...mockIntents[0], status: 'APPROVED' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    if (url.includes('/execute')) {
      const body = JSON.parse(init.body);
      const isBlocked = url.includes('f47ac10b-58cc-4372-a567-0e02b2c3d479'); // Stock update is blocked
      
      return new Response(JSON.stringify({
        id: 'exec-123',
        action_intent_id: 'some-id',
        executor_key: 'test',
        idempotency_key: body.idempotency_key || 'idem-123',
        status: isBlocked ? 'BLOCKED' : 'SUCCEEDED',
        attempts: 1,
        created_at: new Date().toISOString()
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    return new Response(JSON.stringify(intents), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

const waitForLoading = async () => {
  await waitFor(() => {
    expect(screen.queryByText('Buscando histórico de automações...')).not.toBeInTheDocument();
  }, { timeout: 3000 });
};

describe('AutomationsPage', () => {
  it('mostra tela de acesso negado para usuário comum', () => {
    render(<AutomationsPage currentUser={{ id: 2, username: 'common_user', email: 'user@portal.example', role: 'USER' }} />);
    expect(screen.getByText('Acesso Negado')).toBeInTheDocument();
    expect(screen.queryByText('Revisão de Automações')).not.toBeInTheDocument();
  });

  it('renderiza listagem de intenções de ação para admin', async () => {
    installFetchMock();
    render(<AutomationsPage currentUser={{ id: 1, username: 'vesper_admin', email: 'admin@portal.example', role: 'ADMIN' }} />);

    await waitForLoading();
    expect(await screen.findByRole('heading', { name: /Revisão de Automações/i })).toBeInTheDocument();

    expect(screen.getAllByText('Atualização de Estoque Automática').length).toBeGreaterThan(0);
    expect(screen.getByText('Sugestão de Rascunho')).toBeInTheDocument();

    expect(screen.getByText('Ações pendentes')).toBeInTheDocument();
    expect(screen.getByText('Revisadas')).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it('abre o drawer com os detalhes da ação e exibe payload oculto', async () => {
    installFetchMock();
    render(<AutomationsPage currentUser={{ id: 1, username: 'vesper_admin', email: 'admin@portal.example', role: 'ADMIN' }} />);

    await waitForLoading();

    const verButtons = await screen.findAllByRole('button', { name: 'Ver' });
    await userEvent.click(verButtons[0]);

    expect(await screen.findByText('Resumo da Ação')).toBeInTheDocument();
    expect(screen.getByText('Callback do n8n solicitou atualizar quantidade do item 10.')).toBeInTheDocument();
    expect(screen.getByText('Ação de Negócio Bloqueada:')).toBeInTheDocument();

    expect(screen.queryByRole('button', { name: 'Executar' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Aprovar e executar' })).not.toBeInTheDocument();

    const detailsSummary = screen.getByText('Exibir dados brutos da intenção (Payload Técnico)');
    expect(detailsSummary).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it('permite rejeitar ação sugerida exigindo justificativa', async () => {
    const fetchMock = installFetchMock();
    render(<AutomationsPage currentUser={{ id: 1, username: 'vesper_admin', email: 'admin@portal.example', role: 'ADMIN' }} />);

    await waitForLoading();

    const rejectButtons = await screen.findAllByRole('button', { name: 'Rejeitar' });
    await userEvent.click(rejectButtons[0]);

    expect(await screen.findByText('Rejeitar Ação Sugerida')).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: 'Confirmar Rejeição' });
    expect(confirmBtn).toBeDisabled();

    const textarea = screen.getByLabelText(/Justificativa da Rejeição/i);
    await userEvent.type(textarea, 'Rejeitado por teste');
    expect(confirmBtn).toBeEnabled();

    await userEvent.click(confirmBtn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/reject'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ reason: 'Rejeitado por teste' })
        })
      );
    });

    vi.unstubAllGlobals();
  });

  it('permite marcar ação sugerida como revisada', async () => {
    const fetchMock = installFetchMock();
    render(<AutomationsPage currentUser={{ id: 1, username: 'vesper_admin', email: 'admin@portal.example', role: 'ADMIN' }} />);

    await waitForLoading();

    const reviewButtons = await screen.findAllByRole('button', { name: 'Revisar' });
    await userEvent.click(reviewButtons[0]);

    expect(await screen.findByText('Marcar Ação como Revisada')).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: 'Confirmar Revisão' });
    await userEvent.click(confirmBtn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/mark-reviewed'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ reason: undefined })
        })
      );
    });

    vi.unstubAllGlobals();
  });

  it('exibe badges de executabilidade na lista e no drawer', async () => {
    installFetchMock();
    render(<AutomationsPage currentUser={{ id: 1, username: 'vesper_admin', email: 'admin@portal.example', role: 'ADMIN' }} />);

    await waitForLoading();

    expect(screen.getByText('Bloqueada')).toBeInTheDocument();
    expect(screen.getByText('Executável')).toBeInTheDocument();

    const verButtons = await screen.findAllByRole('button', { name: 'Ver' });
    await userEvent.click(verButtons[1]); // Proposals rascunho (Executável)

    expect(await screen.findByText('Executabilidade')).toBeInTheDocument();
    
    vi.unstubAllGlobals();
  });

  it('permite testar simulação (dry run) de uma ação aprovada', async () => {
    const fetchMock = installFetchMock();
    render(<AutomationsPage currentUser={{ id: 1, username: 'vesper_admin', email: 'admin@portal.example', role: 'ADMIN' }} />);

    await waitForLoading();

    const verButtons = await screen.findAllByRole('button', { name: 'Ver' });
    await userEvent.click(verButtons[1]); // Proposals rascunho (status APPROVED)

    const dryRunBtn = await screen.findByText('Testar Simulação');
    await userEvent.click(dryRunBtn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/execute'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ dry_run: true })
        })
      );
    });

    vi.unstubAllGlobals();
  });

  it('permite executar uma ação segura aprovada', async () => {
    const fetchMock = installFetchMock();
    render(<AutomationsPage currentUser={{ id: 1, username: 'vesper_admin', email: 'admin@portal.example', role: 'ADMIN' }} />);

    await waitForLoading();

    const verButtons = await screen.findAllByRole('button', { name: 'Ver' });
    await userEvent.click(verButtons[1]); // Proposals rascunho (status APPROVED)

    const execBtn = await screen.findByText('Executar');
    await userEvent.click(execBtn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/execute'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ dry_run: false })
        })
      );
    });

    vi.unstubAllGlobals();
  });

  it('alterna para a aba de regras de automação, exibe lista de regras e permite alternar toggle', async () => {
    const fetchMock = vi.fn(async (url: string, init?: any) => {
      if (url.includes('/reactions/rules')) {
        return new Response(JSON.stringify([
          {
            id: 'rule-uuid-1',
            name: 'Regra Teste Frontend',
            description: 'Regra de teste para o front',
            event_type: 'test.event',
            module: 'kanban',
            enabled: true,
            priority: 1,
            condition_json: { op: 'always' },
            action_type: 'notify',
            action_payload: { user_id: 1 },
            created_at: new Date().toISOString()
          }
        ]), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      if (url.includes('/enabled')) {
        return new Response(JSON.stringify({
          id: 'rule-uuid-1',
          name: 'Regra Teste Frontend',
          enabled: false,
          condition_json: { op: 'always' },
          action_type: 'notify',
          action_payload: { user_id: 1 },
          created_at: new Date().toISOString()
        }), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<AutomationsPage currentUser={{ id: 1, username: 'vesper_admin', email: 'admin@portal.example', role: 'ADMIN' }} />);
    await waitForLoading();

    const rulesTabBtn = screen.getByRole('button', { name: /Regras de Automação/i });
    await userEvent.click(rulesTabBtn);
    
    expect(await screen.findByText('Regra Teste Frontend')).toBeInTheDocument();
    expect(screen.getByText('Regra de teste para o front')).toBeInTheDocument();
    expect(screen.getAllByText('test.event').length).toBeGreaterThan(0);

    const toggleBtn = screen.getByRole('button', { name: /Desativar regra/i });
    await userEvent.click(toggleBtn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/reactions/rules/rule-uuid-1/enabled'),
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ enabled: false })
        })
      );
    });

    vi.unstubAllGlobals();
  });

  it('alterna para a aba de histórico de reações, exibe a lista de execuções e abre o drawer de auditoria', async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.includes('/reactions/rules')) {
        return new Response(JSON.stringify([
          {
            id: 'rule-uuid-1',
            name: 'Regra Teste Run',
            event_type: 'test.event.run',
            module: 'kanban',
            enabled: true,
            priority: 1,
            condition_json: { op: 'always' },
            action_type: 'notify',
            action_payload: {},
            created_at: new Date().toISOString()
          }
        ]), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      if (url.includes('/reactions/runs')) {
        return new Response(JSON.stringify([
          {
            id: 'run-uuid-1',
            rule_id: 'rule-uuid-1',
            event_id: 'event-uuid-1',
            status: 'EXECUTED',
            condition_result: true,
            action_result: { message: 'Notificação enviada!' },
            created_at: new Date().toISOString()
          }
        ]), { status: 200, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<AutomationsPage currentUser={{ id: 1, username: 'vesper_admin', email: 'admin@portal.example', role: 'ADMIN' }} />);
    await waitForLoading();

    const runsTabBtn = screen.getByRole('button', { name: /Histórico de Reações/i });
    await userEvent.click(runsTabBtn);

    expect(await screen.findByText('Regra Teste Run')).toBeInTheDocument();
    expect(screen.getByText('Executada')).toBeInTheDocument();

    const detailsBtn = screen.getByRole('button', { name: 'Detalhes' });
    await userEvent.click(detailsBtn);

    expect(await screen.findByText('Auditoria de Execução de Reação')).toBeInTheDocument();
    expect(screen.getByText('PASSOU (Verdadeira)')).toBeInTheDocument();

    const detailsTag = document.getElementById('details-technical-log');
    expect(detailsTag).toBeInTheDocument();
    expect(detailsTag).not.toHaveAttribute('open');

    vi.unstubAllGlobals();
  });
});

