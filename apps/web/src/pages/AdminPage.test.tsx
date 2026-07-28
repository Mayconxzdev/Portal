import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AdminPage } from './AdminPage';

const adminUser = {
  id: 1,
  username: 'vesper_admin',
  email: 'admin@portal.example',
  role: 'ADMIN',
  module_permissions: { admin: 'ADMIN' },
};

const installFetchMock = () => {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === '/api/v1/admin/users' && init?.method === 'POST') {
      return new Response(JSON.stringify({
        detail: [
          {
            type: 'string_too_short',
            loc: ['body', 'password'],
            msg: 'String should have at least 6 characters',
            input: '123',
          },
        ],
      }), { status: 422 });
    }

    if (url === '/api/v1/admin/users') {
      return new Response(JSON.stringify([]), { status: 200 });
    }

    if (url === '/api/v1/admin/roles') {
      return new Response(JSON.stringify([{ id: 2, name: 'USER', description: 'Usuario comum' }]), { status: 200 });
    }

    if (url === '/api/v1/admin/modules') {
      return new Response(JSON.stringify([
        { id: 1, name: 'Dashboard', code: 'dashboard', is_active: true, is_restricted: false },
      ]), { status: 200 });
    }

    return new Response(JSON.stringify({ detail: 'Nao encontrado' }), { status: 404 });
  });

  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
};

describe('AdminPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('mostra erro humano quando criacao de usuario recebe detail estruturado da API', async () => {
    const fetchMock = installFetchMock();
    const user = userEvent.setup();

    render(<AdminPage currentUser={adminUser} />);

    const newUserButtons = await screen.findAllByRole('button', { name: /novo usu/i });
    await user.click(newUserButtons[newUserButtons.length - 1]);

    await user.type(screen.getByLabelText(/nome completo/i), 'Novo Usuario');
    await user.type(screen.getByLabelText(/nome de usu/i), 'novo.usuario');
    await user.type(screen.getByLabelText(/^senha inicial$/i), '123');
    await user.click(screen.getByRole('button', { name: /continuar/i }));
    await user.click(screen.getByRole('button', { name: /continuar/i }));
    await user.click(screen.getByRole('button', { name: /criar usu/i }));

    expect(await screen.findByText('Informe uma senha inicial ou gere uma senha temporaria.')).toBeInTheDocument();
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/v1/admin/users', expect.objectContaining({ method: 'POST' })));
  }, 10000);
});
