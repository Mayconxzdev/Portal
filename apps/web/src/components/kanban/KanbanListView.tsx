import React, { useEffect, useMemo, useState } from 'react';
import { Calendar, CheckSquare, Search } from 'lucide-react';
import { apiJson, priorityLabels } from './kanbanApi';
import { KanbanBoard, KanbanCard, ListData } from './types';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Badge } from '../ui/Badge';
import { PriorityBadge } from '../ui/PriorityBadge';
import { LoadingState } from '../ui/LoadingState';

interface Props {
  board: KanbanBoard;
  onOpenCard: (card: KanbanCard) => void;
}

const humanColumn: Record<string, string> = {
  title: 'Tarefa',
  status: 'Status',
  priority: 'Prioridade',
  due_date: 'Prazo',
  assignees: 'Responsáveis',
  labels: 'Etiquetas',
  checklist: 'Checklist',
  updated_at: 'Atualização',
  description: 'Descrição',
  op: 'OP',
  cliente: 'Cliente',
  modelo: 'Modelo',
  produto: 'Produto',
  tensao: 'Tensão',
  qtd: 'Qtd',
  inicio: 'Início',
  entrega: 'Entrega',
  setor: 'Setor',
  pendencia: 'Pendência',
};

const priorityOrder: Record<string, number> = { URGENT: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
const densityPadding = { COMFORTABLE: '12px 10px', COMPACT: '9px 10px', DENSE: '6px 8px' };

const getCustom = (card: KanbanCard, key: string) => String(card.custom_fields?.[key] ?? '');
const dueTime = (card: KanbanCard) => card.due_date ? new Date(card.due_date).getTime() : Number.MAX_SAFE_INTEGER;

export const KanbanListView: React.FC<Props> = ({ board, onOpenCard }) => {
  const [data, setData] = useState<ListData | null>(null);
  const [search, setSearch] = useState('');
  const [priority, setPriority] = useState('');

  const load = async () => {
    setData(await apiJson<ListData>(`/api/v1/kanban/boards/${board.id}/list-data`));
  };

  useEffect(() => {
    load();
  }, [board.id]);

  const visibleSafe = useMemo(() => {
    if (!data) return [];
    const visible = data.visible_columns?.length ? data.visible_columns.filter((c) => c !== 'priority') : ['title', 'status', 'due_date', 'assignees', 'labels', 'updated_at'];
    const ordered = data.column_order?.length ? data.column_order.filter((c) => c !== 'priority') : visible;
    const visibleSet = new Set(visible);
    const systemColumns = new Set(['title', 'status', 'due_date', 'assignees', 'labels', 'checklist', 'updated_at', 'description']);
    const activeCustomKeys = new Set(data.custom_fields.filter((field) => field.is_active).map((field) => field.key));
    return ordered.filter((key) => visibleSet.has(key) && (systemColumns.has(key) || activeCustomKeys.has(key)));
  }, [data]);

  const cards = useMemo(() => {
    if (!data) return [];
    const text = search.toLowerCase();
    const sortBy = data.list_config?.sort_by || 'position';
    return [...data.cards]
      .filter((card) => {
        const customText = Object.values(card.custom_fields || {}).join(' ').toLowerCase();
        if (priority && card.priority !== priority) return false;
        if (text && !`${card.title} ${card.description || ''} ${customText}`.toLowerCase().includes(text)) return false;
        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'due_date') return dueTime(a) - dueTime(b);
        if (sortBy === 'priority') return (priorityOrder[a.priority] ?? 9) - (priorityOrder[b.priority] ?? 9);
        if (sortBy === 'updated_at') return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
        if (sortBy.startsWith('custom.')) return getCustom(a, sortBy.replace('custom.', '')).localeCompare(getCustom(b, sortBy.replace('custom.', '')), 'pt-BR', { numeric: true });
        return 0;
      });
  }, [data, search, priority]);

  if (!data) return <LoadingState text="Carregando lista do quadro..." />;

  const listConfig = data.list_config;
  const density = listConfig?.density || 'COMFORTABLE';
  const rowPadding = densityPadding[density] || densityPadding.COMFORTABLE;
  const groupBy = listConfig?.group_by || '';
  const colorRules = listConfig?.color_rules || {};
  const columnWidths = data.column_widths || {};

  const groupValue = (card: any) => {
    if (groupBy === 'column') return card.status || 'Sem status';
    if (groupBy === 'priority') return priorityLabels[card.priority as keyof typeof priorityLabels] || card.priority;
    if (groupBy === 'assignee') return card.assignees?.[0]?.username || 'Sem responsável';
    if (groupBy === 'label') return card.labels?.[0]?.name || 'Sem etiqueta';
    if (groupBy === 'due_date') return card.due_date ? new Date(card.due_date).toLocaleDateString('pt-BR') : 'Sem prazo';
    return 'Todas as tarefas';
  };

  const groupedCards = cards.reduce<Record<string, typeof cards>>((acc, card) => {
    const key = groupValue(card);
    acc[key] = acc[key] || [];
    acc[key].push(card);
    return acc;
  }, {});

  const rowAccentFor = (card: any) => {
    const col = data.columns?.find((c) => c.id === card.column_id);
    const colColor = col?.color;
    if (colColor?.endsWith(';complete')) {
      const baseColor = colColor.split(';')[0];
      return { '--kanban-list-row-accent': baseColor, '--kanban-list-row-tone': 'complete' } as React.CSSProperties;
    }
    const isOverdue = card.due_date && new Date(card.due_date) < new Date();
    if (colorRules.overdue && isOverdue) return { '--kanban-list-row-accent': '#dc2626', '--kanban-list-row-tone': 'danger' } as React.CSSProperties;
    if (colorRules.priority && card.priority === 'URGENT') return { '--kanban-list-row-accent': '#dc2626', '--kanban-list-row-tone': 'danger' } as React.CSSProperties;
    if (colorRules.priority && card.priority === 'HIGH') return { '--kanban-list-row-accent': '#d97706', '--kanban-list-row-tone': 'warning' } as React.CSSProperties;
    if (colorRules.label && card.labels?.[0]?.color) return { '--kanban-list-row-accent': card.labels[0].color, '--kanban-list-row-tone': 'label' } as React.CSSProperties;
    if (colorRules.status) return { '--kanban-list-row-accent': '#2563eb', '--kanban-list-row-tone': 'status' } as React.CSSProperties;
    return {};
  };

  const valueFor = (card: any, key: string) => {
    if (key === 'title') return <strong className="kanban-list-title">{card.title}</strong>;
    if (key === 'status') {
      const col = data.columns?.find((c) => c.id === card.column_id);
      const colColor = col?.color;
      const baseColor = colColor ? colColor.split(';')[0] : '';
      return (
        <Badge
          variant="neutral"
          style={baseColor ? { backgroundColor: `${baseColor}22`, color: baseColor, borderColor: baseColor } : undefined}
        >
          {card.status || col?.name || 'Sem status'}
        </Badge>
      );
    }
    if (key === 'priority') return <PriorityBadge priority={card.priority} />;
    if (key === 'due_date') return card.due_date ? <span><Calendar size={12} /> {new Date(card.due_date).toLocaleDateString('pt-BR')}</span> : <span className="text-muted">Sem prazo</span>;
    if (key === 'assignees') return card.assignees?.length ? card.assignees.map((item: any) => item.username).join(', ') : <span className="text-muted">Sem responsável</span>;
    if (key === 'labels') return <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>{card.labels?.map((label: any) => <span key={label.id} className="badge" style={{ borderColor: label.color, color: label.color }}>{label.name}</span>)}</div>;
    if (key === 'checklist') return <span><CheckSquare size={12} /> {card.checklist_done}/{card.checklist_total}</span>;
    if (key === 'updated_at') return new Date(card.updated_at).toLocaleString('pt-BR');
    if (key === 'description') return card.description || <span className="text-muted">-</span>;
    return card.custom_fields?.[key] !== undefined ? String(card.custom_fields[key]) : <span className="text-muted">-</span>;
  };

  const renderRows = (items: typeof cards) => items.map((card) => (
    <tr key={card.id} className="kanban-list-row" onClick={() => onOpenCard(card)} style={rowAccentFor(card)}>
      {visibleSafe.map((key) => (
        <td key={key} style={{ padding: rowPadding, width: columnWidths[key] ? `${columnWidths[key]}px` : undefined, minWidth: columnWidths[key] ? `${columnWidths[key]}px` : 110, fontSize: density === 'DENSE' ? 12 : 13 }}>
          {valueFor(card, key)}
        </td>
      ))}
    </tr>
  ));

  return (
    <section className="glass-card kanban-list-shell" style={{ padding: 16, display: 'grid', gap: 12 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 10 }}>
        <Input leftIcon={<Search size={15} />} placeholder="Buscar por tarefa, OP, cliente, modelo ou pendência..." value={search} onChange={(event) => setSearch(event.target.value)} />
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="data-table" style={{ width: '100%', borderCollapse: 'separate', borderSpacing: density === 'DENSE' ? '0 3px' : '0 6px', minWidth: 900 }}>
          <thead>
            <tr>{visibleSafe.map((key) => <th key={key} style={{ textAlign: 'left', fontSize: 12, padding: '8px 10px', width: columnWidths[key] ? `${columnWidths[key]}px` : undefined }}>{humanColumn[key] || key}</th>)}</tr>
          </thead>
          <tbody>
            {groupBy ? Object.entries(groupedCards).map(([group, items]) => (
              <React.Fragment key={group}>
                <tr><td className="kanban-list-group" colSpan={visibleSafe.length} style={{ fontSize: 12, fontWeight: 700, padding: '12px 10px 4px' }}>{group}</td></tr>
                {renderRows(items)}
              </React.Fragment>
            )) : renderRows(cards)}
          </tbody>
        </table>
        {cards.length === 0 && <p className="text-muted" style={{ textAlign: 'center', padding: 24 }}>Nenhuma tarefa encontrada nesta lista.</p>}
      </div>
    </section>
  );
};
