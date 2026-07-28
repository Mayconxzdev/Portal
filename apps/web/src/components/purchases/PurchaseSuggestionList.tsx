import React from 'react';
import { Search, Package, Monitor } from 'lucide-react';
import { PurchaseSuggestion } from './types';

interface PurchaseSuggestionListProps {
  suggestions: PurchaseSuggestion[];
  loading?: boolean;
  onSelect: (suggestion: PurchaseSuggestion) => void;
}

const iconFor = (kind: string) => {
  if (kind === 'it_asset') return <Monitor size={14} />;
  if (kind === 'stock_item' || kind === 'master_product') return <Package size={14} />;
  return <Search size={14} />;
};

export const PurchaseSuggestionList: React.FC<PurchaseSuggestionListProps> = ({
  suggestions,
  loading = false,
  onSelect,
}) => {
  if (!loading && suggestions.length === 0) return null;

  return (
    <div
      style={{
        border: '1px solid var(--border-color)',
        borderRadius: 8,
        background: 'var(--surface-elevated)',
        overflow: 'hidden',
      }}
    >
      {loading && (
        <div style={{ padding: '8px 10px', color: 'var(--text-muted)', fontSize: 12 }}>
          Buscando sugestões...
        </div>
      )}
      {!loading && suggestions.map(suggestion => (
        <button
          key={`${suggestion.kind}-${suggestion.id || suggestion.label}`}
          type="button"
          onClick={() => onSelect(suggestion)}
          style={{
            width: '100%',
            border: 0,
            borderBottom: '1px solid var(--border-color)',
            background: 'transparent',
            color: 'var(--text-primary)',
            textAlign: 'left',
            padding: '8px 10px',
            display: 'grid',
            gridTemplateColumns: '20px 1fr auto',
            gap: 8,
            alignItems: 'center',
            cursor: 'pointer',
          }}
        >
          <span style={{ color: 'var(--primary)' }}>{iconFor(suggestion.kind)}</span>
          <span style={{ minWidth: 0 }}>
            <strong style={{ display: 'block', fontSize: 12 }}>{suggestion.label}</strong>
            <small style={{ display: 'block', color: 'var(--text-muted)' }}>
              {suggestion.subtitle || suggestion.source}
            </small>
          </span>
          <small style={{ color: 'var(--text-muted)' }}>{Math.round((suggestion.confidence || 0) * 100)}%</small>
        </button>
      ))}
    </div>
  );
};
