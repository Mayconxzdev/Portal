import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KanbanViewToggle } from './KanbanViewToggle';

test('troca entre Quadro e Lista', async () => {
  const user = userEvent.setup();
  const onChange = vi.fn();
  render(<KanbanViewToggle value="board" onChange={onChange} />);

  await user.click(screen.getByRole('button', { name: /lista/i }));

  expect(onChange).toHaveBeenCalledWith('list');
});
