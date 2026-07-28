import React, { useEffect, useState } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { Select } from '../ui/Select';
import { Textarea } from '../ui/Textarea';
import { KanbanBoard } from './types';

interface Props {
  board: KanbanBoard;
  isOpen: boolean;
  onClose: () => void;
  onCreate: (payload: Record<string, unknown>) => Promise<void>;
}

export const CreateCardModal: React.FC<Props> = ({ board, isOpen, onClose, onCreate }) => {
  const [draft, setDraft] = useState({ title: '', description: '', priority: 'MEDIUM', due_date: '', column_id: board.columns[0]?.id || 0 });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft((prev) => ({ ...prev, column_id: board.columns.find((column) => !column.is_archived)?.id || 0 }));
  }, [board.id]);

  const submit = async () => {
    if (!draft.title.trim()) return;
    setSaving(true);
    try {
      await onCreate({
        ...draft,
        column_id: Number(draft.column_id),
        due_date: draft.due_date ? new Date(draft.due_date).toISOString() : undefined,
      });
      setDraft({ title: '', description: '', priority: 'MEDIUM', due_date: '', column_id: board.columns.find((column) => !column.is_archived)?.id || 0 });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Nova tarefa"
      size="md"
      footer={<><Button variant="ghost" onClick={onClose}>Cancelar</Button><Button onClick={submit} isLoading={saving}>Criar tarefa</Button></>}
    >
      <div style={{ display: 'grid', gap: 12 }}>
        <Input label="Título" value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="Ex: Separar pedido do cliente" />
        <Textarea label="Descrição" rows={3} value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 10 }}>
          <Select label="Coluna" value={draft.column_id} onChange={(event) => setDraft({ ...draft, column_id: Number(event.target.value) })} options={board.columns.filter((column) => !column.is_archived).map((column) => ({ value: column.id, label: column.name }))} />
          <Input label="Prazo" type="date" value={draft.due_date} onChange={(event) => setDraft({ ...draft, due_date: event.target.value })} />
        </div>
      </div>
    </Modal>
  );
};
