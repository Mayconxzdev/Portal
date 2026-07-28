import React, { useEffect, useMemo, useState } from 'react';
import { Button } from '../ui/Button';
import { Checkbox } from '../ui/Checkbox';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { Select } from '../ui/Select';
import { BoardViewConfig, KanbanBoard } from './types';
import { apiJson } from './kanbanApi';

interface Props {
  board: KanbanBoard;
  isOpen: boolean;
  onClose: () => void;
  onChanged: () => Promise<void>;
}

const defaultColumns = ['title', 'status', 'priority', 'due_date', 'assignees', 'labels', 'updated_at'];
const widthOptions = [
  { value: '0', label: 'Automática' },
  { value: '120', label: 'Pequena' },
  { value: '200', label: 'Média' },
  { value: '300', label: 'Grande' },
];

const viewTypeLabels: Record<string, string> = {
  BOARD: 'Quadro',
  LIST: 'Lista',
  TV_BOARD: 'TV Cards',
  TV_LIST: 'TV Lista',
  PRODUCTION_LIST: 'Produção Lista',
  PRODUCTION_BOARD: 'Produção Cards',
};

export const BoardViewsDrawer: React.FC<Props> = ({ board, isOpen, onClose, onChanged }) => {
  const [views, setViews] = useState<BoardViewConfig[]>(board.views || []);
  const [draft, setDraft] = useState({ name: '', view_type: 'LIST', density: 'COMFORTABLE' });
  const [editingView, setEditingView] = useState<BoardViewConfig | null>(null);
  const [visibleColumnsList, setVisibleColumnsList] = useState<string[]>([]);
  const [colWidths, setColWidths] = useState<Record<string, number>>({});
  const [sortBy, setSortBy] = useState('position');
  const [groupBy, setGroupBy] = useState('');
  const [colorRules, setColorRules] = useState('');
  const [density, setDensity] = useState<'COMFORTABLE' | 'COMPACT' | 'DENSE'>('COMFORTABLE');
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setViews(await apiJson<BoardViewConfig[]>(`/api/v1/kanban/boards/${board.id}/views`));
  };

  useEffect(() => {
    if (isOpen) load().catch((err) => setError(err.message));
  }, [isOpen, board.id]);

  const allAvailableColumns = useMemo(() => [
    { key: 'title', label: 'Título' },
    { key: 'status', label: 'Status' },
    { key: 'priority', label: 'Prioridade' },
    { key: 'due_date', label: 'Prazo / Entrega' },
    { key: 'assignees', label: 'Responsáveis' },
    { key: 'labels', label: 'Etiquetas' },
    { key: 'checklist', label: 'Checklist' },
    { key: 'updated_at', label: 'Última atualização' },
    { key: 'description', label: 'Descrição' },
    ...(board.custom_fields || []).filter((field) => field.is_active).map((field) => ({ key: field.key, label: field.name })),
  ], [board.custom_fields]);

  const columnLabel = (key: string) => allAvailableColumns.find((column) => column.key === key)?.label || key;

  const create = async () => {
    if (!draft.name.trim()) return;
    setError(null);
    try {
      await apiJson(`/api/v1/kanban/boards/${board.id}/views`, {
        method: 'POST',
        body: JSON.stringify({
          name: draft.name,
          view_type: draft.view_type,
          density: draft.density,
          visible_columns: defaultColumns,
          column_order: defaultColumns,
        }),
      });
      setDraft({ ...draft, name: '' });
      await load();
      await onChanged();
    } catch (err: any) {
      setError(err.message || 'Não foi possível criar a visualização.');
    }
  };

  const patch = async (view: BoardViewConfig, payload: Record<string, unknown>) => {
    setError(null);
    try {
      await apiJson(`/api/v1/kanban/board-views/${view.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
      await load();
      await onChanged();
    } catch (err: any) {
      setError(err.message || 'Não foi possível salvar a visualização.');
    }
  };

  const startEditing = (view: BoardViewConfig) => {
    setEditingView(view);
    const visible = view.visible_columns?.length ? view.visible_columns : defaultColumns;
    const order = view.column_order?.length ? view.column_order : visible;
    setVisibleColumnsList(order.filter((key) => visible.includes(key)));
    setColWidths(view.column_widths || {});
    setSortBy(view.sort_by || 'position');
    setGroupBy(view.group_by || '');
    const rules = view.color_rules || {};
    setColorRules(Object.keys(rules).find((key) => rules[key] === true) || '');
    setDensity(view.density || 'COMFORTABLE');
  };

  const saveConfig = async () => {
    if (!editingView) return;
    await patch(editingView, {
      visible_columns: visibleColumnsList,
      column_order: visibleColumnsList,
      column_widths: colWidths,
      sort_by: sortBy,
      group_by: groupBy || null,
      color_rules: colorRules ? { [colorRules]: true } : null,
      density,
    });
    setEditingView(null);
  };

  const restoreDefaults = async () => {
    if (!editingView) return;
    setVisibleColumnsList(defaultColumns);
    setColWidths({});
    setSortBy('position');
    setGroupBy('');
    setColorRules('');
    setDensity('COMFORTABLE');
  };

  const handleToggleColumn = (colKey: string) => {
    setVisibleColumnsList((current) => current.includes(colKey) ? current.filter((key) => key !== colKey) : [...current, colKey]);
  };

  const moveColumn = (index: number, direction: 'up' | 'down') => {
    setVisibleColumnsList((current) => {
      const next = [...current];
      const targetIndex = direction === 'up' ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= next.length) return current;
      [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
      return next;
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Visualizações do quadro - ${board.name}`} size="lg" footer={<Button variant="ghost" onClick={onClose}>Fechar</Button>}>
      <div style={{ display: 'grid', gap: 20 }}>
        {error && (
          <div className="offline-banner">
            <div>
              <div className="offline-banner-title">Não foi possível concluir a ação</div>
              <div className="offline-banner-text">{error}</div>
            </div>
          </div>
        )}

        {editingView ? (
          <div className="glass-card" style={{ padding: 20, display: 'grid', gap: 16, border: '1px solid var(--color-primary)', background: 'rgba(139, 92, 246, 0.03)', borderRadius: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ color: 'var(--text-primary)', fontSize: 15 }}>Configurar: {editingView.name}</strong>
              <Button size="sm" variant="ghost" onClick={() => setEditingView(null)}>Cancelar</Button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <div style={{ display: 'grid', gap: 12 }}>
                <span className="form-label" style={{ fontSize: 13, fontWeight: 700 }}>Colunas visíveis e ordem</span>
                <div style={{ maxHeight: 300, overflowY: 'auto', display: 'grid', gap: 6, paddingRight: 6 }}>
                  {allAvailableColumns.map((column) => {
                    const isVisible = visibleColumnsList.includes(column.key);
                    const indexInOrder = visibleColumnsList.indexOf(column.key);
                    return (
                      <div key={column.key} style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: 8, alignItems: 'center', padding: '6px 10px', background: 'var(--surface-panel-soft)', border: '1px solid var(--semantic-border)', borderRadius: 6 }}>
                        <Checkbox label={column.label} checked={isVisible} onChange={() => handleToggleColumn(column.key)} />
                        {isVisible && (
                          <div style={{ display: 'flex', gap: 4 }}>
                            <button type="button" disabled={indexInOrder === 0} onClick={() => moveColumn(indexInOrder, 'up')} className="btn btn-ghost btn-sm">↑</button>
                            <button type="button" disabled={indexInOrder === visibleColumnsList.length - 1} onClick={() => moveColumn(indexInOrder, 'down')} className="btn btn-ghost btn-sm">↓</button>
                          </div>
                        )}
                        {isVisible && (
                          <Select
                            aria-label={`Largura de ${column.label}`}
                            value={String(colWidths[column.key] || 0)}
                            onChange={(event) => setColWidths({ ...colWidths, [column.key]: Number(event.target.value) })}
                            options={widthOptions}
                            style={{ marginBottom: 0, width: 125, padding: '2px 6px', fontSize: 11.5 }}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: 'grid', gap: 14 }}>
                <Select label="Densidade" value={density} onChange={(event) => setDensity(event.target.value as any)} options={[
                  { value: 'COMFORTABLE', label: 'Confortável' },
                  { value: 'COMPACT', label: 'Compacta' },
                  { value: 'DENSE', label: 'Densa' },
                ]} />
                <Select label="Ordenação" value={sortBy} onChange={(event) => setSortBy(event.target.value)} options={[
                  { value: 'position', label: 'Manual' },
                  { value: 'due_date', label: 'Por entrega/prazo' },
                  { value: 'priority', label: 'Por prioridade' },
                  { value: 'updated_at', label: 'Por atualização recente' },
                  ...((board.custom_fields || []).some((field) => field.key === 'op') ? [{ value: 'custom.op', label: 'Por OP/código' }] : []),
                ]} />
                <Select label="Agrupamento" value={groupBy} onChange={(event) => setGroupBy(event.target.value)} options={[
                  { value: '', label: 'Nenhum' },
                  { value: 'column', label: 'Por status/coluna' },
                  { value: 'priority', label: 'Por prioridade' },
                  { value: 'assignee', label: 'Por responsável' },
                  { value: 'label', label: 'Por etiqueta' },
                  { value: 'due_date', label: 'Por entrega/prazo' },
                ]} />
                <Select label="Regra de cor" value={colorRules} onChange={(event) => setColorRules(event.target.value)} options={[
                  { value: '', label: 'Sem destaque' },
                  { value: 'status', label: 'Por status' },
                  { value: 'priority', label: 'Por prioridade' },
                  { value: 'overdue', label: 'Por atraso' },
                  { value: 'label', label: 'Por etiqueta' },
                ]} />
                <div style={{ border: '1px solid var(--border-color)', borderRadius: 8, padding: 10, background: 'rgba(15,23,42,0.6)' }}>
                  <strong style={{ color: 'var(--text-primary)', fontSize: 12 }}>Prévia da lista</strong>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                    {visibleColumnsList.length === 0 ? <span className="text-muted">Nenhuma coluna selecionada.</span> : visibleColumnsList.slice(0, 8).map((key) => (
                      <span key={key} className="badge badge-neutral">{columnLabel(key)}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 12, marginTop: 4 }}>
              <Button variant="secondary" onClick={restoreDefaults}>Restaurar padrão</Button>
              <Button variant="primary" onClick={saveConfig}>Salvar configuração</Button>
            </div>
          </div>
        ) : (
          <div className="glass-card" style={{ padding: 12, display: 'grid', gap: 10 }}>
            <strong style={{ color: 'var(--text-primary)' }}>Nova visualização</strong>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px 160px auto', gap: 10, alignItems: 'end' }}>
              <Input label="Nome" placeholder="Ex: Lista de entrega" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
              <Select label="Tipo" value={draft.view_type} onChange={(event) => setDraft({ ...draft, view_type: event.target.value })} options={[
                { value: 'BOARD', label: 'Quadro' },
                { value: 'LIST', label: 'Lista' },
                { value: 'TV_BOARD', label: 'TV Cards' },
                { value: 'TV_LIST', label: 'TV Lista' },
                { value: 'PRODUCTION_LIST', label: 'Produção Lista' },
                { value: 'PRODUCTION_BOARD', label: 'Produção Cards' },
              ]} />
              <Select label="Densidade" value={draft.density} onChange={(event) => setDraft({ ...draft, density: event.target.value })} options={[
                { value: 'COMFORTABLE', label: 'Confortável' },
                { value: 'COMPACT', label: 'Compacta' },
                { value: 'DENSE', label: 'Densa' },
              ]} />
              <Button onClick={create}>Criar</Button>
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gap: 10 }}>
          <strong style={{ color: 'var(--text-primary)', fontSize: 14 }}>Visualizações salvas</strong>
          {views.map((view) => (
            <div key={view.id} className="glass-card" style={{ padding: 10, display: 'grid', gridTemplateColumns: '1fr 140px 120px auto auto auto', gap: 10, alignItems: 'center' }}>
              <Input aria-label={`Nome da visualização ${view.name}`} value={view.name} onChange={(event) => patch(view, { name: event.target.value })} style={{ marginBottom: 0, fontSize: 13 }} />
              <span className="badge badge-neutral" style={{ fontSize: 10 }}>{viewTypeLabels[view.view_type] || view.view_type}</span>
              <Checkbox label="Padrão" checked={view.is_default} onChange={() => apiJson(`/api/v1/kanban/board-views/${view.id}/set-default`, { method: 'POST' }).then(load).then(onChanged)} />
              <Button size="sm" variant="secondary" onClick={() => startEditing(view)} disabled={!!editingView}>Configurar</Button>
              <Button size="sm" variant="secondary" onClick={() => apiJson(`/api/v1/kanban/board-views/${view.id}/duplicate`, { method: 'POST' }).then(load).then(onChanged)}>Duplicar</Button>
              <Button size="sm" variant="danger" onClick={() => apiJson(`/api/v1/kanban/board-views/${view.id}`, { method: 'DELETE' }).then(load).then(onChanged)}>Remover</Button>
            </div>
          ))}
        </div>
      </div>
    </Modal>
  );
};
