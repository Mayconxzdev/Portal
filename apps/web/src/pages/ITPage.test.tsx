import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import ITPage from './ITPage';

class MockWebSocket {
  static OPEN = 1;
  readyState = 1;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  send = vi.fn();
  close = vi.fn();
  constructor(public url: string) {}
}

const adminUser = {
  id: 1,
  role: 'ADMIN',
  module_permissions: { it: 'ADMIN' },
};

function installFetchMock() {
  const fetchMock = vi.fn(async (url: string) => {
    if (url.includes('/summary')) {
      return new Response(JSON.stringify({
        open_tickets: 1,
        in_progress_tickets: 1,
        suspended_tickets: 0,
        closed_today: 0,
        overdue_tickets: 1,
        critical_tickets: 1,
        expiring_certificates: 1,
        assets_in_maintenance: 0,
        my_tickets: 1,
        assigned_to_me: 1,
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/overview')) {
      return new Response(JSON.stringify({
        summary: {
          open_tickets: 1,
          in_progress_tickets: 1,
          suspended_tickets: 0,
          closed_today: 0,
          overdue_tickets: 1,
          critical_tickets: 1,
          expiring_certificates: 1,
          assets_in_maintenance: 0,
          my_tickets: 1,
          assigned_to_me: 1,
        },
        recent_activity: []
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    if (url.includes('/tickets')) {
      return new Response(JSON.stringify([{
        id: 1,
        ticket_number: 'TI-000001',
        title: 'Certificado vencendo',
        description: 'Renovar',
        requester_user_id: 1,
        requester_name: 'vesper_admin',
        status: 'ABERTO',
        priority: 'CRITICA',
        category: 'CERTIFICADO',
        updated_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
      }]), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);
  vi.stubGlobal('WebSocket', MockWebSocket as any);
  return fetchMock;
}

describe('ITPage', () => {
  it('renderiza central de TI com abas e abre chamados', async () => {
    const fetchMock = installFetchMock();
    render(<ITPage currentUser={adminUser} />);


    
    // Espera o loading sumir e exibe o cabeçalho real
    expect(await screen.findByRole('heading', { name: /TI/i })).toBeInTheDocument();

    // Navega para aba Chamados
    await userEvent.click(screen.getByRole('tab', { name: 'Chamados' }));
    
    // Verifica se exibe o chamado mockado
    expect(await screen.findByText('Certificado vencendo')).toBeInTheDocument();

    vi.unstubAllGlobals();
  });

  it('renderiza relatorios de TI e aba notas', async () => {
    installFetchMock();
    render(<ITPage currentUser={adminUser} />);

    // Navega para a aba Relatórios
    await userEvent.click(await screen.findByRole('tab', { name: /relatórios/i }));

    // Verifica se exibe os cards de relatórios exportáveis
    expect(await screen.findByText(/Planilha de ativos com número de série/i)).toBeInTheDocument();
    expect(await screen.findByText(/Histórico de Chamados/i)).toBeInTheDocument();
    
    vi.unstubAllGlobals();
  });
});
