import React, { useEffect, useState } from 'react';
import { Button } from '../ui/Button';
import { Checkbox } from '../ui/Checkbox';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { Select } from '../ui/Select';
import { CustomField, KanbanBoard } from './types';
import { apiJson } from './kanbanApi';

interface Props {
  board: KanbanBoard;
  isOpen: boolean;
  onClose: () => void;
  onChanged: () => Promise<void>;
}

export const BoardFieldsDrawer: React.FC<Props> = ({ board, isOpen, onClose, onChanged }) => {
  const [draft, setDraft] = useState({ name: '', key: '', field_type: 'TEXT', showList: true, showTV: true, showDetail: true });
  const [fields, setFields] = useState<CustomField[]>(board.custom_fields || []);

  const load = async () => {
    setFields(await apiJson<CustomField[]>(`/api/v1/kanban/boards/${board.id}/custom-fields`));
  };

  useEffect(() => {
    if (isOpen) load();
  }, [isOpen, board.id]);

  const create = async () => {
    if (!draft.name.trim() || !draft.key.trim()) return;
    await apiJson(`/api/v1/kanban/boards/${board.id}/custom-fields`, {
      method: 'POST',
      body: JSON.stringify({
        name: draft.name,
        key: draft.key,
        field_type: draft.field_type,
        display: { list: draft.showList, tv: draft.showTV, detail: draft.showDetail, board: true, filter: true },
      }),
    });
    setDraft({ name: '', key: '', field_type: 'TEXT', showList: true, showTV: true, showDetail: true });
    await load();
    await onChanged();
  };

  const update = async (field: CustomField, payload: Record<string, unknown>) => {
    await apiJson(`/api/v1/kanban/custom-fields/${field.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
    await load();
    await onChanged();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Campos do quadro" size="lg" footer={<Button variant="ghost" onClick={onClose}>Fechar</Button>}>
      <div style={{ display: 'grid', gap: 14 }}>
        <div className="glass-card" style={{ padding: 12, display: 'grid', gap: 10 }}>
          <strong style={{ color: 'var(--text-primary)' }}>Novo campo</strong>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 160px', gap: 10 }}>
            <Input placeholder="Nome visível" value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
            <Input placeholder="Chave simples, ex: cliente" value={draft.key} onChange={(event) => setDraft({ ...draft, key: event.target.value.toLowerCase().replace(/\s+/g, '_') })} />
            <Select value={draft.field_type} onChange={(event) => setDraft({ ...draft, field_type: event.target.value })} options={[
              { value: 'TEXT', label: 'Texto' },
              { value: 'NUMBER', label: 'Número' },
              { value: 'DATE', label: 'Data' },
              { value: 'SELECT', label: 'Seleção' },
              { value: 'BOOLEAN', label: 'Sim/Não' },
              { value: 'URL', label: 'Link' },
            ]} />
          </div>
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
            <Checkbox label="Detalhe" checked={draft.showDetail} onChange={(event) => setDraft({ ...draft, showDetail: event.target.checked })} />
            <Checkbox label="Lista" checked={draft.showList} onChange={(event) => setDraft({ ...draft, showList: event.target.checked })} />
            <Checkbox label="TV" checked={draft.showTV} onChange={(event) => setDraft({ ...draft, showTV: event.target.checked })} />
          </div>
          <Button onClick={create}>Criar campo</Button>
        </div>
        {fields.map((field) => (
          <div key={field.id} className="glass-card" style={{ padding: 12, display: 'grid', gridTemplateColumns: '1fr 150px auto', gap: 10, alignItems: 'center', opacity: field.is_active ? 1 : 0.55 }}>
            <Input value={field.name} onChange={(event) => update(field, { name: event.target.value })} />
            <span className="badge badge-neutral">{field.key}</span>
            <Button size="sm" variant={field.is_active ? 'secondary' : 'primary'} onClick={() => update(field, { is_active: !field.is_active })}>
              {field.is_active ? 'Desativar' : 'Ativar'}
            </Button>
          </div>
        ))}
      </div>
    </Modal>
  );
};
