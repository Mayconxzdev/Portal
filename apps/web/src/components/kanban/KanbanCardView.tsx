import React from 'react';
import { CSS } from '@dnd-kit/utilities';
import { useSortable } from '@dnd-kit/sortable';
import { Archive, Copy, GripVertical, MessageCircle, Paperclip, UserRound } from 'lucide-react';
import { KanbanCard, KanbanColumn } from './types';

interface Props {
  card: KanbanCard;
  columns: KanbanColumn[];
  canEdit: boolean;
  onOpen: (card: KanbanCard) => void;
  onMove: (card: KanbanCard, columnId: number) => void;
  onArchive: (card: KanbanCard) => void;
  onDuplicate: (card: KanbanCard) => void;
}

export const KanbanCardView: React.FC<Props> = ({ card, columns, canEdit, onOpen, onMove, onArchive, onDuplicate }) => {
  const sortable = useSortable({ id: `card-${card.id}`, data: { type: 'card', card } });
  const col = columns.find((c) => c.id === card.column_id);
  const colColor = col?.color;
  const isComplete = colColor?.endsWith(';complete');
  const baseColor = colColor ? colColor.split(';')[0] : '';
  const style = {
    transform: CSS.Transform.toString(sortable.transform),
    transition: sortable.transition,
    opacity: sortable.isDragging ? 0.45 : 1,
    '--kanban-card-accent': baseColor || 'var(--color-primary)',
  } as React.CSSProperties;

  return (
    <article
      ref={sortable.setNodeRef}
      className={`kanban-task-card ${isComplete ? 'kanban-task-card--complete' : ''}`}
      style={style}
      onClick={() => onOpen(card)}
    >
      {!isComplete && baseColor && <div className="kanban-task-card__accent" />}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
        <strong className="kanban-task-card__title">{card.title}</strong>
        <button
          ref={sortable.setActivatorNodeRef}
          {...sortable.attributes}
          {...sortable.listeners}
          className="action-btn"
          style={{ padding: 6, minWidth: 30 }}
          onClick={(event) => event.stopPropagation()}
          title="Arrastar card"
        >
          <GripVertical size={14} />
        </button>
      </div>
      {card.description && <p className="kanban-task-card__description">{card.description}</p>}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', margin: '8px 0' }}>
        {card.labels.map((label) => (
          <span key={label.id} className="badge kanban-task-card__label" style={{ backgroundColor: `${label.color}22`, borderColor: label.color }}>{label.name}</span>
        ))}
      </div>
      <div className="kanban-task-card__meta">
        <span>{card.checklist_total ? `${card.checklist_done}/${card.checklist_total}` : 'Sem checklist'}</span>
        <span style={{ display: 'inline-flex', gap: 8 }}>
          <UserRound size={14} /> {card.assignees.length || 0}
          <MessageCircle size={14} />
          <Paperclip size={14} />
        </span>
      </div>
      {canEdit && (
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }} onClick={(event) => event.stopPropagation()}>
          <select className="form-input kanban-task-card__select" style={{ minWidth: 150 }} value={card.column_id} onChange={(event) => onMove(card, Number(event.target.value))}>
            {columns.filter((item) => !item.is_archived).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <button className="action-btn" onClick={() => onDuplicate(card)} title="Duplicar"><Copy size={13} /></button>
          <button className="action-btn" onClick={() => onArchive(card)} title="Arquivar"><Archive size={13} /></button>
        </div>
      )}
    </article>
  );
};
