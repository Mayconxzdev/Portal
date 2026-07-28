import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BoardViewsDrawer } from './BoardViewsDrawer';
import { makeBoard } from './testUtils';

vi.mock('./kanbanApi', () => ({
  apiJson: vi.fn(async () => [makeBoard().views[0]]),
}));

test('renderiza visualizações e abre configuração visual', async () => {
  const user = userEvent.setup();
  render(<BoardViewsDrawer board={makeBoard()} isOpen onClose={vi.fn()} onChanged={vi.fn()} />);

  expect(await screen.findByText(/visualizações salvas/i)).toBeInTheDocument();
  expect(screen.getByDisplayValue('Lista de produção')).toBeInTheDocument();

  await user.click(screen.getByRole('button', { name: /configurar/i }));

  expect(screen.getByText(/colunas visíveis e ordem/i)).toBeInTheDocument();
  expect(screen.getByText(/prévia da lista/i)).toBeInTheDocument();
});
