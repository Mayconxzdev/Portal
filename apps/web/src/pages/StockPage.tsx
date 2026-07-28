import React, { useEffect, useState, useMemo, useRef } from 'react';
import { createPortal } from 'react-dom';
import {
  Package,
  Boxes,
  Search,
  RefreshCw,
  Plus,
  X,
  FileSpreadsheet,
  TrendingUp,
  DollarSign,
  AlertTriangle,
  ChevronRight,
  ChevronDown,
  Building2,
  FileText,
  User,
  History,
  ShieldAlert,
  ArrowRight,
  ArrowLeft,
  MoreHorizontal,
  Eye,
  CheckCircle,
  AlertCircle,
  Bell,
  BellOff,
  Zap
} from 'lucide-react';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Input } from '../components/ui/Input';
import { LoadingState } from '../components/ui/LoadingState';
import { Modal } from '../components/ui/Modal';
import { Drawer } from '../components/ui/Drawer';
import { Select } from '../components/ui/Select';
import {
  stockRequest,
  StockSummary,
  StockTreeNode,
  StockCatalogItem,
  StockOffer,
  StockPriceHistory,
  StockReviewItem
} from '../components/stock/stockApi';

/** Interface para alertas inteligentes do catálogo */
interface StockAlert {
  id: string;
  item_id: string;
  item_display_name: string;
  alert_type: 'LOW_STOCK' | 'NO_SUPPLIER' | 'PRICE_STALE' | 'SINGLE_SUPPLIER' | string;
  severity: 'HIGH' | 'MEDIUM' | 'INFO' | string;
  title: string;
  description: string;
  status: string;
  created_at: string | null;
  resolved_at: string | null;
}

const STOCK_CATALOG_CACHE_KEY = 'vesper.stock.catalog.snapshot.v2';

interface CollapsibleTreeNodeProps {
  node: StockTreeNode;
  onSelectNode: (node: StockTreeNode) => void;
  selectedNodePath: string;
}

const CollapsibleTreeNode: React.FC<CollapsibleTreeNodeProps> = ({ node, onSelectNode, selectedNodePath }) => {
  const [isOpen, setIsOpen] = useState(false);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedNodePath === node.path;

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(!isOpen);
  };

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectNode(node);
  };

  return (
    <div className="pl-3 py-1 text-xs">
      <div
        className={`flex items-center gap-1.5 py-1.5 px-2 rounded-xl cursor-pointer hover:bg-white/5 transition-all ${
          isSelected ? 'bg-emerald-500/10 text-emerald-400 font-black border border-emerald-500/20' : 'text-slate-350 font-semibold'
        }`}
        onClick={handleClick}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={handleToggle}
            className="text-slate-400 hover:text-white p-0.5 rounded transition-all focus:outline-none flex items-center justify-center"
          >
            {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        ) : (
          <span className="w-4 flex-shrink-0" />
        )}
        <span className="truncate">{node.title}</span>
      </div>
      {hasChildren && isOpen && (
        <div className="ml-2 border-l border-white/5 mt-1 space-y-1">
          {node.children.map(child => (
            <CollapsibleTreeNode
              key={child.id}
              node={child}
              onSelectNode={onSelectNode}
              selectedNodePath={selectedNodePath}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const StockPage: React.FC<{
  onBack?: () => void;
  currentUser?: any;
  onNavigate?: (moduleCode: string, options?: { search?: Record<string, string> | string }) => void;
}> = ({ onBack, currentUser, onNavigate }) => {
  // Estados Gerais
  const [summary, setSummary] = useState<StockSummary | null>(null);
  const [treeNodes, setTreeNodes] = useState<StockTreeNode[]>([]);
  const [searchResults, setSearchResults] = useState<StockCatalogItem[]>([]);
  
  // Estados de navegacao progressiva por abas
  const [navLevel, setNavLevel] = useState<0 | 1 | 2 | 3>(0);
  const [selectedAba, setSelectedAba] = useState<StockTreeNode | null>(null);
  const [selectedFamily, setSelectedFamily] = useState<StockTreeNode | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<StockTreeNode | null>(null);
  const [selectedVariationGroup, setSelectedVariationGroup] = useState<string | null>(null);
  const [leftPanelSearch, setLeftPanelSearch] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});
  const [productVariations, setProductVariations] = useState<StockCatalogItem[]>([]);
  const [productVariationsLoading, setProductVariationsLoading] = useState(false);
  const [navigationLoading, setNavigationLoading] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);
  
  // Estados de Busca e Filtros
  const [searchQuery, setSearchQuery] = useState('');
  const [confirmedSearchQuery, setConfirmedSearchQuery] = useState('');
  const [filterText, setFilterText] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [catalogPage, setCatalogPage] = useState(1);
  const [alertsPage, setAlertsPage] = useState(1);
  const [selectedSheet, setSelectedSheet] = useState<string>('');
  const [selectedNodePath, setSelectedNodePath] = useState<string>('');
  const [filterNoCybersul, setFilterNoCybersul] = useState(false);
  const [filterNeedsReview, setFilterNeedsReview] = useState(false);
  const [isTreeCollapsed, setIsTreeCollapsed] = useState(false);
  const [includeReview, setIncludeReview] = useState(false);
  const [viewMode, setViewMode] = useState<'catalogo' | 'saneamento'>('catalogo');
  const [saneamentoFilter, setSaneamentoFilter] = useState<string>('todos');
  const [groupedSanitation, setGroupedSanitation] = useState<any | null>(null);
  const [selectedSanitationGroup, setSelectedSanitationGroup] = useState<string | null>(null);
  const [groupItems, setGroupItems] = useState<any[]>([]);
  const [groupItemsLoading, setGroupItemsLoading] = useState(false);
  
  // Fila de revisao
  const [reviewQueue, setReviewQueue] = useState<StockReviewItem[]>([]);

  // Alertas inteligentes
  const [stockAlerts, setStockAlerts] = useState<StockAlert[]>([]);
  const [alertsCollapsed, setAlertsCollapsed] = useState(false);
  const [alertsModalOpen, setAlertsModalOpen] = useState(false);
  const [alertsRefreshing, setAlertsRefreshing] = useState(false);
  
  // UI States
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  
  // Drawer de Detalhes
  const [activeItem, setActiveItem] = useState<StockCatalogItem | null>(null);
  const [itemDetails, setItemDetails] = useState<any | null>(null);
  const [itemOffers, setItemOffers] = useState<StockOffer[]>([]);
  const [itemHistory, setItemHistory] = useState<StockPriceHistory[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTab, setDrawerTab] = useState<'geral' | 'precos' | 'historico' | 'cybersul' | 'tecnico'>('geral');

  // Modais de Fluxos
  const [updatePriceModalOpen, setUpdatePriceModalOpen] = useState(false);
  const [priceForm, setPriceForm] = useState({ supplierId: '', newPrice: '', notes: '' });
  const [pricePreview, setPricePreview] = useState<any | null>(null);
  const [selectedSupplierForUpdate, setSelectedSupplierForUpdate] = useState<StockOffer | null>(null);
  
  const [quoteModalOpen, setQuoteModalOpen] = useState(false);
  const [quotePayload, setQuotePayload] = useState<any | null>(null);
  const [conferenciaMode, setConferenciaMode] = useState<'grid' | 'simplificado' | 'fornecedores'>('grid');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<StockCatalogItem[]>([]);
  const [familyFilter, setFamilyFilter] = useState('');
  const [adminMenuOpen, setAdminMenuOpen] = useState(false);
  const adminMenuButtonRef = useRef<HTMLButtonElement>(null);

  const filteredSuggestions = useMemo(() => {
    return suggestions.filter(
      sug => sug.quality_status !== 'HIDDEN_IN_REVIEW'
    );
  }, [suggestions]);


  // Estado local para o usuario logado com fallback robusto
  const [currentUserState, setCurrentUserState] = useState<any>(currentUser || null);

  useEffect(() => {
    if (currentUser) {
      setCurrentUserState(currentUser);
    }
  }, [currentUser]);

  useEffect(() => {
    if (!currentUserState) {
      fetch('/api/v1/auth/me')
        .then(res => {
          if (res.ok) return res.json();
          throw new Error('Not authenticated');
        })
        .then(userData => {
          setCurrentUserState({
            id: userData.id,
            username: userData.username,
            email: userData.email,
            role: userData.role,
            module_permissions: userData.module_permissions
          });
        })
        .catch(err => {
          console.error("Erro no fallback de usuario do catalogo:", err);
        });
    }
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
      if (adminMenuOpen && adminMenuButtonRef.current && !adminMenuButtonRef.current.contains(event.target as Node)) {
        const target = event.target as HTMLElement;
        if (!target.closest('.stock-floating-menu')) setAdminMenuOpen(false);
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowSuggestions(false);
        setAdminMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    window.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('keydown', handleEscape);
    };
  }, [adminMenuOpen]);

  // Nivel de permissoes do usuario
  const userRole = currentUserState?.role || 'USER';
  const stockPermission = currentUserState?.module_permissions?.stock || (userRole === 'ADMIN' ? 'ADMIN' : 'READ_ONLY');
  const isStaff = userRole === 'ADMIN' || ['MANAGER', 'ADMIN'].includes(stockPermission);
  const isMessias = userRole === 'MESSIAS';
  const isAdminOrMessias = userRole === 'ADMIN' || isMessias;
  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined || value <= 0) return 'Sem preço cadastrado';
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
  };
  const itemSubtitle = (item: StockCatalogItem) => {
    const parts = [
      item.variation_label,
      item.measure_display || item.normalized_measure,
      item.primary_supplier || item.last_supplier || ((item.primary_price ?? item.last_price) ? 'Fornecedor não informado' : null),
      (item.primary_price ?? item.last_price) ? formatCurrency(item.primary_price ?? item.last_price) : 'Cotar para atualizar'
    ].filter(Boolean);
    return parts.join(' · ');
  };

  const nodeLabel = (node?: StockTreeNode | null) => node?.display_label || node?.label || node?.title || '';
  const activeProductLabel = activeItem?.display_name || nodeLabel(selectedProduct) || activeItem?.base_name || 'Selecione um produto';
  const itemMeasureText = (item: StockCatalogItem) => {
    const measure = item.measure_display || item.normalized_measure || '';
    if (!measure) return item.variation_label || 'Medida a revisar';
    if (item.measure_kind === 'partial') return measure.startsWith('Espessura') ? measure : `Espessura: ${measure}`;
    if (item.variation_label && !measure.includes(item.variation_label)) return `${item.variation_label} · ${measure}`;
    return measure;
  };
  const itemAttributeLine = (item: StockCatalogItem) => {
    const parts: string[] = [];
    const meta = item.metadata_json || {};
    if (meta.espessura) parts.push(`Espessura: ${meta.espessura}`);
    if (meta.peso) parts.push(`Peso: ${meta.peso}`);
    if (meta.dimensao && meta.dimensao !== item.variation_label) parts.push(meta.dimensao);
    return parts.join(' · ');
  };
  const itemPrice = (item: StockCatalogItem) => item.primary_price ?? item.last_price;
  const itemSupplier = (item: StockCatalogItem) => item.primary_supplier ?? item.last_supplier;
  const purchaseContext = itemDetails?.purchase_context;
  const hasOpenPurchase = Boolean(purchaseContext?.has_open_purchase);
  const productKind = (label: string) => {
    const text = label.toLowerCase();
    if (text.includes('inox')) return 'Inox';
    if (text.includes('alum')) return 'Aluminio';
    if (text.includes('ferro') || text.includes('aco') || text.includes('aço')) return 'Ferro';
    if (text.includes('rod')) return 'Acessorios';
    if (text.includes('paraf')) return 'Fixador';
    if (text.includes('tubo')) return 'Tubo';
    if (text.includes('chapa')) return 'Chapa';
    return 'Catalogo';
  };
  const productDescription = (label: string) => {
    const kind = productKind(label);
    if (kind === 'Ferro') return 'Produto estrutural para fabricação, reforços e manutenção operacional.';
    if (kind === 'Inox') return 'Item resistente à corrosão para aplicações industriais e acabamento.';
    if (kind === 'Aluminio') return 'Material leve para aplicações técnicas, montagem e acabamento.';
    if (kind === 'Fixador') return 'Grupo de fixadores com variações por diâmetro, rosca e comprimento.';
    return 'Grupo comercial com variações compráveis, fornecedores e preços vinculados.';
  };
  const adminMenuPosition = () => {
    const rect = adminMenuButtonRef.current?.getBoundingClientRect();
    if (!rect) return { top: 72, left: 320 };
    const menuWidth = 250;
    const menuHeight = 180;
    const spaceBelow = window.innerHeight - rect.bottom;
    const openUpwards = spaceBelow < menuHeight && rect.top > menuHeight;
    return {
      top: openUpwards ? rect.top - menuHeight - 8 : rect.bottom + 8,
      left: Math.max(12, Math.min(rect.right - menuWidth, window.innerWidth - menuWidth - 12)),
    };
  };

  const filteredTree = useMemo(() => {
    const query = leftPanelSearch.trim().toLowerCase();
    return treeNodes.map(aba => {
      const allProducts = aba.children?.flatMap(fam => fam.children || []) || [];
      
      if (!query) {
        return {
          ...aba,
          _products: allProducts,
        };
      }
      
      const abaMatches = nodeLabel(aba).toLowerCase().includes(query);
      const matchingProducts = allProducts.filter(p => 
        nodeLabel(p).toLowerCase().includes(query)
      );
      
      if (abaMatches || matchingProducts.length > 0) {
        return {
          ...aba,
          _products: matchingProducts.length > 0 ? matchingProducts : allProducts,
          _forceOpen: true,
        };
      }
      return null;
    }).filter(Boolean) as any[];
  }, [treeNodes, leftPanelSearch]);

  const getGroupLabel = (variationLabel: string | null) => {
    const val = variationLabel || 'Sem variação';
    if (val === 'Sem variação') return val;
    const normalized = val.replace(/[“”]/g, '"');
    const parts = normalized.split(/\s*[xX]\s*/);
    return parts[0].trim();
  };

  const variationGroups = useMemo(() => {
    const groups: Record<string, StockCatalogItem[]> = {};
    productVariations.forEach(item => {
      const groupLabel = getGroupLabel(item.variation_label);
      if (!groups[groupLabel]) {
        groups[groupLabel] = [];
      }
      groups[groupLabel].push(item);
    });
    return Object.entries(groups).map(([label, items]) => {
      // Find min and max prices
      const prices = items.map(item => item.primary_price ?? item.last_price).filter((p): p is number => p !== null && p > 0);
      const minPrice = prices.length > 0 ? Math.min(...prices) : null;
      const maxPrice = prices.length > 0 ? Math.max(...prices) : null;
      
      // Unique suppliers
      const suppliers = Array.from(new Set(items.map(item => item.primary_supplier ?? item.last_supplier).filter(Boolean)));
      
      // Cybersul count
      const cybersulCount = items.filter(item => item.cybersul_code).length;
      
      return {
        label,
        items,
        fullName: `${selectedProduct ? nodeLabel(selectedProduct) : ''} - ${label}`,
        minPrice,
        maxPrice,
        suppliers,
        cybersulCount,
      };
    });
  }, [productVariations, selectedProduct]);

  const selectedGroupItems = useMemo(() => {
    return productVariations.filter(item => getGroupLabel(item.variation_label) === selectedVariationGroup);
  }, [productVariations, selectedVariationGroup]);

  const filteredProducts = useMemo(() => {
    const products = selectedAba?.children?.flatMap((fam: any) => fam.children || []) || [];
    if (!filterText.trim()) return products;
    const q = filterText.toLowerCase().trim();
    return products.filter(prod => 
      nodeLabel(prod).toLowerCase().includes(q) || 
      productKind(nodeLabel(prod)).toLowerCase().includes(q)
    );
  }, [selectedAba, filterText]);

  const filteredVariationGroups = useMemo(() => {
    if (!filterText.trim()) return variationGroups;
    const q = filterText.toLowerCase().trim();
    return variationGroups.filter(group => 
      group.fullName.toLowerCase().includes(q) ||
      group.suppliers.some(s => s && s.toLowerCase().includes(q))
    );
  }, [variationGroups, filterText]);

  const filteredGroupItems = useMemo(() => {
    if (!filterText.trim()) return selectedGroupItems;
    const q = filterText.toLowerCase().trim();
    return selectedGroupItems.filter(item => 
      item.display_name.toLowerCase().includes(q) ||
      itemMeasureText(item).toLowerCase().includes(q) ||
      (item.cybersul_code && item.cybersul_code.toLowerCase().includes(q)) ||
      (itemSupplier(item) && itemSupplier(item)!.toLowerCase().includes(q))
    );
  }, [selectedGroupItems, filterText]);

  const detailPreviewItem = activeItem;
  const priorityAlerts = useMemo(() => {
    const severityWeight: Record<string, number> = { HIGH: 0, CRITICAL: 0, MEDIUM: 1, WARNING: 1, INFO: 2, LOW: 3 };
    return [...stockAlerts].sort((a, b) => {
      const severityDiff = (severityWeight[a.severity] ?? 4) - (severityWeight[b.severity] ?? 4);
      if (severityDiff !== 0) return severityDiff;
      return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
    });
  }, [stockAlerts]);

  const alertSummary = useMemo(() => {
    const labels: Record<string, string> = {
      LOW_STOCK: 'com estoque baixo',
      OUT_OF_STOCK: 'sem estoque',
      NO_STOCK: 'sem estoque',
      NO_SUPPLIER: 'sem fornecedor',
      MISSING_SUPPLIER: 'sem fornecedor',
      PRICE_STALE: 'com preco desatualizado',
      MISSING_PRICE: 'sem preco',
      NO_PRICE: 'sem preco',
      QUOTE_OPEN: 'ja possuem cotacao',
      PURCHASE_OPEN: 'ja possuem compra',
      SINGLE_SUPPLIER: 'com fornecedor unico',
    };
    const counts = new Map<string, number>();
    stockAlerts.forEach((alert) => {
      const label = labels[alert.alert_type] || 'precisam de revisao';
      counts.set(label, (counts.get(label) || 0) + 1);
    });
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [stockAlerts]);

  const paginate = <T,>(items: T[], page: number, perPage: number) => {
    const totalPages = Math.max(1, Math.ceil(items.length / perPage));
    const safePage = Math.min(Math.max(page, 1), totalPages);
    const start = (safePage - 1) * perPage;
    return {
      totalPages,
      safePage,
      start,
      end: Math.min(start + perPage, items.length),
      items: items.slice(start, start + perPage),
    };
  };

  // Helpers de Saneamento
  const handleSelectSanitationGroup = async (groupKey: string) => {
    setSelectedSanitationGroup(groupKey);
    setGroupItemsLoading(true);
    try {
      const items = await stockRequest<any[]>(`/review-queue/group/${groupKey}`);
      setGroupItems(items);
    } catch (err: any) {
      setError('Erro ao carregar itens do grupo de saneamento.');
    } finally {
      setGroupItemsLoading(false);
    }
  };

  const getBulkActionForGroup = (groupKey: string): string | null => {
    if (groupKey === 'high_confidence') return 'APPROVE_ALL';
    if (groupKey === 'quarantine') return 'EXCLUDE_ALL';
    if (groupKey === 'missing_email') return 'KEEP_WITHOUT_EMAIL';
    if (groupKey === 'incomplete_offers') return 'IGNORE_ALL';
    return null;
  };

  const getBulkActionLabel = (groupKey: string): string => {
    if (groupKey === 'high_confidence') return 'Aprovar todos';
    if (groupKey === 'quarantine') return 'Excluir todos';
    if (groupKey === 'missing_email') return 'Manter sem e-mail';
    if (groupKey === 'incomplete_offers') return 'Ignorar todas';
    return '';
  };

  const handleBulkAction = async (groupKey: string) => {
    const action = getBulkActionForGroup(groupKey);
    if (!action) return;
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const res = await stockRequest<any>(`/review-queue/group/${groupKey}/resolve?action=${action}`, {
        method: 'POST'
      });
      setMessage(`Acao em lote executada: ${res.resolved_count} itens resolvidos.`);
      setSelectedSanitationGroup(null);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Erro ao executar acao em massa.');
    } finally {
      setLoading(false);
    }
  };

  // Debounce da Busca
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Sempre reseta includeReview se a busca mudar
  useEffect(() => {
    setIncludeReview(false);
  }, [searchQuery]);

  // Sempre limpa o filtro local quando muda de nível de navegação ou aba/produto selecionado
  useEffect(() => {
    setFilterText('');
  }, [navLevel, selectedAba?.id, selectedProduct?.id, selectedVariationGroup]);

  useEffect(() => {
    setCatalogPage(1);
  }, [navLevel, selectedAba?.id, selectedProduct?.id, selectedVariationGroup, confirmedSearchQuery, filterText]);

  useEffect(() => {
    setAlertsPage(1);
  }, [stockAlerts.length]);

  const hydrateCachedCatalog = () => {
    try {
      const raw = window.sessionStorage.getItem(STOCK_CATALOG_CACHE_KEY);
      if (!raw) return false;
      const cached = JSON.parse(raw) as { summary?: StockSummary; treeNodes?: StockTreeNode[] };
      if (!cached.summary || !Array.isArray(cached.treeNodes)) return false;
      setSummary(cached.summary);
      setTreeNodes(cached.treeNodes);
      setLoading(false);
      return true;
    } catch {
      return false;
    }
  };

  const rememberCatalogSnapshot = (summaryData: StockSummary, treeData: StockTreeNode[]) => {
    try {
      window.sessionStorage.setItem(
        STOCK_CATALOG_CACHE_KEY,
        JSON.stringify({ summary: summaryData, treeNodes: treeData, cachedAt: new Date().toISOString() })
      );
    } catch {
      // Cache local e opcional: falhar aqui nao pode bloquear o catalogo.
    }
  };

  // Carregar Dados Iniciais
  const loadData = async (options: { background?: boolean } = {}) => {
    const background = Boolean(options.background);
    if (!background) setLoading(true);
    setError('');
    try {
      const [summaryData, treeData] = await Promise.all([
        stockRequest<StockSummary>('/summary'),
        stockRequest<StockTreeNode[]>('/navigation/categories')
      ]);
      setSummary(summaryData);
      setTreeNodes(treeData);
      rememberCatalogSnapshot(summaryData, treeData);

      // Carregar alertas inteligentes (silencioso — sem bloquear a carga principal)
      stockRequest<StockAlert[]>('/alerts?limit=30')
        .then(alerts => setStockAlerts(alerts))
        .catch(() => { /* alertas opcionais — falha silenciosa */ });

    } catch (err: any) {
      setError(err.message || 'Erro ao carregar dados do catalogo.');
    } finally {
      if (!background) setLoading(false);
    }
  };

  const loadSanitationData = async () => {
    if (!isAdminOrMessias) return;
    try {
      const [reviewData, groupedData] = await Promise.all([
        stockRequest<StockReviewItem[]>('/review-queue').catch(() => []),
        stockRequest<any>('/review-queue/grouped').catch(() => null),
      ]);
      setReviewQueue(reviewData);
      setGroupedSanitation(groupedData);
    } catch {
      setReviewQueue([]);
      setGroupedSanitation(null);
    }
  };

  // Atualizar alertas manualmente (somente Admin/Messias)
  const handleRefreshAlerts = async () => {
    setAlertsRefreshing(true);
    try {
      await stockRequest<any>('/alerts/refresh', { method: 'POST' });
      const alerts = await stockRequest<StockAlert[]>('/alerts?limit=30');
      setStockAlerts(alerts);
      setMessage(`Alertas atualizados: ${alerts.length} alerta(s) ativo(s).`);
    } catch (err: any) {
      setError(err.message || 'Erro ao atualizar alertas.');
    } finally {
      setAlertsRefreshing(false);
    }
  };

  // Reconhecer alerta individualmente
  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await stockRequest<any>(`/alerts/${alertId}/acknowledge`, { method: 'POST' });
      setStockAlerts(prev => prev.filter(a => a.id !== alertId));
    } catch {
      // Falha silenciosa — UI já removeu localmente
    }
  };

  useEffect(() => {
    const hydrated = hydrateCachedCatalog();
    loadData({ background: hydrated });
  }, []);

  useEffect(() => {
    if (viewMode === 'saneamento') {
      loadSanitationData();
    }
  }, [viewMode]);

  // Debounce da busca para sugestoes (autocomplete)
  useEffect(() => {
    const performSuggestionsSearch = async () => {
      if (!debouncedQuery.trim()) {
        setSuggestions([]);
        return;
      }
      try {
        const results = await stockRequest<StockCatalogItem[]>(`/search?suggest=true&q=${encodeURIComponent(debouncedQuery)}&include_review=${includeReview}`);
        setSuggestions(results);
      } catch (err: any) {
        console.error('Erro ao buscar sugestoes:', err);
      }
    };
    performSuggestionsSearch();
  }, [debouncedQuery, includeReview]);

  // Limpa estados de busca se a busca for limpa e nenhuma categoria estiver selecionada
  useEffect(() => {
    if (!searchQuery.trim() && !selectedNodePath) {
      setSuggestions([]);
      setSearchResults([]);
      setConfirmedSearchQuery('');
    }
  }, [searchQuery, selectedNodePath]);

  // Funcao para executar a busca principal confirmada
  const triggerSearch = async (queryText: string) => {
    if (!queryText.trim()) {
      setSearchResults([]);
      setConfirmedSearchQuery('');
      return;
    }
    setSearchLoading(true);
    setShowSuggestions(false);
    setConfirmedSearchQuery(queryText.trim());
    try {
      const results = await stockRequest<StockCatalogItem[]>(`/search?q=${encodeURIComponent(queryText)}&include_review=${includeReview}`);
      setSearchResults(results);
    } catch (err: any) {
      console.error('Erro na busca principal:', err);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleSelectSuggestion = (item: StockCatalogItem) => {
    setSearchQuery(item.display_name);
    setShowSuggestions(false);
    handleOpenDetails(item);
    triggerSearch(item.display_name);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      triggerSearch(searchQuery);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  const clearCatalogSearch = () => {
    setFamilyFilter('');
    setSearchQuery('');
    setSearchResults([]);
    setConfirmedSearchQuery('');
    setSuggestions([]);
    setShowSuggestions(false);
    setIncludeReview(false);
  };

  const handleSideSearchChange = (value: string) => {
    setFamilyFilter(value);
    setSearchQuery(value);
    if (!value.trim()) {
      clearCatalogSearch();
      return;
    }
    setShowSuggestions(true);
  };

  const handleSideSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      triggerSearch(familyFilter);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };


  // Sincronizar planilhas (Somente Admin/Messias)
  const handleSync = async (type: 'compras-nova' | 'cybersul' | 'unified') => {
    setSyncLoading(type);
    setError('');
    setMessage('');
    try {
      const endpoint = type === 'unified' ? '/import/unified' : `/import/${type}`;
      const res = await stockRequest<any>(endpoint, { method: 'POST' });
      setMessage(res.message || 'Sincronizacao concluida com sucesso.');
      await loadData();
      if (searchQuery) {
        // Recarrega busca ativa
        const results = await stockRequest<StockCatalogItem[]>(`/search?q=${encodeURIComponent(searchQuery)}&include_review=${includeReview}`);
        setSearchResults(results);
      }
    } catch (err: any) {
      setError(err.message || `Falha ao sincronizar: ${type}`);
    } finally {
      setSyncLoading(null);
    }
  };

  // Abrir Drawer de Detalhes
  const handleOpenDetails = async (item: StockCatalogItem) => {
    setActiveItem(item);
    setDrawerTab('geral');
    setDrawerOpen(true);
    try {
      const [details, offers, history] = await Promise.all([
        stockRequest<any>(`/items/${item.id}`),
        stockRequest<StockOffer[]>(`/items/${item.id}/offers`),
        stockRequest<StockPriceHistory[]>(`/items/${item.id}/history`)
      ]);
      setItemDetails(details);
      setItemOffers(offers);
      setItemHistory(history);
    } catch (err: any) {
      setError('Erro ao carregar detalhes do item no Drawer.');
    }
  };

  const handleOpenAlertTarget = async (alert: StockAlert) => {
    setAlertsModalOpen(false);
    try {
      const [details, offers, history] = await Promise.all([
        stockRequest<any>(`/items/${alert.item_id}`),
        stockRequest<StockOffer[]>(`/items/${alert.item_id}/offers`),
        stockRequest<StockPriceHistory[]>(`/items/${alert.item_id}/history`)
      ]);
      const linkedItem: StockCatalogItem = {
        id: String(details.id),
        display_name: details.display_name || alert.item_display_name || details.base_name || 'Item do catalogo',
        base_name: details.base_name || details.display_name || alert.item_display_name || 'Item do catalogo',
        source_sheet: details.source_sheet || '',
        variation_label: details.variation_label || null,
        normalized_measure: details.normalized_measure || null,
        measure_display: details.measure_display || null,
        measure_kind: details.measure_kind || null,
        specification_text: details.specification_text || null,
        internal_code: details.internal_code || null,
        quality_status: details.quality_status,
        needs_review: Boolean(details.needs_review),
        review_reason: details.review_reason || null,
        family_path: details.family_path || '',
        cybersul_code: details.cybersul_code || null,
        cybersul_description: details.cybersul_description || null,
        balance_total: Number(details.balance_total || 0),
        last_price: details.primary_price ?? null,
        last_supplier: details.primary_supplier ?? null,
        primary_price: details.primary_price ?? null,
        primary_supplier: details.primary_supplier ?? null,
        offer_count: details.offer_count ?? offers.length,
        has_price: Boolean(details.has_price),
        metadata_json: details.metadata_json || null,
        unit: details.unit || 'un',
      };
      setActiveItem(linkedItem);
      setDrawerTab(alert.alert_type === 'PRICE_STALE' ? 'precos' : 'geral');
      setDrawerOpen(true);
      setItemDetails(details);
      setItemOffers(offers);
      setItemHistory(history);
    } catch {
      setError('Nao foi possivel abrir o item do alerta. Ele pode ter sido removido ou voce perdeu acesso.');
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const itemId = params.get('item');
    if (!itemId) return;

    const openLinkedItem = async () => {
      try {
        const [details, offers, history] = await Promise.all([
          stockRequest<any>(`/items/${itemId}`),
          stockRequest<StockOffer[]>(`/items/${itemId}/offers`),
          stockRequest<StockPriceHistory[]>(`/items/${itemId}/history`),
        ]);
        const linkedItem: StockCatalogItem = {
          id: String(details.id),
          display_name: details.display_name || details.base_name || 'Item do catalogo',
          base_name: details.base_name || details.display_name || 'Item do catalogo',
          source_sheet: details.source_sheet || '',
          variation_label: details.variation_label || null,
          normalized_measure: details.normalized_measure || null,
          measure_display: details.measure_display || null,
          measure_kind: details.measure_kind || null,
          specification_text: details.specification_text || null,
          internal_code: details.internal_code || null,
          quality_status: details.quality_status,
          needs_review: Boolean(details.needs_review),
          review_reason: details.review_reason || null,
          family_path: details.family_path || '',
          cybersul_code: details.cybersul_code || null,
          cybersul_description: details.cybersul_description || null,
          balance_total: Number(details.balance_total || 0),
          last_price: details.primary_price ?? null,
          last_supplier: details.primary_supplier ?? null,
          primary_price: details.primary_price ?? null,
          primary_supplier: details.primary_supplier ?? null,
          offer_count: details.offer_count ?? offers.length,
          has_price: Boolean(details.has_price),
          metadata_json: details.metadata_json || null,
          unit: details.unit || 'un',
        };
        setActiveItem(linkedItem);
        setDrawerTab('geral');
        setDrawerOpen(true);
        setItemDetails(details);
        setItemOffers(offers);
        setItemHistory(history);
      } catch {
        setError('Nao foi possivel abrir o item vinculado. Ele pode ter sido removido ou voce perdeu acesso.');
      }
    };

    openLinkedItem();
  }, []);

  // Fluxo de atualizacao de preco
  const handleOpenUpdatePrice = (supplierOffer: StockOffer) => {
    setSelectedSupplierForUpdate(supplierOffer);
    setPriceForm({
      supplierId: supplierOffer.supplier_id,
      newPrice: supplierOffer.price ? supplierOffer.price.toFixed(2) : '',
      notes: ''
    });
    setPricePreview(null);
    setUpdatePriceModalOpen(true);
  };

  // Exibir preview do preco antes de salvar
  const handlePriceChange = (val: string) => {
    const num = parseFloat(val.replace(',', '.'));
    setPriceForm(prev => ({ ...prev, newPrice: val }));
    
    if (selectedSupplierForUpdate && !isNaN(num) && num > 0) {
      const oldPrice = selectedSupplierForUpdate.price || 0.0;
      const diff = num - oldPrice;
      const percent = oldPrice > 0 ? (diff / oldPrice) * 100 : 0.0;
      
      setPricePreview({
        oldPrice,
        newPrice: num,
        diff,
        percent
      });
    } else {
      setPricePreview(null);
    }
  };

  // Confirmar atualizacao de preco
  const handleConfirmPriceUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeItem || !selectedSupplierForUpdate || !priceForm.newPrice) return;
    setError('');
    setMessage('');
    const newPrice = parseFloat(priceForm.newPrice.replace(',', '.'));
    try {
      const res = await stockRequest<any>(`/items/${activeItem.id}/price-update`, {
        method: 'POST',
        body: JSON.stringify({
          supplier_id: priceForm.supplierId,
          new_price: newPrice,
          notes: priceForm.notes
        })
      });
      setMessage(res.message || `Preco atualizado para ${res.supplier_name}: ${formatCurrency(res.new_price)}`);
      setUpdatePriceModalOpen(false);

      // ── Update otimista: reflete o novo preço imediatamente no estado local ──
      const updatedActiveItem: StockCatalogItem = {
        ...activeItem,
        primary_price: res.new_price,
        last_price: res.new_price,
        primary_supplier: res.supplier_name,
        last_supplier: res.supplier_name,
        has_price: true,
      };
      setActiveItem(updatedActiveItem);

      // Atualizar na lista de resultados da busca (se o item estiver lá)
      setSearchResults(prev =>
        prev.map(item =>
          item.id === activeItem.id ? updatedActiveItem : item
        )
      );

      // Atualizar nas variações do produto selecionado (se o item estiver lá)
      setProductVariations(prev =>
        prev.map(item =>
          item.id === activeItem.id ? updatedActiveItem : item
        )
      );

      // Atualizar drawer, painel lateral, histórico e alertas com dados reais.
      const [details, offers, history, alerts] = await Promise.all([
        stockRequest<any>(`/items/${activeItem.id}`),
        stockRequest<StockOffer[]>(`/items/${activeItem.id}/offers`),
        stockRequest<StockPriceHistory[]>(`/items/${activeItem.id}/history`),
        stockRequest<StockAlert[]>('/alerts?limit=30').catch(() => stockAlerts)
      ]);
      setItemDetails(details);
      setItemOffers(offers);
      setItemHistory(history);
      setStockAlerts(alerts);
      setSelectedSupplierForUpdate(prev => prev ? {
        ...prev,
        price: res.new_price,
        price_raw: formatCurrency(res.new_price),
      } : prev);

      // Atualizar summary silenciosamente (baixo custo)
      stockRequest<StockSummary>('/summary').then(setSummary).catch(() => {});

    } catch (err: any) {
      setError(err.message || 'Erro ao atualizar preco.');
    }
  };

  // Fluxo de cotacao (quote draft)
  const handleQuoteDraft = async (item: StockCatalogItem) => {
    setError('');
    try {
      const payload = await stockRequest<any>(`/items/${item.id}/quote-draft`, { method: 'POST' });
      const quoteId = payload.quote_id || payload.id;
      if (!quoteId) {
        throw new Error('A cotacao foi criada, mas o Portal nao retornou o identificador para abrir Compras.');
      }
      const actionUrl = payload.action_url || `/purchases?quote=${quoteId}&step=products`;
      setMessage(payload.message || (payload.existing_quote
        ? 'Cotacao em andamento localizada. Abrindo Compras...'
        : 'Cotacao criada em Compras. Abrindo montagem assistida...'));
      window.history.pushState(null, '', actionUrl);
      window.dispatchEvent(new PopStateEvent('popstate'));
    } catch (err: any) {
      setError(err.message || 'Erro ao gerar cotacao.');
    }
  };

  // Resolver item na fila de revisao
  const handleResolveReview = async (reviewId: string, action: 'APPROVE' | 'IGNORE') => {
    setError('');
    setMessage('');
    try {
      await stockRequest<any>(`/review-queue/${reviewId}/resolve?action=${action}`, { method: 'POST' });
      setMessage('Item revisado com sucesso.');
      loadData();
    } catch (err: any) {
      setError(err.message || 'Erro ao resolver pendencia de revisao.');
    }
  };

  // Filtra o sentinel para verificar se existem itens ocultos em revisao
  const hasHiddenReviews = useMemo(() => {
    return searchResults.some(item => item.quality_status === 'HIDDEN_IN_REVIEW');
  }, [searchResults]);

  const displayedResults = useMemo(() => {
    return searchResults.filter(item => {
      if (item.quality_status === 'HIDDEN_IN_REVIEW') return false;
      return true;
    });
  }, [searchResults]);

  const catalogPageSize = navLevel === 0 ? 12 : navLevel === 1 || navLevel === 3 || confirmedSearchQuery ? 8 : 9;
  const rootCatalogPage = paginate(treeNodes, catalogPage, catalogPageSize);
  const productsCatalogPage = paginate(filteredProducts, catalogPage, catalogPageSize);
  const variationGroupsCatalogPage = paginate(filteredVariationGroups, catalogPage, catalogPageSize);
  const groupItemsCatalogPage = paginate(filteredGroupItems, catalogPage, catalogPageSize);
  const searchCatalogPage = paginate(displayedResults, catalogPage, catalogPageSize);
  const alertsPageData = paginate(priorityAlerts, alertsPage, 8);

  const renderPagination = (
    label: string,
    pageData: { totalPages: number; safePage: number; start: number; end: number; items: unknown[] },
    totalItems: number,
    onPageChange: (page: number) => void
  ) => {
    if (pageData.totalPages <= 1) return null;

    return (
      <nav className="stock-pagination" aria-label={`Paginacao de ${label}`}>
        <span>
          {pageData.start + 1}-{pageData.end} de {totalItems}
        </span>
        <div className="stock-pagination-actions">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onPageChange(pageData.safePage - 1)}
            disabled={pageData.safePage <= 1}
            aria-label={`Pagina anterior de ${label}`}
          >
            Anterior
          </Button>
          <strong>{pageData.safePage}</strong>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onPageChange(pageData.safePage + 1)}
            disabled={pageData.safePage >= pageData.totalPages}
            aria-label={`Proxima pagina de ${label}`}
          >
            Proxima
          </Button>
        </div>
      </nav>
    );
  };

  const matchesFilter = (rev: StockReviewItem, filter: string) => {
    const desc = (rev.description || '').toLowerCase();
    const title = (rev.title || '').toLowerCase();
    const type = (rev.review_type || '').toLowerCase();
    const text = `${desc} ${title} ${type}`;
    
    switch(filter) {
      case 'sem_fornecedor':
        return text.includes('fornecedor') || text.includes('supplier');
      case 'sem_codigo':
        return text.includes('codigo') || text.includes('cybersul') || text.includes('sem codigo');
      case 'duplicado':
        return text.includes('duplicado') || text.includes('duplicidade') || text.includes('similar');
      case 'preco_suspeito':
        return text.includes('preco') || text.includes('suspeito') || text.includes('valor');
      case 'baixa_confianca':
        return text.includes('confianca') || text.includes('match') || text.includes('baixa');
      case 'inativo':
        return text.includes('inativo') || text.includes('inativa') || text.includes('inactive');
      case 'saldo_zerado':
        return text.includes('saldo') || text.includes('compra recente');
      default:
        return true;
    }
  };

  const filteredReviews = useMemo(() => {
    return reviewQueue.filter(rev => matchesFilter(rev, saneamentoFilter));
  }, [reviewQueue, saneamentoFilter]);

  const handleNodeClick = async (node: StockTreeNode) => {
    setSelectedNodePath(node.path);
    setSearchQuery(''); // Limpa busca para mostrar listagem da arvore
    setSearchResults([]);
    setSearchLoading(true);
    setError('');
    try {
      let queryUrl = `/search?include_review=${includeReview}`;
      if (node.node_type === 'sheet') {
        queryUrl += `&sheet=${encodeURIComponent(node.title)}`;
        setSelectedSheet(node.title);
      } else if (node.node_type === 'family') {
        queryUrl += `&family_id=${node.id}`;
        setSelectedSheet(node.sheet);
      } else if (node.node_type === 'product') {
        queryUrl += `&product_id=${node.id}`;
        setSelectedSheet(node.sheet);
      }
      const results = await stockRequest<StockCatalogItem[]>(queryUrl);
      setSearchResults(results);
    } catch (err: any) {
      setError(err.message || 'Erro ao filtrar itens da arvore.');
    } finally {
      setSearchLoading(false);
    }
  };

  const handleSelectAba = async (aba: StockTreeNode) => {
    const alreadyLoaded = Boolean(aba.children && aba.children.length > 0);
    setSelectedAba(aba);
    setSelectedFamily(null);
    setSelectedProduct(null);
    setActiveItem(null);
    setSelectedVariationGroup(null);
    setProductVariations([]);
    setNavLevel(1);
    setSearchQuery('');
    setSearchResults([]);
    setConfirmedSearchQuery('');
    setExpandedCategories(prev => ({ ...prev, [aba.id]: true }));
    if (alreadyLoaded) return;

    setNavigationLoading(true);
    try {
      const families = await stockRequest<StockTreeNode[]>(`/navigation/families?category=${encodeURIComponent(nodeLabel(aba))}`);
      const hydratedAba = { ...aba, children: families };
      setSelectedAba(hydratedAba);
      setTreeNodes(prev => prev.map(node => node.id === aba.id ? hydratedAba : node));
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar produtos da categoria.');
    } finally {
      setNavigationLoading(false);
    }
  };

  const handleSelectFamily = (family: StockTreeNode) => {
    setSelectedFamily(family);
    setSelectedProduct(null);
    setActiveItem(null);
    setNavLevel(2);
  };

  const handleSelectProduct = async (product: StockTreeNode) => {
    setSelectedProduct(product);
    setActiveItem(null);
    setNavLevel(2);
    setProductVariationsLoading(true);
    try {
      const results = await stockRequest<StockCatalogItem[]>(`/search?product_id=${product.id}&include_review=${includeReview}`);
      setProductVariations(results);
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar variacoes.');
    } finally {
      setProductVariationsLoading(false);
    }
  };

  return (
    <div className="stock-page module-page text-left">
      {/* FEEDBACK BANNERS */}
      {message && (
        <div className="glass-card mb-4" style={{ padding: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderColor: 'rgba(52, 211, 153, 0.35)', borderRadius: '14px' }}>
          <span style={{ color: '#a7f3d0', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}><CheckCircle size={18} /> {message}</span>
          <button type="button" onClick={() => setMessage('')} className="text-slate-400 hover:text-white"><X size={18} /></button>
        </div>
      )}
      {error && (
        <div className="glass-card mb-4" style={{ padding: 14, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderColor: 'rgba(248, 113, 113, 0.35)', borderRadius: '14px' }}>
          <span style={{ color: '#fecaca', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}><AlertTriangle size={18} /> {error}</span>
          <button type="button" onClick={() => setError('')} className="text-slate-400 hover:text-white"><X size={18} /></button>
        </div>
      )}

      {viewMode === 'catalogo' ? (
        <>
          {/* NAVEGACAO PROGRESSIVA POR ABAS */}
          {/* CABEÇALHO DO MÓDULO E KPIS */}
          <header className="stock-module-header mb-4">
            <div className="stock-header-line">
              <div className="stock-header-title">
                <h1 className="text-xl font-black text-white flex items-center gap-2">
                  <Boxes size={24} className="text-emerald-400" />
                  Estoque & Catálogo
                </h1>
                <p className="text-xs text-slate-450 font-semibold mt-1">
                  Consulte produtos, códigos, preços e fornecedores em uma base única.
                </p>
              </div>

              <div className="stock-kpi-compact-strip">
                <div className="stock-kpi-mini-card">
                  <div className="stock-kpi-mini-icon is-green">
                    <Package size={18} />
                  </div>
                  <div>
                    <span>Produtos disponíveis</span>
                    <strong>{summary?.total_items || 0}</strong>
                  </div>
                </div>
                <div className="stock-kpi-mini-card">
                  <div className="stock-kpi-mini-icon is-blue">
                    <DollarSign size={18} />
                  </div>
                  <div>
                    <span>Preços disponíveis</span>
                    <strong>{summary?.total_offers || 0}</strong>
                  </div>
                </div>
                <div className="stock-kpi-mini-card">
                  <div className="stock-kpi-mini-icon is-indigo">
                    <Building2 size={18} />
                  </div>
                  <div>
                    <span>Fornecedores</span>
                    <strong>{summary?.total_suppliers || 0}</strong>
                  </div>
                </div>
              </div>

              <div className="stock-header-actions flex items-center gap-2">
                <button
                  type="button"
                  className={`stock-alert-trigger ${stockAlerts.length > 0 ? 'has-alerts' : ''}`}
                  onClick={() => setAlertsModalOpen(true)}
                  aria-label={stockAlerts.length > 0 ? `${stockAlerts.length} alertas no catalogo` : 'Alertas do catalogo'}
                  title="Alertas do catalogo"
                >
                  {stockAlerts.length > 0 ? <Bell size={16} /> : <BellOff size={16} />}
                  {stockAlerts.length > 0 && <span>{stockAlerts.length > 99 ? '99+' : stockAlerts.length}</span>}
                </button>
                <Button variant="secondary" size="sm" onClick={() => loadData({ background: true })} leftIcon={<RefreshCw size={14} />}>
                  Atualizar base
                </Button>
                <Button variant="secondary" size="sm" onClick={() => setViewMode('saneamento')} leftIcon={<ShieldAlert size={14} />}>
                  Saneamento da Base
                  {summary && summary.items_in_review > 0 && (
                    <span className="stock-action-badge bg-rose-500 text-white ml-2">
                      {summary.items_in_review}
                    </span>
                  )}
                </Button>
                {isAdminOrMessias && (
                  <div className="stock-admin-menu relative">
                    <button
                      ref={adminMenuButtonRef}
                      type="button"
                      className="stock-admin-trigger"
                      onClick={() => setAdminMenuOpen((open) => !open)}
                      aria-haspopup="menu"
                      aria-expanded={adminMenuOpen}
                    >
                      <MoreHorizontal size={16} />
                      <span>Mais opções</span>
                    </button>
                    {adminMenuOpen && createPortal(
                      <div className="stock-floating-menu" role="menu" style={adminMenuPosition()}>
                        <button
                          type="button"
                          onClick={() => {
                            setAdminMenuOpen(false);
                            handleSync('unified');
                          }}
                          disabled={syncLoading !== null}
                        >
                          <FileSpreadsheet size={15} />
                          {syncLoading === 'unified' ? 'Importando base...' : 'Importar Base Mestre'}
                        </button>
                        <button type="button" onClick={() => { setAdminMenuOpen(false); setViewMode('saneamento'); }}>
                          <ShieldAlert size={15} />
                          Histórico de importações
                        </button>
                        <button type="button" onClick={() => { setAdminMenuOpen(false); setMessage('Relatório será gerado na rotina de exportação do catálogo.'); }}>
                          <FileText size={15} />
                          Exportar relatório
                        </button>
                      </div>,
                      document.body
                    )}
                  </div>
                )}
              </div>
            </div>
          </header>

          {/* ── PAINEL DE ALERTAS INTELIGENTES ── */}
          {false && stockAlerts.length > 0 && (
            <div className="glass-card mb-4" style={{
              padding: '12px 16px',
              borderRadius: 14,
              borderColor: stockAlerts.some(a => a.severity === 'HIGH')
                ? 'rgba(248,113,113,0.3)'
                : stockAlerts.some(a => a.severity === 'MEDIUM')
                ? 'rgba(251,191,36,0.3)'
                : 'rgba(148,163,184,0.15)',
            }}>
              {/* Cabeçalho do painel */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: alertsCollapsed ? 0 : 10 }}>
                <button
                  type="button"
                  onClick={() => setAlertsCollapsed(c => !c)}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: 0 }}
                >
                  <Bell size={15} style={{ color: stockAlerts.some(a => a.severity === 'HIGH') ? '#f87171' : '#fbbf24' }} />
                  <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--color-text-primary, #fff)' }}>
                    {stockAlerts.length} alerta{stockAlerts.length !== 1 ? 's' : ''} no catálogo
                  </span>
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 999,
                    background: stockAlerts.some(a => a.severity === 'HIGH') ? 'rgba(239,68,68,0.15)' : 'rgba(234,179,8,0.12)',
                    color: stockAlerts.some(a => a.severity === 'HIGH') ? '#f87171' : '#fbbf24',
                  }}>
                    {stockAlerts.filter(a => a.severity === 'HIGH').length > 0 ? `${stockAlerts.filter(a => a.severity === 'HIGH').length} crítico${stockAlerts.filter(a => a.severity === 'HIGH').length !== 1 ? 's' : ''}` : `${stockAlerts.filter(a => a.severity === 'MEDIUM').length} médio${stockAlerts.filter(a => a.severity === 'MEDIUM').length !== 1 ? 's' : ''}`}
                  </span>
                  {alertsCollapsed ? <ChevronRight size={14} style={{ color: '#64748b' }} /> : <ChevronDown size={14} style={{ color: '#64748b' }} />}
                </button>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {isAdminOrMessias && (
                    <button
                      type="button"
                      onClick={handleRefreshAlerts}
                      disabled={alertsRefreshing}
                      title="Verificar alertas agora"
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 600, padding: '2px 6px', borderRadius: 6 }}
                    >
                      <Zap size={13} style={{ color: alertsRefreshing ? '#6366f1' : '#64748b' }} />
                      {alertsRefreshing ? 'Atualizando...' : 'Verificar agora'}
                    </button>
                  )}
                </div>
              </div>

              {/* Lista de alertas (colapsável) */}
              {!alertsCollapsed && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 210, overflowY: 'auto' }}>
                  {alertSummary.length > 0 && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', padding: '0 0 2px' }}>
                      {alertSummary.slice(0, 4).map(([label, count]) => (
                        <span
                          key={label}
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            color: 'var(--color-text-secondary, #475569)',
                            background: 'var(--color-surface-subtle, rgba(148,163,184,0.08))',
                            border: '1px solid var(--color-border-subtle, rgba(148,163,184,0.16))',
                            borderRadius: 999,
                            padding: '3px 8px',
                          }}
                        >
                          {count} {label}
                        </span>
                      ))}
                    </div>
                  )}
                  {priorityAlerts.slice(0, 3).map(alert => (
                    <div
                      key={alert.id}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: 10,
                        padding: '7px 10px',
                        borderRadius: 10,
                        background: alert.severity === 'HIGH'
                          ? 'rgba(239,68,68,0.07)'
                          : alert.severity === 'MEDIUM'
                          ? 'rgba(234,179,8,0.07)'
                          : 'rgba(148,163,184,0.06)',
                        border: `1px solid ${
                          alert.severity === 'HIGH' ? 'rgba(239,68,68,0.18)' :
                          alert.severity === 'MEDIUM' ? 'rgba(234,179,8,0.18)' :
                          'rgba(148,163,184,0.08)'
                        }`,
                      }}
                    >
                      {/* Ícone de severidade */}
                      <div style={{ flexShrink: 0, marginTop: 1 }}>
                        {alert.severity === 'HIGH' && <AlertTriangle size={14} style={{ color: '#f87171' }} />}
                        {alert.severity === 'MEDIUM' && <AlertCircle size={14} style={{ color: '#fbbf24' }} />}
                        {alert.severity === 'INFO' && <Eye size={14} style={{ color: '#94a3b8' }} />}
                      </div>
                      {/* Conteúdo do alerta */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ margin: 0, fontSize: 12, fontWeight: 700, color: 'var(--color-text-primary, #fff)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {alert.title}
                        </p>
                        <p style={{ margin: 0, fontSize: 11, color: '#94a3b8', marginTop: 1 }}>
                          {alert.description}
                        </p>
                      </div>
                      {/* Botão de dismiss */}
                      <button
                        type="button"
                        onClick={() => handleAcknowledgeAlert(alert.id)}
                        title="Marcar como revisado"
                        aria-label="Marcar alerta como revisado"
                        style={{ flexShrink: 0, background: 'none', border: 'none', cursor: 'pointer', color: '#059669', padding: 2, borderRadius: 4, display: 'flex', alignItems: 'center' }}
                      >
                        <CheckCircle size={12} />
                      </button>
                    </div>
                  ))}
                  {stockAlerts.length > 3 && (
                    <p style={{ margin: 0, fontSize: 11, color: '#64748b', textAlign: 'center', padding: '4px 0' }}>
                      + {stockAlerts.length - 3} alertas adicionais. Use a revisao de alertas para ver todos.
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* NAVEGACAO PROGRESSIVA POR ABAS */}
          <div className="stock-premium-shell mb-6 animate-fadeIn">
            <aside className="stock-nav-panel" aria-label="Abas do Catálogo" style={{ display: 'flex', flexDirection: 'column', maxHeight: 'calc(100vh - 220px)' }}>
              <div className="stock-nav-panel-header">
                <div>
                  <span className="stock-section-kicker">Abas do Catálogo</span>
                  <h3>Famílias e produtos</h3>
                </div>
                <Package size={20} className="text-slate-400" />
              </div>
              <div className="stock-side-search">
                <Input
                  value={leftPanelSearch}
                  onChange={(e) => setLeftPanelSearch(e.target.value)}
                  placeholder="Buscar na navegação..."
                  leftIcon={<Search size={15} />}
                  className="stock-nav-search"
                />
                {leftPanelSearch && (
                  <button type="button" className="stock-side-search-clear" onClick={() => setLeftPanelSearch('')} aria-label="Limpar busca">
                    <X size={14} />
                  </button>
                )}
              </div>
              
              <div className="stock-nav-list" style={{ overflowY: 'auto', flex: 1, paddingRight: '4px' }}>
                {filteredTree.map((aba) => {
                  const isOpen = leftPanelSearch.trim() !== '' ? aba._forceOpen : !!expandedCategories[aba.id];
                  const isSelected = selectedAba?.id === aba.id;
                  const productsList = aba._products || [];
                  
                  return (
                    <div key={aba.id} className="stock-nav-group mb-2">
                      <button
                        type="button"
                        className={`stock-nav-row ${isSelected ? 'is-active' : ''}`}
                        onClick={() => {
                          handleSelectAba(aba);
                        }}
                      >
                        <span className="stock-nav-row-main">
                          <FileText size={15} className="text-slate-400" />
                          <span>{nodeLabel(aba)}</span>
                        </span>
                        <span className="flex items-center gap-1.5">
                          <span className="stock-nav-row-count">{aba.count_products ?? productsList.length}</span>
                          {isOpen ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
                        </span>
                      </button>
                      
                      {isOpen && productsList.length > 0 && (
                        <div className="pl-4 mt-1 border-l border-white/5 space-y-1">
                          {productsList.map((prod: any) => {
                            const isProdSelected = selectedProduct?.id === prod.id;
                            return (
                              <button
                                key={prod.id}
                                type="button"
                                className={`stock-nav-child ${isProdSelected ? 'is-active text-emerald-450 font-black' : ''}`}
                              onClick={() => {
                                  if (selectedAba?.id !== aba.id) {
                                    setSelectedAba(aba);
                                  }
                                  setSelectedProduct(prod);
                                  setSelectedVariationGroup(null);
                                  setNavLevel(2);
                                  handleSelectProduct(prod);
                                }}
                              >
                                <span className="truncate">{nodeLabel(prod)}</span>
                                <span className="stock-nav-row-count text-[9px] scale-90">{prod.count_variations}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </aside>
              <section className="stock-main-panel">
                <div className="stock-catalog-toolbar">
                  <div className="flex-1 max-w-md relative mr-4" ref={searchContainerRef}>
                    <Input
                      value={navLevel === 0 ? searchQuery : filterText}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (navLevel === 0) {
                          setSearchQuery(val);
                          if (val.trim()) setShowSuggestions(true);
                        } else {
                          setFilterText(val);
                        }
                      }}
                      onFocus={() => {
                        if (navLevel === 0 && searchQuery.trim()) setShowSuggestions(true);
                      }}
                      onKeyDown={navLevel === 0 ? handleKeyDown : undefined}
                      placeholder={
                        navLevel === 0 ? "Buscar no catálogo..." :
                        navLevel === 1 ? "Filtrar produtos desta categoria..." :
                        navLevel === 2 ? "Filtrar grupos de variação..." :
                        navLevel === 3 ? "Filtrar especificações, medidas ou fornecedor..." :
                        "Filtrar fornecedor, preço ou contato..."
                      }
                      leftIcon={<Search size={15} />}
                      className="stock-catalog-search-input"
                    />
                    {((navLevel === 0 && searchQuery) || (navLevel > 0 && filterText)) && (
                      <button
                        type="button"
                        className="stock-side-search-clear"
                        onClick={() => {
                          if (navLevel === 0) {
                            clearCatalogSearch();
                          } else {
                            setFilterText('');
                          }
                        }}
                        aria-label="Limpar busca"
                        style={{ right: '8px', top: '6px' }}
                      >
                        <X size={14} />
                      </button>
                    )}
                    {navLevel === 0 && showSuggestions && searchQuery && filteredSuggestions.length > 0 && (
                      <div className="stock-autocomplete-dropdown stock-side-autocomplete" style={{ width: '100%' }}>
                        <div className="stock-autocomplete-head">
                          <span>Sugestões</span>
                          <button type="button" onClick={() => setShowSuggestions(false)}>
                            <X size={12} />
                            Fechar
                          </button>
                        </div>
                        {filteredSuggestions.slice(0, 6).map((item) => (
                          <button
                            key={item.id}
                            type="button"
                            onClick={() => {
                              handleSelectSuggestion(item);
                              setShowSuggestions(false);
                            }}
                            className="stock-autocomplete-item"
                          >
                            <span className="stock-autocomplete-path">{item.family_path}</span>
                            <strong>{item.display_name}</strong>
                            <small>{itemSubtitle(item)}</small>
                            <span className="stock-autocomplete-meta">
                              {item.cybersul_code || 'Sem código'}
                            </span>
                          </button>
                        ))}
                        {filteredSuggestions.length > 6 && (
                          <button type="button" className="stock-autocomplete-more" onClick={() => triggerSearch(searchQuery)}>
                            Ver todos os resultados
                            <ArrowRight size={13} />
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                  <div>
                    <span className="stock-section-kicker">Estoque & Catálogo</span>
                    <strong>{confirmedSearchQuery ? `Resultado para: "${confirmedSearchQuery}"` : 'Catálogo operacional'}</strong>
                  </div>
                </div>

                {/* BREADCRUMB COMPACTO E BOTAO VOLTAR */}
                {confirmedSearchQuery ? (
                  <div className="stock-search-results-panel">
                    <div className="stock-results-heading">
                      <div>
                        <span className="stock-section-kicker">Resultado da busca</span>
                        <h2>Resultado para: "{confirmedSearchQuery}"</h2>
                        <p>Itens reais encontrados no catálogo operacional.</p>
                      </div>
                      <Button variant="secondary" size="sm" onClick={clearCatalogSearch} leftIcon={<X size={14} />}>
                        Limpar busca
                      </Button>
                    </div>
                    {searchLoading ? (
                      <div className="flex justify-center py-8">
                        <RefreshCw size={24} className="text-emerald-400 animate-spin" />
                      </div>
                    ) : displayedResults.length === 0 ? (
                      <EmptyState
                        icon={<Search size={40} className="text-slate-655" />}
                        title="Nenhum Produto Encontrado"
                        description="Revise a grafia ou tente buscar por família, fornecedor, medida ou código."
                      />
                    ) : (
                      <>
                        <div className="stock-variation-list">
                          {searchCatalogPage.items.map((item) => (
                            <Card
                              key={item.id}
                              className={`stock-variation-row ${activeItem?.id === item.id ? 'is-active' : ''}`}
                              onClick={() => handleOpenDetails(item)}
                            >
                              <div>
                                <span className="stock-row-path">{item.family_path}</span>
                                <h4>{item.display_name}</h4>
                                <p>{itemMeasureText(item)}</p>
                              </div>
                              <div>
                                <span>Fornecedor</span>
                                <strong>{itemSupplier(item) || 'A revisar'}</strong>
                              </div>
                              <div>
                                <span>Preço</span>
                                <strong className="stock-price-text">{formatCurrency(itemPrice(item))}</strong>
                              </div>
                              <div>
                                <span>Cybersul</span>
                                <strong>{item.cybersul_code || 'Sem código'}</strong>
                              </div>
                              <div className="stock-row-actions">
                                <Button variant="secondary" size="sm" onClick={(event) => { event.stopPropagation(); handleOpenDetails(item); }}>
                                  Detalhes
                                </Button>
                                {isStaff && (
                                  <Button variant="primary" size="sm" onClick={(event) => { event.stopPropagation(); handleQuoteDraft(item); }}>
                                    Cotar
                                  </Button>
                                )}
                              </div>
                            </Card>
                          ))}
                        </div>
                        {renderPagination('resultados da busca', searchCatalogPage, displayedResults.length, setCatalogPage)}
                      </>
                    )}
                  </div>
                ) : (
                  <>
                    <div className="stock-breadcrumb-panel flex items-center justify-between px-4 py-3">
                      <div className="stock-breadcrumb-path flex items-center gap-2 text-xs font-bold text-slate-400">
                        <span 
                          className="hover:text-emerald-450 cursor-pointer"
                          onClick={() => {
                            setNavLevel(0);
                            setSelectedAba(null);
                            setSelectedFamily(null);
                            setSelectedProduct(null);
                            setSelectedVariationGroup(null);
                          }}
                        >
                          Estoque & Catálogo
                        </span>
                        {navLevel >= 1 && selectedAba && (
                          <>
                            <ChevronRight size={14} className="text-slate-650" />
                            <span 
                              className="hover:text-emerald-450 cursor-pointer text-white"
                              onClick={() => {
                                setNavLevel(1);
                                setSelectedFamily(null);
                                setSelectedProduct(null);
                                setSelectedVariationGroup(null);
                              }}
                            >
                              {nodeLabel(selectedAba)}
                            </span>
                          </>
                        )}
                        {navLevel >= 2 && selectedProduct && (
                          <>
                            <ChevronRight size={14} className="text-slate-655" />
                            <span 
                              className="hover:text-emerald-450 cursor-pointer text-white"
                              onClick={() => {
                                setNavLevel(2);
                                setSelectedVariationGroup(null);
                              }}
                            >
                              {nodeLabel(selectedProduct)}
                            </span>
                          </>
                        )}
                        {navLevel >= 3 && selectedVariationGroup && (
                          <>
                            <ChevronRight size={14} className="text-slate-655" />
                            <span className="text-slate-350 font-black">
                              {nodeLabel(selectedProduct)} - {selectedVariationGroup}
                            </span>
                          </>
                        )}
                      </div>
                      {navLevel > 0 && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            if (navLevel === 1) {
                              setNavLevel(0);
                              setSelectedAba(null);
                            } else if (navLevel === 2) {
                              setNavLevel(1);
                              setSelectedProduct(null);
                            } else if (navLevel === 3) {
                              setNavLevel(2);
                              setSelectedVariationGroup(null);
                            }
                          }}
                          leftIcon={<ArrowLeft size={14} />}
                        >
                          Voltar
                        </Button>
                      )}
                    </div>

                    {/* CONTEUDO DO NIVEL ATUAL */}
                    {navLevel === 0 && (
                      <div className="space-y-3">
                        <div className="stock-tabs-grid">
                          {rootCatalogPage.items.map((aba) => (
                            <Card 
                              key={aba.id}
                              onClick={() => {
                                handleSelectAba(aba);
                              }}
                              className="stock-tab-card"
                            >
                              <h4 className="text-sm font-black text-white hover:text-emerald-450 transition-colors line-clamp-2">{nodeLabel(aba)}</h4>
                              <div className="text-[10px] text-slate-500 font-bold space-y-0.5 mt-2">
                                <div className="flex justify-between">
                                  <span>Produtos:</span>
                                  <span className="text-slate-350">
                                    {aba.count_products ?? aba.children?.flatMap((fam: any) => fam.children || []).length ?? 0}
                                  </span>
                                </div>
                                <div className="flex justify-between">
                                  <span>Itens com preço:</span>
                                  <span className="text-emerald-450 font-black">{aba.count_priced ?? 0}</span>
                                </div>
                              </div>
                            </Card>
                          ))}
                        </div>
                        {renderPagination('familias do catalogo', rootCatalogPage, treeNodes.length, setCatalogPage)}
                      </div>
                    )}

                    {navLevel === 1 && selectedAba && (
                      <div className="space-y-3">
                        {navigationLoading ? (
                          <div className="flex justify-center py-8">
                            <RefreshCw size={24} className="text-emerald-400 animate-spin" />
                          </div>
                        ) : (!selectedAba.children || selectedAba.children.length === 0) ? (
                          <EmptyState
                            icon={<Boxes size={36} className="text-slate-655" />}
                            title="Nenhum Produto Encontrado"
                            description="Esta aba de catálogo não possui produtos cadastrados."
                          />
                        ) : (
                          <div className="stock-card-grid">
                            {productsCatalogPage.items.map((prod) => (
                              <Card 
                                key={prod.id}
                                onClick={() => {
                                  setSelectedProduct(prod);
                                  setNavLevel(2);
                                  handleSelectProduct(prod);
                                }}
                                className="stock-product-card"
                              >
                                <div className="stock-thumb">
                                  <Package size={42} />
                                </div>
                                <h4>{nodeLabel(prod)}</h4>
                                <div className="stock-chip-row">
                                  <span className="stock-chip">{productKind(nodeLabel(prod))}</span>
                                  <span className="stock-chip">{prod.count_variations ?? 0} variações</span>
                                  <span className="stock-chip ok">{prod.count_priced ?? 0} com preço</span>
                                </div>
                                <p>{productDescription(nodeLabel(prod))}</p>
                              </Card>
                            ))}
                          </div>
                        )}
                        {renderPagination('produtos da familia', productsCatalogPage, filteredProducts.length, setCatalogPage)}
                      </div>
                    )}

                    {navLevel === 2 && selectedProduct && (
                      <div className="space-y-3">
                        {productVariationsLoading ? (
                          <div className="flex justify-center py-8">
                            <RefreshCw size={24} className="text-emerald-400 animate-spin" />
                          </div>
                        ) : variationGroups.length === 0 ? (
                          <EmptyState
                            icon={<Boxes size={36} className="text-slate-655" />}
                            title="Nenhuma Variação Encontrada"
                            description="Este produto não possui variações registradas."
                          />
                        ) : (
                          <div className="stock-card-grid">
                            {variationGroupsCatalogPage.items.map((group) => (
                            <Card 
                              key={group.label}
                              onClick={() => {
                                setSelectedVariationGroup(group.label);
                                setNavLevel(3);
                              }}
                              className="stock-product-card stock-group-card"
                              style={{ minHeight: '190px' }}
                            >
                              <div className="stock-group-header">
                                <h4 className="stock-card-title stock-card-title-clamped">
                                  {group.fullName}
                                </h4>
                              </div>

                              <div className="stock-group-summary mt-3 pt-2 border-t border-white/5">
                                <div className="stock-group-summary-row">
                                  <span>Especificações</span>
                                  <strong>{group.items.length === 1 ? '1 especificação' : `${group.items.length} especificações`}</strong>
                                </div>
                                <div className={`stock-group-summary-row ${group.cybersulCount > 0 ? 'is-linked' : 'is-muted'}`}>
                                  <span>Integração</span>
                                  <strong className={`font-semibold ${group.cybersulCount > 0 ? 'text-emerald-450' : 'text-slate-500'}`}>
                                    {group.cybersulCount > 0 ? 'Cybersul vinculado' : 'Sem Cybersul'}
                                  </strong>
                                </div>
                                <div className={`stock-group-summary-row stock-group-summary-price ${group.minPrice ? 'has-price' : 'is-muted'}`}>
                                  <span>Valor</span>
                                  <strong className="stock-price-text">
                                    {group.minPrice ? (
                                      <>
                                        {formatCurrency(group.minPrice)}
                                        {group.maxPrice && group.maxPrice !== group.minPrice ? ` - ${formatCurrency(group.maxPrice)}` : ''}
                                      </>
                                    ) : (
                                      'Sem preço cadastrado'
                                    )}
                                  </strong>
                                </div>
                              </div>

                              {group.suppliers.length > 0 && (
                                <div className="stock-group-suppliers">
                                  <span className="stock-group-suppliers-label">Fornecedores</span>
                                  <strong className="stock-group-suppliers-value">{group.suppliers.join(', ')}</strong>
                                </div>
                              )}
                            </Card>
                            ))}
                          </div>
                        )}
                        {renderPagination('variacoes do produto', variationGroupsCatalogPage, filteredVariationGroups.length, setCatalogPage)}
                      </div>
                    )}

                    {navLevel === 3 && selectedProduct && selectedVariationGroup && (
                      <div className="space-y-3">
                        {productVariationsLoading ? (
                          <div className="flex justify-center py-8">
                            <RefreshCw size={24} className="text-emerald-400 animate-spin" />
                          </div>
                        ) : filteredGroupItems.length === 0 ? (
                          <EmptyState
                            icon={<Boxes size={36} className="text-slate-655" />}
                            title="Nenhuma Especificação Encontrada"
                            description="Este grupo não possui especificações registradas."
                          />
                        ) : (
                          <div className="stock-variation-list">
                            {/* Column Headers for visual table layout */}
                            <div className="stock-table-header" style={{ gridTemplateColumns: 'minmax(220px, 1.5fr) minmax(100px, 0.65fr) minmax(120px, 0.7fr) minmax(120px, 0.7fr) auto' }}>
                              <div>Variação / Equivalente</div>
                              <div>Fornecedor</div>
                              <div>Preço</div>
                              <div>Código Cybersul</div>
                              <div className="text-right">Ações</div>
                            </div>
                            
                            {groupItemsCatalogPage.items.map((item) => {
                              const isSelected = activeItem?.id === item.id;
                              const price = itemPrice(item);
                              const supplier = itemSupplier(item);
                              
                              return (
                                <Card
                                  key={item.id}
                                  className={`stock-variation-row ${isSelected ? 'is-active' : ''}`}
                                  onClick={() => setActiveItem(item)}
                                >
                                  {/* Coluna 1: Variação / Equivalente */}
                                  <div>
                                    <span className="stock-variation-name font-bold text-white text-[15px] block truncate">
                                      {item.variation_label || 'Sem variação'}
                                    </span>
                                    <span className="stock-variation-sub text-slate-400 text-sm mt-0.5 block truncate">
                                      {itemMeasureText(item)}
                                    </span>
                                    {itemAttributeLine(item) && (
                                      <span className="stock-variation-attrs text-slate-500 text-xs mt-1 block truncate">
                                        {itemAttributeLine(item)}
                                      </span>
                                    )}
                                  </div>

                                  {/* Coluna 2: Fornecedor */}
                                  <div>
                                    <span className="stock-variation-meta text-[10px] text-slate-500 font-bold uppercase tracking-wider block lg:hidden">Fornecedor</span>
                                    <strong className="text-[13px] font-semibold text-slate-350 block truncate mt-1">
                                      {supplier || <span className="text-slate-550 italic">A revisar</span>}
                                    </strong>
                                  </div>

                                  {/* Coluna 3: Preço */}
                                  <div>
                                    <span className="stock-variation-meta text-[10px] text-slate-500 font-bold uppercase tracking-wider block lg:hidden">Preço</span>
                                    {price && price > 0 ? (
                                      <strong className="stock-price block mt-1">
                                        {formatCurrency(price)}
                                      </strong>
                                    ) : (
                                      <button
                                        type="button"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          handleQuoteDraft(item);
                                        }}
                                        className="text-xs text-sky-400 hover:text-sky-300 font-black underline block mt-1 text-left bg-transparent border-0 p-0 cursor-pointer transition-colors"
                                      >
                                        Cotar para atualizar
                                      </button>
                                    )}
                                  </div>

                                  {/* Coluna 4: Cybersul */}
                                  <div>
                                    <span className="stock-variation-meta text-[10px] text-slate-500 font-bold uppercase tracking-wider block lg:hidden">Cybersul</span>
                                    <div className="mt-1">
                                      {item.cybersul_code ? (
                                        <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-black bg-emerald-500/10 text-emerald-450 border border-emerald-500/20">
                                          {item.cybersul_code}
                                        </span>
                                      ) : (
                                        <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-white/5 text-slate-450 border border-white/5">
                                          Sem código
                                        </span>
                                      )}
                                    </div>
                                  </div>

                                  {/* Coluna 5: Ações */}
                                  <div className="stock-row-actions">
                                    <Button
                                      variant="secondary"
                                      size="sm"
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        handleOpenDetails(item);
                                      }}
                                      leftIcon={<Eye size={12} />}
                                      className="h-8 px-2.5 text-xs"
                                    >
                                      Detalhes
                                    </Button>
                                    {isStaff && (
                                      <>
                                        <Button
                                          variant="secondary"
                                          size="sm"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            handleOpenDetails(item);
                                            setTimeout(() => setDrawerTab('precos'), 200);
                                          }}
                                          leftIcon={<DollarSign size={12} />}
                                          className="h-8 px-2.5 text-xs"
                                        >
                                          Preço
                                        </Button>
                                        <Button
                                          variant="primary"
                                          size="sm"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            handleQuoteDraft(item);
                                          }}
                                          leftIcon={<Plus size={12} />}
                                          className="h-8 px-2.5 text-xs"
                                        >
                                          Cotar
                                        </Button>
                                      </>
                                    )}
                                  </div>
                                </Card>
                              );
                            })}
                            {renderPagination('itens da variacao', groupItemsCatalogPage, filteredGroupItems.length, setCatalogPage)}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </section>

              <aside className="stock-detail-panel" aria-label="Resumo do item selecionado">
                {activeItem ? (
                  <>
                    <button type="button" className="stock-detail-close" onClick={() => setActiveItem(null)} aria-label="Limpar seleção">
                      <X size={18} />
                    </button>
                    <div className="stock-detail-hero">
                      <Package size={72} className="text-emerald-450" />
                    </div>
                    <div className="stock-detail-body">
                      <span className="stock-chip">{productKind(activeItem.display_name)}</span>
                      <h3>{activeItem.display_name}</h3>
                      <p>{productDescription(activeItem.display_name)}</p>

                      <div className="stock-detail-summary mt-4">
                        <div>
                          <span>Variacao do item</span>
                          <strong>{activeItem.variation_label || 'Sem variação'}</strong>
                        </div>
                        <div>
                          <span>Medida normalizada</span>
                          <strong>{activeItem.measure_display || activeItem.normalized_measure || 'Sem medida métrica'}</strong>
                        </div>
                        <div>
                          <span>Código Cybersul</span>
                          <strong>{activeItem.cybersul_code || 'Sem código'}</strong>
                        </div>
                        <div>
                          <span>Fornecedor principal</span>
                          <strong>{itemSupplier(activeItem) || 'Fornecedor a revisar'}</strong>
                        </div>
                        <div>
                          <span>Preço atual</span>
                          <strong className="stock-price-text">{formatCurrency(itemPrice(activeItem))}</strong>
                        </div>
                        {activeItem.cybersul_code && (
                          <div>
                            <span>Estoque total</span>
                            <strong>{activeItem.balance_total ?? 0} unid.</strong>
                          </div>
                        )}
                      </div>

                      {hasOpenPurchase && (
                        <div className="stock-linked-purchase mt-4">
                          <span>Cotacao em andamento</span>
                          <strong>{purchaseContext?.message || 'Ja existe uma cotacao aberta para este item.'}</strong>
                          {purchaseContext?.action_url && (
                            <button
                              type="button"
                              onClick={() => {
                                window.history.pushState(null, '', purchaseContext.action_url);
                                window.dispatchEvent(new PopStateEvent('popstate'));
                              }}
                            >
                              Abrir em Compras
                            </button>
                          )}
                        </div>
                      )}

                      <div className="stock-detail-actions mt-4">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleOpenDetails(activeItem)}
                          leftIcon={<Eye size={14} />}
                        >
                          Ver todos os detalhes
                        </Button>
                        {isStaff && (
                          <>
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => {
                                const off = itemOffers.find(o => o.supplier_name === itemSupplier(activeItem));
                                if (off) {
                                  handleOpenUpdatePrice(off);
                                } else {
                                  handleOpenDetails(activeItem);
                                  setTimeout(() => setDrawerTab('precos'), 200);
                                }
                              }}
                              leftIcon={<DollarSign size={14} />}
                            >
                              Atualizar preço
                            </Button>
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleQuoteDraft(activeItem)}
                              leftIcon={<Plus size={14} />}
                            >
                              Cotar
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </>
                ) : selectedProduct ? (
                  <>
                    <div className="stock-detail-hero">
                      <Boxes size={72} className="text-sky-455" />
                    </div>
                    <div className="stock-detail-body">
                      <span className="stock-chip">{productKind(nodeLabel(selectedProduct))}</span>
                      <h3>{nodeLabel(selectedProduct)}</h3>
                      <p>{productDescription(nodeLabel(selectedProduct))}</p>

                      <div className="stock-detail-summary mt-4">
                        <div>
                          <span>Variações disponíveis</span>
                          <strong>{selectedProduct.count_variations ?? 0} opções</strong>
                        </div>
                        <div>
                          <span>Itens com preço</span>
                          <strong>{selectedProduct.count_priced ?? 0} itens</strong>
                        </div>
                      </div>

                      <div className="stock-detail-actions mt-4">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={async () => {
                            if (productVariations.length > 0) {
                              handleOpenDetails(productVariations[0]);
                            } else {
                              setMessage('Abra uma variação para ver detalhes.');
                            }
                          }}
                          leftIcon={<Eye size={14} />}
                        >
                          Detalhes do Produto
                        </Button>
                      </div>
                    </div>
                  </>
                ) : selectedAba ? (
                  <>
                    <div className="stock-detail-hero">
                      <FileText size={72} className="text-indigo-455" />
                    </div>
                    <div className="stock-detail-body">
                      <span className="stock-chip">Categoria</span>
                      <h3>{nodeLabel(selectedAba)}</h3>
                      <p>Família de produtos e materiais do catálogo corporativo.</p>

                      <div className="stock-detail-summary mt-4">
                        <div>
                          <span>Produtos catalogados</span>
                          <strong>{selectedAba.children?.flatMap((fam: any) => fam.children || []).length ?? 0} itens</strong>
                        </div>
                        <div>
                          <span>Itens com preço</span>
                          <strong>{selectedAba.count_priced ?? 0} itens</strong>
                        </div>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="stock-detail-empty p-6 text-center">
                    <Boxes size={48} className="mx-auto text-slate-600 mb-3" />
                    <span className="stock-chip mx-auto block w-max mb-2">Estoque</span>
                    <h3>Selecione um produto</h3>
                    <p className="text-xs leading-relaxed">
                      Escolha uma categoria, produto ou variação para ver detalhes, fornecedores, preços e código Cybersul.
                    </p>
                  </div>
                )}
              </aside>
            </div>
        </>
      ) : (
        /* CENTRAL DE SANEAMENTO DA BASE EM GRUPOS INTELIGENTES */
        <Card className="p-5 bg-slate-900/35 border border-white/5 text-left space-y-6 animate-fadeIn" style={{ borderRadius: '22px' }}>
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-white/5 pb-4">
            <div>
              <h3 className="text-base font-black text-white flex items-center gap-2">
                <ShieldAlert className="text-rose-450 animate-pulse" size={20} />
                Central de Saneamento da Base
              </h3>
              <p className="text-xs text-slate-450 font-semibold mt-1">
                Visualizacao estruturada por criticidade para reclassificar, corrigir e organizar a integridade de dados.
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setViewMode('catalogo');
                setSelectedSanitationGroup(null);
              }}
              leftIcon={<Boxes size={16} />}
            >
              Voltar ao Catalogo
            </Button>
          </div>

          {/* Grid de 8 Cards de Saneamento Inteligentes */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(groupedSanitation || {}).map(([key, group]: [string, any]) => (
              <Card
                key={key}
                onClick={() => handleSelectSanitationGroup(key)}
                className={`p-4 bg-slate-950/45 border transition-all cursor-pointer hover:border-rose-500/30 flex flex-col justify-between ${
                  selectedSanitationGroup === key ? 'border-rose-500/50 shadow-[0_0_15px_rgba(239,68,68,0.07)]' : 'border-white/5'
                }`}
                style={{ borderRadius: '16px' }}
              >
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-slate-300 text-xs font-black uppercase tracking-wider">{group.label}</span>
                    <Badge variant={group.count > 0 ? "danger" : "success"} className="font-black">
                      {group.count}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-450 font-semibold mb-4 leading-relaxed">
                    {group.description}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 pt-2 border-t border-white/5">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelectSanitationGroup(key);
                    }}
                  >
                    Ver detalhes
                  </Button>
                  {group.count > 0 && getBulkActionForGroup(key) && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleBulkAction(key);
                      }}
                    >
                      {getBulkActionLabel(key)}
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>

          {/* Detalhes do Grupo de Saneamento Selecionado */}
          {selectedSanitationGroup && (
            <Card className="p-4 bg-slate-950/30 border border-rose-500/20 mt-6" style={{ borderRadius: '16px' }}>
              <div className="flex justify-between items-center mb-4 pb-2 border-b border-white/5">
                <div>
                  <h4 className="text-sm font-black text-white uppercase tracking-wider">
                    {groupedSanitation?.[selectedSanitationGroup]?.label || selectedSanitationGroup}
                  </h4>
                  <p className="text-[10px] text-slate-500 font-semibold mt-0.5">
                    Exibindo os itens inconsistentes identificados nesta categoria.
                  </p>
                </div>
                <button
                  onClick={() => setSelectedSanitationGroup(null)}
                  className="text-slate-400 hover:text-white text-xs font-bold flex items-center gap-1"
                >
                  <X size={14} /> Fechar Lista
                </button>
              </div>

              {groupItemsLoading ? (
                <LoadingState text="Buscando itens pendentes..." />
              ) : groupItems.length === 0 ? (
                <div className="p-8 text-center text-slate-500 font-black">
                  Tudo limpo! Nenhuma pendencia encontrada para este grupo de saneamento.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto pr-1">
                  {groupItems.map((item: any) => (
                    <Card
                      key={item.id}
                      className="p-3 bg-slate-900/40 border border-white/5 hover:border-white/10 transition-all flex flex-col justify-between"
                      style={{ borderRadius: '12px' }}
                    >
                      <div className="space-y-1 text-left">
                        <h5 className="text-xs font-black text-white">{item.display_name}</h5>
                        {item.code && (
                          <span className="text-[10px] text-sky-400 font-mono block">
                            Codigo Cybersul: {item.code}
                          </span>
                        )}
                        <p className="text-[11px] text-slate-450 font-semibold italic">
                          Motivo: {item.reason}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2 justify-end mt-3 pt-2 border-t border-white/5">
                        {(() => {
                          const handleActionClick = async (action: string, successMsg: string) => {
                            setError('');
                            setMessage('');
                            try {
                              if (selectedSanitationGroup === 'human_review' || selectedSanitationGroup === 'duplicates' || selectedSanitationGroup === 'high_confidence') {
                                const resolveAction = action === 'APPROVE' ? 'APPROVE' : 'IGNORE';
                                await stockRequest<any>(`/review-queue/${item.id}/resolve?action=${resolveAction}`, { method: 'POST' });
                                setMessage(successMsg);
                              } else {
                                setMessage(successMsg);
                              }
                              await loadData();
                              // Atualizar a lista do grupo localmente
                              const updatedItems = await stockRequest<any[]>(`/review-queue/group/${selectedSanitationGroup}`);
                              setGroupItems(updatedItems);
                            } catch (err: any) {
                              setError(err.message || 'Erro ao processar acao.');
                            }
                          };

                          switch (selectedSanitationGroup) {
                            case 'inactive':
                              return (
                                <>
                                  <Button variant="secondary" size="sm" onClick={() => handleActionClick('IGNORE', 'Item inativo mantido ocultado com sucesso.')}>
                                    Manter oculto
                                  </Button>
                                  <Button variant="secondary" size="sm" onClick={() => setMessage('A reativacao de itens deve ser feita exclusivamente no ERP Cybersul.')}>
                                    Reativar no Cybersul
                                  </Button>
                                </>
                              );
                            case 'missing_code':
                              return (
                                <>
                                  <Button variant="secondary" size="sm" onClick={() => setMessage('Pesquise o produto no catalogo principal e utilize o menu Detalhes para efetuar a vinculacao.')}>
                                    Vincular codigo
                                  </Button>
                                  <Button variant="secondary" size="sm" onClick={() => handleActionClick('IGNORE', 'Item mantido sem codigo oficial.')}>
                                    Manter nao oficial
                                  </Button>
                                  <Button variant="secondary" size="sm" onClick={() => handleActionClick('IGNORE', 'Item ocultado do catalogo operacional.')}>
                                    Ocultar
                                  </Button>
                                </>
                              );
                            case 'incomplete_offers':
                              return (
                                <>
                                  <Button variant="secondary" size="sm" onClick={() => handleActionClick('IGNORE', 'Oferta invalida sem preco excluida.')}>
                                    Ignorar oferta
                                  </Button>
                                  <Button variant="secondary" size="sm" onClick={() => setMessage('Busque o produto e utilize a aba de Fornecedores para atualizar o preco manual.')}>
                                    Adicionar preco
                                  </Button>
                                </>
                              );
                            case 'missing_email':
                              return (
                                <>
                                  <Button variant="secondary" size="sm" onClick={() => setMessage('Altere as informacoes de e-mail deste fornecedor na aba de fornecedores de Compras.')}>
                                    Adicionar e-mail
                                  </Button>
                                  <Button variant="secondary" size="sm" onClick={() => handleActionClick('IGNORE', 'Fornecedor mantido sem e-mail de contato.')}>
                                    Manter sem e-mail
                                  </Button>
                                </>
                              );
                            case 'duplicates':
                              return (
                                <>
                                  <Button variant="primary" size="sm" onClick={() => handleActionClick('APPROVE', 'Vinculo de duplicado aprovado com sucesso.')}>
                                    Aprovar vinculo
                                  </Button>
                                  <Button variant="secondary" size="sm" onClick={() => handleActionClick('IGNORE', 'Divergencia resolvida, itens mantidos separados.')}>
                                    Separar item
                                  </Button>
                                </>
                              );
                            case 'quarantine':
                              return (
                                <>
                                  <Button variant="secondary" size="sm" onClick={() => handleActionClick('IGNORE', 'Linha suspeita mantida em quarentena.')}>
                                    Manter em quarentena
                                  </Button>
                                  <Button variant="secondary" size="sm" onClick={() => handleActionClick('IGNORE', 'Excluido do catalogo operacional.')}>
                                    Excluir do catalogo
                                  </Button>
                                </>
                              );
                            case 'high_confidence':
                              return (
                                <>
                                  <Button variant="primary" size="sm" onClick={() => handleActionClick('APPROVE', 'Vinculo aprovado.')}>
                                    Aprovar vinculo
                                  </Button>
                                  <Button variant="secondary" size="sm" onClick={() => handleActionClick('IGNORE', 'Vinculo ignorado, itens mantidos separados.')}>
                                    Separar item
                                  </Button>
                                </>
                              );
                            case 'human_review':
                              return (
                                <>
                                  <Button variant="primary" size="sm" onClick={() => handleActionClick('APPROVE', 'Aprovado para o catalogo operacional.')}>
                                    Aprovar para catalogo
                                  </Button>
                                  <Button variant="secondary" size="sm" onClick={() => handleActionClick('IGNORE', 'Rejeitado e mantido separado.')}>
                                    Manter separado
                                  </Button>
                                </>
                              );
                            default:
                              return null;
                          }
                        })()}
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </Card>
          )}
        </Card>
      )}

      <Modal
        isOpen={alertsModalOpen}
        onClose={() => setAlertsModalOpen(false)}
        title="Alertas do catalogo"
      >
        <div className="stock-alert-modal">
          <div className="stock-alert-modal-summary" aria-label="Resumo dos alertas">
            {alertSummary.length > 0 ? (
              alertSummary.slice(0, 5).map(([label, count]) => (
                <span key={label}>
                  <strong>{count}</strong>
                  {label}
                </span>
              ))
            ) : (
              <span>
                <strong>0</strong>
                nenhum alerta ativo
              </span>
            )}
          </div>

          {stockAlerts.length === 0 ? (
            <div className="stock-alert-empty">
              <BellOff size={22} />
              <strong>Nenhum alerta ativo encontrado.</strong>
              <p>Quando houver item sem preco, sem fornecedor ou com estoque baixo, ele aparece aqui.</p>
            </div>
          ) : (
            <>
              <div className="stock-alert-list" role="list">
                {alertsPageData.items.map((alert) => (
                  <article key={alert.id} className={`stock-alert-row severity-${alert.severity.toLowerCase()}`} role="listitem">
                    <div className="stock-alert-row-icon">
                      {alert.severity === 'HIGH' ? <AlertTriangle size={16} /> : alert.severity === 'MEDIUM' ? <AlertCircle size={16} /> : <Eye size={16} />}
                    </div>
                    <button type="button" className="stock-alert-row-main" onClick={() => handleOpenAlertTarget(alert)}>
                      <span>{alert.title}</span>
                      <strong>{alert.item_display_name || 'Item do catalogo'}</strong>
                      <p>{alert.description}</p>
                    </button>
                    <div className="stock-alert-row-actions">
                      <Button variant="secondary" size="sm" onClick={() => handleOpenAlertTarget(alert)}>
                        Ver item
                      </Button>
                      <button
                        type="button"
                        className="stock-alert-review"
                        onClick={() => handleAcknowledgeAlert(alert.id)}
                        aria-label="Marcar alerta como revisado"
                        title="Marcar como revisado"
                      >
                        <CheckCircle size={15} />
                      </button>
                    </div>
                  </article>
                ))}
              </div>
              {renderPagination('alertas do catalogo', alertsPageData, priorityAlerts.length, setAlertsPage)}
            </>
          )}

          {isAdminOrMessias && (
            <div className="stock-alert-modal-footer">
              <Button variant="secondary" size="sm" onClick={handleRefreshAlerts} leftIcon={<Zap size={14} />} disabled={alertsRefreshing}>
                {alertsRefreshing ? 'Atualizando...' : 'Verificar agora'}
              </Button>
            </div>
          )}
        </div>
      </Modal>

      {/* DRAWER LATERAL DE DETALHES */}
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={itemDetails?.display_name || 'Detalhes do Item'}
      >
        {itemDetails ? (
          <div className="flex flex-col h-full text-left">
            {/* Abas do Drawer */}
            <div className="flex gap-2 border-b border-white/5 pb-2 mb-4 text-xs font-bold text-slate-400">
              <button
                onClick={() => setDrawerTab('geral')}
                className={`pb-2 px-2 border-b-2 transition-all ${drawerTab === 'geral' ? 'border-emerald-500 text-white font-black' : 'border-transparent hover:text-white'}`}
              >
                Resumo
              </button>
              <button
                onClick={() => setDrawerTab('precos')}
                className={`pb-2 px-2 border-b-2 transition-all ${drawerTab === 'precos' ? 'border-emerald-500 text-white font-black' : 'border-transparent hover:text-white'}`}
              >
                Fornecedores ({itemOffers.length})
              </button>
              <button
                onClick={() => setDrawerTab('historico')}
                className={`pb-2 px-2 border-b-2 transition-all ${drawerTab === 'historico' ? 'border-emerald-500 text-white font-black' : 'border-transparent hover:text-white'}`}
              >
                Historico
              </button>
              <button
                onClick={() => setDrawerTab('cybersul')}
                className={`pb-2 px-2 border-b-2 transition-all ${drawerTab === 'cybersul' ? 'border-emerald-500 text-white font-black' : 'border-transparent hover:text-white'}`}
              >
                Estoque
              </button>
              {isAdminOrMessias && (
                <button
                  onClick={() => setDrawerTab('tecnico')}
                  className={`pb-2 px-2 border-b-2 transition-all ${drawerTab === 'tecnico' ? 'border-rose-500 text-rose-400 font-black' : 'border-transparent hover:text-rose-400/80'}`}
                >
                  Tecnico (Admin)
                </button>
              )}
            </div>

            {/* Conteudo das Abas */}
            <div className="flex-1 overflow-y-auto space-y-4 font-bold text-xs text-slate-350 pr-1">
              
              {drawerTab === 'geral' && (
                <div className="space-y-4">
                  <div className="bg-slate-950/45 p-4 rounded-2xl border border-white/5 space-y-3">
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase font-black">Produto</span>
                      <p className="text-white text-sm font-black mt-0.5">{itemDetails.display_name}</p>
                    </div>
                    <div>
                      <span className="text-slate-500 text-[10px] uppercase font-black">Categoria e familia</span>
                      <p className="text-white mt-0.5">{itemDetails.family_path}</p>
                    </div>
                    {itemDetails.variation_label && (
                      <div>
                        <span className="text-slate-500 text-[10px] uppercase font-black">Variacao</span>
                        <p className="text-white mt-0.5">{itemDetails.variation_label}</p>
                      </div>
                    )}
                    {itemDetails.specification_text && (
                      <div>
                        <span className="text-slate-500 text-[10px] uppercase font-black">Especificacao</span>
                        <p className="text-white mt-0.5">{itemDetails.specification_text}</p>
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <Card className="p-4 bg-slate-950/45 border border-white/5">
                      <span className="text-slate-500 text-[10px] uppercase block">Preco atual</span>
                      <span className="text-sm font-semibold text-white mt-1 block">
                        {itemDetails.current_price ? formatCurrency(itemDetails.current_price) : 'Preco ainda nao registrado no Portal.'}
                      </span>
                    </Card>
                    <Card className="p-4 bg-slate-950/45 border border-white/5">
                      <span className="text-slate-500 text-[10px] uppercase block">Fornecedor Principal</span>
                      <span className="text-sm font-semibold text-emerald-400 mt-1 block wrap">
                        {itemDetails.current_supplier || 'Fornecedor ainda nao cadastrado no Portal.'}
                      </span>
                    </Card>
                  </div>

                  {itemDetails.purchase_context && (
                    <Card className="p-4 bg-slate-950/45 border border-white/5 space-y-2">
                      <span className="text-slate-500 text-[10px] uppercase block">Compras relacionadas</span>
                      <p className="text-white text-sm font-black">
                        {itemDetails.purchase_context.has_open_purchase ? 'Cotacao em andamento' : 'Sem compra aberta para este item'}
                      </p>
                      <p className="text-slate-350 text-xs font-semibold leading-relaxed">
                        {itemDetails.purchase_context.message}
                      </p>
                      {itemDetails.purchase_context.quantity_explanation && (
                        <p className="text-slate-400 text-[11px] font-semibold leading-relaxed">
                          {itemDetails.purchase_context.quantity_explanation}
                        </p>
                      )}
                      {itemDetails.purchase_context.action_url && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            const url = new URL(itemDetails.purchase_context.action_url, window.location.origin);
                            onNavigate?.('purchases', { search: url.search });
                          }}
                        >
                          Abrir em Compras
                        </Button>
                      )}
                    </Card>
                  )}
                  
                  {itemDetails.needs_review && (
                    <Card className="p-4 bg-rose-950/10 border border-rose-500/20 text-rose-400">
                      <span className="font-black block uppercase text-[10px] mb-1">Motivo de Revisao</span>
                      <p className="font-semibold leading-relaxed">{itemDetails.review_reason}</p>
                    </Card>
                  )}
                </div>
              )}

              {drawerTab === 'precos' && (
                <div className="space-y-3">
                  {itemOffers.length === 0 ? (
                    <div className="p-6 text-center text-slate-500 font-semibold">Fornecedor ainda nao cadastrado no Portal.</div>
                  ) : (
                    itemOffers.map(off => (
                      <Card key={off.id} className="p-3 bg-slate-950/45 border border-white/5 flex justify-between items-center">
                        <div className="space-y-1">
                          <span className="text-white font-black text-sm block">{off.supplier_name}</span>
                          <span className="text-slate-400 block text-[11px] font-semibold">{off.email || 'E-mail nao cadastrado'} · {off.phone || 'Telefone nao cadastrado'}</span>
                          {isAdminOrMessias && (
                            <span className="text-slate-500 block text-[10px] font-bold">Origem: {off.source_sheet}</span>
                          )}
                        </div>
                        <div className="text-right space-y-2">
                          <span className="text-white font-black text-sm block">{formatCurrency(off.price)}</span>
                          <Button variant="secondary" size="sm" onClick={() => handleOpenUpdatePrice(off)}>
                            Atualizar Preco
                          </Button>
                        </div>
                      </Card>
                    ))
                  )}
                </div>
              )}

              {drawerTab === 'historico' && (
                <div className="space-y-3">
                  {itemHistory.length === 0 ? (
                    <div className="p-6 text-center text-slate-500">Nenhuma alteracao de preco registrada no historico.</div>
                  ) : (
                    itemHistory.map(h => (
                      <Card key={h.id} className="p-3 bg-slate-950/45 border border-white/5 text-[11px] font-semibold">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-white font-black">{h.supplier_name}</span>
                          <span className="text-slate-500 font-bold">{new Date(h.changed_at).toLocaleDateString()}</span>
                        </div>
                        <div className="flex gap-2 items-center text-xs font-bold text-slate-330 mb-2">
                          <span className="text-slate-500 line-through">{formatCurrency(h.old_price)}</span>
                          <ArrowRight size={14} className="text-slate-500" />
                          <span className="text-emerald-400 font-black">{formatCurrency(h.new_price)}</span>
                        </div>
                        {h.notes && (
                          <div className="p-2 bg-slate-900/45 rounded text-slate-400 border border-white/5 italic">
                            "{h.notes}"
                          </div>
                        )}
                        <span className="text-[10px] text-slate-500 block mt-2">Alterado por: {h.changed_by} {isAdminOrMessias && h.source ? `(${h.source})` : ''}</span>
                      </Card>
                    ))
                  )}
                </div>
              )}

              {drawerTab === 'cybersul' && (
                <div className="space-y-4">
                  {itemDetails.cybersul_product_id ? (
                    <div className="space-y-4">
                      <div className="bg-slate-950/45 p-4 rounded-2xl border border-white/5 space-y-3">
                        <div>
                          <span className="text-slate-500 text-[10px] uppercase block">Codigo Cybersul</span>
                          <span className="text-white text-sm font-black mt-0.5">{itemDetails.cybersul_code}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 text-[10px] uppercase block">Descricao Oficial</span>
                          <p className="text-white mt-0.5">{itemDetails.cybersul_description}</p>
                        </div>
                        {itemDetails.ncm && (
                          <div>
                            <span className="text-slate-500 text-[10px] uppercase block">NCM</span>
                            <span className="text-white mt-0.5">{itemDetails.ncm}</span>
                          </div>
                        )}
                        {itemDetails.group_name && (
                          <div>
                            <span className="text-slate-500 text-[10px] uppercase block">Grupo de Produto</span>
                            <span className="text-white mt-0.5">{itemDetails.group_name}</span>
                          </div>
                        )}
                      </div>

                      <div className="grid grid-cols-3 gap-4">
                        <Card className="p-3 bg-slate-950/45 border border-white/5 text-center">
                          <span className="text-slate-500 text-[10px] uppercase block">Saldo Vesper</span>
                          <span className="text-base font-black text-white mt-1 block">{itemDetails.balance_vesper}</span>
                        </Card>
                        <Card className="p-3 bg-slate-950/45 border border-white/5 text-center">
                          <span className="text-slate-500 text-[10px] uppercase block">Saldo Ventrio</span>
                          <span className="text-base font-black text-white mt-1 block">{itemDetails.balance_ventrio}</span>
                        </Card>
                        <Card className="p-3 bg-slate-950/45 border border-white/5 text-center">
                          <span className="text-slate-500 text-[10px] uppercase block">Saldo Total</span>
                          <span className="text-base font-black text-emerald-400 mt-1 block">{itemDetails.balance_total}</span>
                        </Card>
                      </div>
                    </div>
                  ) : (
                    <EmptyState
                      icon={<ShieldAlert size={36} className="text-slate-650" />}
                      title="Item sem Codigo Cybersul"
                      description="Este item ainda nao possui um codigo oficial do sistema Cybersul associado. Caso seja necessario, solicite a vinculacao a um administrador."
                    />
                  )}
                </div>
              )}

              {drawerTab === 'tecnico' && isAdminOrMessias && (
                <div className="bg-slate-950/45 p-4 rounded-2xl border border-white/5 space-y-3 font-mono text-[10px] text-rose-300">
                  <div>
                    <span className="text-slate-500 block font-bold uppercase">Item UUID</span>
                    {itemDetails.id}
                  </div>
                  <div>
                    <span className="text-slate-500 block font-bold uppercase">Identity Hash (SHA-256)</span>
                    {itemDetails?.identity_hash}
                  </div>
                  <div>
                    <span className="text-slate-500 block font-bold uppercase">Aba de Origem</span>
                    {itemDetails.source_sheet}
                  </div>
                </div>
              )}

            </div>
          </div>
        ) : (
          <LoadingState text="Carregando detalhes..." />
        )}
      </Drawer>

      {/* MODAL: ATUALIZAR PRECO */}
      <Modal
        isOpen={updatePriceModalOpen}
        onClose={() => setUpdatePriceModalOpen(false)}
        title="Atualizar Preco do Fornecedor"
      >
        <form onSubmit={handleConfirmPriceUpdate} className="space-y-4 text-left">
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
              Fornecedor: <span className="text-white font-black">{selectedSupplierForUpdate?.supplier_name}</span>
            </label>
            <Input
              type="text"
              label="Novo Preco (R$)"
              value={priceForm.newPrice}
              onChange={(e) => handlePriceChange(e.target.value)}
              placeholder="Digite o preco..."
              required
            />
          </div>

          {pricePreview && (
            <Card className="p-3 bg-slate-950/45 border border-white/5 text-xs font-bold">
              <span className="text-[10px] text-slate-500 uppercase font-black block mb-2">Comparativo de Reajuste</span>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-slate-450 block">Preco Antigo:</span>
                  <span className="text-slate-400 line-through">{formatCurrency(pricePreview.oldPrice)}</span>
                </div>
                <div>
                  <span className="text-white block">Preco Novo:</span>
                  <span className="text-emerald-400 font-black">{formatCurrency(pricePreview.newPrice)}</span>
                </div>
              </div>
              <div className="border-t border-white/5 mt-3 pt-2 flex justify-between items-center">
                <span>Diferenca:</span>
                <span className={pricePreview.diff > 0 ? 'text-rose-400 font-black' : 'text-emerald-400 font-black'}>
                  {pricePreview.diff > 0 ? '+' : ''}{formatCurrency(pricePreview.diff)} ({pricePreview.diff > 0 ? '+' : ''}{pricePreview.percent.toFixed(1)}%)
                </span>
              </div>
            </Card>
          )}

          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-400 block">Observacao / Justificativa</label>
            <textarea
              value={priceForm.notes}
              onChange={(e) => setPriceForm(prev => ({ ...prev, notes: e.target.value }))}
              placeholder="Ex: Reajuste anual da tabela do fornecedor..."
              className="w-full bg-slate-950/45 border border-white/5 p-3 rounded-xl text-white text-xs font-semibold focus:outline-none"
              rows={3}
            />
          </div>

          <div className="flex gap-2 justify-end">
            <Button variant="secondary" size="md" onClick={() => setUpdatePriceModalOpen(false)}>
              Cancelar
            </Button>
            <Button variant="primary" size="md" type="submit">
              Confirmar Preco
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: COTAR PRODUTO */}
      <Modal
        isOpen={quoteModalOpen}
        onClose={() => setQuoteModalOpen(false)}
        title="Rascunho de Cotacao de Produto"
      >
        {quotePayload ? (
          <div className="space-y-4 text-left font-bold text-xs text-slate-350">
            <div className="bg-slate-950/45 p-4 rounded-xl border border-white/5 space-y-2">
              <div>
                <span className="text-slate-500 text-[10px] uppercase">Produto Selecionado</span>
                <p className="text-white font-black text-sm">{quotePayload.display_name}</p>
              </div>
              {quotePayload.cybersul_code && (
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Codigo Cybersul</span>
                  <p className="text-white font-mono">{quotePayload.cybersul_code}</p>
                </div>
              )}
              {quotePayload.observations && (
                <div>
                  <span className="text-slate-500 text-[10px] uppercase">Observacoes</span>
                  <p className="text-white font-semibold">{quotePayload.observations}</p>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <span className="text-slate-450 block">Fornecedores Recomendados / Contatos</span>
              {quotePayload.suggested_suppliers.length === 0 ? (
                <div className="p-3 text-center text-slate-500 bg-slate-950/45 rounded-xl border border-white/5">Nenhum fornecedor cadastrado na planilha para este item.</div>
              ) : (
                <div className="space-y-2">
                  {quotePayload.suggested_suppliers.map((s: any) => (
                    <div key={s.supplier_id} className="p-2.5 bg-slate-950/45 rounded-lg border border-white/5 flex justify-between items-center text-[11px]">
                      <div>
                        <span className="text-white font-black block">{s.supplier_name}</span>
                        <span className="text-slate-450 block">{s.email || 'Sem e-mail'}</span>
                      </div>
                      <span className="text-emerald-400 font-bold">{s.last_price ? formatCurrency(s.last_price) : '-'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <Card className="p-3 bg-emerald-950/15 border border-emerald-500/20 text-emerald-400 flex items-start gap-2.5 font-semibold leading-relaxed">
              <CheckCircle size={20} className="shrink-0" />
              <span>
                <strong>Sprint 1:</strong> O rascunho de cotacao com os fornecedores e precos foi consolidado com sucesso. O Portal salvou as informacoes no payload sem disparar e-mails reais ou monitoramento.
              </span>
            </Card>

            <div className="flex gap-2 justify-end">
              <Button variant="secondary" size="md" onClick={() => setQuoteModalOpen(false)}>
                Fechar
              </Button>
              <Button variant="primary" size="md" onClick={() => {
                setMessage('Rascunho de cotacao preparado para Compras. Nenhum e-mail foi enviado.');
                setQuoteModalOpen(false);
              }}>
                Confirmar rascunho
              </Button>
            </div>
          </div>
        ) : (
          <LoadingState text="Carregando Cotacao..." />
        )}
      </Modal>

    </div>
  );
};

export default StockPage;
