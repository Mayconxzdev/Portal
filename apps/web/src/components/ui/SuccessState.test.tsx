import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SuccessState } from './SuccessState';

describe('SuccessState', () => {
  it('renderiza título padrão e a mensagem', () => {
    render(<SuccessState message="Operação concluída" />);
    expect(screen.getByText('Sucesso')).toBeInTheDocument();
    expect(screen.getByText('Operação concluída')).toBeInTheDocument();
  });

  it('aceita título customizado', () => {
    render(<SuccessState title="Chamado aberto" message="Ticket #123 criado." />);
    expect(screen.getByRole('heading', { name: 'Chamado aberto' })).toBeInTheDocument();
    expect(screen.getByText('Ticket #123 criado.')).toBeInTheDocument();
  });

  it('exibe botão de ação quando actionText e onAction são fornecidos', async () => {
    const onAction = vi.fn();
    const user = userEvent.setup();
    render(
      <SuccessState
        message="OK"
        actionText="Ver chamado"
        onAction={onAction}
      />,
    );
    await user.click(screen.getByRole('button', { name: /ver chamado/i }));
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it('omite botão de ação quando onAction não é fornecido', () => {
    render(<SuccessState message="OK" actionText="Ver" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('omite botão de ação quando actionText não é fornecido', () => {
    const onAction = vi.fn();
    render(<SuccessState message="OK" onAction={onAction} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(onAction).not.toHaveBeenCalled();
  });

  it('anuncia para leitores de tela via role=status e aria-live=polite', () => {
    const { container } = render(<SuccessState message="OK" />);
    const node = container.querySelector('[role="status"]');
    expect(node).not.toBeNull();
    expect(node?.getAttribute('aria-live')).toBe('polite');
  });

  it('aplica classe compact quando prop compact é true', () => {
    const { container } = render(<SuccessState message="OK" compact />);
    const node = container.querySelector('.success-state-container');
    expect(node?.className).toContain('success-state-compact');
  });
});
