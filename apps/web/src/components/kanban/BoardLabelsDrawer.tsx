import React, { useEffect, useState } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { KanbanBoard, KanbanLabel } from './types';
import { apiJson } from './kanbanApi';
import { AlertCircle, Check, HelpCircle } from 'lucide-react';

interface Props {
  board: KanbanBoard;
  isOpen: boolean;
  onClose: () => void;
  onChanged: () => Promise<void>;
}

export const BoardLabelsDrawer: React.FC<Props> = ({ board, isOpen, onClose, onChanged }) => {
  const [draft, setDraft] = useState({ name: '', color: '#3b82f6' });
  const [labels, setLabels] = useState<KanbanLabel[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const data = await apiJson<KanbanLabel[]>(`/api/v1/kanban/boards/${board.id}/labels?include_inactive=true`);
    setLabels(data);
  };

  useEffect(() => {
    if (isOpen) {
      load().catch(() => setLabels(board.labels || []));
      setError(null);
    }
  }, [isOpen, board.id]);

  const create = async () => {
    if (!draft.name.trim()) return;
    try {
      await apiJson(`/api/v1/kanban/boards/${board.id}/labels`, { method: 'POST', body: JSON.stringify(draft) });
      setDraft({ name: '', color: '#3b82f6' });
      await load();
      await onChanged();
    } catch (err: any) {
      setError(err.message || 'Falha ao criar etiqueta.');
    }
  };

  const update = async (label: KanbanLabel, payload: Record<string, unknown>) => {
    try {
      await apiJson(`/api/v1/kanban/labels/${label.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
      await load();
      await onChanged();
    } catch (err: any) {
      setError(err.message || 'Falha ao atualizar etiqueta.');
    }
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      title="Etiquetas do quadro" 
      size="md" 
      footer={<Button variant="ghost" onClick={onClose}>Fechar</Button>}
    >
      <div style={{ display: 'grid', gap: 16 }}>
        {/* Painel Informativo sobre Diferença de Etiquetas e Prioridades */}
        <div style={{ 
          background: 'rgba(59, 130, 246, 0.08)', 
          border: '1px solid rgba(59, 130, 246, 0.2)', 
          borderRadius: 8, 
          padding: 12,
          fontSize: 12,
          color: 'var(--text-primary)',
          display: 'grid',
          gap: 6
        }}>
          <strong style={{ color: '#93c5fd', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <HelpCircle size={15} /> Etiquetas vs Prioridades
          </strong>
          <span>
            • <strong>Prioridades</strong> são níveis fixos de entrega do card (Urgente, Alta, Média, Baixa) que determinam a criticidade automática. Cada card possui exatamente uma.
          </span>
          <span>
            • <strong>Etiquetas</strong> são tags personalizáveis que você cria livremente para classificar cards (ex: <em>Aguardando, Elétrica, Setor B</em>). Você pode adicionar várias em um mesmo card.
          </span>
        </div>

        {error && (
          <div style={{ color: '#ef4444', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: 8, fontSize: 12 }}>
            {error}
          </div>
        )}

        {/* Criação de Nova Etiqueta */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 60px auto', gap: 10, alignItems: 'end' }}>
          <Input 
            placeholder="Nome da nova etiqueta..." 
            value={draft.name} 
            onChange={(event) => setDraft({ ...draft, name: event.target.value })} 
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'center' }}>
            <label style={{ fontSize: 10, color: 'var(--text-secondary)', fontWeight: 600 }}>Cor</label>
            <input 
              type="color" 
              value={draft.color} 
              onChange={(event) => setDraft({ ...draft, color: event.target.value })} 
              style={colorPickerStyle}
            />
          </div>
          <Button onClick={create} style={{ height: 40 }}>Criar</Button>
        </div>

        {/* Listagem e Edição de Etiquetas */}
        <div style={{ marginTop: 10 }}>
          <strong style={{ display: 'block', color: 'var(--text-primary)', fontSize: 13, marginBottom: 8 }}>Etiquetas cadastradas</strong>
          <div style={{ display: 'grid', gap: 8, maxHeight: '300px', overflowY: 'auto', paddingRight: 4 }}>
            {labels.map((label) => (
              <div 
                key={label.id} 
                style={{ 
                  display: 'grid', 
                  gridTemplateColumns: '1fr 60px auto', 
                  gap: 10, 
                  alignItems: 'center',
                  background: 'rgba(255, 255, 255, 0.01)',
                  border: '1px solid rgba(255,255,255,0.03)',
                  borderRadius: 6,
                  padding: 4
                }}
              >
                <input 
                  type="text"
                  className="form-input"
                  value={label.name} 
                  onChange={(event) => update(label, { name: event.target.value })} 
                  style={{ margin: 0, height: 36, padding: '4px 8px', fontSize: 13 }}
                />
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <input 
                    type="color" 
                    value={label.color} 
                    onChange={(event) => update(label, { color: event.target.value })} 
                    style={colorPickerStyle}
                  />
                </div>
                <Button 
                  size="sm" 
                  variant={label.is_active ? 'secondary' : 'primary'} 
                  onClick={() => update(label, { is_active: !label.is_active })}
                  style={{ height: 36, fontSize: 12, padding: '0 12px' }}
                >
                  {label.is_active ? 'Desativar' : 'Ativar'}
                </Button>
              </div>
            ))}
            {labels.length === 0 && (
              <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontStyle: 'italic' }}>Nenhuma etiqueta cadastrada.</span>
            )}
          </div>
        </div>
      </div>
    </Modal>
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
