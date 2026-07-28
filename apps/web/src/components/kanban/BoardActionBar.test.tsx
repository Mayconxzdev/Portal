import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { BoardActionBar } from './BoardActionBar';

describe('BoardActionBar', () => {
  it('nao exibe Acessos como acao principal do Kanban', () => {
    render(
      <BoardActionBar
        viewMode="board"
        canEditCards
        canEditStructure
        onViewModeChange={vi.fn()}
        onCreateCard={vi.fn()}
        onManageColumns={vi.fn()}
        onFields={vi.fn()}
        onLabels={vi.fn()}
        onTV={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByText('Nova tarefa')).toBeInTheDocument();
    expect(screen.queryByText('Acessos')).not.toBeInTheDocument();
  });
});
