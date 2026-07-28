import React, { useMemo, useState } from 'react';
import { Archive, ChevronDown, Search, Kanban } from 'lucide-react';
import { KanbanBoard } from './types';

interface BoardSwitcherProps {
  boards: KanbanBoard[];
  selectedBoard: KanbanBoard;
  includeArchived: boolean;
  onIncludeArchivedChange: (value: boolean) => void;
  onSelectBoard: (boardId: number) => void;
}

export const BoardSwitcher: React.FC<BoardSwitcherProps> = ({
  boards,
  selectedBoard,
  includeArchived,
  onIncludeArchivedChange,
  onSelectBoard,
}) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return boards.filter((board) => {
      if (!includeArchived && board.is_archived) return false;
      if (!normalized) return true;
      return `${board.name} ${board.description || ''}`.toLowerCase().includes(normalized);
    });
  }, [boards, includeArchived, query]);

  return (
    <div className="board-switcher">
      <button type="button" className="board-switcher__button" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <Kanban size={16} />
        <span>{selectedBoard.name}</span>
        <ChevronDown size={16} />
      </button>
      {open && (
        <div className="board-switcher__panel">
          <label className="board-switcher__search">
            <Search size={15} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar quadro..." />
          </label>
          <label className="board-switcher__archived">
            <input type="checkbox" checked={includeArchived} onChange={(event) => onIncludeArchivedChange(event.target.checked)} />
            Exibir arquivados
          </label>
          <div className="board-switcher__list">
            {filtered.length === 0 ? (
              <p>Nenhum quadro encontrado.</p>
            ) : (
              filtered.map((board) => (
                <button
                  type="button"
                  key={board.id}
                  className={board.id === selectedBoard.id ? 'active' : ''}
                  onClick={() => {
                    setOpen(false);
                    onSelectBoard(board.id);
                  }}
                >
                  <span>{board.name}</span>
                  {board.is_archived && <Archive size={14} />}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default BoardSwitcher;
