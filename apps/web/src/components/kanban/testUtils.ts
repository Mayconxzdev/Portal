import { BoardViewConfig, KanbanBoard, KanbanCard } from './types';

export const makeCard = (overrides: Partial<KanbanCard> = {}): KanbanCard => ({
  id: 1,
  board_id: 1,
  column_id: 1,
  title: 'Revisar OP 1001',
  description: 'Pedido do cliente',
  position: 0,
  priority: 'HIGH',
  due_date: '2026-05-25T00:00:00',
  custom_fields: { op: '1001', cliente: 'Cliente A' },
  is_archived: false,
  created_at: '2026-05-20T10:00:00',
  updated_at: '2026-05-22T10:00:00',
  labels: [{ id: 1, board_id: 1, name: 'Urgente', color: '#ef4444', is_active: true }],
  assignees: [{ id: 1, card_id: 1, user_id: 1, assigned_by_user_id: 1, created_at: '2026-05-20T10:00:00', user: { id: 1, username: 'vesper_admin' } }],
  checklist_total: 2,
  checklist_done: 1,
  ...overrides,
});

export const makeView = (overrides: Partial<BoardViewConfig> = {}): BoardViewConfig => ({
  id: 1,
  board_id: 1,
  name: 'Lista de produção',
  view_type: 'LIST',
  is_default: true,
  density: 'COMPACT',
  visible_columns: ['op', 'title', 'status', 'priority'],
  column_order: ['op', 'title', 'status', 'priority'],
  column_widths: { op: 120, title: 300 },
  sort_by: 'custom.op',
  group_by: '',
  color_rules: { priority: true },
  auto_scroll: false,
  ...overrides,
});

export const makeBoard = (overrides: Partial<KanbanBoard> = {}): KanbanBoard => {
  const card = makeCard();
  return {
    id: 1,
    name: 'Produção',
    slug: 'producao',
    description: 'Fluxo operacional de produção.',
    is_archived: false,
    access_level: 'ADMIN',
    columns: [
      { id: 1, board_id: 1, name: 'A Fazer', position: 0, is_done_column: false, is_archived: false, cards: [card] },
      { id: 2, board_id: 1, name: 'Concluído', position: 1, is_done_column: true, is_archived: false, cards: [] },
    ],
    custom_fields: [
      { id: 1, board_id: 1, name: 'OP', key: 'op', field_type: 'TEXT', is_required: false, is_active: true, position: 0 },
      { id: 2, board_id: 1, name: 'Cliente', key: 'cliente', field_type: 'TEXT', is_required: false, is_active: true, position: 1 },
    ],
    labels: [{ id: 1, board_id: 1, name: 'Urgente', color: '#ef4444', is_active: true }],
    views: [makeView()],
    ...overrides,
  };
};
