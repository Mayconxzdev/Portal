import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, test, vi } from 'vitest';
import { CreateColumnModal } from './CreateColumnModal';
import { makeBoard } from './testUtils';
import { apiJson } from './kanbanApi';

vi.mock('./kanbanApi', () => ({
  apiJson: vi.fn(async () => ({})),
}));

test('nao cria coluna sem nome e cria quando o nome e informado', async () => {
  const user = userEvent.setup();
  const onChanged = vi.fn().mockResolvedValue(undefined);
  const board = makeBoard();

  render(<CreateColumnModal board={board} isOpen onClose={vi.fn()} onChanged={onChanged} />);

  // Clicar em criar sem nome
  await user.click(screen.getByRole('button', { name: /criar/i }));
  expect(apiJson).not.toHaveBeenCalled();

  // Digitar nome e clicar em criar
  await user.type(screen.getByLabelText(/nome da coluna/i), 'Separacao');
  await user.click(screen.getByRole('button', { name: /criar/i }));

  expect(apiJson).toHaveBeenCalledWith(
    `/api/v1/kanban/boards/${board.id}/columns`,
    expect.objectContaining({
      method: 'POST',
      body: expect.stringContaining('"name":"Separacao"')
    })
  );
  expect(onChanged).toHaveBeenCalled();
});
