import { render, screen, waitFor } from '@testing-library/react';
import { KanbanListView } from './KanbanListView';
import { makeBoard, makeCard, makeView } from './testUtils';

vi.mock('./kanbanApi', async () => {
  const actual = await vi.importActual<typeof import('./kanbanApi')>('./kanbanApi');
  return {
    ...actual,
    apiJson: vi.fn(async () => ({
      board: makeBoard(),
      cards: [makeCard()],
      columns: makeBoard().columns,
      labels: makeBoard().labels,
      custom_fields: makeBoard().custom_fields,
      views: [makeView()],
      list_config: makeView(),
      visible_columns: ['op', 'title', 'status'],
      column_order: ['op', 'title', 'status'],
      column_widths: { op: 120 },
      generated_at: '2026-05-25T10:00:00',
    })),
  };
});

test('renderiza linhas da lista com campos visíveis', async () => {
  render(<KanbanListView board={makeBoard()} onOpenCard={vi.fn()} />);

  await waitFor(() => expect(screen.getByText('Revisar OP 1001')).toBeInTheDocument());

  expect(screen.getByRole('columnheader', { name: 'OP' })).toBeInTheDocument();
  expect(screen.getByText('1001')).toBeInTheDocument();
  expect(screen.queryByRole('columnheader', { name: 'Cliente' })).not.toBeInTheDocument();
});
