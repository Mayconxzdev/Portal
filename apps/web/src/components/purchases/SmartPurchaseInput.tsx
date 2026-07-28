import React, { useEffect, useMemo, useRef, useState } from 'react';
import { PurchaseSuggestion } from './types';
import { PurchaseSuggestionList } from './PurchaseSuggestionList';

export type PurchaseInputMode = 'auto' | 'internal' | 'external';

interface SmartPurchaseInputProps {
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  mode?: PurchaseInputMode;
  onModeChange?: (mode: PurchaseInputMode) => void;
}

const modeOptions: { key: PurchaseInputMode; label: string; helper: string }[] = [
  { key: 'auto', label: 'Automático', helper: 'O Portal decide se é interno ou externo.' },
  { key: 'internal', label: 'Dentro do Portal', helper: 'Prioriza Estoque, Catálogo, histórico e fornecedores internos.' },
  { key: 'external', label: 'Internet', helper: 'Trata como compra externa e pesquisa mercado após a revisão.' },
];

const buildInsights = (text: string, mode: PurchaseInputMode) => {
  const clean = text.trim();
  if (!clean) return [];

  const insights: string[] = [];
  const budgetMatch = clean.match(/(?:até|ate|orçamento|orcamento|limite|r\$|rs)\s*(?:r\$|rs)?\s*([\d.\s]+(?:,\d{1,2})?)/i);
  const destinationMatch = clean.match(/\bpara\s+(?:o\s+|a\s+)?(.+?)(?:\s+(?:até|ate|com|limite|orçamento|orcamento|r\$|rs)\b|[,.;]|$)/i);
  const quantityMatch = clean.match(/^\s*(\d+(?:[,.]\d+)?)\s+/);

  if (mode === 'internal') insights.push('Buscando primeiro dentro do Portal');
  if (mode === 'external') insights.push('Compra externa: pesquisa online depois da revisão');
  if (mode === 'auto') insights.push('Classificação automática ativa');
  if (quantityMatch) insights.push(`Quantidade detectada: ${quantityMatch[1].replace('.', ',')}`);
  if (budgetMatch) insights.push(`Orçamento detectado: ${budgetMatch[1].trim()}`);
  if (destinationMatch) insights.push(`Destino: ${destinationMatch[1].trim().slice(0, 36)}`);
  if (/https?:\/\//i.test(clean)) insights.push('Link detectado');
  if (/\b(ram|ssd|notebook|pc|monitor|teclado|mouse|placa de vídeo|placa de video)\b/i.test(clean)) {
    insights.push('Perfil provável: TI / mercado externo');
  }
  if (/\b(arame|tubo|chapa|inox|aço|aco|flange|rolamento|parafuso)\b/i.test(clean)) {
    insights.push('Perfil provável: material industrial');
  }
  return Array.from(new Set(insights)).slice(0, 5);
};

export const SmartPurchaseInput: React.FC<SmartPurchaseInputProps> = ({
  value,
  onChange,
  rows = 4,
  mode = 'auto',
  onModeChange,
}) => {
  const [suggestions, setSuggestions] = useState<PurchaseSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const requestSeq = useRef(0);
  const insights = useMemo(() => buildInsights(value, mode), [value, mode]);
  const selectedMode = modeOptions.find(item => item.key === mode) || modeOptions[0];

  useEffect(() => {
    const trimmed = value.trim();
    requestSeq.current += 1;
    const requestId = requestSeq.current;

    if (trimmed.length < 3 || mode === 'external') {
      setSuggestions([]);
      setLoading(false);
      return;
    }

    const lastLine = trimmed.split(/\r?\n/).pop()?.trim() || trimmed;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ q: lastLine, context: mode });
        const response = await fetch(`/api/v1/purchases/suggestions?${params.toString()}`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          if (requestSeq.current === requestId) setSuggestions([]);
          return;
        }
        const data = await response.json();
        if (requestSeq.current === requestId) {
          setSuggestions(Array.isArray(data) ? data : []);
        }
      } catch (error: any) {
        if (error?.name !== 'AbortError' && requestSeq.current === requestId) setSuggestions([]);
      } finally {
        if (requestSeq.current === requestId) setLoading(false);
      }
    }, 260);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [value, mode]);

  const selectSuggestion = (suggestion: PurchaseSuggestion) => {
    const lines = value.split(/\r?\n/);
    lines[lines.length - 1] = suggestion.label;
    onChange(lines.join('\n'));
    setSuggestions([]);
  };

  return (
    <div style={{ display: 'grid', gap: 8 }}>
      <div
        role="group"
        aria-label="Origem da compra"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
          gap: 6,
        }}
      >
        {modeOptions.map(option => {
          const active = option.key === mode;
          return (
            <button
              key={option.key}
              type="button"
              onClick={() => onModeChange?.(option.key)}
              title={option.helper}
              style={{
                border: `1px solid ${active ? 'var(--primary)' : 'var(--border-color)'}`,
                background: active ? 'rgba(124, 92, 255, 0.12)' : 'var(--surface-elevated)',
                color: active ? 'var(--primary)' : 'var(--text-primary)',
                borderRadius: 8,
                padding: '8px 10px',
                fontSize: 12,
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      <textarea
        id="need-pasted-list"
        value={value}
        onChange={event => onChange(event.target.value)}
        placeholder="Ex: preciso de 2 memórias RAM DDR5 16 GB, até R$ 3.000 no total, para um computador da equipe"
        rows={rows}
        style={{
          width: '100%',
          padding: '10px 12px',
          background: 'var(--surface-elevated)',
          border: '1px solid var(--border-color)',
          borderRadius: 8,
          color: 'var(--text-primary)',
          fontSize: 13,
        }}
      />

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>{selectedMode.helper}</span>
        {insights.map(item => (
          <span
            key={item}
            style={{
              border: '1px solid var(--border-color)',
              background: 'var(--surface-muted)',
              color: 'var(--text-secondary)',
              borderRadius: 999,
              padding: '3px 8px',
              fontSize: 11,
              fontWeight: 700,
            }}
          >
            {item}
          </span>
        ))}
      </div>

      <PurchaseSuggestionList suggestions={suggestions} loading={loading} onSelect={selectSuggestion} />
    </div>
  );
};
