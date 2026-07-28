import React from 'react';
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical } from 'lucide-react';
import { KanbanCard, KanbanColumn } from './types';
import { KanbanCardView } from './KanbanCardView';

interface Props {
  column: KanbanColumn;
  columns: KanbanColumn[];
  canEditCards: boolean;
  onOpenCard: (card: KanbanCard) => void;
  onMoveCard: (card: KanbanCard, columnId: number) => void;
  onArchiveCard: (card: KanbanCard) => void;
  onDuplicateCard: (card: KanbanCard) => void;
}

export const KanbanColumnView: React.FC<Props> = ({ column, columns, canEditCards, onOpenCard, onMoveCard, onArchiveCard, onDuplicateCard }) => {
  const sortable = useSortable({ id: `column-${column.id}`, data: { type: 'column', column } });
  const cards = column.cards.filter((card) => !card.is_archived);
  const colColor = column.color;
  const baseColor = colColor ? colColor.split(';')[0] : '';
  const style = {
    transform: CSS.Transform.toString(sortable.transform),
    transition: sortable.transition,
    minWidth: 'min(300px, calc(100vw - 48px))',
    maxWidth: 'min(360px, calc(100vw - 48px))',
    width: 'clamp(300px, 27vw, 360px)',
    opacity: sortable.isDragging ? 0.55 : 1,
    '--kanban-column-accent': baseColor || 'transparent',
  } as React.CSSProperties;

  return (
    <div ref={sortable.setNodeRef} className="glass-card kanban-column" style={style}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 className="kanban-column__title">{column.name}</h3>
        <button ref={sortable.setActivatorNodeRef} {...sortable.attributes} {...sortable.listeners} className="action-btn" title="Arrastar coluna">
          <GripVertical size={14} />
        </button>
      </div>
      <SortableContext items={cards.map((card) => `card-${card.id}`)} strategy={verticalListSortingStrategy}>
        <div className="kanban-column__cards">
          {cards.length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Sem cards.</p>}
          {cards.map((card) => (
            <KanbanCardView
              key={card.id}
              card={card}
              columns={columns}
              canEdit={canEditCards}
              onOpen={onOpenCard}
              onMove={onMoveCard}
              onArchive={onArchiveCard}
              onDuplicate={onDuplicateCard}
            />
          ))}
        </div>
      </SortableContext>
    </div>
  );
};
