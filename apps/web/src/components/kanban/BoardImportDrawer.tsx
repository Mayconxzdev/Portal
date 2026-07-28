import React, { useState } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Modal } from '../ui/Modal';
import { Select } from '../ui/Select';
import { KanbanBoard } from './types';
import { apiJson } from './kanbanApi';

interface Preview {
  import_id: string;
  filename: string;
  headers: string[];
  rows: Record<string, unknown>[];
  total_rows: number;
}

interface Props {
  board: KanbanBoard;
  isOpen: boolean;
  onClose: () => void;
  onChanged: () => Promise<void>;
}

export const BoardImportDrawer: React.FC<Props> = ({ board, isOpen, onClose, onChanged }) => {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [duplicateField, setDuplicateField] = useState('op');
  const [strategy, setStrategy] = useState('ignore');

  const upload = async (file?: File) => {
    if (!file) return;
    const form = new FormData();
    form.append('upload', file);
    const data = await apiJson<Preview>(`/api/v1/kanban/boards/${board.id}/import/preview`, { method: 'POST', body: form });
    setPreview(data);
    const auto: Record<string, string> = {};
    data.headers.forEach((header) => {
      const key = header.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, '_');
      if (['titulo', 'tarefa', 'title'].includes(key)) auto[header] = 'title';
      else if (['descricao', 'description'].includes(key)) auto[header] = 'description';
      else if (['prioridade', 'priority'].includes(key)) auto[header] = 'priority';
      else if (['prazo', 'entrega', 'due_date'].includes(key)) auto[header] = key === 'entrega' ? 'custom.entrega' : 'due_date';
      else if (board.custom_fields.some((field) => field.is_active && field.key === key)) auto[header] = `custom.${key}`;
    });
    setMapping(auto);
  };

  const confirm = async () => {
    if (!preview) return;
    await apiJson(`/api/v1/kanban/boards/${board.id}/import/confirm`, {
      method: 'POST',
      body: JSON.stringify({
        import_id: preview.import_id,
        mapping,
        duplicate_field: duplicateField || undefined,
        duplicate_strategy: strategy,
        default_column_id: board.columns.find((column) => !column.is_archived)?.id,
      }),
    });
    setPreview(null);
    await onChanged();
    onClose();
  };

  const targetOptions = [
    { value: '', label: 'Ignorar coluna' },
    { value: 'title', label: 'Titulo da tarefa' },
    { value: 'description', label: 'Descricao' },
    { value: 'priority', label: 'Prioridade' },
    { value: 'due_date', label: 'Prazo' },
    { value: 'column', label: 'Coluna/status' },
    ...board.custom_fields.filter((field) => field.is_active).map((field) => ({ value: `custom.${field.key}`, label: field.name })),
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Importar planilha" size="lg" footer={<><Button variant="ghost" onClick={onClose}>Fechar</Button>{preview && <Button onClick={confirm}>Importar dados</Button>}</>}>
      <div style={{ display: 'grid', gap: 14 }}>
        <Input
          label="Arquivo para importar"
          type="file"
          accept=".csv,.xlsx"
          onChange={(event) => upload(event.target.files?.[0])}
          helpText="A importacao aceita CSV e XLSX, sempre com pre-visualizacao antes de criar cards."
        />
        {preview && (
          <>
            <p className="text-muted" style={{ margin: 0 }}>{preview.filename}: {preview.total_rows} linha(s) encontradas.</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <Input label="Campo para detectar duplicidade" value={duplicateField} onChange={(event) => setDuplicateField(event.target.value)} />
              <Select label="Quando encontrar duplicidade" value={strategy} onChange={(event) => setStrategy(event.target.value)} options={[
                { value: 'ignore', label: 'Ignorar existente' },
                { value: 'update', label: 'Atualizar existente' },
              ]} />
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              {preview.headers.map((header) => (
                <div key={header} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, alignItems: 'center' }}>
                  <span style={{ color: 'var(--text-primary)' }}>{header}</span>
                  <Select value={mapping[header] || ''} onChange={(event) => setMapping({ ...mapping, [header]: event.target.value })} options={targetOptions} />
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </Modal>
  );
};
