import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { CreateTicketModal } from './CreateTicketModal';

describe('CreateTicketModal', () => {
  it('abre chamado sem mostrar prioridade para usuario comum', async () => {
    const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
      if (url.endsWith('/api/v1/it/tickets') || url.endsWith('/tickets')) {
        expect(String(options?.body)).not.toContain('priority');
        return new Response(JSON.stringify({
          id: 1,
          ticket_number: 'TI-000001',
          title: 'Internet caiu',
          description: 'Sem rede',
          requester_user_id: 2,
          status: 'ABERTO',
          priority: 'MEDIA',
          category: 'INTERNET_REDE',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        }), { status: 201, headers: { 'Content-Type': 'application/json' } });
      }
      return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } });
    });
    vi.stubGlobal('fetch', fetchMock);
    const onCreated = vi.fn();

    render(<CreateTicketModal open onClose={() => undefined} onCreated={onCreated} />);
    expect(screen.queryByLabelText(/prioridade/i)).not.toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/titulo/i), 'Internet caiu');
    await userEvent.type(
      screen.getByLabelText((label) => label.toLowerCase().includes('acontecendo')),
      'Sem rede no setor.'
    );
    await userEvent.click(screen.getByRole('button', { name: /enviar chamado/i }));

    expect(onCreated).toHaveBeenCalledWith(expect.objectContaining({ ticket_number: 'TI-000001' }));
    vi.unstubAllGlobals();
  });
});
