import React from 'react';
import { Plus, RefreshCw, Settings, Tags, Tv } from 'lucide-react';
import { Button } from '../ui/Button';
import { KanbanViewToggle } from './KanbanViewToggle';

interface Props {
  viewMode: 'board' | 'list';
  canEditCards: boolean;
  canEditStructure: boolean;
  onViewModeChange: (mode: 'board' | 'list') => void;
  onCreateCard: () => void;
  onManageColumns: () => void;
  onFields: () => void;
  onLabels: () => void;
  onTV: () => void;
  onRefresh: () => void;
}

export const BoardActionBar: React.FC<Props> = ({
  viewMode,
  canEditCards,
  canEditStructure,
  onViewModeChange,
  onCreateCard,
  onManageColumns,
  onFields,
  onLabels,
  onTV,
  onRefresh,
}) => (
  <section className="glass-card" style={{ padding: 12, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
    <KanbanViewToggle value={viewMode} onChange={onViewModeChange} />
    {canEditCards && <Button size="sm" onClick={onCreateCard} leftIcon={<Plus size={14} />}>Nova tarefa</Button>}
    {canEditStructure && <Button size="sm" variant="secondary" onClick={onManageColumns} leftIcon={<Settings size={14} />}>Gerenciar colunas</Button>}
    <Button size="sm" variant="secondary" onClick={onTV} leftIcon={<Tv size={14} />}>Modo TV</Button>
    {canEditStructure && <Button size="sm" variant="ghost" onClick={onFields} leftIcon={<Settings size={14} />}>Campos</Button>}
    {canEditStructure && <Button size="sm" variant="ghost" onClick={onLabels} leftIcon={<Tags size={14} />}>Etiquetas</Button>}
    <Button size="sm" variant="ghost" onClick={onRefresh} leftIcon={<RefreshCw size={14} />}>Atualizar</Button>
  </section>
);

