import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import DashboardPage from './DashboardPage';

const metrics = {
  users_total: 3,
  modules_total: 10,
  pending_approvals: 0,
  audit_logs_total: 12,
  active_tickets: 1,
  active_proposals: 0,
  low_stock_items: 0,
  active_workflows: 0,
  active_kanban_boards: 2,
  total_kanban_cards: 6,
  open_kanban_cards: 0,
  overdue_kanban_cards: 0,
  unassigned_kanban_cards: 0,
  high_priority_kanban_cards: 0,
  recently_updated_kanban_cards: 0,
  due_today_kanban_cards: 0,
  critical_kanban_cards: 0,
  boards_with_pending: {},
  kanban_cards_by_priority: {},
  expiring_it_certificates: 0,
};

describe('DashboardPage', () => {
  it('mostra cards com métricas reais e módulos futuros como em breve', () => {
    render(
      <DashboardPage
        metrics={metrics}
        modules={[]}
        currentUser={{ username: 'vesper_admin', role: 'ADMIN' }}
        onNavigate={vi.fn()}
      />,
    );

    expect(screen.getByText(/Bem-vindo, vesper_admin/i)).toBeInTheDocument();
    expect(screen.getAllByText('1 chamado ativo').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Em breve').length).toBeGreaterThan(0);
    expect(screen.queryByText('15 pendências')).not.toBeInTheDocument();
    expect(screen.queryByText('Agentes ativos: 9/9')).not.toBeInTheDocument();
  });

  it('não navega ao clicar em módulo planejado', async () => {
    const onNavigate = vi.fn();
    render(
      <DashboardPage
        metrics={metrics}
        modules={[]}
        currentUser={{ username: 'vesper_admin', role: 'ADMIN' }}
        onNavigate={onNavigate}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /Compras/i }));
    expect(onNavigate).not.toHaveBeenCalledWith('compras');
  });
});
