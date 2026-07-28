import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Download, Eye, FileSpreadsheet, Mail, RefreshCw, Search, Wrench } from 'lucide-react';
import { Button } from '../ui/Button';
import { Drawer } from '../ui/Drawer';
import { EmptyState } from '../ui/EmptyState';
import { Input } from '../ui/Input';

type ReconciliationItem = {
  row_key: string;
  sheet: string;
  row_number: number;
  family: string;
  subfamily?: string | null;
  variation: string;
  display_name: string;
  supplier_name?: string | null;
  company_name?: string | null;
  email?: string | null;
  phone?: string | null;
  spreadsheet_price?: number | null;
  raw_price?: number | null;
  final_value?: number | null;
  portal_price?: number | null;
  difference_amount?: number | null;
  difference_percent?: number | null;
  price_type: string;
  unit: string;
  updated_at?: string | null;
  situation: string;
  issues: string[];
  portal_item_id?: string | null;
  portal_supplier_id?: string | null;
  portal_item_name?: string | null;
  portal_supplier_name?: string | null;
  ready_for_quote: boolean;
  technical_details?: Record<string, unknown>;
};

type ReconciliationPayload = {
  source_path: string;
  file_updated_at?: string | null;
  sheets_read: string[];
  sheets_ignored: string[];
  layouts: Record<string, number>;
  summary: Record<string, number>;
  items: ReconciliationItem[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
};

type GroupedReconciliationItem = {
  group_key: string;
  portal_item_id?: string | null;
  family: string;
  subfamily?: string | null;
  variation: string;
  display_name: string;
  portal_price?: number | null;
  offers: ReconciliationItem[];
};

type Props = {
  currentUser?: { role?: string; username?: string } | null;
  showToast: (message: string, isError?: boolean) => void;
};

const emptyPayload: ReconciliationPayload = {
  source_path: '',
  sheets_read: [],
  sheets_ignored: [],
  layouts: {},
  summary: {},
  items: [],
  total: 0,
  limit: 80,
  offset: 0,
  has_more: false,
};

const filters = [
  { key: 'all', label: 'Tudo' },
  { key: 'divergent', label: 'Divergente' },
  { key: 'missing', label: 'Faltando no Portal' },
  { key: 'no_supplier', label: 'Sem fornecedor' },
  { key: 'no_email', label: 'Sem e-mail' },
  { key: 'ambiguous', label: 'Variação ambígua' },
  { key: 'price_diff', label: 'Preço diferente' },
  { key: 'ready', label: 'Pronto' },
];

const money = (value?: number | null) => {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value));
};

const metricLabel: Record<string, string> = {
  sheets_read: 'Abas lidas',
  suppliers_found: 'Fornecedores encontrados',
  products_found: 'Produtos/variações encontrados',
  prices_detected: 'Preços conferidos',
  prices_divergent: 'Divergências',
  needs_review: 'Itens para revisar',
  suppliers_without_email: 'Fornecedores sem e-mail',
};

export const SpreadsheetReconciliationWorkspace: React.FC<Props> = ({ currentUser, showToast }) => {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [payload, setPayload] = useState<ReconciliationPayload>(emptyPayload);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<ReconciliationItem | null>(null);
  const [supplierItem, setSupplierItem] = useState<ReconciliationItem | null>(null);
  const [familyItem, setFamilyItem] = useState<ReconciliationItem | null>(null);
  const [emailValue, setEmailValue] = useState('');
  const [phoneValue, setPhoneValue] = useState('');
  const [savingAction, setSavingAction] = useState(false);
  const [syncingCatalog, setSyncingCatalog] = useState(false);
  const [viewMode, setViewMode] = useState<'simple' | 'suppliers'>('simple');
  const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({});

  const toggleExpand = (key: string) => {
    setExpandedKeys(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const groupedItems = useMemo(() => {
    if (viewMode !== 'simple') return [];
    const groups: Record<string, GroupedReconciliationItem> = {};
    payload.items.forEach(item => {
      const key = item.portal_item_id || `${item.sheet}::${item.family}::${item.variation}`;
      if (!groups[key]) {
        groups[key] = {
          group_key: key,
          portal_item_id: item.portal_item_id,
          family: item.family,
          subfamily: item.subfamily,
          variation: item.variation,
          display_name: item.display_name,
          portal_price: item.portal_price,
          offers: [],
        };
      }
      groups[key].offers.push(item);
    });
    return Object.values(groups);
  }, [payload.items, viewMode]);

  const canSeeTechnicalDetails = currentUser?.role === 'ADMIN' || currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';

  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedQuery(query.trim()), 350);
    return () => window.clearTimeout(handle);
  }, [query]);

  const loadData = useCallback(async (nextOffset = 0) => {
    const isMore = nextOffset > 0;
    if (isMore) setLoadingMore(true);
    else setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: '80', offset: String(nextOffset), status_filter: filter });
      if (debouncedQuery) params.set('search', debouncedQuery);
      const res = await fetch(`/api/v1/purchases/xlsx-reconciliation?${params.toString()}`);
      if (!res.ok) throw new Error('load failed');
      const data = await res.json();
      setPayload(current => isMore ? { ...data, items: [...current.items, ...data.items] } : data);
    } catch {
      setError('Não consegui conferir a planilha agora.');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [debouncedQuery, filter]);

  useEffect(() => {
    loadData(0);
  }, [loadData]);

  const metrics = useMemo(() => (
    ['sheets_read', 'suppliers_found', 'products_found', 'prices_detected', 'prices_divergent', 'needs_review', 'suppliers_without_email']
      .map(key => ({ key, label: metricLabel[key], value: payload.summary?.[key] || 0 }))
  ), [payload.summary]);

  const updatePrice = async (item: ReconciliationItem) => {
    if (!item.portal_item_id || !item.spreadsheet_price) {
      showToast('Este item precisa corrigir família/variação antes de atualizar preço.', true);
      return;
    }
    setSavingAction(true);
    try {
      const res = await fetch('/api/v1/purchases/xlsx-reconciliation/update-price', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          row_key: item.row_key,
          product_item_id: item.portal_item_id,
          supplier_id: item.portal_supplier_id || null,
          spreadsheet_price: item.spreadsheet_price,
          notes: `Conferência da planilha: ${item.sheet} linha ${item.row_number}`,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Erro ao atualizar preço.');
      }
      showToast('Preço atualizado somente para esta variação.');
      await loadData(0);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao atualizar preço.', true);
    } finally {
      setSavingAction(false);
    }
  };

  const openSupplierDrawer = (item: ReconciliationItem) => {
    setSupplierItem(item);
    setEmailValue(item.email || '');
    setPhoneValue(item.phone || '');
  };

  const saveSupplier = async () => {
    if (!supplierItem?.portal_supplier_id) {
      showToast('Fornecedor ainda não existe no Portal.', true);
      return;
    }
    setSavingAction(true);
    try {
      const res = await fetch('/api/v1/purchases/xlsx-reconciliation/supplier-contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ supplier_id: supplierItem.portal_supplier_id, email: emailValue || null, phone: phoneValue || null }),
      });
      if (!res.ok) throw new Error('Erro ao corrigir fornecedor.');
      showToast('Contato do fornecedor atualizado.');
      setSupplierItem(null);
      await loadData(0);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao corrigir fornecedor.', true);
    } finally {
      setSavingAction(false);
    }
  };

  const exportReport = async () => {
    setSavingAction(true);
    try {
      const res = await fetch('/api/v1/purchases/xlsx-reconciliation/export', { method: 'POST' });
      if (!res.ok) throw new Error('Erro ao exportar relatório.');
      const data = await res.json();
      showToast(`Relatório exportado com ${data.rows} linhas.`);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao exportar relatório.', true);
    } finally {
      setSavingAction(false);
    }
  };

  const syncFromSpreadsheet = async () => {
    setSyncingCatalog(true);
    try {
      const res = await fetch('/api/v1/purchases/catalog/sync-from-xlsx', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Erro ao atualizar da planilha.');
      showToast('Catálogo atualizado da planilha.');
      await loadData(0);
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Erro ao atualizar da planilha.', true);
    } finally {
      setSyncingCatalog(false);
    }
  };

  return (
    <section className="xlsx-reconciliation-workspace">
      <div className="xlsx-reconciliation-hero">
        <div>
          <h2>Conferência da Planilha de Compras</h2>
          <p>Confira fornecedores, produtos e preços reais da planilha antes de cotar ou atualizar valores.</p>
        </div>
        <div className="xlsx-reconciliation-actions">
          <Button variant="secondary" leftIcon={<RefreshCw size={16} />} disabled={syncingCatalog} onClick={syncFromSpreadsheet}>
            {syncingCatalog ? 'Atualizando...' : 'Atualizar da planilha'}
          </Button>
          <Button variant="secondary" leftIcon={<RefreshCw size={16} />} onClick={() => loadData(0)}>Atualizar conferência</Button>
          <Button variant="primary" leftIcon={<Download size={16} />} disabled={savingAction} onClick={exportReport}>Exportar relatório</Button>
        </div>
      </div>

      <label className="xlsx-reconciliation-search" htmlFor="xlsx-reconciliation-search">
        <Search size={18} />
        <input
          id="xlsx-reconciliation-search"
          value={query}
          onChange={event => setQuery(event.target.value)}
          placeholder="Buscar item da planilha, fornecedor, medida ou código..."
        />
      </label>

      <div className="xlsx-reconciliation-metrics">
        {metrics.map(metric => (
          <div key={metric.key} className="xlsx-reconciliation-metric">
            <strong>{metric.value}</strong>
            <small>{metric.label}</small>
          </div>
        ))}
      </div>

      <div className="xlsx-reconciliation-toolbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '8px' }}>
        <div className="xlsx-reconciliation-filters">
          {filters.map(option => (
            <button key={option.key} type="button" className={filter === option.key ? 'active' : ''} onClick={() => setFilter(option.key)}>
              {option.label}
            </button>
          ))}
        </div>
        <div className="xlsx-view-mode-toggle">
          <button
            type="button"
            className={viewMode === 'simple' ? 'active' : ''}
            onClick={() => setViewMode('simple')}
          >
            Visualização Simples
          </button>
          <button
            type="button"
            className={viewMode === 'suppliers' ? 'active' : ''}
            onClick={() => setViewMode('suppliers')}
          >
            Visualização de Fornecedores
          </button>
        </div>
      </div>

      <div className="xlsx-reconciliation-table-card">
        {loading ? (
          <div className="xlsx-reconciliation-loading">Conferindo planilha de compras...</div>
        ) : error ? (
          <div className="xlsx-reconciliation-error">
            <AlertTriangle size={16} />
            <span>{error}</span>
            <Button variant="secondary" size="sm" onClick={() => loadData(0)}>Tentar novamente</Button>
          </div>
        ) : payload.items.length === 0 ? (
          <EmptyState title="Nenhum item encontrado" description="Tente outro filtro ou busca da planilha." />
        ) : (
          <div className="xlsx-reconciliation-table-wrap">
            <table className="xlsx-reconciliation-table">
              <thead>
                <tr>
                  <th>Aba</th>
                  <th>Produto/Insumo</th>
                  <th>Variação</th>
                  <th>Fornecedor</th>
                  <th>E-mail</th>
                  <th>Preço na planilha</th>
                  <th>Preço no Portal</th>
                  <th>Situação</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {viewMode === 'simple' ? (
                  groupedItems.map(group => {
                    const uniqueSheets = Array.from(new Set(group.offers.map(o => o.sheet)));
                    const suppliers = Array.from(new Set(group.offers.map(o => o.supplier_name || o.company_name || 'Sem fornecedor').filter(Boolean)));
                    const emails = Array.from(new Set(group.offers.map(o => o.email).filter(Boolean)));
                    const prices = group.offers.map(o => o.spreadsheet_price).filter((p): p is number => typeof p === 'number');
                    const minPrice = prices.length > 0 ? Math.min(...prices) : null;
                    const maxPrice = prices.length > 0 ? Math.max(...prices) : null;
                    const priceDisplay = minPrice === null ? '-' : minPrice === maxPrice ? money(minPrice) : `${money(minPrice)} ~ ${money(maxPrice)}`;
                    const situations = Array.from(new Set(group.offers.map(o => o.situation)));
                    const isExpanded = !!expandedKeys[group.group_key];

                    return (
                      <React.Fragment key={group.group_key}>
                        <tr style={{ background: isExpanded ? 'rgba(255,255,255,0.02)' : undefined }}>
                          <td>{uniqueSheets.join(', ')}</td>
                          <td>
                            <strong>{group.family}</strong>
                            <small>{group.subfamily || ''}</small>
                          </td>
                          <td>{group.variation}</td>
                          <td>{suppliers.join(', ') || 'Sem fornecedor'}</td>
                          <td>{emails.length === 0 ? 'Sem e-mail' : emails.join(', ')}</td>
                          <td>{priceDisplay}</td>
                          <td>{money(group.portal_price)}</td>
                          <td>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                              {situations.map(sit => (
                                <span key={sit} className={`xlsx-status ${sit === 'Pronto' ? 'ready' : sit === 'Preço diferente' ? 'diff' : 'review'}`}>{sit}</span>
                              ))}
                            </div>
                          </td>
                          <td>
                            <Button
                              size="sm"
                              variant="ghost"
                              leftIcon={isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                              onClick={() => toggleExpand(group.group_key)}
                            >
                              {isExpanded ? 'Recolher' : `Expandir (${group.offers.length})`}
                            </Button>
                          </td>
                        </tr>
                        {isExpanded && group.offers.map(offer => (
                          <tr key={offer.row_key} className="xlsx-sub-row">
                            <td>
                              <span style={{ paddingLeft: '8px', color: 'var(--text-muted)' }}>↳ Linha {offer.row_number}</span>
                            </td>
                            <td></td>
                            <td></td>
                            <td>{offer.supplier_name || offer.company_name || 'Sem fornecedor'}</td>
                            <td>{offer.email || 'Sem e-mail'}</td>
                            <td>{money(offer.spreadsheet_price)}</td>
                            <td>{money(offer.portal_price)}</td>
                            <td>
                              <span className={`xlsx-status ${offer.situation === 'Pronto' ? 'ready' : offer.situation === 'Preço diferente' ? 'diff' : 'review'}`}>
                                {offer.situation}
                              </span>
                            </td>
                            <td>
                              <div className="xlsx-row-actions">
                                <Button size="sm" variant="ghost" leftIcon={<Eye size={13} />} onClick={() => setSelectedItem(offer)}>Detalhes</Button>
                                <Button size="sm" variant="secondary" leftIcon={<Mail size={13} />} onClick={() => openSupplierDrawer(offer)}>Fornecedor</Button>
                                <Button size="sm" variant="secondary" leftIcon={<Wrench size={13} />} onClick={() => setFamilyItem(offer)}>Família</Button>
                                <Button size="sm" variant="primary" disabled={savingAction} onClick={() => updatePrice(offer)}>Atualizar preço</Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </React.Fragment>
                    );
                  })
                ) : (
                  payload.items.map(item => (
                    <tr key={item.row_key}>
                      <td>{item.sheet}</td>
                      <td>
                        <strong>{item.family}</strong>
                        <small>{item.subfamily || item.portal_item_name || ''}</small>
                      </td>
                      <td>{item.variation}</td>
                      <td>{item.supplier_name || item.company_name || 'Sem fornecedor'}</td>
                      <td>{item.email || 'Sem e-mail'}</td>
                      <td>{money(item.spreadsheet_price)}</td>
                      <td>{money(item.portal_price)}</td>
                      <td><span className={`xlsx-status ${item.situation === 'Pronto' ? 'ready' : item.situation === 'Preço diferente' ? 'diff' : 'review'}`}>{item.situation}</span></td>
                      <td>
                        <div className="xlsx-row-actions">
                          <Button size="sm" variant="ghost" leftIcon={<Eye size={13} />} onClick={() => setSelectedItem(item)}>Detalhes</Button>
                          <Button size="sm" variant="secondary" leftIcon={<Mail size={13} />} onClick={() => openSupplierDrawer(item)}>Fornecedor</Button>
                          <Button size="sm" variant="secondary" leftIcon={<Wrench size={13} />} onClick={() => setFamilyItem(item)}>Família</Button>
                          <Button size="sm" variant="primary" disabled={savingAction} onClick={() => updatePrice(item)}>Atualizar preço</Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {payload.has_more && !loading && (
        <div className="xlsx-load-more">
          <Button variant="secondary" disabled={loadingMore} onClick={() => loadData(payload.offset + payload.limit)}>
            {loadingMore ? 'Carregando...' : 'Carregar mais'}
          </Button>
        </div>
      )}

      <Drawer open={!!selectedItem} onClose={() => setSelectedItem(null)} title="Detalhes da divergência" description={selectedItem?.display_name || ''}>
        {selectedItem && (
          <div className="xlsx-drawer-content">
            <div className="xlsx-detail-grid">
              <div><span>Aba</span><strong>{selectedItem.sheet}</strong></div>
              <div><span>Linha</span><strong>{selectedItem.row_number}</strong></div>
              <div><span>Preço na planilha</span><strong>{money(selectedItem.spreadsheet_price)}</strong></div>
              <div><span>Preço no Portal</span><strong>{money(selectedItem.portal_price)}</strong></div>
              <div><span>Diferença</span><strong>{money(selectedItem.difference_amount)}</strong></div>
              <div><span>Situação</span><strong>{selectedItem.situation}</strong></div>
            </div>
            <div className="xlsx-issues">
              {(selectedItem.issues || []).map(issue => <span key={issue}>{issue}</span>)}
            </div>
            <Button variant="primary" onClick={() => updatePrice(selectedItem)}>Atualizar preço no Portal</Button>
            {canSeeTechnicalDetails && selectedItem.technical_details && (
              <details className="products-prices-technical">
                <summary>Detalhes técnicos</summary>
                <pre>{JSON.stringify(selectedItem.technical_details, null, 2)}</pre>
              </details>
            )}
          </div>
        )}
      </Drawer>

      <Drawer open={!!supplierItem} onClose={() => setSupplierItem(null)} title="Corrigir fornecedor" description={supplierItem?.supplier_name || supplierItem?.company_name || ''}>
        {supplierItem && (
          <div className="xlsx-drawer-content">
            <Input label="E-mail" value={emailValue} onChange={event => setEmailValue(event.target.value)} />
            <Input label="Telefone" value={phoneValue} onChange={event => setPhoneValue(event.target.value)} />
            <Button variant="primary" disabled={savingAction || !supplierItem.portal_supplier_id} onClick={saveSupplier}>Salvar contato</Button>
            {!supplierItem.portal_supplier_id && <p>Este fornecedor precisa ser criado ou vinculado no Portal antes de corrigir contato.</p>}
          </div>
        )}
      </Drawer>

      <Drawer open={!!familyItem} onClose={() => setFamilyItem(null)} title="Corrigir família/variação" description={familyItem?.display_name || ''}>
        {familyItem && (
          <div className="xlsx-drawer-content">
            <div className="xlsx-warning">
              <AlertTriangle size={16} />
              <span>Correção de família e variação exige revisão administrativa para não misturar itens parecidos.</span>
            </div>
            <div className="xlsx-detail-grid">
              <div><span>Família detectada</span><strong>{familyItem.family}</strong></div>
              <div><span>Variação detectada</span><strong>{familyItem.variation}</strong></div>
              <div><span>Item no Portal</span><strong>{familyItem.portal_item_name || 'Não vinculado'}</strong></div>
            </div>
            <Button variant="secondary" disabled leftIcon={<CheckCircle2 size={14} />}>Marcar revisado</Button>
          </div>
        )}
      </Drawer>
    </section>
  );
};
