import React, { useState, useEffect } from 'react';
import { Button } from '../ui/Button';
import { Checkbox } from '../ui/Checkbox';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { ConfirmDialog } from '../ui/ConfirmDialog';
import { KanbanBoard, KanbanColumn } from './types';
import { Select } from '../ui/Select';
import { apiJson } from './kanbanApi';
import { Plus, Trash, Save, Check } from 'lucide-react';

interface Props {
  board: KanbanBoard;
  isOpen: boolean;
  onClose: () => void;
  onChanged: () => Promise<void>;
}

export const CreateColumnModal: React.FC<Props> = ({ board, isOpen, onClose, onChanged }) => {
  // Estado para criar uma nova coluna
  const [newColumn, setNewColumn] = useState({
    name: '',
    color: '#3b82f6',
    color_mode: 'compact' as 'compact' | 'complete',
    wip_limit: '',
    is_done_column: false
  });
  const [creating, setCreating] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [deleteColData, setDeleteColData] = useState<{ id: number, name: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Estado local para a edição de colunas existentes (carregado do board)
  const [editList, setEditList] = useState<Record<number, {
    name: string;
    color: string;
    color_mode: 'compact' | 'complete';
    wip_limit: string;
    is_done_column: boolean;
    saving?: boolean;
    success?: boolean;
  }>>({});

  useEffect(() => {
    if (isOpen && board.columns) {
      const initialEdits: typeof editList = {};
      // Ordenar colunas pela posição
      const sorted = [...board.columns].sort((a, b) => a.position - b.position);
      sorted.forEach((col) => {
        const isComplete = col.color?.endsWith(';complete') || false;
        const baseColor = col.color ? col.color.split(';')[0] : '#64748b';
        initialEdits[col.id] = {
          name: col.name,
          color: baseColor,
          color_mode: isComplete ? 'complete' : 'compact',
          wip_limit: col.wip_limit !== undefined && col.wip_limit !== null ? String(col.wip_limit) : '',
          is_done_column: col.is_done_column,
          saving: false,
          success: false
        };
      });
      setEditList(initialEdits);
      setError(null);
    }
  }, [isOpen, board.columns]);

  // Função para criar uma coluna nova
  const handleCreate = async () => {
    if (!newColumn.name.trim()) return;
    setCreating(true);
    setError(null);
    const saveColor = newColumn.color_mode === 'complete' ? `${newColumn.color};complete` : newColumn.color;
    try {
      await apiJson(`/api/v1/kanban/boards/${board.id}/columns`, {
        method: 'POST',
        body: JSON.stringify({
          name: newColumn.name,
          color: saveColor,
          wip_limit: newColumn.wip_limit ? Number(newColumn.wip_limit) : undefined,
          is_done_column: newColumn.is_done_column,
        }),
      });
      setNewColumn({ name: '', color: '#3b82f6', color_mode: 'compact', wip_limit: '', is_done_column: false });
      await onChanged();
    } catch (err: any) {
      setError(err.message || 'Falha ao criar coluna.');
    } finally {
      setCreating(false);
    }
  };

  // Função para salvar uma coluna existente
  const handleSave = async (id: number) => {
    const colDraft = editList[id];
    if (!colDraft || !colDraft.name.trim()) return;

    setEditList(prev => ({
      ...prev,
      [id]: { ...prev[id], saving: true, success: false }
    }));
    setError(null);

    const saveColor = colDraft.color_mode === 'complete' ? `${colDraft.color};complete` : colDraft.color;
    try {
      await apiJson(`/api/v1/kanban/columns/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: colDraft.name,
          color: saveColor,
          wip_limit: colDraft.wip_limit ? Number(colDraft.wip_limit) : null,
          is_done_column: colDraft.is_done_column,
        }),
      });
      
      setEditList(prev => ({
        ...prev,
        [id]: { ...prev[id], saving: false, success: true }
      }));
      setTimeout(() => {
        setEditList(prev => (prev[id] ? { ...prev, [id]: { ...prev[id], success: false } } : prev));
      }, 2500);

      await onChanged();
    } catch (err: any) {
      setError(err.message || 'Falha ao salvar coluna.');
      setEditList(prev => ({
        ...prev,
        [id]: { ...prev[id], saving: false }
      }));
    }
  };

  // Função para deletar uma coluna
  const handleDelete = async (id: number, name: string) => {
    setDeleteColData({ id, name });
    setDeleteConfirmOpen(true);
  };

  const proceedDeleteColumn = async (id: number) => {
    setError(null);
    try {
      await apiJson(`/api/v1/kanban/columns/${id}`, { method: 'DELETE' });
      await onChanged();
    } catch (err: any) {
      setError(err.message || 'Falha ao excluir coluna.');
    }
  };

  // Atualizar dados de edição locais da coluna
  const updateDraft = (id: number, fields: Partial<(typeof editList)[number]>) => {
    setEditList(prev => ({
      ...prev,
      [id]: { ...prev[id], ...fields }
    }));
  };

  return (
    <>
      <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Gerenciar colunas do quadro"
      size="lg"
      footer={<Button variant="ghost" onClick={onClose}>Fechar</Button>}
    >
      <div style={{ display: 'grid', gap: 20 }}>
        {error && (
          <div style={{ color: '#ef4444', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: 10, fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* Seção Adicionar Nova Coluna */}
        <div style={{ background: 'var(--surface-panel-soft)', border: '1px solid var(--border-color)', borderRadius: 8, padding: 14 }}>
          <strong style={{ display: 'block', color: 'var(--text-primary)', fontSize: 14, marginBottom: 12 }}>Adicionar nova coluna</strong>
          <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr 1fr 100px 60px auto', gap: 12, alignItems: 'end' }}>
            <Input
              label="Nome da coluna"
              value={newColumn.name}
              onChange={(e) => setNewColumn({ ...newColumn, name: e.target.value })}
              placeholder="Ex: Em separação"
            />
            <Input
              label="Limite WIP"
              type="number"
              min={0}
              value={newColumn.wip_limit}
              onChange={(e) => setNewColumn({ ...newColumn, wip_limit: e.target.value })}
              placeholder="Sem limite"
            />
            <div style={{ paddingBottom: 10 }}>
              <Checkbox
                label="Concluído"
                checked={newColumn.is_done_column}
                onChange={(e) => setNewColumn({ ...newColumn, is_done_column: e.target.checked })}
              />
            </div>
            <Select
              label="Modo Cor"
              value={newColumn.color_mode}
              onChange={(e) => setNewColumn({ ...newColumn, color_mode: e.target.value as any })}
              options={[
                { value: 'compact', label: 'Compacto' },
                { value: 'complete', label: 'Completo' }
              ]}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'center' }}>
              <label style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 600 }}>Cor</label>
              <input
                type="color"
                value={newColumn.color}
                onChange={(e) => setNewColumn({ ...newColumn, color: e.target.value })}
                style={colorPickerStyle}
                title="Selecione uma cor"
              />
            </div>
            <Button onClick={handleCreate} isLoading={creating} leftIcon={<Plus size={15} />}>
              Criar
            </Button>
          </div>
        </div>

        {/* Seção Lista de Colunas Existentes */}
        <div>
          <strong style={{ display: 'block', color: 'var(--text-primary)', fontSize: 14, marginBottom: 10 }}>Colunas atuais</strong>
          <div style={{ display: 'grid', gap: 10 }}>
            {board.columns && board.columns.length === 0 && (
              <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontStyle: 'italic' }}>Nenhuma coluna criada ainda.</span>
            )}
            
            {[...board.columns].sort((a, b) => a.position - b.position).map((col) => {
              const isColComplete = col.color?.endsWith(';complete') || false;
              const baseColColor = col.color ? col.color.split(';')[0] : '#64748b';
              const draft = editList[col.id] || {
                name: col.name,
                color: baseColColor,
                color_mode: isColComplete ? 'complete' : 'compact',
                wip_limit: col.wip_limit !== undefined && col.wip_limit !== null ? String(col.wip_limit) : '',
                is_done_column: col.is_done_column
              };
              
              return (
                <div 
                  key={col.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1.5fr 90px 90px 100px 50px 100px',
                    gap: 12,
                    alignItems: 'center',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid rgba(255,255,255,0.05)',
                    borderRadius: 6,
                    padding: 8
                  }}
                >
                  <input
                    type="text"
                    className="form-input"
                    value={draft.name}
                    onChange={(e) => updateDraft(col.id, { name: e.target.value })}
                    style={{ margin: 0, height: 36, padding: '4px 8px', fontSize: 13 }}
                  />
                  <input
                    type="number"
                    className="form-input"
                    min={0}
                    placeholder="Sem limite"
                    value={draft.wip_limit}
                    onChange={(e) => updateDraft(col.id, { wip_limit: e.target.value })}
                    style={{ margin: 0, height: 36, padding: '4px 8px', fontSize: 13 }}
                  />
                  <Checkbox
                    label="Concluído"
                    checked={draft.is_done_column}
                    onChange={(e) => updateDraft(col.id, { is_done_column: e.target.checked })}
                  />
                  <Select
                    value={draft.color_mode}
                    onChange={(e) => updateDraft(col.id, { color_mode: e.target.value as any })}
                    options={[
                      { value: 'compact', label: 'Compacto' },
                      { value: 'complete', label: 'Completo' }
                    ]}
                    style={{ margin: 0 }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'center' }}>
                    <input
                      type="color"
                      value={draft.color}
                      onChange={(e) => updateDraft(col.id, { color: e.target.value })}
                      style={colorPickerStyle}
                      title="Selecione uma cor para esta coluna"
                    />
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Button
                      size="sm"
                      variant={draft.success ? 'success' : 'secondary'}
                      onClick={() => handleSave(col.id)}
                      disabled={draft.saving}
                      title="Salvar alterações da coluna"
                      style={{ padding: '0 8px', height: 34, flex: 1 }}
                    >
                      {draft.saving ? '...' : draft.success ? <Check size={14} /> : <Save size={14} />}
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => handleDelete(col.id, col.name)}
                      title="Excluir coluna"
                      style={{ padding: '0 8px', height: 34 }}
                    >
                      <Trash size={14} />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Modal>

    <ConfirmDialog
      isOpen={deleteConfirmOpen}
      onClose={() => { setDeleteConfirmOpen(false); setDeleteColData(null); }}
      onConfirm={async () => {
        if (deleteColData) {
          const { id } = deleteColData;
          setDeleteConfirmOpen(false);
          setDeleteColData(null);
          await proceedDeleteColumn(id);
        }
      }}
      title="Excluir coluna"
      message={
        (() => {
          if (!deleteColData) return '';
          const activeCol = board.columns.find(c => c.id === deleteColData.id);
          const hasCards = activeCol && activeCol.cards && activeCol.cards.length > 0;
          return hasCards
            ? `A coluna "${deleteColData.name}" contém ${activeCol.cards.length} tarefa(s) ativa(s). Se você a excluir, TODAS as tarefas dessa coluna serão excluídas. Deseja continuar?`
            : `Deseja realmente excluir a coluna "${deleteColData.name}"?`;
        })()
      }
      confirmText="Excluir"
      cancelText="Cancelar"
      variant="danger"
    />
    </>
  );
};

const colorPickerStyle: React.CSSProperties = {
  width: '38px',
  height: '38px',
  padding: 0,
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  background: 'none',
  cursor: 'pointer',
  display: 'block'
};
