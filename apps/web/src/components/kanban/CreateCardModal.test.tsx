import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CreateCardModal } from './CreateCardModal';
import { makeBoard } from './testUtils';

test('não cria tarefa sem título e cria quando o título é informado', async () => {
  const user = userEvent.setup();
  const onCreate = vi.fn().mockResolvedValue(undefined);
  render(<CreateCardModal board={makeBoard()} isOpen onClose={vi.fn()} onCreate={onCreate} />);

  await user.click(screen.getByRole('button', { name: /criar tarefa/i }));
  expect(onCreate).not.toHaveBeenCalled();

  await user.type(screen.getByLabelText(/título/i), 'Nova OP');
  await user.click(screen.getByRole('button', { name: /criar tarefa/i }));

  expect(onCreate).toHaveBeenCalledWith(expect.objectContaining({ title: 'Nova OP' }));
});
