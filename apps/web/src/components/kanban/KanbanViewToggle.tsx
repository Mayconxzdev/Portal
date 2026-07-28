import React from 'react';
import { List, Table2 } from 'lucide-react';
import { Button } from '../ui/Button';

interface Props {
  value: 'board' | 'list';
  onChange: (mode: 'board' | 'list') => void;
}

export const KanbanViewToggle: React.FC<Props> = ({ value, onChange }) => (
  <div style={{ display: 'flex', gap: 4, padding: 4, border: '1px solid var(--border-color)', borderRadius: 8, background: 'rgba(255,255,255,0.03)' }}>
    <Button size="sm" variant={value === 'board' ? 'primary' : 'ghost'} onClick={() => onChange('board')} leftIcon={<Table2 size={14} />}>Quadro</Button>
    <Button size="sm" variant={value === 'list' ? 'primary' : 'ghost'} onClick={() => onChange('list')} leftIcon={<List size={14} />}>Lista</Button>
  </div>
);
