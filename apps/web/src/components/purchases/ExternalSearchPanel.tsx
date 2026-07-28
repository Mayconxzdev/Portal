import React from 'react';
import { ShoppingCart, AlertTriangle, Search, AlertCircle, ShieldCheck } from 'lucide-react';
import { Button } from '../ui/Button';
import { PurchaseResearchSession } from './types';

interface PurchaseItem {
  id: string;
  description: string;
  free_text_description?: string;
  quantity: number;
  unit_of_measure: string;
}

interface ExternalOption {
  id?: string;
  title: string;
  store_name: string;
  seller_name?: string;
  unit_price: number;
  shipping_price?: number;
  total_price: number;
  delivery_estimate?: string;
  product_url?: string;
  image_url?: string;
  verification_status?: string;
  verification_summary?: string;
  compatibility_score?: number;
  confidence_score?: number;
  source_domain?: string;
  price_conditions?: {
    condition_type: string;
    amount: number;
    is_recommended?: boolean;
  }[];
}

interface ManualOptionDraft {
  store_name: string;
  title: string;
  unit_price: string;
  shipping_price: string;
  delivery_estimate: string;
  product_url: string;
}

interface ExternalSearchPanelProps {
  searchActiveItem: PurchaseItem;
  searchQuery: string;
  onSearchQueryChange: (val: string) => void;
  searchingExternal: boolean;
  handleExternalSearch: (q: string) => void;
  searchError: string | null;
  searchResults: ExternalOption[];
  handleAddOptionManually: (itemId: string, opt: any) => Promise<void>;
  manualOptionDraft: ManualOptionDraft;
  setManualOptionDraft: React.Dispatch<React.SetStateAction<ManualOptionDraft>>;
  linkImportUrl: string;
  onLinkImportUrlChange: (val: string) => void;
  importingLink: boolean;
  handleImportLink: (url: string) => void;
  cartImportUrl: string;
  onCartImportUrlChange: (val: string) => void;
  importingCart: boolean;
  handleImportCart: (url: string) => void;
  researchSession?: PurchaseResearchSession | null;
  onRefreshResearchSession?: () => void;
  onBack: () => void;
  fmt: (val: number) => string;
}

export const ExternalSearchPanel: React.FC<ExternalSearchPanelProps> = ({
  searchActiveItem,
  searchQuery,
  onSearchQueryChange,
  searchingExternal,
  handleExternalSearch,
  searchError,
  searchResults,
  handleAddOptionManually,
  manualOptionDraft,
  setManualOptionDraft,
  linkImportUrl,
  onLinkImportUrlChange,
  importingLink,
  handleImportLink,
  cartImportUrl,
  onCartImportUrlChange,
  importingCart,
  handleImportCart,
  researchSession,
  onRefreshResearchSession,
  onBack,
  fmt,
}) => {
  const highlights = researchSession?.recommendation_summary?.highlights || {};
  const sessionStatus = String(researchSession?.status || '').toLowerCase();
  const isQueuedWithoutProgress = Boolean(researchSession && sessionStatus === 'queued' && !researchSession.progress_percent);
  const canRetryResearch = Boolean(researchSession && ['queued', 'retryable_error'].includes(sessionStatus));
  const progressTitle = researchSession?.recommendation_summary?.summary
    || (isQueuedWithoutProgress
      ? 'Pesquisa salva e pronta para processar'
      : researchSession?.current_step || 'Pesquisa em andamento');
  const progressSubtitle = isQueuedWithoutProgress
    ? 'A pesquisa foi salva. Use Atualizar pesquisa se ela não avançar automaticamente.'
    : researchSession?.recommendation_summary?.summary
      ? researchSession.current_step
      : 'Acompanhe as etapas confirmadas conforme os dados chegam.';
  const highlightCards = [
    { key: 'cheapest', label: 'Menor preco total', value: highlights.cheapest },
    { key: 'best', label: 'Melhor opcao geral', value: highlights.best_overall },
    { key: 'fastest', label: 'Entrega mais rapida', value: highlights.fastest },
  ].filter(item => item.value);

  return (
    <div className="purchase-work-scroll" style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '16px 0' }}>
      <div className="purchase-current-task">
        <span>Pesquisa externa persistente</span>
        <strong>Buscar no mercado externo: {searchActiveItem.description || searchActiveItem.free_text_description}</strong>
        <p>O Portal separa descoberta de confirmacao e nao inventa preco, frete ou disponibilidade.</p>
      </div>

      {researchSession && (
        <div className="glass-card" style={{ padding: 14, border: '1px solid var(--border-color)', borderRadius: 10, display: 'grid', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
            <div>
              <strong style={{ display: 'block', color: 'var(--text-primary)' }}>
                {progressTitle}
              </strong>
              {progressSubtitle !== progressTitle && (
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{progressSubtitle}</span>
              )}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{researchSession.progress_percent}%</span>
              {canRetryResearch && onRefreshResearchSession && (
                <Button variant="secondary" size="sm" onClick={onRefreshResearchSession}>
                  Atualizar pesquisa
                </Button>
              )}
            </div>
          </div>
          <div style={{ height: 6, background: 'var(--surface-muted)', borderRadius: 99, overflow: 'hidden' }}>
            <div style={{ width: `${Math.min(100, Math.max(0, researchSession.progress_percent || 0))}%`, height: '100%', background: 'var(--primary)', borderRadius: 99 }} />
          </div>
          {highlightCards.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
              {highlightCards.map(card => (
                <div key={card.key} style={{ padding: 10, border: '1px solid var(--border-color)', borderRadius: 8, background: 'var(--surface-elevated)' }}>
                  <span style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)' }}>{card.label}</span>
                  <strong style={{ display: 'block', marginTop: 4, color: 'var(--text-primary)' }}>{card.value?.title || 'Aguardando'}</strong>
                  {typeof card.value?.total_price === 'number' && (
                    <small style={{ color: 'var(--success-text)' }}>{fmt(card.value.total_price)}</small>
                  )}
                </div>
              ))}
            </div>
          )}
          {researchSession.missing_questions?.length > 0 && (
            <div style={{ padding: 10, border: '1px solid rgba(245,158,11,0.35)', borderRadius: 8, background: 'rgba(245,158,11,0.08)' }}>
              <strong style={{ display: 'block', fontSize: 12, color: 'var(--warning-text)' }}>Falta confirmar antes da decisao</strong>
              {researchSession.missing_questions.slice(0, 3).map((question, index) => (
                <p key={`${question.field || index}`} style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-primary)' }}>
                  {question.question || question.reason || 'Confirme uma informacao que altera a compra.'}
                </p>
              ))}
            </div>
          )}
          {(researchSession.recommendation_summary?.why || []).length > 0 && (
            <details>
              <summary style={{ cursor: 'pointer', color: 'var(--primary)', fontWeight: 700, fontSize: 12 }}>
                Por que recomendamos esta opcao?
              </summary>
              <ul style={{ margin: '8px 0 0', paddingLeft: 18, color: 'var(--text-muted)', fontSize: 12 }}>
                {(researchSession.recommendation_summary?.why || []).map((line, index) => <li key={index}>{line}</li>)}
              </ul>
            </details>
          )}
          {researchSession.canonical_products?.length > 0 && (
            <div style={{ display: 'grid', gap: 8 }}>
              <strong style={{ fontSize: 12, color: 'var(--text-primary)' }}>Produtos agrupados</strong>
              {researchSession.canonical_products.map(product => (
                <div key={product.id} style={{ padding: 10, border: '1px solid var(--border-color)', borderRadius: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <strong style={{ color: 'var(--text-primary)' }}>{product.title || product.name}</strong>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{product.offers?.length || 0} oferta(s)</span>
                  </div>
                  {typeof product.best_total_price === 'number' && (
                    <small style={{ color: 'var(--success-text)' }}>Melhor total confirmado ou parcial: {fmt(product.best_total_price)}</small>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          type="text"
          style={{ flex: 1, padding: '8px 12px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 8, color: 'var(--text-primary)' }}
          value={searchQuery}
          onChange={e => onSearchQueryChange(e.target.value)}
          placeholder="Ex: memoria ram ddr5 16gb corsair"
          onKeyDown={e => {
            if (e.key === 'Enter') handleExternalSearch(searchQuery);
          }}
        />
        <Button variant="primary" onClick={() => handleExternalSearch(searchQuery)} disabled={searchingExternal}>
          {searchingExternal ? 'Buscando...' : 'Buscar online'}
        </Button>
      </div>

      {searchError && (
        <div className="glass-card" style={{ padding: 16, border: '1px solid rgba(239,68,68,0.2)', background: 'rgba(239,68,68,0.04)', borderRadius: 8 }}>
          <h4 style={{ color: '#f87171', fontSize: 13, margin: '0 0 6px 0', fontWeight: 'bold' }}>Pesquisa automática indisponível</h4>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5, margin: '0 0 12px 0' }}>{searchError}</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, borderTop: '1px solid var(--border-color)', paddingTop: 12 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Adicionar opção manualmente via link de produto</label>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  type="text"
                  style={{ flex: 1, padding: '5px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                  value={linkImportUrl}
                  onChange={e => onLinkImportUrlChange(e.target.value)}
                  placeholder="Cole a URL do produto (ex: Kabum, Mercado Livre)"
                />
                <Button variant="secondary" size="sm" onClick={() => handleImportLink(linkImportUrl)} disabled={importingLink}>
                  {importingLink ? 'Importando...' : 'Importar link'}
                </Button>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>Importar itens via link de carrinho compartilhado</label>
              <div style={{ display: 'flex', gap: 6 }}>
                <input
                  type="text"
                  style={{ flex: 1, padding: '5px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
                  value={cartImportUrl}
                  onChange={e => onCartImportUrlChange(e.target.value)}
                  placeholder="Cole a URL do carrinho"
                />
                <Button variant="secondary" size="sm" onClick={() => handleImportCart(cartImportUrl)} disabled={importingCart}>
                  {importingCart ? 'Importando...' : 'Importar carrinho'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="glass-card" style={{ padding: 14, border: '1px solid var(--border-color)', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div>
          <h4 style={{ margin: 0, color: 'var(--text-primary)', fontSize: 13 }}>Cadastrar opcao manualmente</h4>
          <p style={{ margin: '3px 0 0', color: 'var(--text-muted)', fontSize: 12 }}>
            Use quando a pesquisa automatica nao estiver configurada ou quando a loja exigir login.
          </p>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 8 }}>
          <input
            type="text"
            style={{ padding: '7px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
            value={manualOptionDraft.store_name}
            onChange={e => setManualOptionDraft(prev => ({ ...prev, store_name: e.target.value }))}
            placeholder="Loja ou fornecedor"
          />
          <input
            type="text"
            style={{ padding: '7px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
            value={manualOptionDraft.title}
            onChange={e => setManualOptionDraft(prev => ({ ...prev, title: e.target.value }))}
            placeholder="Produto ofertado"
          />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
          <input
            type="number"
            min="0"
            step="0.01"
            style={{ padding: '7px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
            value={manualOptionDraft.unit_price}
            onChange={e => setManualOptionDraft(prev => ({ ...prev, unit_price: e.target.value }))}
            placeholder="Preco"
          />
          <input
            type="number"
            min="0"
            step="0.01"
            style={{ padding: '7px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
            value={manualOptionDraft.shipping_price}
            onChange={e => setManualOptionDraft(prev => ({ ...prev, shipping_price: e.target.value }))}
            placeholder="Frete"
          />
          <input
            type="text"
            style={{ padding: '7px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
            value={manualOptionDraft.delivery_estimate}
            onChange={e => setManualOptionDraft(prev => ({ ...prev, delivery_estimate: e.target.value }))}
            placeholder="Prazo"
          />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
          <input
            type="url"
            style={{ padding: '7px 10px', background: 'var(--surface-elevated)', border: '1px solid var(--border-color)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 12 }}
            value={manualOptionDraft.product_url}
            onChange={e => setManualOptionDraft(prev => ({ ...prev, product_url: e.target.value }))}
            placeholder="Link opcional"
          />
          <Button variant="primary" size="sm" onClick={() => handleAddOptionManually(searchActiveItem.id, manualOptionDraft)}>
            Salvar opcao
          </Button>
        </div>
      </div>

      {searchResults.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {searchResults.map((opt, i) => {
            const recommendedCondition = opt.price_conditions?.find(condition => condition.is_recommended);
            return (
            <div
              key={opt.id || i}
              className="glass-card"
              style={{ display: 'flex', gap: 12, padding: 12, border: '1px solid var(--border-color)', borderRadius: 8 }}
            >
              {opt.image_url && (
                <img
                  src={opt.image_url}
                  alt={opt.title}
                  style={{ width: 60, height: 60, objectFit: 'contain', borderRadius: 6, background: '#fff', padding: 2 }}
                />
              )}
              <div style={{ flex: 1 }}>
                <strong style={{ fontSize: 13, display: 'block' }}>{opt.title}</strong>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Loja: {opt.store_name || opt.source_domain || 'origem registrada'} · Prazo: {opt.delivery_estimate || 'a confirmar'}
                </span>
                <div style={{ fontSize: 12, color: 'var(--success-text)', fontWeight: 'bold', marginTop: 4 }}>
                  Preco: {fmt(opt.unit_price)} + Frete: {opt.shipping_price != null ? fmt(opt.shipping_price || 0) : 'a confirmar'} = Total {fmt(opt.total_price)}
                </div>
                {recommendedCondition && (
                  <small style={{ display: 'block', color: 'var(--text-primary)', marginTop: 3 }}>
                    Condicao usada na comparacao: {recommendedCondition.condition_type.toUpperCase()} {fmt(recommendedCondition.amount)}
                  </small>
                )}
                <small style={{ display: 'block', color: 'var(--text-muted)', marginTop: 4 }}>
                  {opt.verification_summary || 'Dados aguardam confirmacao antes da recomendacao final.'}
                </small>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, justifyContent: 'center' }}>
                <Button variant="primary" size="sm" onClick={() => handleAddOptionManually(searchActiveItem.id, opt)}>
                  Selecionar
                </Button>
              </div>
            </div>
          );
          })}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-start', marginTop: 10 }}>
        <Button variant="secondary" size="sm" onClick={onBack}>
          Voltar para itens
        </Button>
      </div>
    </div>
  );
};
