import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BoardAccessDrawer } from './BoardAccessDrawer';
import { makeBoard } from './testUtils';

vi.mock('./kanbanApi', () => ({
  apiJson: vi.fn(async (url: string) => {
    if (url.includes('/permissions')) {
      return [
        { id: 1, board_id: 1, user_id: 1, access_level: 'ADMIN', username: 'vesper_admin', user_email: 'admin@vesper.local' },
        { id: 2, board_id: 1, role_id: 1, access_level: 'READ_ONLY', role_name: 'Manager' },
      ];
    }
    if (url.includes('/roles')) return [{ id: 1, name: 'Manager', description: 'Gestores' }];
    if (url.includes('/users')) return [{ id: 3, username: 'maycon', email: 'maycon@vesper.local' }];
    return {};
  }),
}));

test('mostra nomes humanos e não IDs crus no painel de acessos', async () => {
  render(<BoardAccessDrawer board={makeBoard()} isOpen onClose={vi.fn()} onChanged={vi.fn()} />);

  expect(await screen.findByText('vesper_admin')).toBeInTheDocument();
  expect(screen.getByText('admin@vesper.local')).toBeInTheDocument();
  expect(screen.getAllByText('Manager').length).toBeGreaterThan(0);
  expect(screen.queryByText(/Usuário #/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/Perfil #/i)).not.toBeInTheDocument();
});

test('busca usuário para novo acesso', async () => {
  const user = userEvent.setup();
  render(<BoardAccessDrawer board={makeBoard()} isOpen onClose={vi.fn()} onChanged={vi.fn()} />);

  await user.type(screen.getByLabelText(/buscar usuário/i), 'maycon');
  await user.click(screen.getByRole('button', { name: /buscar/i }));

  expect(await screen.findByText('maycon')).toBeInTheDocument();
});
