import React from 'react';
import { Button } from '../ui/Button';
import { EmptyState } from '../ui/EmptyState';
import { Badge } from '../ui/Badge';

import { SupplierSuggestion } from './types';


interface SupplierQuotationPanelProps {
  activeQuote: { title: string; items: any[] };
  supplierSuggestions: SupplierSuggestion[];
  selectedSupplierMap: Record<string, Set<string>>;
  setSelectedSupplierMap: React.Dispatch<React.SetStateAction<Record<string, Set<string>>>>;
  loadingSupplierSuggestions: boolean;
  loadSupplierSuggestions: () => void;
  selectedSupplierCount: number;
  setQuoteWizardStep: (step: 'products' | 'suppliers' | 'preview') => void;
  saveSupplierSelection: () => void;
  showToast: (msg: string) => void;
}

export const SupplierQuotationPanel: React.FC<SupplierQuotationPanelProps> = ({
  activeQuote,
  supplierSuggestions,
  selectedSupplierMap,
  setSelectedSupplierMap,
  loadingSupplierSuggestions,
  loadSupplierSuggestions,
  selectedSupplierCount,
  setQuoteWizardStep,
  saveSupplierSelection,
  showToast,
}) => {
  return (
    <div className="new-quote-panel">
      <div className="new-quote-panel-header">
        <div>
          <h2>Fornecedores</h2>
          <p>Selecione quais fornecedores receberão quais itens. Um mesmo item pode ir para vários fornecedores.</p>
        </div>
        <Button variant="secondary" size="sm" onClick={loadSupplierSuggestions} disabled={loadingSupplierSuggestions}>
          {loadingSupplierSuggestions ? 'Atualizando...' : 'Atualizar sugestões'}
        </Button>
      </div>

      {supplierSuggestions.length === 0 ? (
        <EmptyState
          title="Nenhuma sugestão carregada"
          description="Use as sugestões internas para encontrar fornecedores com contato e histórico."
        />
      ) : (
        <div className="supplier-suggestion-list">
          {supplierSuggestions.map(suggestion => {
            const selectable = Boolean(suggestion.supplier_id) && suggestion.status !== 'needs_master_data_link';
            const selectedItems = selectedSupplierMap[suggestion.supplier_id || suggestion.supplier_name] || new Set<string>();
            return (
              <div key={suggestion.supplier_id || suggestion.supplier_name} className="supplier-suggestion-card">
                <div className="supplier-suggestion-head">
                  <div>
                    <strong>{suggestion.supplier_name}</strong>
                    <span>
                      {suggestion.coverage_count} de {suggestion.total_items} itens ·{' '}
                      {suggestion.contact_email || 'contato precisa confirmação'}
                    </span>
                  </div>
                  <Badge variant={selectable ? 'success' : 'warning'}>
                    {selectable ? 'pode cotar' : 'precisa cadastrar'}
                  </Badge>
                </div>
                <div className="supplier-reasons">
                  {suggestion.reasons.map(reason => (
                    <span key={reason}>{reason}</span>
                  ))}
                </div>
                <div className="supplier-item-selection">
                  {activeQuote.items.map(item => {
                    const checked = selectedItems.has(item.id);
                    const suggested = suggestion.item_ids.includes(item.id);
                    return (
                      <label key={item.id} className={!selectable ? 'disabled' : ''}>
                        <input
                          type="checkbox"
                          disabled={!selectable}
                          checked={checked}
                          onChange={event => {
                            const key = suggestion.supplier_id || suggestion.supplier_name;
                            setSelectedSupplierMap(prev => {
                              const next = { ...prev };
                              const itemSet = new Set(next[key] || []);
                              if (event.target.checked) itemSet.add(item.id);
                              else itemSet.delete(item.id);
                              next[key] = itemSet;
                              return next;
                            });
                          }}
                        />
                        <span>
                          {item.description || item.free_text_description || 'Item'}
                          {suggested ? ' · sugerido' : ''}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="quote-step-footer">
        <Button variant="secondary" onClick={() => setQuoteWizardStep('products')}>
          Voltar
        </Button>
        <Button
          variant="secondary"
          onClick={() =>
            showToast('Busca externa ainda não configurada. Cadastre manualmente ou use fornecedores internos por enquanto.')
          }
        >
          Buscar novos fornecedores
        </Button>
        <Button variant="primary" onClick={saveSupplierSelection} disabled={selectedSupplierCount === 0}>
          Salvar distribuição
        </Button>
      </div>
    </div>
  );
};
