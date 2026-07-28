import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { AdminKanbanPermissions } from './AdminKanbanPermissions';

describe('AdminKanbanPermissions', () => {
  it('renderiza usuarios, quadros e salva permissoes sem IDs crus', async () => {
    const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
      if (url.includes('/users/search')) {
        return new Response(JSON.stringify([{ id: 2, username: 'joao', email: 'joao@vesper.local', role_name: 'USER' }]), { status: 200 });
      }
      if (url.includes('/admin/kanban/boards')) {
        return new Response(JSON.stringify([{ id: 1, name: 'Producao', slug: 'producao', is_archived: false }]), { status: 200 });
      }
      if (url.includes('/admin/kanban/board-permissions') && !options) {
        return new Response(JSON.stringify({ user_id: 2, username: 'joao', email: 'joao@vesper.local', role_name: 'USER', permissions: [{ board_id: 1, board_name: 'Producao', board_slug: 'producao', access_level: 'READ_ONLY' }] }), { status: 200 });
      }
      return new Response(JSON.stringify({ user_id: 2, username: 'joao', email: 'joao@vesper.local', role_name: 'USER', permissions: [{ board_id: 1, board_name: 'Producao', board_slug: 'producao', access_level: 'NORMAL' }] }), { status: 200 });
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<AdminKanbanPermissions />);
    expect(await screen.findByText('joao')).toBeInTheDocument();
    await userEvent.click(screen.getByText('joao'));
    expect((await screen.findAllByText('Producao')).length).toBeGreaterThan(0);
    expect(screen.queryByText(/user_id|board_id|#2/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByText('Salvar'));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/admin/kanban/board-permissions/bulk', expect.objectContaining({ method: 'PUT' })));
  });
});
