import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Clock,
  FileSearch,
  History,
  Package,
  Plus,
  RefreshCw,
  Search,
  ShoppingCart,
  Tags,
  X,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { Drawer } from '../ui/Drawer';
import { EmptyState } from '../ui/EmptyState';
import { Input } from '../ui/Input';
import { Textarea } from '../ui/Textarea';

type PriceVariation = {
  id: string;
  family_id?: string | null;
  family_name: string;
  name: string;
  short_name: string;
  variation_name: string;
  attributes: Record<string, unknown>;
  unit_of_measure: string;
  category?: string | null;
  current_price?: number | string | null;
  reference_price?: number | string | null;
  currency: string;
  supplier_id?: string | null;
  supplier_name?: string | null;
  last_updated_at?: string | null;
  history_count: number;
  suppliers_count: number;
  description?: string | null;
  situation?: string | null;
  needs_review?: boolean;
  technical_details?: Record<string, unknown>;
};

type SupplierOffer = {
  id: string;
  product_item_id: string;
  supplier_id?: string | null;
  supplier_name?: string | null;
  email?: string | null;
  phone?: string | null;
  raw_price?: number | string | null;
  final_value?: number | string | null;
  current_price?: number | string | null;
  currency: string;
  unit: string;
  observed_at?: string | null;
  is_current_supplier: boolean;
  is_consolidated: boolean;
  status: string;
};

type PriceFamily = {
  family_id?: string | null;
  family_name: string;
  description?: string | null;
  variations_count: number;
  suppliers_count: number;
  min_price?: number | string | null;
  max_price?: number | string | null;
  last_updated_at?: string | null;
  variations: PriceVariation[];
};

type ProductsPricesPayload = {
  items: PriceFamily[];
  total_variations: number;
  limit: number;
  offset: number;
  has_more: boolean;
  summary: {
    products_count: number;
    families_count: number;
    variations_count?: number;
    supplier_offers_count?: number;
    current_prices_count: number;
    recently_updated_count: number;
    needs_review_count?: number;
    suppliers_without_email_count?: number;
    last_sync_at?: string | null;
  };
};

type PriceHistoryRow = {
  id: string;
  unit_price: number | string;
  unit_of_measure?: string | null;
  supplier_name?: string | null;
  observed_at: string;
  document_number?: string | null;
  source_id?: string | null;
};

type UpdateResult = {
  old_price?: number | string | null;
  new_price: number | string;
  difference_amount?: number | string | null;
  difference_percent?: number | string | null;
  updated_at: string;
};

type Props = {
  currentUser?: {
    role?: string;
    username?: string;
  } | null;
  onQuoteVariation: (variation: PriceVariation) => void;
  showToast: (message: string, isError?: boolean) => void;
};

const emptyPayload: ProductsPricesPayload = {
  items: [],
  total_variations: 0,
  limit: 80,
  offset: 0,
  has_more: false,
  summary: {
    products_count: 0,
    families_count: 0,
    current_prices_count: 0,
    recently_updated_count: 0,
  },
};

const money = (value?: number | string | null) => {
  if (value === null || value === undefined || value === '') return 'Sem preço';
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value));
};

const date = (value?: string | null) => {
  if (!value) return 'Sem atualização';
  return new Date(value).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

const percent = (value?: number | string | null) => {
  if (value === null || value === undefined || value === '') return '-';
  const parsed = Number(value);
  return `${parsed > 0 ? '+' : ''}${parsed.toFixed(2)}%`;
};

const readableAttributes = (attrs: Record<string, unknown>) => {
  const hidden = new Set(['variation_name']);
  return Object.entries(attrs || {})
    .filter(([key, val]) => !hidden.has(key) && val !== null && val !== undefined && `${val}`.trim() !== '')
    .slice(0, 4)
    .map(([key, val]) => `${key.replace(/_/g, ' ')}: ${val}`);
};

export const ProductsPricesWorkspace: React.FC<Props> = ({ currentUser, onQuoteVariation, showToast }) => {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [payload, setPayload] = useState<ProductsPricesPayload>(emptyPayload);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedFamilies, setExpandedFamilies] = useState<Set<string>>(new Set());
  const [selectedVariation, setSelectedVariation] = useState<PriceVariation | null>(null);
  const [supplierOffers, setSupplierOffers] = useState<SupplierOffer[]>([]);
  const [loadingOffers, setLoadingOffers] = useState(false);
  const [historyRows, setHistoryRows] = useState<PriceHistoryRow[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState(false);
  const [updatingVariation, setUpdatingVariation] = useState<PriceVariation | null>(null);
  const [updatingOffer, setUpdatingOffer] = useState<SupplierOffer | null>(null);
  const [newPrice, setNewPrice] = useState('');
  const [documentNumber, setDocumentNumber] = useState('');
  const [paymentTerms, setPaymentTerms] = useState('');
  const [notes, setNotes] = useState('');
  const [savingPrice, setSavingPrice] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<UpdateResult | null>(null);
  const [syncingCatalog, setSyncingCatalog] = useState(false);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedQuery(query.trim()), 350);
    return () => window.clearTimeout(handle);
  }, [query]);

  const loadProductsPrices = useCallback(async (nextOffset = 0) => {
    const isMore = nextOffset > 0;
    if (isMore) setLoadingMore(true);
    else setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        limit: '80',
        offset: String(nextOffset),
      });
      if (debouncedQuery) params.set('search', debouncedQuery);
      const res = await fetch(`/api/v1/purchases/catalog/families?${params.toString()}`);
      if (!res.ok) throw new Error('load failed');
      const data: ProductsPricesPayload = { ...emptyPayload, ...(await res.json()) };
      data.summary = { ...emptyPayload.summary, ...(data.summary || {}) };
      setPayload(current => {
        if (!isMore) return data;
        return {
          ...data,
          items: [...current.items, ...data.items],
        };
      });
    } catch {
      setError('Nao consegui carregar os produtos agora.');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [debouncedQuery]);

  useEffect(() => {
    loadProductsPrices(0);
    setExpandedFamilies(new Set());
  }, [loadProductsPrices]);

  const syncFromSpreadsheet = async () => {
    setSyncingCatalog(true);
    try {
      const res = await fetch('/api/v1/purchases/catalog/sync-from-xlsx', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Nao consegui atualizar da planilha.');
      showToast('Catalogo atualizado da planilha.');
      await loadProductsPrices(0);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Nao consegui atualizar da planilha.', true);
    } finally {
      setSyncingCatalog(false);
    }
  };

  const loadFamilyVariations = useCallback(async (family: PriceFamily) => {
    if (!family.family_id || family.variations.length > 0) return;
    try {
      const params = new URLSearchParams({ limit: '80', offset: '0' });
      if (debouncedQuery) params.set('search', debouncedQuery);
      const res = await fetch(`/api/v1/purchases/catalog/families/${family.family_id}/variations?${params.toString()}`);
      if (!res.ok) throw new Error('variations failed');
      const data: PriceFamily = await res.json();
      const key = family.family_id || family.family_name;
      setPayload(current => ({
        ...current,
        items: current.items.map(item => (item.family_id || item.family_name) === key ? { ...item, ...data } : item),
      }));
    } catch {
      showToast('Nao consegui carregar as variacoes desta familia.', true);
    }
  }, [debouncedQuery, showToast]);

  const loadHistory = useCallback(async (variation: PriceVariation) => {
    setLoadingHistory(true);
    setHistoryError(false);
    try {
      const res = await fetch(`/api/v1/purchases/prices/items/${variation.id}/timeline?limit=20`);
      if (!res.ok) throw new Error('history failed');
      setHistoryRows(await res.json());
    } catch {
      setHistoryError(true);
      setHistoryRows([]);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  const loadOffers = useCallback(async (variation: PriceVariation) => {
    setLoadingOffers(true);
    try {
      const res = await fetch(`/api/v1/purchases/catalog/items/${variation.id}/supplier-offers`);
      if (!res.ok) throw new Error('offers failed');
      const data = await res.json();
      setSupplierOffers(data.items || []);
    } catch {
      setSupplierOffers([]);
    } finally {
      setLoadingOffers(false);
    }
  }, []);

  const openVariation = (variation: PriceVariation) => {
    setSelectedVariation(variation);
    loadHistory(variation);
    loadOffers(variation);
  };

  const openUpdate = (variation: PriceVariation, offer?: SupplierOffer | null) => {
    setUpdatingVariation(variation);
    setUpdatingOffer(offer || null);
    setSelectedVariation(variation);
    setNewPrice('');
    setDocumentNumber('');
    setPaymentTerms('');
    setNotes('');
    setLastUpdate(null);
  };

  const submitUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!updatingVariation) return;
    const parsed = Number(newPrice);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      showToast('Informe um novo preço maior que zero.', true);
      return;
    }
    setSavingPrice(true);
    try {
      const endpoint = updatingOffer
        ? `/api/v1/purchases/catalog/items/${updatingVariation.id}/supplier-offers/${updatingOffer.id}/update-price`
        : `/api/v1/purchases/products-prices/items/${updatingVariation.id}/price`;
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          new_price: parsed,
          supplier_id: updatingOffer?.supplier_id || updatingVariation.supplier_id || null,
          document_number: documentNumber || null,
          payment_terms: paymentTerms || null,
          notes: notes || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao atualizar preço.');
      setLastUpdate(data);
      showToast('Preço atualizado somente para esta variação.');
      await loadProductsPrices(0);
      await loadHistory(updatingVariation);
      await loadOffers(updatingVariation);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao atualizar preço.', true);
    } finally {
      setSavingPrice(false);
    }
  };

  const selectedOldPrice = updatingOffer?.current_price ?? updatingOffer?.final_value ?? updatingVariation?.current_price;
  const previewDifference = useMemo(() => {
    if (!updatingVariation || !newPrice || selectedOldPrice === null || selectedOldPrice === undefined) return null;
    const oldVal = Number(selectedOldPrice);
    const newVal = Number(newPrice);
    if (!Number.isFinite(oldVal) || !Number.isFinite(newVal)) return null;
    return {
      amount: newVal - oldVal,
      pct: oldVal > 0 ? ((newVal - oldVal) / oldVal) * 100 : null,
    };
  }, [newPrice, selectedOldPrice, updatingVariation]);

  const toggleFamily = (family: PriceFamily) => {
    const key = family.family_id || family.family_name;
    setExpandedFamilies(current => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
    if (!expandedFamilies.has(key)) {
      loadFamilyVariations(family);
    }
  };

  const metricCards = [
    { label: 'Variações cadastradas', value: payload.summary.variations_count || payload.summary.products_count, icon: <Package size={20} /> },
    { label: 'Famílias encontradas', value: payload.summary.families_count, icon: <Tags size={20} /> },
    { label: 'Preços atuais', value: payload.summary.current_prices_count, icon: <ShoppingCart size={20} /> },
    { label: 'Itens para revisar', value: payload.summary.needs_review_count || 0, icon: <Clock size={20} /> },
  ];
  const canSeeTechnicalDetails = currentUser?.role === 'ADMIN' || currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';

  return (
    <section className="products-prices-workspace">
      <div className="products-prices-hero">
        <div>
          <h2>Produtos e Preços</h2>
          <p>Consulte preços atuais, veja histórico e atualize valores com segurança.</p>
        </div>
        <div className="products-prices-actions">
          <Button
            variant="secondary"
            leftIcon={<RefreshCw size={16} />}
            disabled={syncingCatalog}
            onClick={syncFromSpreadsheet}
          >
            {syncingCatalog ? 'Atualizando...' : 'Atualizar da planilha'}
          </Button>
          <Button
            variant="primary"
            leftIcon={<Plus size={16} />}
            onClick={() => selectedVariation ? openUpdate(selectedVariation) : showToast('Escolha uma variação para atualizar.')}
          >
            Atualizar preço
          </Button>
          <Button
            variant="secondary"
            leftIcon={<FileSearch size={16} />}
            onClick={() => selectedVariation ? onQuoteVariation(selectedVariation) : showToast('Escolha uma variação para cotar.')}
          >
            Cotar produto
          </Button>
        </div>
      </div>

      <label className="products-prices-search" htmlFor="products-prices-search">
        <Search size={20} />
        <input
          id="products-prices-search"
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="Buscar produto, medida, material, fornecedor..."
        />
        {query && (
          <button type="button" aria-label="Limpar busca" onClick={() => setQuery('')}>
            <X size={16} />
          </button>
        )}
      </label>

      <div className="products-prices-metrics">
        {metricCards.map(card => (
          <div className="products-prices-metric" key={card.label}>
            <span>{card.icon}</span>
            <strong>{card.value}</strong>
            <small>{card.label}</small>
          </div>
        ))}
      </div>

      <div className="products-prices-tabs" aria-label="Produtos e preços">
        <span className="active">Produtos e variações</span>
        <span>Preços atuais</span>
        <span>Atualizar preço</span>
        <span>Histórico</span>
      </div>

      <div className="products-prices-list">
        {loading ? (
          <div className="products-prices-loading">Carregando produtos e preços...</div>
        ) : error ? (
          <div className="products-prices-error">
            <span>{error}</span>
            <Button variant="secondary" size="sm" leftIcon={<RefreshCw size={14} />} onClick={() => loadProductsPrices(0)}>
              Tentar novamente
            </Button>
          </div>
        ) : payload.items.length === 0 ? (
          <EmptyState
            title="Nenhum produto encontrado"
            description="Tente buscar por outro nome, medida ou fornecedor."
          />
        ) : (
          payload.items.map(family => {
            const key = family.family_id || family.family_name;
            const expanded = expandedFamilies.has(key);
            return (
              <article className="products-prices-family" key={key}>
                <button className="products-prices-family-header" type="button" onClick={() => toggleFamily(family)}>
                  <div>
                    <strong>{family.family_name}</strong>
                    <small>{family.variations_count} variações • {family.suppliers_count} fornecedores</small>
                  </div>
                  <div>
                    <span>{family.min_price ? `${money(family.min_price)} - ${money(family.max_price)}` : 'Sem preço atual'}</span>
                    <small>{date(family.last_updated_at)}</small>
                  </div>
                </button>

                {expanded && (
                  <div className="products-prices-variations">
                    {family.variations.length === 0 ? (
                      <div className="products-prices-loading">Carregando variações desta família...</div>
                    ) : family.variations.map(variation => (
                      <div className="products-prices-variation" key={variation.id} onClick={() => openVariation(variation)}>
                        <div className="products-prices-variation-main">
                          <strong>{variation.short_name || variation.name}</strong>
                          <span>{readableAttributes(variation.attributes).join(' | ') || variation.description || variation.name}</span>
                        </div>
                        <div className="products-prices-variation-price">
                          <strong>{money(variation.current_price)}</strong>
                          <span>{variation.supplier_name || 'Sem fornecedor vinculado'}</span>
                          <small>{date(variation.last_updated_at)}</small>
                        </div>
                        <div className="products-prices-variation-actions" onClick={event => event.stopPropagation()}>
                          <Button size="sm" variant="primary" onClick={() => openUpdate(variation)}>Atualizar preço</Button>
                          <Button size="sm" variant="secondary" onClick={() => onQuoteVariation({ ...variation, reference_price: variation.current_price } as PriceVariation)}>Cotar esta variação</Button>
                          <Button size="sm" variant="ghost" onClick={() => openVariation(variation)}>Ver histórico</Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            );
          })
        )}
      </div>

      {payload.has_more && !loading && (
        <div className="products-prices-load-more">
          <Button variant="secondary" disabled={loadingMore} onClick={() => loadProductsPrices(payload.offset + payload.limit)}>
            {loadingMore ? 'Carregando...' : 'Carregar mais'}
          </Button>
        </div>
      )}

      <Drawer
        open={!!selectedVariation}
        onClose={() => setSelectedVariation(null)}
        title={selectedVariation?.family_name || 'Produto'}
        description={selectedVariation?.variation_name || selectedVariation?.name || ''}
        footer={selectedVariation ? (
          <div className="products-prices-drawer-actions">
            <Button variant="primary" onClick={() => openUpdate(selectedVariation)}>Atualizar preço</Button>
            <Button variant="secondary" onClick={() => onQuoteVariation({ ...selectedVariation, reference_price: selectedVariation.current_price } as PriceVariation)}>Cotar esta variação</Button>
          </div>
        ) : undefined}
      >
        {selectedVariation && (
          <div className="products-prices-drawer">
            <div className="products-prices-current">
              <span>Preço atual</span>
              <strong>{money(selectedVariation.current_price)}</strong>
              <small>{selectedVariation.supplier_name || 'Sem fornecedor vinculado'} • {date(selectedVariation.last_updated_at)}</small>
            </div>

            <div>
              <h4>Fornecedores cotados</h4>
              {loadingOffers ? (
                <p>Carregando fornecedores deste produto...</p>
              ) : supplierOffers.length === 0 ? (
                <p>Esse produto ainda não tem fornecedores cotados no catálogo.</p>
              ) : (
                <div className="products-prices-history">
                  {supplierOffers.map(offer => (
                    <div key={offer.id}>
                      <strong>{offer.supplier_name || 'Fornecedor sem nome'}</strong>
                      <span>{money(offer.current_price || offer.final_value || offer.raw_price)} • {offer.email || 'Sem e-mail'}</span>
                      <small>{offer.is_current_supplier ? 'Preço atual da empresa' : 'Oferta do fornecedor'}</small>
                      <Button size="sm" variant="secondary" onClick={() => openUpdate(selectedVariation, offer)}>Atualizar preço</Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <h4>Histórico do item</h4>
              {loadingHistory ? (
                <p>Carregando histórico deste produto...</p>
              ) : historyError ? (
                <div className="products-prices-error">
                  <span>O histórico demorou mais que o esperado.</span>
                  <Button size="sm" variant="secondary" onClick={() => loadHistory(selectedVariation)}>Tentar novamente</Button>
                </div>
              ) : historyRows.length === 0 ? (
                <p>Esse produto ainda não tem histórico.</p>
              ) : (
                <div className="products-prices-history">
                  {historyRows.map(row => (
                    <div key={row.id}>
                      <strong>{money(row.unit_price)}</strong>
                      <span>{row.supplier_name || 'Sem fornecedor'} • {date(row.observed_at)}</span>
                      {row.source_id && <small>Documento: {row.source_id}</small>}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {canSeeTechnicalDetails && (
              <details className="products-prices-technical">
                <summary>Detalhes técnicos</summary>
                <pre>{JSON.stringify(selectedVariation.technical_details || {}, null, 2)}</pre>
              </details>
            )}
          </div>
        )}
      </Drawer>

      <Drawer
        open={!!updatingVariation}
        onClose={() => setUpdatingVariation(null)}
        title="Atualizar preço"
        description={updatingVariation ? `${updatingVariation.family_name} • ${updatingVariation.variation_name}` : ''}
      >
        {updatingVariation && (
          <form className="products-prices-update-form" onSubmit={submitUpdate}>
            <div className="products-prices-current">
              <span>Preço atual</span>
              <strong>{money(selectedOldPrice)}</strong>
              <small>{updatingOffer?.supplier_name || updatingVariation.supplier_name || 'Sem fornecedor vinculado'}</small>
            </div>

            <Input
              label="Novo preço"
              type="number"
              min="0.01"
              step="0.01"
              value={newPrice}
              onChange={event => setNewPrice(event.target.value)}
              required
            />
            <Input
              label="Documento"
              placeholder="NF, boleto, proposta..."
              value={documentNumber}
              onChange={event => setDocumentNumber(event.target.value)}
            />
            <Input
              label="Condição de pagamento"
              placeholder="Ex: 28 DDL"
              value={paymentTerms}
              onChange={event => setPaymentTerms(event.target.value)}
            />
            <Textarea
              label="Observação"
              rows={3}
              value={notes}
              onChange={event => setNotes(event.target.value)}
            />

            <div className="products-prices-diff">
              <div><span>Preço antigo</span><strong>{money(selectedOldPrice)}</strong></div>
              <div><span>Novo preço</span><strong>{newPrice ? money(newPrice) : '-'}</strong></div>
              <div><span>Diferença</span><strong>{previewDifference ? money(previewDifference.amount) : '-'}</strong></div>
              <div><span>Variação</span><strong>{previewDifference?.pct === null || previewDifference?.pct === undefined ? '-' : percent(previewDifference.pct)}</strong></div>
            </div>

            {lastUpdate && (
              <div className="products-prices-success">
                Preço atualizado. Antes: {money(lastUpdate.old_price)}. Agora: {money(lastUpdate.new_price)}.
              </div>
            )}

            <Button type="submit" variant="primary" disabled={savingPrice} leftIcon={<History size={16} />}>
              {savingPrice ? 'Salvando...' : 'Confirmar atualização'}
            </Button>
          </form>
        )}
      </Drawer>
    </section>
  );
};
