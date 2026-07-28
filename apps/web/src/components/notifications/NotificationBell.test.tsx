import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import NotificationBell from './NotificationBell';
import { resolveNotificationDestination } from './notificationDestinations';

class MockWebSocket {
  static OPEN = 1;
  readyState = MockWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;

  constructor() {
    setTimeout(() => this.onopen?.(), 0);
  }

  send = vi.fn();
  close = vi.fn(() => this.onclose?.());
}

const notification = {
  id: '4b4f57d1-e411-46ba-9a92-44766fa50425',
  user_id: 1,
  role_target: null,
  module: 'automations',
  event_type: 'automation.action_intent.created',
  title: 'Acao sugerida pendente',
  message: 'Uma nova sugestao precisa de revisao.',
  severity: 'WARNING',
  status: 'UNREAD',
  source_type: 'action_intent',
  source_id: 'intent-1',
  action_url: '/automations',
  created_at: new Date().toISOString(),
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('NotificationBell', () => {
  it('resolve deep link exato de compra por request', () => {
    const destination = resolveNotificationDestination({
      module: 'purchases',
      source_type: 'purchase_request',
      source_id: '4b4f57d1-e411-46ba-9a92-44766fa50425',
      action_url: '/purchases?request=4b4f57d1-e411-46ba-9a92-44766fa50425',
    });

    expect(destination).toEqual({
      moduleCode: 'purchases',
      search: { request: '4b4f57d1-e411-46ba-9a92-44766fa50425' },
    });
  });

  it('mostra empty state quando nao existem notificacoes', async () => {
    vi.stubGlobal('WebSocket', MockWebSocket as any);
    const fetchMock = vi.fn(async (url: string) => {
      if (url.includes('/unread-count')) {
        return new Response(JSON.stringify({ count: 0 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(JSON.stringify({ items: [], next_cursor: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<NotificationBell backendOnline={true} onNavigate={vi.fn()} />);

    await userEvent.click(screen.getByRole('button', { name: /Notificacoes/i }));
    expect(await screen.findByText('Sem notificacoes reais no momento.')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/notifications/unread-count');
  });

  it('renderiza notificacao real e marca como lida', async () => {
    vi.stubGlobal('WebSocket', MockWebSocket as any);
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes('/unread-count')) {
        return new Response(JSON.stringify({ count: 1 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (url.includes('/read')) {
        return new Response(JSON.stringify({ ...notification, status: 'READ' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(JSON.stringify({ items: [notification], next_cursor: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<NotificationBell backendOnline={true} onNavigate={vi.fn()} />);

    await userEvent.click(screen.getByRole('button', { name: /Notificacoes/i }));
    expect(await screen.findByText('Acao sugerida pendente')).toBeInTheDocument();
    expect(screen.getByText('Uma nova sugestao precisa de revisao.')).toBeInTheDocument();
    expect(screen.queryByText('intent-1')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Marcar como lida' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        `/api/v1/notifications/${notification.id}/read`,
        { method: 'POST' },
      );
    });

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/notifications/unread-count');
  });

  it('abre o destino da action_url quando acionada', async () => {
    vi.stubGlobal('WebSocket', MockWebSocket as any);
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/unread-count')) {
        return new Response(JSON.stringify({ count: 1 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (url.includes('/read')) {
        return new Response(JSON.stringify({ ...notification, status: 'READ' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(JSON.stringify({ items: [notification], next_cursor: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }));
    const onNavigate = vi.fn();

    render(<NotificationBell backendOnline={true} onNavigate={onNavigate} />);

    await userEvent.click(screen.getByRole('button', { name: /Notificacoes/i }));
    await userEvent.click(await screen.findByRole('button', { name: /Acao sugerida pendente/i }));

    await waitFor(() => {
      expect(onNavigate).toHaveBeenCalledWith('automations', undefined);
    });
  });

  it('mantem o contador vindo do endpoint mesmo quando a primeira pagina tem menos itens', async () => {
    vi.stubGlobal('WebSocket', MockWebSocket as any);
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      if (url.includes('/unread-count')) {
        return new Response(JSON.stringify({ count: 12 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(JSON.stringify({ items: [notification], next_cursor: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }));

    render(<NotificationBell backendOnline={true} onNavigate={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('9+')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: /Notificacoes/i }));
    expect(await screen.findByText('12 nao lidas')).toBeInTheDocument();
  });

  it('marcar todas chama endpoint e atualiza contador', async () => {
    vi.stubGlobal('WebSocket', MockWebSocket as any);
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes('/unread-count')) {
        return new Response(JSON.stringify({ count: 2 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      if (url.includes('/read-all')) {
        return new Response(JSON.stringify({ status: 'success', marked_count: 2 }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(JSON.stringify({ items: [notification, { ...notification, id: 'n2' }], next_cursor: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<NotificationBell backendOnline={true} onNavigate={vi.fn()} />);

    await userEvent.click(screen.getByRole('button', { name: /Notificacoes/i }));
    await userEvent.click(await screen.findByRole('button', { name: 'Marcar todas como lidas' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith('/api/v1/notifications/read-all', { method: 'POST' });
    });
  });
});
