import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BoardImportDrawer } from './BoardImportDrawer';
import { makeBoard } from './testUtils';

vi.mock('./kanbanApi', () => ({
  apiJson: vi.fn(async () => ({
    import_id: 'preview-1',
    filename: 'cards.csv',
    headers: ['OP', 'Titulo'],
    rows: [{ OP: '1001', Titulo: 'Revisar OP' }],
    total_rows: 1,
  })),
}));

test('mostra preview e mapeamento da importação', async () => {
  const user = userEvent.setup();
  render(<BoardImportDrawer board={makeBoard()} isOpen onClose={vi.fn()} onChanged={vi.fn()} />);

  const file = new File(['OP,Titulo\n1001,Revisar OP'], 'cards.csv', { type: 'text/csv' });
  const input = screen.getByLabelText('Arquivo para importar') as HTMLInputElement;
  await user.upload(input, file);

  await waitFor(() => expect(screen.getByText(/cards.csv: 1 linha/i)).toBeInTheDocument());
  expect(screen.getAllByText('OP').length).toBeGreaterThan(0);
  expect(screen.getByText('Titulo')).toBeInTheDocument();
});
