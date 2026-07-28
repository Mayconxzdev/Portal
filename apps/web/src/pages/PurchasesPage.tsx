import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  ShoppingCart, Plus, Search, FileText, Users, CheckCircle2,
  Clock, AlertTriangle, X, Eye, TrendingDown, ShieldCheck,
  Clipboard, Send, ChevronRight,
  MailOpen, Scale, Package, Wrench, AlertCircle, Lock,
  Trash2, CreditCard, Truck, Check, Copy, RotateCcw, List
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Drawer } from '../components/ui/Drawer';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Select } from '../components/ui/Select';
import { EmptyState } from '../components/ui/EmptyState';
import { EntityQuickActions } from '../components/actions/EntityQuickActions';
import { ActionCommandCard } from '../components/actions/ActionCommandCard';
import { useActionCommands, ActionCommandDraft } from '../hooks/useActionCommands';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { PurchasesHeader } from '../components/purchases/PurchasesHeader';
import { PurchasesIndicators } from '../components/purchases/PurchasesIndicators';
import { PurchasesQueue } from '../components/purchases/PurchasesQueue';
import { NewPurchaseComposer } from '../components/purchases/NewPurchaseComposer';
import type { PurchaseInputMode } from '../components/purchases/SmartPurchaseInput';
import { ParsedItemsReview } from '../components/purchases/ParsedItemsReview';
import { ApprovalSelectionPanel } from '../components/purchases/ApprovalSelectionPanel';
import { ExternalSearchPanel } from '../components/purchases/ExternalSearchPanel';
import { SupplierQuotationPanel } from '../components/purchases/SupplierQuotationPanel';
import { EmailQuotationPreview } from '../components/purchases/EmailQuotationPreview';
import { PurchaseRegistrationPanel } from '../components/purchases/PurchaseRegistrationPanel';
import { DeliveryPanel } from '../components/purchases/DeliveryPanel';
import { PurchaseSummary } from '../components/purchases/PurchaseSummary';
import { PurchaseWorkspace } from '../components/purchases/PurchaseWorkspace';
import { setQueryParams } from '../utils/urlState';

type PurchaseQueueFilter = 'all' | 'attention' | 'suppliers' | 'approval' | 'ready' | 'delivery';

const PURCHASE_QUEUE_FILTERS: PurchaseQueueFilter[] = ['all', 'attention', 'suppliers', 'approval', 'ready', 'delivery'];

// ---------------------------------------------------------------------------
// Interfaces TypeScript — alinhadas com a nova API UUID
// ---------------------------------------------------------------------------
import {
  MasterSupplier,
  MasterItem,
  MasterService,
  PurchaseItemOptionResponse,
  PurchaseItemResponse,
  PurchaseRFQ,
  PurchaseRFQSupplier,
  PurchaseQuoteDetail,
  ParsedQuoteLine,
  SupplierSuggestion,
  EmailPreview,
  InboundAttachment,
  ResponseCandidate,
  ResponseEvidence,
  ResponseExtractedField,
  ResponseExtraction,
  RFQDraft,
  QuoteResponseLine,
  QuoteResponse,
  CompareSupplierSummary,
  CompareItemOffer,
  CompareItemRow,
  PurchaseComparison,
  PurchasesSummary,
  PurchaseAttentionItem,
  PurchaseStatusGroup,
  PurchaseOngoingQuote,
  PurchasesOverview,
  NewItemForm,
  PurchaseRequest,
  PurchaseResearchSession
} from '../components/purchases/types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const fmt = (val?: number) => {
  if (val === undefined || val === null) return 'R$ 0,00';
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
};

const fmtDate = (d?: string) => {
  if (!d) return '-';
  return new Date(d).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
};

const fmtDateTime = (d?: string) => {
  if (!d) return '-';
  return new Date(d).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const humanSourceLabel = (source?: string) => {
  const normalized = (source || '').toLowerCase();
  if (!normalized) return 'Registro do Portal';
  if (normalized.includes('invoice') || normalized.includes('nota')) return 'Nota fiscal';
  if (normalized.includes('quote') || normalized.includes('cotacao') || normalized.includes('cotação')) return 'Cotação';
  if (normalized.includes('purchase') || normalized.includes('order') || normalized.includes('pedido')) return 'Pedido de compra';
  if (normalized.includes('manual')) return 'Cadastro manual';
  if (normalized.includes('stock') || normalized.includes('catalog')) return 'Estoque e Catálogo';
  if (normalized.includes('supplier') || normalized.includes('fornecedor')) return 'Fornecedor';
  if (normalized.includes('history') || normalized.includes('historico') || normalized.includes('histórico')) return 'Histórico';
  return 'Registro do Portal';
};

const humanEvidenceLabel = (source?: string, documentNumber?: string) => {
  const label = humanSourceLabel(source);
  return documentNumber ?`${label} (${documentNumber})` : label;
};

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Rascunho',
  REQUESTED: 'Solicitada',
  PENDING_APPROVAL: 'Aprov. Pendente',
  APPROVED: 'Aprovada',
  RFQ_PREPARING: 'Preparando Cotação',
  RFQ_SENT: 'Cotação Enviada',
  QUOTES_RECEIVED: 'Cotações Recebidas',
  COMPARING: 'Comparando',
  APPROVAL_REQUIRED: 'Aprovação Final',
  ORDERED: 'Pedido Gerado',
  REJECTED: 'Rejeitada',
  CANCELLED: 'Cancelada',
  // RFQ status
  READY_FOR_REVIEW: 'Pronto p/ Revisão',
  PENDING_SEND_APPROVAL: 'Aprovação de Envio',
  SENT: 'Enviada',
};

const PRIORITY_LABELS: Record<string, string> = {
  LOW: 'Baixa', NORMAL: 'Normal', HIGH: 'Alta', URGENT: 'Urgente',
};

// ---------------------------------------------------------------------------
// Subcomponente: Bloco de Aviso de Envio Bloqueado
// ---------------------------------------------------------------------------
const EmailBlockedNotice: React.FC = () => null;

// ---------------------------------------------------------------------------
// Componente principal
// ---------------------------------------------------------------------------
export const PurchasesPage: React.FC<{
  currentUser?: any;
  onBack?: () => void;
  onNavigate?: (moduleCode: string, options?: { search?: Record<string, string | number | boolean | null | undefined> | URLSearchParams | string; replace?: boolean }) => void;
}> = ({ currentUser, onNavigate }) => {
  // -------------------------------------------------------------------------
  // Estado principal
  // -------------------------------------------------------------------------
  const [activeTab, setActiveTab] = useState<'overview' | 'new_quote' | 'quotations' | 'responses' | 'comparison' | 'orders' | 'deliveries' | 'history' | 'product_prices' | 'xlsx_reconciliation' | 'requests' | 'suppliers' | 'price_history' | 'catalog'>('overview');
  const isAdminOrMessias = currentUser?.role === 'ADMIN' || currentUser?.role === 'MESSIAS';
  const [preparedActionDraft, setPreparedActionDraft] = useState<any | null>(null);
  const { confirmCommand, cancelCommand } = useActionCommands();

  // Estado do ConfirmDialog
  const [confirmDialogConfig, setConfirmDialogConfig] = useState<{
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    confirmText?: string;
    cancelText?: string;
    variant?: 'danger' | 'warning' | 'primary';
  }>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => {},
  });

  const showConfirm = (config: Omit<typeof confirmDialogConfig, 'isOpen'>) => {
    setConfirmDialogConfig({ ...config, isOpen: true });
  };

  const closeConfirm = () => {
    setConfirmDialogConfig(prev => ({ ...prev, isOpen: false }));
  };

  const [sendingRFQ, setSendingRFQ] = useState(false);
  const [resendingSupplierId, setResendingSupplierId] = useState<string | null>(null);
  const [choosingSupplierId, setChoosingSupplierId] = useState<string | null>(null);
  
  // Rastreabilidade de preços de compras (Price Traceability)
  const [priceReferences, setPriceReferences] = useState<any[]>([]);
  const [priceSuggestions, setPriceSuggestions] = useState<any[]>([]);
  const [priceHistory, setPriceHistory] = useState<any[]>([]);
  const [loadingPrices, setLoadingPrices] = useState(false);
  const [priceSubTab, setPriceSubTab] = useState<'references' | 'suggestions' | 'conference' | 'timeline'>('references');
  
  // Timeline por item
  const [selectedTimelineItem, setSelectedTimelineItem] = useState<string>('');
  const [timelineData, setTimelineData] = useState<any[]>([]);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

  // Form de conferência
  const [confSupplierId, setConfSupplierId] = useState('');
  const [confProductItemId, setConfProductItemId] = useState('');
  const [confSourceType, setConfSourceType] = useState('BOLETO');
  const [confDocNumber, setConfDocNumber] = useState('');
  const [confDocDate, setConfDocDate] = useState('');
  const [confUnitPrice, setConfUnitPrice] = useState<number | ''>('');
  const [confQuantity, setConfQuantity] = useState<number | ''>('');
  const [confTotalAmount, setConfTotalAmount] = useState<number | ''>('');
  const [confPaymentTerms, setConfPaymentTerms] = useState('');
  const [confNotes, setConfNotes] = useState('');
  const [submittingEvidence, setSubmittingEvidence] = useState(false);

  // Rejeição
  const [rejectingSuggestionId, setRejectingSuggestionId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);

  // Estados do Catálogo Inteligente
  const [families, setFamilies] = useState<any[]>([]);
  const [loadingFamilies, setLoadingFamilies] = useState(false);
  const [expandedFamilyId, setExpandedFamilyId] = useState<string | null>(null);
  const [expandedFamilyDetails, setExpandedFamilyDetails] = useState<any | null>(null);
  const [loadingFamilyDetails, setLoadingFamilyDetails] = useState(false);
  const [selectedItemForPriceUpdate, setSelectedItemForPriceUpdate] = useState<any | null>(null);
  const [newPriceValue, setNewPriceValue] = useState<number | ''>('');
  const [isPriceModalOpen, setIsPriceModalOpen] = useState(false);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [historyTimeline, setHistoryTimeline] = useState<any[]>([]);
  const [loadingHistoryTimeline, setLoadingHistoryTimeline] = useState(false);

  // Busca textual e toast (declarados antes de loadFamilies que os utiliza)
  const [searchTerm, setSearchTerm] = useState('');
  const [purchaseFilter, setPurchaseFilter] = useState<PurchaseQueueFilter>('all');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastError, setToastError] = useState(false);

  const showToast = useCallback((msg: string, isError = false) => {
    setToastMessage(msg);
    setToastError(isError);
    setTimeout(() => setToastMessage(null), 4500);
  }, []);

  // Callbacks do Catálogo Inteligente
  const loadFamilies = useCallback(async () => {
    setLoadingFamilies(true);
    try {
      const res = await fetch('/api/v1/master-data/families');
      if (res.ok) {
        setFamilies(await res.json());
      } else {
        showToast('Erro ao carregar catálogo de famílias.', true);
      }
    } catch (e) {
      console.error(e);
      showToast('Erro ao buscar catálogo.', true);
    } finally {
      setLoadingFamilies(false);
    }
  }, [showToast]);

  const handleExpandFamily = useCallback(async (familyId: string) => {
    if (expandedFamilyId === familyId) {
      setExpandedFamilyId(null);
      setExpandedFamilyDetails(null);
      return;
    }
    setExpandedFamilyId(familyId);
    setLoadingFamilyDetails(true);
    try {
      const res = await fetch(`/api/v1/master-data/families/${familyId}`);
      if (res.ok) {
        setExpandedFamilyDetails(await res.json());
      } else {
        showToast('Erro ao carregar detalhes da família.', true);
      }
    } catch (e) {
      console.error(e);
      showToast('Erro ao buscar detalhes da família.', true);
    } finally {
      setLoadingFamilyDetails(false);
    }
  }, [expandedFamilyId, showToast]);


  const handleUpdatePriceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItemForPriceUpdate || newPriceValue === '') return;
    try {
      const res = await fetch(`/api/v1/master-data/items/${selectedItemForPriceUpdate.id}/update-price`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_price: parseFloat(newPriceValue.toString()) })
      });
      if (res.ok) {
        showToast('Preço de referência atualizado com sucesso.');
        setIsPriceModalOpen(false);
        if (expandedFamilyId) {
          const detRes = await fetch(`/api/v1/master-data/families/${expandedFamilyId}`);
          if (detRes.ok) {
            setExpandedFamilyDetails(await detRes.json());
          }
        }
      } else {
        const errorData = await res.json();
        showToast(errorData.detail || 'Erro ao atualizar preço.', true);
      }
    } catch (e) {
      console.error(e);
      showToast('Erro ao conectar com o servidor.', true);
    }
  };

  useEffect(() => {
    if (activeTab === 'catalog') {
      loadFamilies();
    }
  }, [activeTab, loadFamilies]);

  // Sincroniza filtro inicial pela URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const filterParam = params.get('filter');
    if (filterParam && PURCHASE_QUEUE_FILTERS.includes(filterParam as PurchaseQueueFilter)) {
      setPurchaseFilter(filterParam as PurchaseQueueFilter);
    }
  }, []);

  const applyPurchaseFilter = useCallback((filter: PurchaseQueueFilter) => {
    setPurchaseFilter(filter);
    setSelectedRequest(null);
    setActiveQuote(null);
    setActiveTab('overview');
    setQueryParams({ filter: filter === 'all' ?null : filter }, { replace: false });
  }, []);


  const filteredFamilies = useMemo(() => {
    if (!searchTerm) return families;
    const cleanSearch = searchTerm.toLowerCase();
    return families.filter(f =>
      f.name.toLowerCase().includes(cleanSearch) ||
      (f.description && f.description.toLowerCase().includes(cleanSearch))
    );
  }, [families, searchTerm]);

  const [requests, setRequests] = useState<PurchaseRequest[]>([]);
  const [masterSuppliers, setMasterSuppliers] = useState<MasterSupplier[]>([]);
  const [masterItems, setMasterItems] = useState<MasterItem[]>([]);
  const [masterServices, setMasterServices] = useState<MasterService[]>([]);
  const [summary, setSummary] = useState<PurchasesSummary>({
    total_requests: 0, drafts: 0, pending_approval: 0, approved: 0,
    quoting: 0, ordered: 0, delivered: 0, cancelled: 0,
    total_suppliers: 0, active_suppliers: 0, total_quotations_pending: 0,
    estimated_value_open: 0
  });
  const [overview, setOverview] = useState<PurchasesOverview | null>(null);

  const [loading, setLoading] = useState(true);
  const loadAllSeq = useRef(0);
  const loadAllAbortRef = useRef<AbortController | null>(null);
  const [quoteWizardStep, setQuoteWizardStep] = useState<'products' | 'suppliers' | 'preview'>('products');
  const [activeQuote, setActiveQuote] = useState<PurchaseQuoteDetail | null>(null);
  const [, setCreatingQuote] = useState(false);
  const [quoteTitle, setQuoteTitle] = useState('Nova compra');
  const [quoteDescription, setQuoteDescription] = useState('');
  const [catalogSearch, setCatalogSearch] = useState('');
  const [catalogResults, setCatalogResults] = useState<any[]>([]);
  const [catalogSearching, setCatalogSearching] = useState(false);
  const [pastedListText, setPastedListText] = useState('');
  const [purchaseInputMode, setPurchaseInputMode] = useState<PurchaseInputMode>('auto');
  const [parsedLines, setParsedLines] = useState<ParsedQuoteLine[]>([]);
  const [parsingList, setParsingList] = useState(false);
  const [supplierSuggestions, setSupplierSuggestions] = useState<SupplierSuggestion[]>([]);
  const [selectedSupplierMap, setSelectedSupplierMap] = useState<Record<string, Set<string>>>({});
  const [loadingSupplierSuggestions, setLoadingSupplierSuggestions] = useState(false);
  const [emailPreviews, setEmailPreviews] = useState<EmailPreview[]>([]);
  const [selectedEmailPreviewId, setSelectedEmailPreviewId] = useState<string | null>(null);
  const [loadingPreviews, setLoadingPreviews] = useState(false);
  const [bccOverrides, setBccOverrides] = useState<Record<string, boolean>>({});
  const [emailDraftEdits, setEmailDraftEdits] = useState<Record<string, { subject?: string; body_text?: string }>>({});
  const [sendingMessageId, setSendingMessageId] = useState<string | null>(null);
  const [responseCandidates, setResponseCandidates] = useState<ResponseCandidate[]>([]);
  const [loadingResponses, setLoadingResponses] = useState(false);
  const [selectedResponseCandidate, setSelectedResponseCandidate] = useState<ResponseCandidate | null>(null);
  const [responseDrawerOpen, setResponseDrawerOpen] = useState(false);
  const [responseActionId, setResponseActionId] = useState<string | null>(null);
  const [responseExtractions, setResponseExtractions] = useState<Record<string, ResponseExtraction>>({});
  const [extractingResponseId, setExtractingResponseId] = useState<string | null>(null);
  const [reviewingExtractionId, setReviewingExtractionId] = useState<string | null>(null);

  // Novos estados para Compras Inteligente Real
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchingExternal, setSearchingExternal] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchActiveItem, setSearchActiveItem] = useState<any | null>(null);
  const [activeResearchSession, setActiveResearchSession] = useState<PurchaseResearchSession | null>(null);
  const [manualOptionDraft, setManualOptionDraft] = useState({
    store_name: '',
    title: '',
    unit_price: '',
    shipping_price: '',
    delivery_estimate: '',
    product_url: '',
  });
  
  const [linkImportUrl, setLinkImportUrl] = useState('');
  const [importingLink, setImportingLink] = useState(false);
  
  const [cartImportUrl, setCartImportUrl] = useState('');
  const [importingCart, setImportingCart] = useState(false);
  const [cartImportPrivateText, setCartImportPrivateText] = useState('');
  const [showPrivateCartModal, setShowPrivateCartModal] = useState(false);
  
  const [isReceiving, setIsReceiving] = useState(false);
  const [deliveryItemsState, setDeliveryItemsState] = useState<any[]>([]);
  const [deliveryNotes, setDeliveryNotes] = useState('');
  
  const [isRegisteringOrder, setIsRegisteringOrder] = useState(false);
  const [finalValue, setFinalValue] = useState<number | ''>('');
  const [shippingPrice, setShippingPrice] = useState<number | ''>('');
  const [orderNumber, setOrderNumber] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('Boleto');
  const [orderNotes, setOrderNotes] = useState('');
  
  const [isAddingDetails, setIsAddingDetails] = useState(false);

  const handleExternalSearch = useCallback(async (query: string) => {
    if (!query.trim()) return;
    setSearchingExternal(true);
    setSearchError(null);
    setSearchResults([]);
    setActiveResearchSession(null);
    try {
      if (searchActiveItem?.id) {
        const res = await fetch(`/api/v1/purchases/items/${searchActiveItem.id}/research-sessions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: query.trim(),
            destination: searchActiveItem.destination || searchActiveItem.department || null,
            budget_limit: searchActiveItem.budget_limit || null,
            run_immediately: true,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          setSearchError(data.detail || 'Nao foi possivel iniciar a pesquisa persistente.');
          return;
        }
        setActiveResearchSession(data);
        setSearchResults(Array.isArray(data.options) ?data.options : []);
        const sessionStatus = String(data.status || '').toLowerCase();
        if (['queued', 'running', 'retryable_error'].includes(sessionStatus)) {
          setSearchError(null);
        } else if (data.missing_questions?.length) {
          setSearchError('Alguns dados ainda precisam de confirmacao antes de recomendar a melhor opcao.');
        } else if (!Array.isArray(data.options) || data.options.length === 0) {
          setSearchError('Pesquisa automatica de mercado ainda nao esta configurada. Adicione links ou opcoes manualmente.');
        }
        return;
      }

      const res = await fetch(`/api/v1/purchases/external-search?q=${encodeURIComponent(query)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status && data.status !== 'success') {
          setSearchError(data.message || 'Pesquisa automatica de mercado ainda nao esta configurada.');
          setSearchResults([]);
          return;
        }
        setSearchResults(Array.isArray(data) ?data : (data.results || []));
      } else {
        const err = await res.json();
        setSearchError(err.detail || 'Erro ao realizar busca externa.');
      }
    } catch (e) {
      console.error(e);
      setSearchError('Erro de conexao ao buscar produtos externamente.');
    } finally {
      setSearchingExternal(false);
    }
  }, [searchActiveItem]);

  useEffect(() => {
    if (!activeResearchSession?.id) return;
    const terminalStatuses = new Set(['completed', 'completed_with_pending', 'cancelled', 'blocked']);
    if (terminalStatuses.has(String(activeResearchSession.status || '').toLowerCase())) return;

    const controller = new AbortController();
    const timer = window.setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/purchases/research-sessions/${activeResearchSession.id}`, {
          signal: controller.signal,
        });
        if (!res.ok) return;
        const data = await res.json();
        setActiveResearchSession(data);
        setSearchResults(Array.isArray(data.options) ?data.options : []);
      } catch (error: any) {
        if (error?.name !== 'AbortError') {
          // O proximo polling tenta novamente; nao polui a tela com erro tecnico.
        }
      }
    }, 1800);

    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [activeResearchSession?.id, activeResearchSession?.status]);

  const refreshActiveResearchSession = useCallback(async () => {
    if (!activeResearchSession?.id) return;
    setSearchingExternal(true);
    setSearchError(null);
    try {
      const res = await fetch(`/api/v1/purchases/research-sessions/${activeResearchSession.id}/refresh`, {
        method: 'POST',
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setSearchError(data.detail || 'Não foi possível atualizar a pesquisa agora.');
        return;
      }
      setActiveResearchSession(data);
      setSearchResults(Array.isArray(data.options) ? data.options : []);
      if (!Array.isArray(data.options) || data.options.length === 0) {
        setSearchError('Ainda não há ofertas confirmadas. Adicione um link ou opção manual enquanto a pesquisa continua.');
      }
    } catch (error) {
      setSearchError('Erro de conexão ao atualizar a pesquisa.');
    } finally {
      setSearchingExternal(false);
    }
  }, [activeResearchSession?.id]);


  const handleImportLink = useCallback(async (url: string) => {
    if (!url.trim()) return;
    setImportingLink(true);
    try {
      const res = await fetch('/api/v1/purchases/needs/import-link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success' && data.suggested_request) {
          showToast('Link do produto importado com sucesso!');
          const line = data.suggested_request.items[0];
          setParsedLines(prev => [
            ...prev,
            {
              raw_text: url,
              description: line.free_text_description || 'Produto importado',
              quantity: line.quantity || 1,
              unit_of_measure: line.unit_of_measure || 'un',
              confidence: 'high',
              match_status: 'confirmed',
              purchase_type: 'external',
              classification_message: 'Importado via link do produto.',
              suggested_display_name: line.free_text_description,
              budget_limit: line.estimated_unit_price
            } as any
          ]);
          setLinkImportUrl('');
        }
      } else {
        const err = await res.json();
        showToast(err.detail || 'Erro ao importar link.', true);
      }
    } catch (e) {
      showToast('Erro de conexão ao importar link.', true);
    } finally {
      setImportingLink(false);
    }
  }, [showToast]);

  const handleImportCart = useCallback(async (urlOrText: string) => {
    if (!urlOrText.trim()) return;
    setImportingCart(true);
    try {
      const isUrl = urlOrText.startsWith('http://') || urlOrText.startsWith('https://');
      const payload = { url: urlOrText };
      const res = await fetch('/api/v1/purchases/needs/import-cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success' && data.suggested_request) {
          showToast('Carrinho importado com sucesso!');
          const newLines = data.suggested_request.items.map((line: any) => ({
            raw_text: line.free_text_description,
            description: line.free_text_description || 'Item do carrinho',
            quantity: line.quantity || 1,
            unit_of_measure: line.unit_of_measure || 'un',
            confidence: 'high',
            match_status: 'confirmed',
            purchase_type: 'external',
            classification_message: 'Importado via carrinho.',
            suggested_display_name: line.free_text_description,
            budget_limit: line.estimated_unit_price
          }));
          setParsedLines(prev => [...prev, ...newLines]);
          setCartImportUrl('');
          setCartImportPrivateText('');
          setShowPrivateCartModal(false);
        }
      } else {
        const err = await res.json();
        showToast(err.detail || 'Erro ao importar carrinho.', true);
      }
    } catch (e) {
      showToast('Erro de conexão ao importar carrinho.', true);
    } finally {
      setImportingCart(false);
    }
  }, [showToast]);


  // Drawer de detalhe da requisição
  const [selectedRequest, setSelectedRequest] = useState<PurchaseRequest | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // RFQ selecionada dentro do drawer
  const [selectedRFQ, setSelectedRFQ] = useState<PurchaseRFQ | null>(null);
  const [rfqSuppliers, setRfqSuppliers] = useState<PurchaseRFQSupplier[]>([]);
  const [rfqDrafts, setRfqDrafts] = useState<RFQDraft[]>([]);
  const [rfqComparison, setRfqComparison] = useState<PurchaseComparison | null>(null);
  const [loadingRFQ, setLoadingRFQ] = useState(false);
  const [rfqTab, setRfqTab] = useState<'suppliers' | 'drafts' | 'comparison'>('suppliers');

  // Modais
  const [isRequestModalOpen, setIsRequestModalOpen] = useState(false);
  const [isRFQModalOpen, setIsRFQModalOpen] = useState(false);
  const [isAddSupplierToRFQOpen, setIsAddSupplierToRFQOpen] = useState(false);
  const [isDraftDrawerOpen, setIsDraftDrawerOpen] = useState(false);
  const [selectedDraft, setSelectedDraft] = useState<RFQDraft | null>(null);

  // Formulário: Nova Requisição
  const [reqTitle, setReqTitle] = useState('');
  const [reqDesc, setReqDesc] = useState('');
  const [reqJustify, setReqJustify] = useState('');
  const [reqPriority, setReqPriority] = useState('NORMAL');
  const [reqNeededBy, setReqNeededBy] = useState('');
  const [reqDepartment, setReqDepartment] = useState('');
  const [reqItems, setReqItems] = useState<NewItemForm[]>([
    { free_text_description: '', quantity: 1, unit_of_measure: 'un', specifications: '', estimated_unit_price: 0, itemType: 'freetext' }
  ]);
  const [savingRequest, setSavingRequest] = useState(false);

  const updateReqItem = useCallback((index: number, patch: Partial<NewItemForm>) => {
    setReqItems((current) => current.map((item, i) => (i === index ?{ ...item, ...patch } : item)));
  }, []);

  const handleQuoteVariation = useCallback((item: any) => {
    setReqTitle(`Cotação para ${item.name}`);
    setReqDesc(`Solicitação de cotação para o item ${item.name} (${item.sku || 'Sem codigo'}).`);
    setReqItems([
      {
        item_id: item.id,
        free_text_description: item.name,
        quantity: 1,
        unit_of_measure: item.unit_of_measure || 'un',
        specifications: item.description || '',
        estimated_unit_price: item.reference_price || 0,
        itemType: 'product'
      }
    ]);
    setIsRequestModalOpen(true);
  }, []);

  const handleAddReqItem = useCallback(() => {
    setReqItems((current) => [
      ...current,
      { free_text_description: '', quantity: 1, unit_of_measure: 'un', specifications: '', estimated_unit_price: 0, itemType: 'freetext' }
    ]);
  }, []);

  const handleRemoveReqItem = useCallback((index: number) => {
    setReqItems((current) => (current.length <= 1 ?current : current.filter((_, i) => i !== index)));
  }, []);

  const handleItemTypeChange = useCallback((index: number, itemType: NewItemForm['itemType']) => {
    updateReqItem(index, {
      itemType,
      item_id: undefined,
      service_id: undefined,
      free_text_description: '',
      specifications: '',
      unit_of_measure: 'un',
    });
  }, [updateReqItem]);

  const estimatedTotal = useMemo(() => (
    reqItems.reduce((total, item) => total + ((Number(item.quantity) || 0) * (Number(item.estimated_unit_price) || 0)), 0)
  ), [reqItems]);

  // Formulário: Nova RFQ
  const [rfqTitle, setRfqTitle] = useState('');
  const [rfqDeadline, setRfqDeadline] = useState('');
  const [rfqTemplate, setRfqTemplate] = useState('');
  const [savingRFQ, setSavingRFQ] = useState(false);

  // Acoes - cotacao
  const [selectedSupplierId, setSelectedSupplierId] = useState('');
  const [supplierContactEmail, setSupplierContactEmail] = useState('');
  const [addingSupplier, setAddingSupplier] = useState(false);
  const [generatingDrafts, setGeneratingDrafts] = useState(false);
  const [requestingApproval, setRequestingApproval] = useState(false);

  // --- Fila de Revisão de Fornecedores ---
  const [supplierReviewQueue, setSupplierReviewQueue] = useState<any[]>([]);
  const [supplierReviewSummary, setSupplierReviewSummary] = useState<any>(null);
  const [loadingSupplierQueue, setLoadingSupplierQueue] = useState(false);
  const [selectedSupplierForReview, setSelectedSupplierForReview] = useState<any | null>(null);
  const [isSupplierReviewDrawerOpen, setIsSupplierReviewDrawerOpen] = useState(false);
  const [supplierLinkedItems, setSupplierLinkedItems] = useState<any[]>([]);
  const [loadingSupplierLinkedItems, setLoadingSupplierLinkedItems] = useState(false);
  const [reviewContactEmail, setReviewContactEmail] = useState('');
  const [reviewContactPhone, setReviewContactPhone] = useState('');
  const [savingReviewContact, setSavingReviewContact] = useState(false);

  const filteredRequests = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return requests;
    return requests.filter((req) => (
      req.title.toLowerCase().includes(term) ||
      (req.description || '').toLowerCase().includes(term) ||
      (req.department || '').toLowerCase().includes(term) ||
      req.status.toLowerCase().includes(term)
    ));
  }, [requests, searchTerm]);

  const filteredSuppliers = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    if (!term) return masterSuppliers;
    return masterSuppliers.filter((supplier) => {
      const categories = supplier.categories || [];
      return (
        supplier.person.name.toLowerCase().includes(term) ||
        (supplier.person.email || '').toLowerCase().includes(term) ||
        (supplier.preferred_contact_email || '').toLowerCase().includes(term) ||
        categories.some((category: string) => category.toLowerCase().includes(term))
      );
    });
  }, [masterSuppliers, searchTerm]);

  // -------------------------------------------------------------------------
  // Carregamento de dados
  // -------------------------------------------------------------------------
  const loadAll = useCallback(async () => {
    const seq = loadAllSeq.current + 1;
    loadAllSeq.current = seq;
    loadAllAbortRef.current?.abort();
    const controller = new AbortController();
    loadAllAbortRef.current = controller;
    setLoading(true);
    try {
      const needsUrl = `/api/v1/purchases/needs${purchaseFilter === 'all' ?'' : `?queue_filter=${encodeURIComponent(purchaseFilter)}`}`;
      const [overviewRes, sumRes, reqRes, supRes, itemsRes, servicesRes] = await Promise.all([
        fetch('/api/v1/purchases/overview', { signal: controller.signal }),
        fetch('/api/v1/purchases/summary', { signal: controller.signal }),
        fetch(needsUrl, { signal: controller.signal }),
        fetch('/api/v1/master-data/suppliers', { signal: controller.signal }),
        fetch('/api/v1/master-data/items', { signal: controller.signal }),
        fetch('/api/v1/master-data/services', { signal: controller.signal }),
      ]);
      if (seq !== loadAllSeq.current) return;
      if (overviewRes.ok) {
        const overviewData = await overviewRes.json();
        setOverview(overviewData);
        if (overviewData.summary) setSummary(overviewData.summary);
      }
      if (sumRes.ok) setSummary(await sumRes.json());
      if (reqRes.ok) setRequests(await reqRes.json());
      if (supRes.ok) setMasterSuppliers(await supRes.json());
      if (itemsRes.ok) setMasterItems(await itemsRes.json());
      if (servicesRes.ok) setMasterServices(await servicesRes.json());
    } catch (e: any) {
      if (e?.name === 'AbortError') return;
      console.error('Erro ao carregar compras:', e);
      showToast('Falha ao sincronizar com o servidor.', true);
    } finally {
      if (seq === loadAllSeq.current) {
        setLoading(false);
        loadAllAbortRef.current = null;
      }
    }
  }, [purchaseFilter, showToast]);

  useEffect(() => { loadAll(); }, [loadAll]);
  useEffect(() => () => loadAllAbortRef.current?.abort(), []);

  const loadQuoteDetail = useCallback(async (quoteId: string) => {
    const res = await fetch(`/api/v1/purchases/quotes/${quoteId}`);
    if (!res.ok) {
      showToast('Não foi possível abrir a cotação.', true);
      return null;
    }
    const data = await res.json();
    setActiveQuote(data);
    return data as PurchaseQuoteDetail;
  }, [showToast]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const quoteId = params.get('quote');
    const step = params.get('step');
    if (quoteId) {
      setActiveTab('new_quote');
      setQuoteWizardStep(step === 'suppliers' ?'suppliers' : step === 'preview' ?'preview' : 'products');
      loadQuoteDetail(quoteId);
    }
  }, [loadQuoteDetail]);

  const handleCreateOperationalQuote = useCallback(async (mode: 'manual' | 'pasted_list' = 'manual') => {
    setCreatingQuote(true);
    try {
      const res = await fetch('/api/v1/purchases/quotes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: quoteTitle || 'Compra com fornecedores para revisar',
          description: quoteDescription || null,
          origin_type: mode,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Não foi possível preparar a cotação.');
      }
      const data = await res.json();
      setActiveQuote(data);
      setActiveTab('new_quote');
      setQuoteWizardStep('products');
      setQueryParams({ quote: data.id, step: 'products' });
      await loadAll();
      return data as PurchaseQuoteDetail;
    } catch (err: any) {
      showToast(err.message || 'Erro ao preparar a cotação.', true);
      return null;
    } finally {
      setCreatingQuote(false);
    }
  }, [loadAll, quoteDescription, quoteTitle, showToast]);

  const ensureActiveQuote = useCallback(async (mode: 'manual' | 'pasted_list' = 'manual') => {
    if (activeQuote) return activeQuote;
    return handleCreateOperationalQuote(mode);
  }, [activeQuote, handleCreateOperationalQuote]);

  const searchCatalogForQuote = useCallback(async () => {
    if (!catalogSearch.trim()) return;
    setCatalogSearching(true);
    try {
      const res = await fetch(`/api/v1/stock-catalog/search?q=${encodeURIComponent(catalogSearch)}&suggest=true`);
      if (res.ok) setCatalogResults(await res.json());
    } catch {
      showToast('Erro ao buscar no catalogo.', true);
    } finally {
      setCatalogSearching(false);
    }
  }, [catalogSearch, showToast]);

  const addCatalogItemToQuote = useCallback(async (item: any) => {
    const quote = await ensureActiveQuote('manual');
    if (!quote) return;
    const res = await fetch(`/api/v1/purchases/quotes/${quote.id}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stock_catalog_item_id: item.id,
        free_text_description: item.display_name,
        quantity: 1,
        unit_of_measure: item.unit || 'un',
        specifications: item.specification_text || item.measure_display || item.variation_label || '',
        estimated_unit_price: item.primary_price || item.last_price || null,
        source_type: 'stock_catalog',
        source_ref_id: item.id,
        source_confidence: 'high',
        match_status: 'confirmed',
        source_snapshot_json: item,
      }),
    });
    if (!res.ok) {
      showToast('Nao foi possivel adicionar o produto.', true);
      return;
    }
    await loadQuoteDetail(quote.id);
    showToast('Produto adicionado à cotação.');
  }, [ensureActiveQuote, loadQuoteDetail, showToast]);

  const parsePastedList = useCallback(async () => {
    const quote = await ensureActiveQuote('pasted_list');
    if (!quote || !pastedListText.trim()) return;
    setParsingList(true);
    try {
      const res = await fetch(`/api/v1/purchases/quotes/${quote.id}/parse-list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: pastedListText }),
      });
      if (!res.ok) throw new Error('Nao foi possivel interpretar a lista.');
      setParsedLines(await res.json());
    } catch (err: any) {
      showToast(err.message || 'Erro ao interpretar lista.', true);
    } finally {
      setParsingList(false);
    }
  }, [ensureActiveQuote, pastedListText, showToast]);

  const parsePastedNeedList = useCallback(async () => {
    if (!pastedListText.trim()) return;
    setParsingList(true);
    try {
      const res = await fetch('/api/v1/purchases/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: pastedListText, context: `new_purchase:${purchaseInputMode}` }),
      });
      if (!res.ok) throw new Error('Nao foi possivel interpretar a lista.');
      const data = await res.json();
      const mapped = (data.items || []).map((item: any) => {
        const metadata = item.metadata_json || {};
        return {
          raw_text: metadata.raw_text || item.description,
          description: item.description,
          quantity: item.quantity,
          unit_of_measure: item.unit_of_measure || 'un',
          confidence: (item.confidence_score || 0) >= 0.8 ?'high' : (item.confidence_score || 0) >= 0.5 ?'check' : 'low',
          match_status: item.item_type === 'ambiguous' ?'needs_confirmation' : 'confirmed',
          purchase_type: item.item_type,
          classification_message: item.classification_reason,
          match_score: item.confidence_score,
          suggested_stock_catalog_item_id: item.stock_catalog_item_id || undefined,
          suggested_display_name: metadata.suggested_display_name,
          suggested_specification: metadata.suggested_specification,
          budget_limit: item.budget_limit,
          destination: item.destination,
          department: item.department,
        };
      });
      setParsedLines(mapped);
    } catch (err: any) {
      showToast(err.message || 'Erro ao interpretar lista.', true);
    } finally {
      setParsingList(false);
    }
  }, [pastedListText, purchaseInputMode, showToast]);

  const openRequestFromParsedNeed = useCallback(() => {
    if (parsedLines.length === 0) return;
    const titleItems = parsedLines
      .map(line => line.purchase_type === 'internal' ?line.suggested_display_name || line.description : line.description)
      .filter(Boolean)
      .slice(0, 2);
    setReqTitle(titleItems.length ?`Compra - ${titleItems.join(' + ')}` : 'Necessidade aguardando descrição');
    setReqDesc('Necessidade preparada a partir da análise inteligente. Revise os itens antes de confirmar.');
    setReqJustify('');
    setReqPriority('NORMAL');
    setReqDepartment('');
    setReqNeededBy('');
    setReqItems(parsedLines.map(line => ({
      stock_catalog_item_id: line.purchase_type === 'internal' ?line.suggested_stock_catalog_item_id || undefined : undefined,
      free_text_description: line.purchase_type === 'internal' ?line.suggested_display_name || line.description : line.description,
      quantity: line.quantity,
      unit_of_measure: line.unit_of_measure || 'un',
      specifications: line.purchase_type === 'internal'
        ?line.suggested_specification || ''
        : line.classification_message || 'Item externo sem vínculo automático com Estoque.',
      estimated_unit_price: 0,
      itemType: 'freetext',
    })));
    setIsRequestModalOpen(true);
  }, [parsedLines]);

  const addParsedLineToQuote = useCallback(async (line: ParsedQuoteLine) => {
    if (line.purchase_type !== 'internal') {
      showToast('Compra externa precisa ser revisada como necessidade antes de virar cotação interna.', true);
      return;
    }
    const quote = await ensureActiveQuote('pasted_list');
    if (!quote) return;
    const res = await fetch(`/api/v1/purchases/quotes/${quote.id}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stock_catalog_item_id: line.suggested_stock_catalog_item_id || null,
        free_text_description: line.suggested_display_name || line.description,
        quantity: line.quantity,
        unit_of_measure: line.unit_of_measure,
        specifications: line.suggested_specification || '',
        source_type: 'pasted_list',
        source_ref_id: line.raw_text,
        source_confidence: line.confidence,
        match_status: line.match_status,
        source_snapshot_json: line,
      }),
    });
    if (!res.ok) {
      showToast('Nao foi possivel adicionar item da lista.', true);
      return;
    }
    await loadQuoteDetail(quote.id);
  }, [ensureActiveQuote, loadQuoteDetail, showToast]);

  const loadSupplierSuggestions = useCallback(async () => {
    if (!activeQuote) return;
    setLoadingSupplierSuggestions(true);
    try {
      const res = await fetch(`/api/v1/purchases/quotes/${activeQuote.id}/supplier-suggestions`);
      if (res.ok) {
        const data: SupplierSuggestion[] = await res.json();
        setSupplierSuggestions(data);
        const nextMap: Record<string, Set<string>> = {};
        data.filter(s => s.status === 'known' && s.supplier_id).slice(0, 5).forEach(s => {
          nextMap[s.supplier_id!] = new Set(s.item_ids.length ?s.item_ids : activeQuote.items.map(item => item.id));
        });
        setSelectedSupplierMap(nextMap);
      }
    } finally {
      setLoadingSupplierSuggestions(false);
    }
  }, [activeQuote]);

  const saveSupplierSelection = useCallback(async () => {
    if (!activeQuote) return;
    const suppliers = Object.entries(selectedSupplierMap).map(([supplierId, itemSet]) => ({
      supplier_id: supplierId,
      item_ids: Array.from(itemSet),
    }));
    const res = await fetch(`/api/v1/purchases/quotes/${activeQuote.id}/supplier-selection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ suppliers }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || 'Revise fornecedores e contatos antes de continuar.', true);
      return;
    }
    setActiveQuote(await res.json());
    setQuoteWizardStep('preview');
    setQueryParams({ quote: activeQuote.id, step: 'preview' });
  }, [activeQuote, selectedSupplierMap, showToast]);

  const loadEmailPreviews = useCallback(async () => {
    if (!activeQuote) return;
    setLoadingPreviews(true);
    try {
      const res = await fetch(`/api/v1/purchases/quotes/${activeQuote.id}/email-previews`);
      if (res.ok) {
        const previews = await res.json();
        setEmailPreviews(previews);
        setSelectedEmailPreviewId(current => current && previews.some((preview: EmailPreview) => preview.message_id === current) ?current : previews[0]?.message_id || null);
        setBccOverrides(Object.fromEntries(previews.map((preview: EmailPreview) => [preview.rfq_supplier_id, preview.bcc_enabled])));
        setEmailDraftEdits(Object.fromEntries(previews.map((preview: EmailPreview) => [
          preview.message_id,
          { subject: preview.subject, body_text: preview.body_text || '' },
        ])));
      }
    } finally {
      setLoadingPreviews(false);
    }
  }, [activeQuote]);

  const messageTextToHtml = useCallback((value: string) => value
    .split(/\n{2,}/)
    .map(paragraph => paragraph.trim())
    .filter(Boolean)
    .map(paragraph => `<p>${paragraph
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')}</p>`)
    .join(''), []);

  const updateEmailMessage = useCallback(async (messageId: string, changes: Record<string, unknown>) => {
    const res = await fetch(`/api/v1/purchases/email-messages/${messageId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(changes),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || 'Nao foi possivel salvar a mensagem.', true);
      return null;
    }
    const updated = await res.json();
    setEmailPreviews(prev => prev.map(item => item.message_id === messageId ?updated : item));
    setEmailDraftEdits(prev => ({
      ...prev,
      [updated.message_id]: { subject: updated.subject, body_text: updated.body_text || '' },
    }));
    return updated as EmailPreview;
  }, [showToast]);

  const handleBccToggle = useCallback(async (preview: EmailPreview, enabled: boolean) => {
    setBccOverrides(prev => ({ ...prev, [preview.rfq_supplier_id]: enabled }));
    const updated = await updateEmailMessage(preview.message_id, { bcc_enabled: enabled });
    if (updated) showToast(enabled ?'BCC padrao ativo para esta mensagem.' : 'BCC desmarcado para esta mensagem.');
  }, [showToast, updateEmailMessage]);

  const saveEmailDraft = useCallback(async (preview: EmailPreview) => {
    const draft = emailDraftEdits[preview.message_id] || {};
    const bodyText = draft.body_text ?? preview.body_text ?? '';
    const updated = await updateEmailMessage(preview.message_id, {
      subject: draft.subject ?? preview.subject,
      body_text: bodyText,
      body_html: messageTextToHtml(bodyText),
    });
    if (updated) showToast('Mensagem salva e hash atualizado.');
  }, [emailDraftEdits, messageTextToHtml, showToast, updateEmailMessage]);

  const sendEmailMessage = useCallback(async (preview: EmailPreview, isTest: boolean = false) => {
    setSendingMessageId(preview.message_id);
    try {
      const mode = isTest ?'test' : 'real';
      const res = await fetch(`/api/v1/purchases/email-messages/${preview.message_id}/send?mode=${mode}`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToast(data.detail || 'Não foi possível enviar a cotação.', true);
        return;
      }
      if (data.message) {
        setEmailPreviews(prev => prev.map(item => item.message_id === preview.message_id ?data.message : item));
      }
      showToast(data.human_message || 'Envio registrado.');
    } finally {
      setSendingMessageId(null);
    }
  }, [showToast]);

  const loadResponseCandidates = useCallback(async () => {
    setLoadingResponses(true);
    try {
      const res = await fetch('/api/v1/purchases/response-candidates');
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || 'Nao foi possivel carregar respostas recebidas.', true);
        return;
      }
      setResponseCandidates(await res.json());
    } catch (e) {
      console.error('Erro ao carregar respostas recebidas:', e);
      showToast('Falha ao buscar respostas recebidas.', true);
    } finally {
      setLoadingResponses(false);
    }
  }, [showToast]);

  const openResponseCandidate = useCallback((candidate: ResponseCandidate) => {
    setSelectedResponseCandidate(candidate);
    setResponseDrawerOpen(true);
  }, []);

  const decideResponseCandidate = useCallback(async (candidate: ResponseCandidate, decision: 'confirm' | 'reject' | 'ignore') => {
    setResponseActionId(`${candidate.id}:${decision}`);
    try {
      const res = await fetch(`/api/v1/purchases/response-candidates/${candidate.id}/${decision}`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToast(data.detail || 'Nao foi possivel registrar a decisao.', true);
        return;
      }
      showToast(data.human_message || 'Resposta atualizada.');
      setSelectedResponseCandidate(data.candidate || null);
      await loadResponseCandidates();
      await loadAll();
    } catch (e) {
      console.error('Erro ao decidir resposta:', e);
      showToast('Falha ao registrar a decisao da resposta.', true);
    } finally {
      setResponseActionId(null);
    }
  }, [loadAll, loadResponseCandidates, showToast]);

  const extractResponseCandidate = useCallback(async (candidate: ResponseCandidate) => {
    setExtractingResponseId(candidate.id);
    try {
      const res = await fetch(`/api/v1/purchases/response-candidates/${candidate.id}/extract`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToast(data.detail || 'Nao foi possivel extrair dados desta resposta.', true);
        return;
      }
      setResponseExtractions(prev => ({ ...prev, [candidate.id]: data }));
      showToast(data.fields?.length ?'Sugestoes extraidas para revisao.' : 'Nenhum campo confiavel encontrado. Revise manualmente.');
    } catch (e) {
      console.error('Erro ao extrair resposta:', e);
      showToast('Falha ao extrair dados da resposta.', true);
    } finally {
      setExtractingResponseId(null);
    }
  }, [showToast]);

  const reviewResponseExtraction = useCallback(async (candidate: ResponseCandidate, extraction: ResponseExtraction) => {
    setReviewingExtractionId(extraction.id);
    try {
      const res = await fetch(`/api/v1/purchases/response-extractions/${extraction.id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decisions: extraction.fields.map(field => ({ field_id: field.id, decision: 'accept' })),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToast(data.detail || 'Nao foi possivel revisar os campos.', true);
        return;
      }
      setResponseExtractions(prev => ({ ...prev, [candidate.id]: data.extraction }));
      showToast(data.human_message || 'Campos revisados.');
    } catch (e) {
      console.error('Erro ao revisar extracao:', e);
      showToast('Falha ao revisar a extracao.', true);
    } finally {
      setReviewingExtractionId(null);
    }
  }, [showToast]);

  useEffect(() => {
    if (activeTab === 'new_quote' && quoteWizardStep === 'suppliers') loadSupplierSuggestions();
    if (activeTab === 'new_quote' && quoteWizardStep === 'preview') loadEmailPreviews();
    if (activeTab === 'responses') loadResponseCandidates();
  }, [activeTab, quoteWizardStep, loadSupplierSuggestions, loadEmailPreviews, loadResponseCandidates]);

  // Carrega fila de revisão de fornecedores
  const loadSupplierReviewQueue = useCallback(async () => {
    setLoadingSupplierQueue(true);
    try {
      const res = await fetch('/api/v1/purchases/suppliers/review');
      if (res.ok) {
        const data = await res.json();
        setSupplierReviewQueue(data.items || []);
        setSupplierReviewSummary(data.summary || null);
      }
    } catch (e) {
      console.error('Erro ao carregar fila de fornecedores:', e);
    } finally {
      setLoadingSupplierQueue(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'suppliers') {
      loadSupplierReviewQueue();
    }
  }, [activeTab, loadSupplierReviewQueue]);

  const handleOpenSupplierReview = useCallback(async (sup: any) => {
    setSelectedSupplierForReview(sup);
    setReviewContactEmail(sup.email || '');
    setReviewContactPhone(sup.phone || '');
    setIsSupplierReviewDrawerOpen(true);
    setLoadingSupplierLinkedItems(true);
    try {
      const res = await fetch(`/api/v1/purchases/suppliers/${sup.supplier_id}/linked-items`);
      if (res.ok) {
        const data = await res.json();
        setSupplierLinkedItems(data.items || []);
      }
    } catch (e) {
      console.error('Erro ao carregar itens vinculados:', e);
    } finally {
      setLoadingSupplierLinkedItems(false);
    }
  }, []);

  const handleSaveReviewContact = useCallback(async () => {
    if (!selectedSupplierForReview) return;
    setSavingReviewContact(true);
    try {
      const res = await fetch(`/api/v1/purchases/suppliers/${selectedSupplierForReview.supplier_id}/review-contact`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: reviewContactEmail, phone: reviewContactPhone })
      });
      if (res.ok) {
        showToast('Contato do fornecedor atualizado com sucesso.');
        setIsSupplierReviewDrawerOpen(false);
        loadSupplierReviewQueue();
      } else {
        showToast('Erro ao salvar contato.', true);
      }
    } catch {
      showToast('Erro de conexão.', true);
    } finally {
      setSavingReviewContact(false);
    }
  }, [selectedSupplierForReview, reviewContactEmail, reviewContactPhone, showToast, loadSupplierReviewQueue]);

  // Lógica de rastreabilidade de preços de compras (Price Traceability)
  const loadPriceTraceabilityData = useCallback(async () => {
    setLoadingPrices(true);
    try {
      const [refRes, sugRes, histRes] = await Promise.all([
        fetch('/api/v1/purchases/prices/references'),
        fetch('/api/v1/purchases/prices/suggestions'),
        fetch('/api/v1/purchases/prices/history'),
      ]);
      if (refRes.ok) setPriceReferences(await refRes.json());
      if (sugRes.ok) setPriceSuggestions(await sugRes.json());
      if (histRes.ok) setPriceHistory(await histRes.json());
    } catch (e) {
      console.error('Erro ao carregar dados de rastreabilidade de preços:', e);
      showToast('Falha ao carregar dados de histórico de preços.', true);
    } finally {
      setLoadingPrices(false);
    }
  }, [showToast]);

  const loadTimeline = useCallback(async (itemId: string) => {
    if (!itemId) return;
    setLoadingTimeline(true);
    try {
      const res = await fetch(`/api/v1/purchases/prices/items/${itemId}/timeline`);
      if (res.ok) {
        setTimelineData(await res.json());
      } else {
        showToast('Erro ao carregar a linha do tempo do item.', true);
      }
    } catch (e) {
      console.error(e);
      showToast('Erro ao buscar timeline.', true);
    } finally {
      setLoadingTimeline(false);
    }
  }, [showToast]);

  useEffect(() => {
    if (activeTab === 'price_history') {
      loadPriceTraceabilityData();
    }
  }, [activeTab, loadPriceTraceabilityData]);

  useEffect(() => {
    if (selectedTimelineItem) {
      loadTimeline(selectedTimelineItem);
    }
  }, [selectedTimelineItem, loadTimeline]);

  // Busca preço antigo de referência dinamicamente para o formulário
  const currentReferencePriceInfo = useMemo(() => {
    if (!confProductItemId) return null;
    let ref = priceReferences.find(
      r => r.product_item_id === confProductItemId && r.supplier_id === (confSupplierId || null)
    );
    if (!ref && confSupplierId) {
      ref = priceReferences.find(r => r.product_item_id === confProductItemId && !r.supplier_id);
    }
    return ref || null;
  }, [confProductItemId, confSupplierId, priceReferences]);

  const dynamicVariation = useMemo(() => {
    if (!currentReferencePriceInfo || confUnitPrice === '') return null;
    const oldPrice = currentReferencePriceInfo.current_unit_price;
    const newPrice = Number(confUnitPrice);
    if (oldPrice <= 0) return 0;
    return ((newPrice - oldPrice) / oldPrice) * 100;
  }, [currentReferencePriceInfo, confUnitPrice]);

  const handleCreateEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!confProductItemId) {
      showToast('É obrigatório selecionar um item de produto.', true);
      return;
    }
    if (confUnitPrice === '' || Number(confUnitPrice) <= 0) {
      showToast('É obrigatório informar o valor unitário válido.', true);
      return;
    }

    setSubmittingEvidence(true);
    try {
      // Procura a unidade de medida do item selecionado
      const selectedItem = masterItems.find(i => i.id === confProductItemId);
      const uom = selectedItem ?selectedItem.unit_of_measure : 'un';

      const res = await fetch('/api/v1/purchases/prices/evidences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: confSourceType,
          supplier_id: confSupplierId || null,
          product_item_id: confProductItemId,
          service_id: null,
          document_number: confDocNumber || null,
          document_date: confDocDate ?new Date(confDocDate).toISOString() : null,
          unit_price: Number(confUnitPrice),
          quantity: confQuantity !== '' ?Number(confQuantity) : null,
          total_amount: confTotalAmount !== '' ?Number(confTotalAmount) : null,
          currency: 'BRL',
          unit_of_measure: uom,
          payment_terms: confPaymentTerms || null,
          due_date: null,
          file_id: null,
          raw_summary: null,
          notes: confNotes || null
        })
      });

      if (res.ok) {
        showToast('Conferência de documento registrada. Sugestão de reajuste criada.');
        setConfSupplierId('');
        setConfProductItemId('');
        setConfSourceType('BOLETO');
        setConfDocNumber('');
        setConfDocDate('');
        setConfUnitPrice('');
        setConfQuantity('');
        setConfTotalAmount('');
        setConfPaymentTerms('');
        setConfNotes('');
        
        loadPriceTraceabilityData();
        setPriceSubTab('suggestions');
      } else {
        const err = await res.json();
        showToast(`Erro ao criar evidência: ${err.detail || 'Tente novamente.'}`, true);
      }
    } catch (e) {
      console.error(e);
      showToast('Erro ao conectar com o servidor.', true);
    } finally {
      setSubmittingEvidence(false);
    }
  };

  const handleApproveSuggestion = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/purchases/prices/suggestions/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ review_notes: 'Aprovado pelo Gestor' })
      });
      if (res.ok) {
        showToast('Atualização de preço de referência aprovada com sucesso!');
        loadPriceTraceabilityData();
      } else {
        const err = await res.json();
        showToast(`Erro ao aprovar: ${err.detail}`, true);
      }
    } catch (e) {
      console.error(e);
      showToast('Erro ao processar aprovação.', true);
    }
  };

  const handleRejectSuggestionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectingSuggestionId) return;
    if (!rejectReason.trim()) {
      showToast('Por favor, informe a justificativa da rejeição.', true);
      return;
    }

    try {
      const res = await fetch(`/api/v1/purchases/prices/suggestions/${rejectingSuggestionId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ review_notes: rejectReason.trim() })
      });
      if (res.ok) {
        showToast('Sugestão de preço rejeitada.');
        setIsRejectModalOpen(false);
        setRejectReason('');
        setRejectingSuggestionId(null);
        loadPriceTraceabilityData();
      } else {
        const err = await res.json();
        showToast(`Erro ao rejeitar: ${err.detail}`, true);
      }
    } catch (e) {
      console.error(e);
      showToast('Erro ao processar rejeição.', true);
    }
  };

  const loadRequestDetail = useCallback(async (id: string) => {
    setLoadingDetail(true);
    try {
      const res = await fetch(`/api/v1/purchases/requests/${id}`);
      if (res.ok) {
        setSelectedRequest(await res.json());
      } else {
        showToast('Erro ao carregar detalhes da requisição.', true);
      }
    } catch (e) {
      showToast('Falha de conexão.', true);
    } finally {
      setLoadingDetail(false);
    }
  }, [showToast]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requestId = params.get('request') || params.get('request_id') || params.get('need') || params.get('id');
    if (!requestId) return;
    setActiveTab('overview');
    setPurchaseFilter('all');
    loadRequestDetail(requestId);
  }, [loadRequestDetail]);

  const handleSelectOption = useCallback(async (itemId: string, optionId: string) => {
    try {
      const res = await fetch(`/api/v1/purchases/items/${itemId}/options/${optionId}/select`, {
        method: 'POST'
      });
      if (res.ok) {
        showToast('Opção selecionada com sucesso!');
        if (selectedRequest) {
          loadRequestDetail(selectedRequest.id);
        }
      } else {
        const err = await res.json();
        showToast(err.detail || 'Erro ao selecionar opção.', true);
      }
    } catch (e) {
      showToast('Erro de rede ao selecionar opção.', true);
    }
  }, [loadRequestDetail, selectedRequest, showToast]);

  const handleCreateIntelligentNeed = useCallback(async () => {
    if (parsedLines.length === 0) {
      showToast('Adicione pelo menos um item à compra.', true);
      return;
    }
    
    setSavingRequest(true);
    const idempotencyKey = (window.crypto?.randomUUID?.() || `purchase-${Date.now()}-${Math.random().toString(16).slice(2)}`);
    const completeCreatedRequest = async (created: any) => {
      showToast('Compra inteligente criada com sucesso!');
      setParsedLines([]);
      setPastedListText('');
      setReqTitle('');
      setReqDesc('');
      setReqJustify('');
      setReqPriority('NORMAL');
      setReqDepartment('');
      setReqNeededBy('');
      
      await loadAll();
      
      setPurchaseFilter('all');
      setSelectedRequest(created);
      setActiveTab('overview');
      setQueryParams({ request: created.id, quote: null, step: null, filter: null }, { replace: false });
    };
    try {
      const payload = {
        idempotency_key: idempotencyKey,
        title: reqTitle.trim() || inferPurchaseTitleFromLines(parsedLines),
        description: reqDesc || null,
        justification: reqJustify || null,
        priority: reqPriority,
        urgency: reqPriority,
        department: reqDepartment || null,
        needed_by: reqNeededBy ?new Date(reqNeededBy).toISOString() : null,
        items: parsedLines.map(line => ({
          stock_catalog_item_id: line.suggested_stock_catalog_item_id || null,
          free_text_description: line.description,
          quantity: line.quantity,
          unit_of_measure: line.unit_of_measure || 'un',
          specifications: line.suggested_specification || line.classification_message || '',
          estimated_unit_price: line.budget_limit || 0,
          budget_limit: line.budget_limit || null,
          destination: line.destination || null,
          department: line.department || null,
          classification: line.purchase_type ?line.purchase_type.toUpperCase() : 'EXTERNAL',
          classification_confidence: typeof line.match_score === 'number' ?line.match_score : null,
          requires_approval: Boolean(line.requires_approval)
        }))
      };
      
      const res = await fetch('/api/v1/purchases/needs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        const created = await res.json();
        await completeCreatedRequest(created);
      } else {
        const err = await res.json();
        showToast(err.detail || 'Erro ao criar necessidade.', true);
      }
    } catch (e) {
      try {
        const lookup = await fetch(`/api/v1/purchases/requests/by-idempotency/${encodeURIComponent(idempotencyKey)}`);
        const lookupData = await lookup.json().catch(() => ({}));
        if (lookup.ok && lookupData.request) {
          await completeCreatedRequest(lookupData.request);
          return;
        }
      } catch (_) {
        // Mantem a mensagem humana abaixo.
      }
      showToast('Nao consegui confirmar a resposta agora. Se a compra tiver sido criada, ela aparecera na fila ao atualizar.', true);
    } finally {
      setSavingRequest(false);
    }
  }, [parsedLines, reqTitle, reqDesc, reqJustify, reqPriority, reqDepartment, reqNeededBy, loadAll, showToast]);

  const handlePlaceOrderSubmit = useCallback(async () => {
    if (!selectedRequest) return;
    if (finalValue === '') {
      showToast('Informe o valor final da compra.', true);
      return;
    }
    
    try {
      const payload = {
        final_value: parseFloat(finalValue.toString()),
        shipping_price: shippingPrice !== '' ?parseFloat(shippingPrice.toString()) : 0.0,
        order_number: orderNumber.trim() || `ORD-${Math.floor(Math.random()*1000000)}`,
        payment_method: paymentMethod,
        notes: orderNotes.trim() || null
      };
      
      const res = await fetch(`/api/v1/purchases/needs/${selectedRequest.id}/place-order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        showToast('Pedido registrado com sucesso!');
        setIsRegisteringOrder(false);
        setFinalValue('');
        setShippingPrice('');
        setOrderNumber('');
        setOrderNotes('');
        
        await loadAll();
        loadRequestDetail(selectedRequest.id);
      } else {
        const err = await res.json();
        showToast(err.detail || 'Erro ao registrar pedido.', true);
      }
    } catch (e) {
      showToast('Erro de rede ao registrar pedido de compra.', true);
    }
  }, [selectedRequest, finalValue, shippingPrice, orderNumber, paymentMethod, orderNotes, loadAll, loadRequestDetail, showToast]);

  const handleReceiveDeliverySubmit = useCallback(async () => {
    if (!selectedRequest) return;
    
    try {
      const payload = {
        items: deliveryItemsState.map(i => ({
          item_id: i.item_id,
          quantity_received: parseFloat(i.quantity_received.toString()),
          is_damaged: i.is_damaged,
          deviation_notes: i.deviation_notes || null,
          save_in_catalog: i.save_in_catalog
        })),
        notes: deliveryNotes.trim() || null
      };
      
      const res = await fetch(`/api/v1/purchases/needs/${selectedRequest.id}/receive-delivery`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        showToast('Recebimento registrado e estoque atualizado com sucesso!');
        setIsReceiving(false);
        setDeliveryItemsState([]);
        setDeliveryNotes('');
        
        await loadAll();
        loadRequestDetail(selectedRequest.id);
      } else {
        const err = await res.json();
        showToast(err.detail || 'Erro ao registrar recebimento.', true);
      }
    } catch (e) {
      showToast('Erro de rede ao registrar recebimento da entrega.', true);
    }
  }, [selectedRequest, deliveryItemsState, deliveryNotes, loadAll, loadRequestDetail, showToast]);

  const renderIntelligentWorkContent = (req: PurchaseRequest) => {
    if (searchActiveItem) {
      return renderExternalSearchPanel(req);
    }
    if (isReceiving && req.status === 'ORDERED') {
      return renderDeliveryReceivePanel(req);
    }
    if (isRegisteringOrder && req.status === 'APPROVED') {
      return renderPlaceOrderPanel(req);
    }

    switch (req.status) {
      case 'DRAFT':
      case 'REQUESTED':
        return renderDraftItemsConfirmationPanel(req);

      case 'PENDING_APPROVAL':
        return renderPendingApprovalPanel(req);

      case 'APPROVAL_REQUIRED':
        return renderApprovalItemOptionPanel(req);

      case 'RFQ_PREPARING':
      case 'RFQ_SENT':
      case 'QUOTES_RECEIVED':
      case 'COMPARING':
        return renderQuotesComparisonPanel(req);

      case 'APPROVED':
        return renderPlaceOrderPanel(req);

      case 'ORDERED':
        return renderDeliveryReceivePanel(req);

      default:
        return (
          <div style={{ padding: 16 }}>
            <h3>Status da Compra: {STATUS_LABELS[req.status] || req.status}</h3>
            <p>O fluxo correspondente a este status ainda não está configurado.</p>
          </div>
        );
    }
  };

  const loadRFQDetails = useCallback(async (rfqId: string) => {
    setLoadingRFQ(true);
    setRfqSuppliers([]);
    setRfqDrafts([]);
    setRfqComparison(null);
    try {
      const [rfqRes, draftsRes, compRes] = await Promise.all([
        fetch(`/api/v1/purchases/rfqs/${rfqId}`),
        fetch(`/api/v1/purchases/rfqs/${rfqId}/drafts`),
        fetch(`/api/v1/purchases/rfqs/${rfqId}/comparison`),
      ]);
      if (rfqRes.ok) {
        const rfqData = await rfqRes.json();
        // rfq_suppliers estão em rfqData se incluídos, senão buscar separado
        setSelectedRFQ(rfqData);
      }
      if (draftsRes.ok) setRfqDrafts(await draftsRes.json());
      if (compRes.ok) setRfqComparison(await compRes.json());
    } catch (e) {
      console.error('Erro ao carregar cotação:', e);
    } finally {
      setLoadingRFQ(false);
    }
  }, []);

  // -------------------------------------------------------------------------
  // Ações — Requisição
  // -------------------------------------------------------------------------
  const handleOpenRequestRow = (req: PurchaseRequest) => {
    setSelectedRequest(req);
    setSelectedRFQ(null);
    setRfqDrafts([]);
    setRfqComparison(null);
    setDrawerOpen(true);
    setActiveTab('overview');
    setQueryParams({ request: req.id, quote: null, step: null }, { replace: false });
    loadRequestDetail(req.id);
  };

  const handleSubmitRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reqTitle.trim()) { showToast('Informe o título da requisição.', true); return; }
    const hasEmptyItem = reqItems.some(i =>
      !i.free_text_description.trim() && !i.item_id && !i.service_id
    );
    if (hasEmptyItem) { showToast('Todos os itens precisam ter descrição ou vínculo ao cadastro mestre.', true); return; }

    setSavingRequest(true);
    try {
      const payload = {
        title: reqTitle.trim(),
        description: reqDesc || null,
        justification: reqJustify || null,
        priority: reqPriority,
        urgency: reqPriority,
        department: reqDepartment || null,
        needed_by: reqNeededBy ?new Date(reqNeededBy).toISOString() : null,
        items: reqItems.map(i => ({
          item_id: i.item_id || null,
          service_id: i.service_id || null,
          stock_catalog_item_id: i.stock_catalog_item_id || null,
          free_text_description: i.free_text_description || null,
          quantity: i.quantity,
          unit_of_measure: i.unit_of_measure || 'un',
          specifications: i.specifications || null,
          estimated_unit_price: i.estimated_unit_price || null,
        }))
      };
      const res = await fetch('/api/v1/purchases/requests', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      if (res.ok) {
        const created: PurchaseRequest = await res.json();
        showToast('Requisição criada com sucesso!');
        setIsRequestModalOpen(false);
        setReqTitle(''); setReqDesc(''); setReqJustify(''); setReqPriority('NORMAL'); setReqNeededBy(''); setReqDepartment('');
        setReqItems([{ free_text_description: '', quantity: 1, unit_of_measure: 'un', specifications: '', estimated_unit_price: 0, itemType: 'freetext' }]);
        await loadAll();
        // Abre o detalhe automaticamente
        setDrawerOpen(true);
        loadRequestDetail(created.id);
      } else {
        const err = await res.json();
        showToast(`Erro: ${err.detail || 'Verifique os dados.'}`, true);
      }
    } catch (e) {
      showToast('Erro de conexão.', true);
    } finally {
      setSavingRequest(false);
    }
  };

  const handleSendToApproval = async (id: string) => {
    try {
      const res = await fetch(`/api/v1/purchases/requests/${id}/send-to-approval`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        showToast(
          data.status === 'APPROVED'
            ?'Aprovada automaticamente (valor abaixo de R$ 1.000,00)!'
            : 'Enviada para análise financeira na Central de Aprovações!'
        );
        loadRequestDetail(id);
        loadAll();
      } else {
        const err = await res.json();
        showToast(`Erro: ${err.detail}`, true);
      }
    } catch { showToast('Erro de rede.', true); }
  };

  const handleCancelRequest = async (id: string) => {
    showConfirm({
      title: 'Cancelar Requisição',
      message: 'Deseja cancelar esta requisição permanentemente?',
      confirmText: 'Sim, Cancelar',
      cancelText: 'Voltar',
      variant: 'danger',
      onConfirm: async () => {
        closeConfirm();
        try {
          const res = await fetch(`/api/v1/purchases/requests/${id}/cancel`, { method: 'POST' });
          if (res.ok) {
            showToast('Requisição cancelada.');
            loadRequestDetail(id);
            loadAll();
          } else {
            const err = await res.json();
            showToast(`Erro: ${err.detail}`, true);
          }
        } catch { showToast('Erro de rede.', true); }
      }
    });
  };

  const handleSendRFQ = async () => {
    if (!selectedRFQ) return;
    setSendingRFQ(true);
    try {
      const res = await fetch(`/api/v1/purchases/rfqs/${selectedRFQ.id}/send`, { method: 'POST' });
      if (res.ok) {
        showToast('Cotação enviada com sucesso para todos os fornecedores!');
        loadRFQDetails(selectedRFQ.id);
      } else {
        const err = await res.json();
        showToast(`Erro ao enviar: ${err.detail || 'Verifique as configurações SMTP.'}`, true);
      }
    } catch {
      showToast('Erro de conexão.', true);
    } finally {
      setSendingRFQ(false);
    }
  };

  const handleResendSupplierEmail = async (supplierId: string) => {
    if (!selectedRFQ) return;
    setResendingSupplierId(supplierId);
    try {
      const res = await fetch(`/api/v1/purchases/rfqs/${selectedRFQ.id}/suppliers/${supplierId}/resend`, { method: 'POST' });
      if (res.ok) {
        showToast('E-mail de cotação reenviado com sucesso!');
        loadRFQDetails(selectedRFQ.id);
      } else {
        const err = await res.json();
        showToast(`Erro ao reenviar: ${err.detail || 'Falha no SMTP.'}`, true);
      }
    } catch {
      showToast('Erro de conexão.', true);
    } finally {
      setResendingSupplierId(null);
    }
  };

  const handleChooseSupplier = async (quoteResponseId: string) => {
    if (!selectedRFQ) return;
    showConfirm({
      title: 'Escolher Proposta Vencedora',
      message: 'Deseja homologar esta proposta como vencedora da cotação?Os preços dos itens serão atualizados como referências ativas.',
      confirmText: 'Confirmar e Atualizar Preços',
      cancelText: 'Cancelar',
      onConfirm: async () => {
        closeConfirm();
        setChoosingSupplierId(quoteResponseId);
        try {
          const res = await fetch(`/api/v1/purchases/rfqs/${selectedRFQ.id}/choose-supplier`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quote_response_id: quoteResponseId })
          });
          if (res.ok) {
            showToast('Proposta homologada e preços de referência atualizados com sucesso!');
            if (selectedRequest) {
              loadRequestDetail(selectedRequest.id);
            }
            loadAll();
            setDrawerOpen(false);
          } else {
            const err = await res.json();
            showToast(`Erro: ${err.detail}`, true);
          }
        } catch {
          showToast('Erro de rede.', true);
        } finally {
          setChoosingSupplierId(null);
        }
      }
    });
  };

  // -------------------------------------------------------------------------
  // Acoes - cotacao
  // -------------------------------------------------------------------------
  const handleOpenCreateRFQ = () => {
    if (!selectedRequest) return;
    setRfqTitle(`Cotação - ${selectedRequest.title}`);
    setRfqDeadline('');
    setRfqTemplate('');
    setIsRFQModalOpen(true);
  };

  const handleSubmitRFQ = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRequest) return;
    setSavingRFQ(true);
    try {
      const payload = {
        title: rfqTitle.trim(),
        deadline: rfqDeadline ?new Date(rfqDeadline).toISOString() : null,
        message_template: rfqTemplate || null,
      };
      const res = await fetch(`/api/v1/purchases/requests/${selectedRequest.id}/rfqs`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      if (res.ok) {
        const newRFQ: PurchaseRFQ = await res.json();
        showToast('Cotação preparada. Agora revise os fornecedores.');
        setIsRFQModalOpen(false);
        await loadRequestDetail(selectedRequest.id);
        setSelectedRFQ(newRFQ);
        loadRFQDetails(newRFQ.id);
      } else {
        const err = await res.json();
        showToast(`Erro: ${err.detail}`, true);
      }
    } catch { showToast('Erro de conexão.', true); }
    finally { setSavingRFQ(false); }
  };

  const handleSelectRFQ = (rfq: PurchaseRFQ) => {
    setSelectedRFQ(rfq);
    setRfqTab('suppliers');
    loadRFQDetails(rfq.id);
  };

  // -------------------------------------------------------------------------
  // Acoes - cotacao
  // -------------------------------------------------------------------------
  const handleOpenAddSupplier = () => {
    setSelectedSupplierId(masterSuppliers.length > 0 ?masterSuppliers[0].id : '');
    setSupplierContactEmail('');
    setIsAddSupplierToRFQOpen(true);
  };

  const handleAddSupplierToRFQ = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRFQ || !selectedSupplierId) { showToast('Selecione um fornecedor.', true); return; }
    setAddingSupplier(true);
    try {
      const payload = { supplier_id: selectedSupplierId, contact_email: supplierContactEmail || null };
      const res = await fetch(`/api/v1/purchases/rfqs/${selectedRFQ.id}/suppliers`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
      });
      if (res.ok) {
        showToast('Fornecedor adicionado à cotação.');
        setIsAddSupplierToRFQOpen(false);
        loadRFQDetails(selectedRFQ.id);
      } else {
        const err = await res.json();
        showToast(`Erro: ${err.detail || 'Fornecedor já pode estar nesta cotação.'}`, true);
      }
    } catch { showToast('Erro de conexão.', true); }
    finally { setAddingSupplier(false); }
  };

  const handleGenerateDrafts = async () => {
    if (!selectedRFQ) return;
    setGeneratingDrafts(true);
    try {
      const res = await fetch(`/api/v1/purchases/rfqs/${selectedRFQ.id}/generate-drafts`, { method: 'POST' });
      if (res.ok) {
        showToast('Rascunhos de mensagem gerados com sucesso!');
        setRfqTab('drafts');
        loadRFQDetails(selectedRFQ.id);
      } else {
        const err = await res.json();
        showToast(`Erro: ${err.detail}`, true);
      }
    } catch { showToast('Erro de conexão.', true); }
    finally { setGeneratingDrafts(false); }
  };

  const handleRequestSendApproval = async () => {
    if (!selectedRFQ) return;
    showConfirm({
      title: 'Liberar envio da cotação',
      message: 'O Portal vai validar a cotação e liberar o envio apenas para os fornecedores selecionados. Nenhum fornecedor novo será incluído automaticamente.',
      confirmText: 'Liberar envio',
      cancelText: 'Revisar antes',
      variant: 'warning',
      onConfirm: async () => {
        closeConfirm();
        setRequestingApproval(true);
        try {
          const res = await fetch(`/api/v1/purchases/rfqs/${selectedRFQ.id}/request-send-approval`, { method: 'POST' });
          if (res.ok) {
            showToast('Cotação liberada para envio direto. Revise os rascunhos e clique em Enviar cotação.');
          } else {
            const err = await res.json();
            showToast(`Erro: ${err.detail}`, true);
          }
        } catch { showToast('Erro de conexao.', true); }
        finally { setRequestingApproval(false); }
      }
    });
  };

  const getStatusColor = (status: string) => {
    const map: Record<string, string> = {
      DRAFT: 'var(--text-muted)', REQUESTED: '#60a5fa', PENDING_APPROVAL: '#fbbf24',
      APPROVED: '#34d399', RFQ_PREPARING: '#a78bfa', RFQ_SENT: '#818cf8',
      QUOTES_RECEIVED: '#2dd4bf', COMPARING: '#f472b6', ORDERED: '#34d399',
      REJECTED: '#f87171', CANCELLED: '#9ca3af',
    };
    return map[status] || 'var(--text-muted)';
  };

  const getPriorityColor = (p: string) => {
    const map: Record<string, string> = { LOW: '#6b7280', NORMAL: '#60a5fa', HIGH: '#f59e0b', URGENT: '#ef4444' };
    return map[p] || '#6b7280';
  };

  const responseConfidenceLabel = (confidence: string) => {
    if (confidence === 'high') return 'Alta';
    if (confidence === 'check') return 'Confira';
    return 'Baixa';
  };

  const responseStatusLabel = (candidate: ResponseCandidate) => {
    if (candidate.candidate_status === 'needs_review') return 'Para revisar';
    if (candidate.candidate_status === 'suggested') return 'Sugestao para conferir';
    if (candidate.candidate_status === 'unidentified') return 'Identificar cotacao';
    if (candidate.candidate_status === 'confirmed') return 'Vinculada';
    if (candidate.candidate_status === 'rejected') return 'Descartada';
    if (candidate.candidate_status === 'ignored') return 'Ignorada';
    return candidate.human_status || 'Resposta recebida';
  };

  const parsedLineTypeLabel = (line: ParsedQuoteLine) => {
    if (line.purchase_type === 'internal') return 'Item do Estoque';
    if (line.purchase_type === 'ambiguous') return 'Precisa revisar';
    return 'Compra externa';
  };

  const parsedLineStatusText = (line: ParsedQuoteLine) => {
    if (line.purchase_type === 'internal') {
      return line.classification_message || 'Correspondência segura no Estoque.';
    }
    if (line.purchase_type === 'ambiguous' || line.confidence === 'low' || line.match_status === 'needs_confirmation') {
      return line.classification_message || 'Confira esta sugestão: possível item interno, confirme antes de vincular.';
    }
    return line.classification_message || 'Nenhum item interno compatível foi encontrado. Vou tratar como compra externa.';
  };

  const purchaseTypeForRequest = (request: PurchaseRequest) => {
    const hasInternal = request.items.some(item => item.stock_catalog_item_id || item.source_type === 'stock_catalog');
    const hasExternal = request.items.some(item => !item.stock_catalog_item_id && item.source_type !== 'stock_catalog');
    if (hasInternal && hasExternal) return 'mista';
    if (hasInternal) return 'interna';
    return 'externa';
  };

  const requestDisplayTitle = (request: PurchaseRequest) => {
    const genericTitle = !request.title || /^nova compra$/i.test(request.title.trim()) || /^compra de itens informados$/i.test(request.title.trim());
    if (!genericTitle) return request.title;
    const itemNames = request.items
      .map(item => item.description || item.free_text_description)
      .filter(Boolean)
      .slice(0, 2);
    if (itemNames.length === 0) return 'Necessidade aguardando descrição';
    return itemNames.join(' + ');
  };

  const inferPurchaseTitleFromLines = (lines: ParsedQuoteLine[]) => {
    const itemNames = lines
      .map(line => line.purchase_type === 'internal' ?line.suggested_display_name || line.description : line.description)
      .map(name => (name || '').trim())
      .filter(Boolean)
      .slice(0, 2);
    if (itemNames.length === 0) return 'Necessidade aguardando descrição';
    return itemNames.join(' + ');
  };

  const requestEstimatedValue = (request: PurchaseRequest) => {
    if (typeof request.estimated_total === 'number') return request.estimated_total;
    return request.items.reduce((sum, item) => sum + ((item.estimated_unit_price || 0) * (item.quantity || 0)), 0);
  };

  const nextPurchaseAction = (request: PurchaseRequest) => {
    const type = purchaseTypeForRequest(request);
    if (request.status === 'PENDING_APPROVAL' || request.status === 'APPROVAL_REQUIRED') {
      return {
        label: 'Acompanhar aprovação',
        description: 'A compra está aguardando decisão formal antes de seguir.',
        action: 'Abrir aprovação',
      };
    }
    if (request.status === 'APPROVED') {
      return {
        label: 'Pronta para comprar',
        description: 'Revise a opção aprovada, registre o pedido e acompanhe a entrega.',
        action: 'Registrar compra',
      };
    }
    if (request.status === 'ORDERED') {
      return {
        label: 'Acompanhar entrega',
        description: 'Pedido registrado. Atualize recebimento total, parcial ou divergente.',
        action: 'Registrar recebimento',
      };
    }
    if (request.rfqs?.length) {
      return {
        label: 'Revisar fornecedores',
        description: 'Há cotação interna em preparo ou aguardando retorno.',
        action: 'Abrir cotação',
      };
    }
    if (type === 'externa') {
      return {
        label: 'Analisar opções externas',
        description: 'Adicione links ou uma opção manual. A pesquisa automática ainda depende de conector real.',
        action: 'Adicionar opção',
      };
    }
    if (type === 'mista') {
      return {
        label: 'Separar fluxos',
        description: 'Itens internos seguem fornecedores; itens externos precisam de links ou opções manuais.',
        action: 'Revisar itens',
      };
    }
    return {
      label: 'Revisar fornecedores',
      description: 'O Portal pode sugerir fornecedores internos para os itens do Estoque.',
      action: 'Preparar cotação',
    };
  };

  const queueRequests = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    return requests.filter(request => {
      const searchable = [
        requestDisplayTitle(request),
        request.title,
        request.status,
        request.priority,
        purchaseTypeForRequest(request),
        ...request.items.map(item => `${item.description || ''} ${item.free_text_description || ''} ${item.specifications || ''}`),
      ].join(' ').toLowerCase();
      if (term && !searchable.includes(term)) return false;
      return true;
    });
  }, [requests, searchTerm]);

  const indicatorItems = useMemo(() => [
    {
      key: 'all' as const,
      label: 'Todas',
      value: overview?.queue_counts?.all ?? summary.total_requests ?? requests.length,
      icon: <List size={18} />,
    },
    {
      key: 'attention' as const,
      label: 'Precisa da sua atenção',
      value: overview?.queue_counts?.attention ?? requests.filter(request => ['DRAFT', 'REQUESTED', 'RFQ_PREPARING', 'QUOTES_RECEIVED', 'COMPARING'].includes(request.status)).length,
      icon: <AlertTriangle size={18} />,
    },
    {
      key: 'suppliers' as const,
      label: 'Aguardando fornecedores',
      value: overview?.queue_counts?.suppliers ?? requests.filter(request => ['RFQ_PREPARING', 'RFQ_SENT', 'QUOTES_RECEIVED'].includes(request.status) || Boolean(request.rfqs?.length)).length,
      icon: <Users size={18} />,
    },
    {
      key: 'approval' as const,
      label: 'Aguardando aprovação',
      value: overview?.queue_counts?.approval ?? summary.pending_approval,
      icon: <ShieldCheck size={18} />,
    },
    {
      key: 'ready' as const,
      label: 'Prontas para comprar',
      value: overview?.queue_counts?.ready ?? requests.filter(request => request.status === 'APPROVED').length,
      icon: <Check size={18} />,
    },
    {
      key: 'delivery' as const,
      label: 'Entregas pendentes',
      value: overview?.queue_counts?.delivery ?? requests.filter(request => request.status === 'ORDERED').length,
      icon: <Truck size={18} />,
    },
  ], [overview?.queue_counts, requests, summary.pending_approval, summary.total_requests]);

  const emptyQueueCopy = useMemo(() => {
    if (purchaseFilter === 'attention') {
      return {
        title: 'Nada precisa da sua atenção agora',
        description: 'Quando houver interpretação pendente, fornecedor para revisar ou resposta para comparar, aparece aqui.',
      };
    }
    if (purchaseFilter === 'suppliers') {
      return {
        title: 'Nenhuma compra aguardando fornecedor',
        description: 'Cotações internas em preparo ou aguardando resposta aparecerão neste filtro.',
      };
    }
    if (purchaseFilter === 'approval') {
      return {
        title: 'Nenhuma compra aguardando aprovação',
        description: 'Pedidos enviados para decisão formal aparecerão aqui.',
      };
    }
    if (purchaseFilter === 'ready') {
      return {
        title: 'Nenhuma compra pronta para executar',
        description: 'Quando houver aprovação ou opção escolhida, a compra aparece aqui.',
      };
    }
    if (purchaseFilter === 'delivery') {
      return {
        title: 'Nenhuma entrega pendente',
        description: 'Pedidos já registrados e aguardando recebimento aparecerão aqui.',
      };
    }
    return {
      title: 'Nenhuma necessidade de compra',
      description: 'Use Nova compra para informar o que precisa comprar.',
    };
  }, [purchaseFilter]);

  // Limpa seleção incompatível com o filtro ativo
  useEffect(() => {
    if (activeTab === 'overview' && selectedRequest && purchaseFilter !== 'all') {
      const isStillInQueue = queueRequests.some(req => req.id === selectedRequest.id);
      if (!isStillInQueue) {
        setSelectedRequest(null);
        setActiveQuote(null);
      }
    }
  }, [activeTab, purchaseFilter, queueRequests, selectedRequest]);

  useEffect(() => {
    if (!selectedRequest) return;
    const freshRequest = requests.find(req => req.id === selectedRequest.id);
    if (!freshRequest) {
      setSelectedRequest(null);
      setActiveQuote(null);
      return;
    }
    if (freshRequest !== selectedRequest) {
      setSelectedRequest(freshRequest);
    }
  }, [requests, selectedRequest]);

  // -------------------------------------------------------------------------
  // Sub-painéis adaptativos da Central Inteligente
  // -------------------------------------------------------------------------
  
  const renderDeliveryReceivePanel = (req: PurchaseRequest) => {
    return (
      <DeliveryPanel
        req={req}
        deliveryItemsState={deliveryItemsState}
        setDeliveryItemsState={setDeliveryItemsState}
        deliveryNotes={deliveryNotes}
        setDeliveryNotes={setDeliveryNotes}
        onSubmit={handleReceiveDeliverySubmit}
        onCancel={() => { setIsReceiving(false); setDeliveryItemsState([]); }}
      />
    );
  };

  const renderPlaceOrderPanel = (req: PurchaseRequest) => {
    return (
      <PurchaseRegistrationPanel
        req={req}
        finalValue={finalValue}
        setFinalValue={setFinalValue}
        shippingPrice={shippingPrice}
        setShippingPrice={setShippingPrice}
        orderNumber={orderNumber}
        setOrderNumber={setOrderNumber}
        paymentMethod={paymentMethod}
        setPaymentMethod={setPaymentMethod}
        orderNotes={orderNotes}
        setOrderNotes={setOrderNotes}
        onSubmit={handlePlaceOrderSubmit}
        onCancel={() => setIsRegisteringOrder(false)}
        fmt={fmt}
      />
    );
  };

  const renderApprovalItemOptionPanel = (req: PurchaseRequest) => {
    return (
      <ApprovalSelectionPanel
        req={req}
        onSelectOption={handleSelectOption}
        onSendToApproval={handleSendToApproval}
        onNavigate={onNavigate}
        loadRequestDetail={loadRequestDetail}
        fmt={fmt}
        statusLabels={STATUS_LABELS}
      />
    );
  };

  const renderPendingApprovalPanel = (req: PurchaseRequest) => {
    return (
      <ApprovalSelectionPanel
        req={req}
        onSelectOption={handleSelectOption}
        onSendToApproval={handleSendToApproval}
        onNavigate={onNavigate}
        loadRequestDetail={loadRequestDetail}
        fmt={fmt}
        statusLabels={STATUS_LABELS}
      />
    );
  };

  const handleAddOptionManually = async (itemId: string, opt: any) => {
    const unitPrice = Number(opt.unit_price);
    const shippingValue = Number(opt.shipping_price || 0);
    if (!String(opt.title || '').trim() || !String(opt.store_name || '').trim() || !Number.isFinite(unitPrice) || unitPrice <= 0) {
      showToast('Informe fornecedor/loja, produto e preco valido para cadastrar a opcao.', true);
      return;
    }
    try {
      const res = await fetch(`/api/v1/purchases/items/${itemId}/options`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_type: 'EXTERNAL_MARKET',
          store_name: opt.store_name,
          title: opt.title,
          unit_price: unitPrice,
          shipping_price: shippingValue,
          total_price: Number(opt.total_price || unitPrice + shippingValue),
          delivery_estimate: opt.delivery_estimate,
          availability: true,
          product_url: opt.product_url,
          image_url: opt.image_url,
          search_session_id: activeResearchSession?.id || null,
          source_domain: opt.source_domain || null,
          evidence_level: opt.evidence_level || 'manual',
          captured_method: opt.captured_method || 'manual_entry',
          verification_status: opt.verification_status || 'DISCOVERED',
          verification_summary: opt.verification_summary || 'Opcao manual; confirme link, frete e disponibilidade antes de recomendar.'
        })
      });
      if (res.ok) {
        const createdOption = await res.json();
        await handleSelectOption(itemId, createdOption.id);
        setManualOptionDraft({ store_name: '', title: '', unit_price: '', shipping_price: '', delivery_estimate: '', product_url: '' });
        setSearchActiveItem(null);
        setActiveResearchSession(null);
      } else {
        const err = await res.json();
        showToast(err.detail || 'Erro ao salvar opção.', true);
      }
    } catch (e) {
      showToast('Erro de rede ao salvar opção comercial.', true);
    }
  };

  const renderExternalSearchPanel = (req: PurchaseRequest) => {
    return (
      <ExternalSearchPanel
        searchActiveItem={searchActiveItem}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        searchingExternal={searchingExternal}
        handleExternalSearch={handleExternalSearch}
        searchError={searchError}
        searchResults={searchResults}
        handleAddOptionManually={handleAddOptionManually}
        manualOptionDraft={manualOptionDraft}
        setManualOptionDraft={setManualOptionDraft}
        linkImportUrl={linkImportUrl}
        onLinkImportUrlChange={setLinkImportUrl}
        importingLink={importingLink}
        handleImportLink={handleImportLink}
        cartImportUrl={cartImportUrl}
        onCartImportUrlChange={setCartImportUrl}
        importingCart={importingCart}
        handleImportCart={handleImportCart}
        researchSession={activeResearchSession}
        onRefreshResearchSession={refreshActiveResearchSession}
        onBack={() => {
          setSearchActiveItem(null);
          setActiveResearchSession(null);
        }}
        fmt={fmt}
      />
    );
  };

  const renderQuotesComparisonPanel = (req: PurchaseRequest) => {
    return (
      <div className="purchase-work-scroll" style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '16px 0' }}>
        <div className="purchase-current-task">
          <span>Próxima ação</span>
          <strong>Comparar propostas dos fornecedores</strong>
          <p>Revise respostas, pendências e mensagens antes de escolher a melhor opção.</p>
        </div>
        
        <div className="glass-card" style={{ padding: 12, border: '1px solid var(--border-color)', borderRadius: 8 }}>
          <h4 style={{ fontSize: 13, fontWeight: 'bold', margin: '0 0 8px 0' }}>Cotações em andamento</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {(req.rfqs || []).map(rfq => (
              <div key={rfq.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                <span>{rfq.title}</span>
                <Badge variant={rfq.status === 'RFQ_SENT' ?'success' : 'neutral'}>
                  {rfq.status === 'RFQ_SENT' ?'Enviada' : 'Rascunho'}
                </Badge>
              </div>
            ))}
            {(req.rfqs || []).length === 0 && (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>Nenhuma cotação formal iniciada.</div>
            )}
          </div>
        </div>
        
        <div className="glass-card" style={{ padding: 12, border: '1px solid var(--success-border)', background: 'var(--success-surface)', borderRadius: 8 }}>
          <h4 style={{ fontSize: 12, fontWeight: 'bold', color: 'var(--success-text)', margin: '0 0 4px 0' }}>Recomendação do Portal</h4>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
            Recomendamos prosseguir com a cotação formal para os fornecedores internos catalogados ou validar alternativas externas.
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 10 }}>
          <Button variant="primary" onClick={() => handleOpenRequestRow(req)}>
            Gerenciar cotações e mensagens
          </Button>
        </div>
      </div>
    );
  };

  const renderDraftItemsConfirmationPanel = (req: PurchaseRequest) => {
    return (
      <ParsedItemsReview
        req={req}
        onRevisarInterno={() => {
          setPurchaseFilter('suppliers');
          setSelectedRequest(req);
        }}
        onPesquisarExterno={(item) => {
          setSearchActiveItem(item);
          setSearchQuery(item.description || item.free_text_description || '');
          setSearchResults([]);
          setSearchError(null);
          setActiveResearchSession(null);
        }}
        onResolveAmbiguity={async (itemId, type) => {
          try {
            await fetch(`/api/v1/purchases/requests/${req.id}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                items: req.items.map(i => i.id === itemId ?{ id: i.id, classification: type } : { id: i.id })
              })
            });
            loadRequestDetail(req.id);
          } catch (e) {
            console.error(e);
            showToast('Erro ao resolver ambiguidade.', true);
          }
        }}
        onSendToApproval={handleSendToApproval}
        fmt={fmt}
      />
    );
  };

  const renderAdaptiveCentral = () => {
    const focusedRequest = selectedRequest && queueRequests.some(req => req.id === selectedRequest.id)
      ?selectedRequest
      : queueRequests[0] || null;
    const primaryAttention = undefined as PurchaseAttentionItem | undefined;
    const queue = queueRequests.slice(0, 12);
    const focusedAction = focusedRequest ?nextPurchaseAction(focusedRequest) : null;
    const focusedType = focusedRequest ?purchaseTypeForRequest(focusedRequest) : null;

    return (
      <PurchaseWorkspace
        queue={queue}
        focusedRequest={focusedRequest}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        onSelectRequest={(req) => {
          setSelectedRequest(req);
          setSearchActiveItem(null);
          setIsReceiving(false);
          setIsRegisteringOrder(false);
          setDrawerOpen(false);
          setQueryParams({ request: req.id, quote: null, step: null }, { replace: false });
        }}
        purchaseFilter={purchaseFilter}
        onFilterChange={applyPurchaseFilter}
        emptyQueueCopy={emptyQueueCopy}
        requestDisplayTitle={requestDisplayTitle}
        purchaseTypeForRequest={purchaseTypeForRequest}
        nextPurchaseAction={nextPurchaseAction}
        fmtDate={fmtDate}
        priorityLabels={PRIORITY_LABELS}
        renderIntelligentWorkContent={renderIntelligentWorkContent}
        STATUS_LABELS={STATUS_LABELS}
        focusedAction={focusedAction}
        focusedType={focusedType}
        isRegisteringOrder={isRegisteringOrder}
        setIsRegisteringOrder={setIsRegisteringOrder}
        isReceiving={isReceiving}
        setIsReceiving={setIsReceiving}
        setDeliveryItemsState={setDeliveryItemsState}
        handleOpenRequestRow={handleOpenRequestRow}
        primaryAttention={primaryAttention}
        requests={requests}
        requestEstimatedValue={requestEstimatedValue}
        fmt={fmt}
        onNewPurchaseClick={() => {
          setActiveTab('new_quote');
          setQueryParams({ request: null, quote: null, step: null }, { replace: false });
        }}
      />
    );
  };

  const renderResponsesWorkspace = () => (
    <div className="responses-workspace">
      <div className="responses-header">
        <div>
          <h3 className="purchases-table-title">Respostas</h3>
          <span>Respostas recebidas por e-mail entram aqui para vinculo e revisao humana antes do comparativo.</span>
        </div>
        <Button variant="secondary" size="sm" leftIcon={<MailOpen size={14} />} onClick={loadResponseCandidates} disabled={loadingResponses}>
          {loadingResponses ?'Atualizando...' : 'Atualizar'}
        </Button>
      </div>

      {loadingResponses ?(
        <div className="responses-empty-state">Carregando respostas recebidas...</div>
      ) : responseCandidates.length === 0 ?(
        <EmptyState
          title="Nenhuma resposta para revisar"
          description="Quando uma resposta de fornecedor chegar pelo monitoramento, ela aparecera aqui com o vinculo sugerido."
        />
      ) : (
        <div className="responses-grid">
          {responseCandidates.map(candidate => (
            <button
              key={candidate.id}
              type="button"
              className={`response-card confidence-${candidate.confidence_level}`}
              onClick={() => openResponseCandidate(candidate)}
            >
              <div className="response-card-top">
                <span className="response-status-pill">{responseStatusLabel(candidate)}</span>
                <span className="response-confidence">{responseConfidenceLabel(candidate.confidence_level)}</span>
              </div>
              <strong>{candidate.supplier_name || candidate.from_name || candidate.from_email}</strong>
              <span className="response-subject">{candidate.subject || 'Sem assunto'}</span>
              <div className="response-meta-row">
                  <span>{candidate.quote_code || 'Cotação a identificar'}</span>
                <span>{fmtDateTime(candidate.received_at)}</span>
              </div>
              <p>{candidate.match_reasons[0] || 'O Portal guardou a mensagem para revisao.'}</p>
              {candidate.attachments.length > 0 && (
                <small>{candidate.attachments.length} anexo(s), {candidate.attachments.filter(att => att.scan_status === 'blocked').length} bloqueado(s)</small>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );

  const renderNewQuoteWizard = () => {
    const currentStep = activeQuote ?quoteWizardStep : 'products';
    const selectedSupplierCount = Object.values(selectedSupplierMap).filter(itemSet => itemSet.size > 0).length;
    const currentStepLabel = currentStep === 'suppliers' ?'Pesquisa de fornecedores' : currentStep === 'preview' ?'Comparativo e mensagens' : 'Necessidade';
    const selectedEmailPreview = emailPreviews.find(preview => preview.message_id === selectedEmailPreviewId) || emailPreviews[0];

    return (
      <div className="new-quote-workspace">
        <div className="purchase-workspace-status" aria-label="Estado atual da compra">
          <span>{activeQuote ?'Cotação interna em preparo' : 'Entrada inteligente'}</span>
          <strong>{currentStepLabel}</strong>
          <small>{activeQuote ?'O Portal mostra a acao util para o estado atual.' : 'Digite ou cole a necessidade para o Portal classificar.'}</small>
        </div>

        {!activeQuote ?(
          <NewPurchaseComposer
            pastedListText={pastedListText}
            onPastedListTextChange={setPastedListText}
            purchaseMode={purchaseInputMode}
            onPurchaseModeChange={setPurchaseInputMode}
            parsingList={parsingList}
            onParseNeedList={parsePastedNeedList}
            parsedLines={parsedLines}
            setParsedLines={setParsedLines}
            parsedLineStatusText={parsedLineStatusText}
            handleCreateIntelligentNeed={handleCreateIntelligentNeed}
            savingRequest={savingRequest}
            linkImportUrl={linkImportUrl}
            onLinkImportUrlChange={setLinkImportUrl}
            importingLink={importingLink}
            handleImportLink={handleImportLink}
            cartImportUrl={cartImportUrl}
            onCartImportUrlChange={setCartImportUrl}
            importingCart={importingCart}
            handleImportCart={handleImportCart}
            setShowPrivateCartModal={setShowPrivateCartModal}
            reqTitle={reqTitle}
            setReqTitle={setReqTitle}
            reqPriority={reqPriority}
            setReqPriority={setReqPriority}
            reqDepartment={reqDepartment}
            setReqDepartment={setReqDepartment}
            reqNeededBy={reqNeededBy}
            setReqNeededBy={setReqNeededBy}
            reqDesc={reqDesc}
            setReqDesc={setReqDesc}
            reqJustify={reqJustify}
            setReqJustify={setReqJustify}
          />
        ) : (
          <div className="new-quote-grid">
            <section className="new-quote-main">
              {currentStep === 'products' && (
                <div className="new-quote-panel">
                  <div className="new-quote-panel-header">
                    <div>
                      <h2>Produtos</h2>
                      <p>Escolha itens do Catálogo, confirme itens vindos do Estoque ou cole uma lista para revisar.</p>
                    </div>
                    <Badge variant="neutral">{activeQuote.items.length} item(ns)</Badge>
                  </div>

                  <div className="quote-title-row">
                    <Input
                      id="quote-title"
                      label="Nome da cotação"
                      value={quoteTitle}
                      onChange={e => setQuoteTitle(e.target.value)}
                      placeholder="Ex: Cotação de materiais de manutenção"
                    />
                    <Input
                      id="catalog-search"
                      label="Buscar no Catálogo"
                      value={catalogSearch}
                      onChange={e => setCatalogSearch(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); searchCatalogForQuote(); } }}
                      placeholder="Parafuso Allen, Cantoneira, Cabo PP..."
                    />
                    <Button variant="secondary" onClick={searchCatalogForQuote} disabled={catalogSearching}>
                      {catalogSearching ?'Buscando...' : 'Buscar'}
                    </Button>
                  </div>

                  {catalogResults.length > 0 && (
                    <div className="quote-result-list">
                      {catalogResults.slice(0, 6).map((item: any) => (
                        <button key={item.id} type="button" className="quote-result-card" onClick={() => addCatalogItemToQuote(item)}>
                          <strong>{item.display_name || item.name || item.description}</strong>
                          <span>{item.specification_text || item.measure_display || item.cybersul_code || 'Especificação preservada no registro'}</span>
                        </button>
                      ))}
                    </div>
                  )}

                  <div className="pasted-list-box">
                    <label htmlFor="pasted-list">Colar lista de materiais</label>
                    <textarea
                      id="pasted-list"
                      value={pastedListText}
                      onChange={e => setPastedListText(e.target.value)}
                      placeholder={'5 un Parafuso Allen inox 1/4\\n2 barras Cantoneira Ferro 3 x 3/16\\n10 m Cabo PP 3x2,5'}
                      rows={5}
                    />
                    <div className="quote-actions-line">
                      <Button variant="secondary" size="sm" onClick={parsePastedList} disabled={parsingList || !pastedListText.trim()}>
                        {parsingList ?'Analisando...' : 'Analisar lista'}
                      </Button>
                      <span>Itens ambíguos ficam pendentes de confirmação antes do envio.</span>
                    </div>
                  </div>

                  {parsedLines.length > 0 && (
                    <div className="quote-review-list">
                      {parsedLines.map((line, index) => (
                        <div key={`${line.raw_text}-${index}`} className={`quote-review-item confidence-${line.confidence}`}>
                          <div>
                            <strong>{line.purchase_type === 'internal' ?line.suggested_display_name || line.description : line.description}</strong>
                            <span>{parsedLineTypeLabel(line)} · {line.quantity} {line.unit_of_measure} · {line.purchase_type === 'internal' ?line.suggested_specification || 'Sem especificacao confirmada' : 'Nao sera vinculado ao Estoque sem revisao'}</span>
                            <small>{parsedLineStatusText(line)}</small>
                          </div>
                          <Button size="sm" variant="secondary" onClick={() => addParsedLineToQuote(line)} disabled={line.purchase_type !== 'internal'}>
                            {line.purchase_type === 'internal' ?'Adicionar' : 'Compra externa'}
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="quote-items-list">
                    {activeQuote.items.length === 0 ?(
                      <EmptyState title="Nenhum produto selecionado" description="Busque no Catálogo ou cole uma lista para iniciar a cotação." />
                    ) : activeQuote.items.map(item => (
                      <div key={item.id} className="quote-item-row">
                        <div>
                          <strong>{item.description || item.free_text_description || 'Item sem descrição'}</strong>
                          <span>{item.specifications || 'Sem observação'} · {item.quantity} {item.unit_of_measure}</span>
                          <small>{item.source_type === 'stock_catalog' ?'Veio do Estoque & Catálogo' : item.source_type === 'pasted_list' ?'Veio de lista colada' : 'Item manual'}</small>
                        </div>
                        <Badge variant={item.match_status === 'needs_confirmation' ?'warning' : 'success'}>
                          {item.match_status === 'needs_confirmation' ?'confirme o produto' : 'confirmado'}
                        </Badge>
                      </div>
                    ))}
                  </div>

                  <div className="quote-step-footer">
                    <Button variant="primary" onClick={() => setQuoteWizardStep('suppliers')} disabled={activeQuote.items.length === 0}>
                      Continuar para fornecedores
                    </Button>
                  </div>
                </div>
              )}

              {currentStep === 'suppliers' && (
                <SupplierQuotationPanel
                  activeQuote={activeQuote}
                  supplierSuggestions={supplierSuggestions}
                  selectedSupplierMap={selectedSupplierMap}
                  setSelectedSupplierMap={setSelectedSupplierMap}
                  loadingSupplierSuggestions={loadingSupplierSuggestions}
                  loadSupplierSuggestions={loadSupplierSuggestions}
                  selectedSupplierCount={selectedSupplierCount}
                  setQuoteWizardStep={setQuoteWizardStep}
                  saveSupplierSelection={saveSupplierSelection}
                  showToast={showToast}
                />
              )}

              {currentStep === 'preview' && (
                <EmailQuotationPreview
                  emailPreviews={emailPreviews}
                  selectedEmailPreviewId={selectedEmailPreviewId}
                  setSelectedEmailPreviewId={setSelectedEmailPreviewId}
                  loadingPreviews={loadingPreviews}
                  loadEmailPreviews={loadEmailPreviews}
                  bccOverrides={bccOverrides}
                  handleBccToggle={handleBccToggle}
                  emailDraftEdits={emailDraftEdits}
                  setEmailDraftEdits={setEmailDraftEdits}
                  saveEmailDraft={saveEmailDraft}
                  updateEmailMessage={updateEmailMessage}
                  sendEmailMessage={sendEmailMessage}
                  sendingMessageId={sendingMessageId}
                  setQuoteWizardStep={setQuoteWizardStep}
                />
              )}
            </section>

            <aside className="new-quote-context">
              <h3>Resumo</h3>
              <p>{activeQuote.title}</p>
              <div><strong>{activeQuote.items.length}</strong><span>itens</span></div>
              <div><strong>{selectedSupplierCount}</strong><span>fornecedores selecionados</span></div>
              <div><strong>{emailPreviews.length}</strong><span>pré-visualizações</span></div>
              <p className="context-note">PDF opcional está preparado, mas só será ativado quando o gerador de documentos for configurado.</p>
            </aside>
          </div>
        )}
      </div>
    );
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div className="purchases-page">
      {/* Toast */}
      {toastMessage && (
        <div
          id="purchases-toast"
          className="purchases-toast"
          style={{ background: toastError ?'rgba(239,68,68,0.15)' : 'rgba(52,211,153,0.15)', borderColor: toastError ?'rgba(239,68,68,0.3)' : 'rgba(52,211,153,0.3)' }}
        >
          {toastError ?<AlertCircle size={16} style={{ color: '#f87171' }} /> : <ShieldCheck size={16} style={{ color: '#34d399' }} />}
          <span>{toastMessage}</span>
        </div>
      )}

      <PurchasesHeader
        onRefresh={loadAll}
        onNewPurchase={() => {
          setActiveTab('new_quote');
          setQuoteWizardStep('products');
          setSearchTerm('');
          setQueryParams({ request: null, quote: null, step: null }, { replace: false });
        }}
        loading={loading}
      />

      <PurchasesIndicators
        indicatorItems={indicatorItems}
        purchaseFilter={purchaseFilter}
        onFilterChange={applyPurchaseFilter}
      />

      <div style={{ padding: '0 0 4px 0' }}>
        <EmailBlockedNotice />
      </div>

      {loading ?(
        <div className="glass-card purchases-table-card" style={{ padding: '60px', display: 'flex', justifyContent: 'center' }}>
          <div className="spinner" style={{ width: 40, height: 40, border: '3px solid rgba(255,255,255,0.1)', borderTopColor: '#34d399', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        </div>
      ) : activeTab === 'new_quote' ?(
        renderNewQuoteWizard()
      ) : (
        renderAdaptiveCentral()
      )}

      {/* ============================= DRAWER DE REQUISIÇÃO ============================= */}
      <Drawer
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setSelectedRequest(null); setSelectedRFQ(null); }}
        title={selectedRequest ?selectedRequest.title : 'Carregando...'}
        description={selectedRequest ?`${STATUS_LABELS[selectedRequest.status] || selectedRequest.status} • ${PRIORITY_LABELS[selectedRequest.priority] || 'Normal'}` : ''}
        footer={selectedRequest ?(
          <div style={{ display: 'flex', gap: 8, width: '100%', flexWrap: 'wrap' }}>
            {selectedRequest.status === 'DRAFT' && (
              <Button variant="primary" style={{ flex: 1 }} leftIcon={<CheckCircle2 size={15} />} onClick={() => handleSendToApproval(selectedRequest.id)}>
                Enviar para Aprovação
              </Button>
            )}
            {(selectedRequest.status === 'APPROVED' || selectedRequest.status === 'RFQ_PREPARING') && !selectedRFQ && (
              <Button variant="primary" style={{ flex: 1 }} leftIcon={<Plus size={15} />} onClick={handleOpenCreateRFQ}>
                Criar cotação
              </Button>
            )}
            {['DRAFT', 'REQUESTED', 'PENDING_APPROVAL', 'APPROVED'].includes(selectedRequest.status) && (
              <Button variant="danger" onClick={() => handleCancelRequest(selectedRequest.id)}>Cancelar</Button>
            )}
            <Button variant="secondary" onClick={() => { setDrawerOpen(false); setSelectedRequest(null); setSelectedRFQ(null); }}>Fechar</Button>
          </div>
        ) : undefined}
      >
        {loadingDetail ?(
          <div style={{ padding: 60, display: 'flex', justifyContent: 'center' }}>
            <div className="spinner" style={{ width: 30, height: 30, border: '3px solid rgba(255,255,255,0.1)', borderTopColor: '#34d399', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
          </div>
        ) : selectedRequest ?(
          <div>
            {/* Banners de status */}
            {selectedRequest.status === 'PENDING_APPROVAL' && (
              <div style={{ display: 'flex', gap: 8, background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 12, color: '#fbbf24' }}>
                <AlertTriangle size={18} style={{ flexShrink: 0 }} />
                <span><strong>Aguardando aprovação financeira</strong> (Central de Aprovações #{selectedRequest.approval_id}).</span>
              </div>
            )}
            {selectedRequest.status === 'APPROVED' && (
              <div style={{ display: 'flex', gap: 8, background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 12, color: '#34d399' }}>
                <CheckCircle2 size={18} style={{ flexShrink: 0 }} />
                <span><strong>Orçamento autorizado.</strong> Clique em "Criar cotação" para iniciar o processo de cotação.</span>
              </div>
            )}

            {/* Dados gerais */}
            <div className="drawer-section">
              <h4 className="drawer-section-title">Dados Gerais</h4>
              <div className="drawer-details-grid">
                <div className="drawer-detail-item"><span className="drawer-detail-label">Prioridade</span><span className="drawer-detail-value">{PRIORITY_LABELS[selectedRequest.priority] || selectedRequest.priority}</span></div>
                <div className="drawer-detail-item"><span className="drawer-detail-label">Departamento</span><span className="drawer-detail-value">{selectedRequest.department || '-'}</span></div>
                <div className="drawer-detail-item"><span className="drawer-detail-label">Data Limite</span><span className="drawer-detail-value">{fmtDate(selectedRequest.needed_by)}</span></div>
                <div className="drawer-detail-item"><span className="drawer-detail-label">Criado em</span><span className="drawer-detail-value">{fmtDateTime(selectedRequest.created_at)}</span></div>
              </div>
              {selectedRequest.description && <p style={{ margin: '10px 0 0', fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{selectedRequest.description}</p>}
              {selectedRequest.justification && (
                <div style={{ marginTop: 10, padding: '8px 12px', background: 'rgba(255,255,255,0.04)', borderRadius: 6, fontSize: 12, fontStyle: 'italic', color: 'var(--text-muted)', borderLeft: '3px solid var(--color-primary)' }}>
                  "{selectedRequest.justification}"
                </div>
              )}
            </div>

            {/* Itens */}
            <div className="drawer-section">
              <h4 className="drawer-section-title">Itens Solicitados ({selectedRequest.items.length})</h4>
              {selectedRequest.items.map(item => (
                <div key={item.id} className="drawer-item-card">
                  <div className="drawer-item-info">
                    <span className="drawer-item-name">{item.description || item.free_text_description || 'Item sem descrição'}</span>
                    <span className="drawer-item-qty">
                      {item.quantity} {item.unit_of_measure}
                      {item.item_id && <><Package size={10} style={{ marginLeft: 6, display: 'inline' }} /> Produto Master Data</>}
                      {item.service_id && <><Wrench size={10} style={{ marginLeft: 6, display: 'inline' }} /> Serviço Master Data</>}
                      {!item.item_id && !item.service_id && (
                        <span style={{ marginLeft: 6, color: '#f59e0b', fontSize: 10 }}>Texto livre - converter para cadastro mestre</span>
                      )}
                    </span>
                  </div>
                  <div className="drawer-item-price">
                    <div>Unit: {fmt(item.estimated_unit_price)}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Total: {fmt((item.estimated_unit_price || 0) * item.quantity)}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* Cotacoes associadas */}
            <div className="drawer-section">
              <h4 className="drawer-section-title">Cotacoes ({(selectedRequest.rfqs || []).length})</h4>
              {(selectedRequest.rfqs || []).length === 0 ?(
                <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', padding: '16px', border: '1px dashed var(--border-color)', borderRadius: 8 }}>
                  Nenhuma cotação criada para esta requisição.
                  {(selectedRequest.status === 'APPROVED' || selectedRequest.status === 'RFQ_PREPARING') && (
                    <div style={{ marginTop: 8 }}>
                      <Button variant="secondary" size="sm" leftIcon={<Plus size={13} />} onClick={handleOpenCreateRFQ}>Criar cotação</Button>
                    </div>
                  )}
                </div>
              ) : (selectedRequest.rfqs || []).map(rfq => (
                <div
                  key={rfq.id}
                  onClick={() => handleSelectRFQ(rfq)}
                  style={{ cursor: 'pointer', padding: '10px 14px', borderRadius: 8, marginBottom: 8, background: selectedRFQ?.id === rfq.id ?'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.04)', border: `1px solid ${selectedRFQ?.id === rfq.id ?'rgba(99,102,241,0.4)' : 'var(--border-color)'}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>{rfq.title}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{STATUS_LABELS[rfq.status] || rfq.status} • Criada em {fmtDate(rfq.created_at)}</div>
                  </div>
                  <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
                </div>
              ))}
            </div>

            {/* Painel da cotacao selecionada */}
            {selectedRFQ && (
              <div style={{ border: '1px solid rgba(99,102,241,0.3)', borderRadius: 12, padding: 16, background: 'rgba(99,102,241,0.05)', marginTop: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#c4b5fd' }}>{selectedRFQ.title}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {STATUS_LABELS[selectedRFQ.status] || selectedRFQ.status}
                      {selectedRFQ.deadline && ` • Prazo: ${fmtDate(selectedRFQ.deadline)}`}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <EntityQuickActions
                      moduleName="purchases"
                      entityType="rfq"
                      entityId={selectedRFQ.id}
                      onActionPrepared={(draft) => setPreparedActionDraft(draft)}
                      variant="dropdown"
                    />
                    <Button
                      id="btn-generate-drafts"
                      variant="secondary"
                      size="sm"
                      leftIcon={<MailOpen size={13} />}
                      onClick={handleGenerateDrafts}
                      disabled={generatingDrafts}
                    >
                      {generatingDrafts ?'Gerando...' : 'Gerar Rascunhos'}
                    </Button>
                    <Button
                      id="btn-send-rfq"
                      variant="primary"
                      size="sm"
                      leftIcon={<Send size={13} />}
                      onClick={handleSendRFQ}
                      disabled={sendingRFQ}
                    >
                      {sendingRFQ ?'Enviando...' : 'Enviar cotação'}
                    </Button>
                  </div>
                </div>

                {/* Abas internas da cotação selecionada */}
                <div style={{ display: 'flex', gap: 4, marginBottom: 12, borderBottom: '1px solid var(--border-color)', paddingBottom: 8 }}>
                  {(['suppliers', 'drafts', 'comparison'] as const).map(tab => (
                    <button
                      key={tab}
                      id={`rfq-tab-${tab}`}
                      onClick={() => setRfqTab(tab)}
                      style={{
                        background: rfqTab === tab ?'rgba(99,102,241,0.2)' : 'transparent',
                        border: rfqTab === tab ?'1px solid rgba(99,102,241,0.4)' : '1px solid transparent',
                        borderRadius: 6, padding: '4px 12px', fontSize: 12, color: rfqTab === tab ?'#c4b5fd' : 'var(--text-muted)', cursor: 'pointer'
                      }}
                    >
                      {tab === 'suppliers' ?`Fornecedores (${rfqSuppliers.length})` : tab === 'drafts' ?`Rascunhos (${rfqDrafts.length})` : 'Comparativo'}
                    </button>
                  ))}
                </div>

                {loadingRFQ ?(
                  <div style={{ padding: 20, textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>Carregando detalhes da cotação...</div>
                ) : rfqTab === 'suppliers' ?(
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
                      {masterSuppliers.length > 0 ?(
                        <Button id="btn-add-supplier" variant="secondary" size="sm" leftIcon={<Plus size={13} />} onClick={handleOpenAddSupplier}>
                          Adicionar Fornecedor
                        </Button>
                      ) : (
                        <span style={{ fontSize: 11, color: '#fbbf24' }}>Cadastre fornecedores em Cadastros Mestres primeiro.</span>
                      )}
                    </div>
                    {rfqSuppliers.length === 0 ?(
                      <div id="empty-rfq-suppliers" style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', padding: 16 }}>
                        Nenhum fornecedor adicionado. Use "Adicionar Fornecedor" acima.
                      </div>
                    ) : rfqSuppliers.map(rs => (
                      <div key={rs.id} style={{ padding: '8px 12px', borderRadius: 8, marginBottom: 6, background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>{rs.supplier_name || rs.supplier_id}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{rs.contact_email || 'E-mail não informado'} • {STATUS_LABELS[rs.status] || rs.status}</div>
                        </div>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <Button
                            variant="ghost"
                            size="sm"
                            leftIcon={<Send size={12} />}
                            onClick={() => handleResendSupplierEmail(rs.supplier_id)}
                            disabled={resendingSupplierId === rs.supplier_id}
                          >
                            {resendingSupplierId === rs.supplier_id ?'Reenviando...' : 'Reenviar E-mail'}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : rfqTab === 'drafts' ?(
                  <div>
                    <EmailBlockedNotice />
                    {rfqDrafts.length === 0 ?(
                      <div id="empty-rfq-drafts" style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', padding: 16 }}>
                        Nenhum rascunho gerado ainda. Adicione fornecedores e clique em "Gerar Rascunhos".
                      </div>
                    ) : rfqDrafts.map((draft, i) => (
                      <div key={i} style={{ padding: 12, borderRadius: 8, marginBottom: 8, background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>{draft.supplier_name}</div>
                          <div style={{ display: 'flex', gap: 4 }}>
                            <Button
                              variant="ghost"
                              size="sm"
                              leftIcon={<Eye size={12} />}
                              onClick={() => { setSelectedDraft(draft); setIsDraftDrawerOpen(true); }}
                            >
                              Ver Rascunho
                            </Button>
                            <Button
                              id={`btn-copy-draft-${i}`}
                              variant="ghost"
                              size="sm"
                              leftIcon={<Copy size={12} />}
                              onClick={() => { navigator.clipboard.writeText(`Assunto: ${draft.subject}\n\n${draft.body}`); showToast('Rascunho copiado para a área de transferência.'); }}
                            >
                              Copiar
                            </Button>
                          </div>
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Assunto: <em>{draft.subject}</em></div>
                        {draft.contact_email && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Para: {draft.contact_email}</div>}
                        <div style={{ marginTop: 8, padding: '6px 10px', background: 'rgba(52,211,153,0.08)', borderRadius: 6, fontSize: 11, color: '#34d399', display: 'flex', gap: 6, alignItems: 'center' }}>
                          <Check size={12} /> Rascunho pronto para envio. Clique em "Enviar Cotação" acima para disparar os e-mails.
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  // Aba Comparativo
                  <div id="comparison-panel">
                    {!rfqComparison || rfqComparison.suppliers_summary.length === 0 ?(
                      <div style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'center', padding: 20, border: '1px dashed var(--border-color)', borderRadius: 8 }}>
                        <Scale size={24} style={{ marginBottom: 8, opacity: 0.4 }} /><br />
                        Quando as respostas de cotação forem registradas, o comparativo aparecerá aqui.
                      </div>
                    ) : (
                      <div>
                        {rfqComparison.recommendation_summary && (
                          <div style={{ padding: 12, background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)', borderRadius: 8, fontSize: 12, color: '#34d399', marginBottom: 12 }}>
                            <strong>Recomendação:</strong> {rfqComparison.recommendation_summary}
                          </div>
                        )}
                        <div style={{ overflowX: 'auto' }}>
                          <table className="purchases-data-table">
                            <thead>
                              <tr>
                                <th>Fornecedor</th>
                                <th>Valor Total</th>
                                <th>Prazo Médio</th>
                                <th>Condição</th>
                                <th>Melhor Preço</th>
                                <th>Melhor Prazo</th>
                                <th>Ação</th>
                              </tr>
                            </thead>
                            <tbody>
                              {rfqComparison.suppliers_summary.map(s => (
                                <tr key={s.supplier_id}>
                                  <td style={{ fontWeight: s.is_best_price ?700 : 400, color: s.is_best_price ?'#34d399' : 'var(--text-primary)' }}>
                                    {s.supplier_name}{s.is_best_price && ' ⭐'}
                                  </td>
                                  <td style={{ fontWeight: 700 }}>{fmt(s.total_amount)}</td>
                                  <td>{s.average_delivery_days ?`${s.average_delivery_days} dias` : '-'}</td>
                                  <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.payment_terms || '-'}</td>
                                  <td style={{ textAlign: 'center' }}>{s.is_best_price ?<Check size={16} style={{ color: '#34d399' }} /> : '-'}</td>
                                  <td style={{ textAlign: 'center' }}>{s.is_best_delivery ?<Check size={16} style={{ color: '#a78bfa' }} /> : '-'}</td>
                                  <td>
                                    {s.quote_response_id ?(
                                      <Button
                                        variant="primary"
                                        size="sm"
                                        onClick={() => handleChooseSupplier(s.quote_response_id!)}
                                        disabled={choosingSupplierId === s.quote_response_id!}
                                      >
                                        {choosingSupplierId === s.quote_response_id! ?'Salvando...' : 'Escolher Proposta'}
                                      </Button>
                                    ) : (
                                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Sem resposta</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : null}
      </Drawer>

      {/* ============================= MODAL: IMPORTAR CARRINHO PRIVADO ============================= */}
      <Modal
        isOpen={showPrivateCartModal}
        onClose={() => setShowPrivateCartModal(false)}
        title="Importar Carrinho Privado (Copiado)"
        size="md"
        footer={
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', width: '100%' }}>
            <Button variant="secondary" onClick={() => setShowPrivateCartModal(false)}>Cancelar</Button>
            <Button variant="primary" onClick={() => handleImportCart(cartImportPrivateText)} disabled={importingCart || !cartImportPrivateText.trim()}>
              {importingCart ?'Importando...' : 'Importar Conteúdo'}
            </Button>
          </div>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.4 }}>
            Como este carrinho exige login, cole o conteúdo de texto copiado da página do carrinho (ou o código HTML/JSON) para que o assistente extraia os produtos de forma estruturada.
          </p>
          <Textarea
            id="cart-private-text"
            label="Conteúdo do Carrinho"
            placeholder="Selecione tudo (Ctrl+A) na página do carrinho, copie (Ctrl+C) e cole aqui..."
            rows={8}
            value={cartImportPrivateText}
            onChange={e => setCartImportPrivateText(e.target.value)}
          />
        </div>
      </Modal>

      {/* ============================= MODAL: NOVA REQUISIÇÃO ============================= */}
      <Modal
        isOpen={isRequestModalOpen}
        onClose={() => setIsRequestModalOpen(false)}
        title="Nova Requisição de Compras"
        size="lg"
        footer={
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', width: '100%' }}>
            <Button variant="secondary" onClick={() => setIsRequestModalOpen(false)}>Cancelar</Button>
            <Button id="btn-submit-request" variant="primary" onClick={handleSubmitRequest} disabled={savingRequest}>
              {savingRequest ?'Criando...' : 'Criar Requisição'}
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSubmitRequest} className="purchase-form-grid">
          <div className="purchase-form-row">
            <Input id="req-title" label="Título *" placeholder="Ex: Compra de nobreaks para sala de servidores" value={reqTitle} onChange={e => setReqTitle(e.target.value)} required />
            <Select
              id="req-priority"
              label="Prioridade *"
              value={reqPriority}
              onChange={e => setReqPriority(e.target.value)}
              options={[{ value: 'LOW', label: 'Baixa' }, { value: 'NORMAL', label: 'Normal' }, { value: 'HIGH', label: 'Alta' }, { value: 'URGENT', label: 'Urgente' }]}
            />
          </div>
          <div className="purchase-form-row">
            <Input id="req-department" label="Departamento" placeholder="Ex: TI, Financeiro, Produção" value={reqDepartment} onChange={e => setReqDepartment(e.target.value)} />
            <Input id="req-needed-by" label="Data Limite" type="date" value={reqNeededBy} onChange={e => setReqNeededBy(e.target.value)} />
          </div>
          <Textarea id="req-description" label="Escopo / Detalhes" placeholder="Detalhe especificações técnicas, marca, modelo..." value={reqDesc} onChange={e => setReqDesc(e.target.value)} />
          <Textarea id="req-justification" label="Justificativa" placeholder="Qual problema de negócio esta compra resolve?" value={reqJustify} onChange={e => setReqJustify(e.target.value)} />

          {/* Itens */}
          <div className="dynamic-items-section">
            <div className="dynamic-items-header">
              <h4 className="dynamic-items-title">Itens Necessários</h4>
              <Button variant="secondary" size="sm" leftIcon={<Plus size={14} />} onClick={handleAddReqItem} type="button">Adicionar Item</Button>
            </div>
            {reqItems.map((item, i) => (
              <div key={i} style={{ border: '1px solid var(--border-color)', borderRadius: 8, padding: 12, marginBottom: 8, background: 'var(--surface-elevated)' }}>
                {/* Seletor de tipo */}
                <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
                  {([
                    { v: 'product', label: 'Produto/Item', icon: <Package size={12} /> },
                    { v: 'service', label: 'Serviço', icon: <Wrench size={12} /> },
                    { v: 'freetext', label: 'Texto Livre', icon: <FileText size={12} /> }
                  ] as { v: NewItemForm['itemType'], label: string, icon: React.ReactNode }[]).map(t => (
                    <button
                      key={t.v}
                      type="button"
                      onClick={() => handleItemTypeChange(i, t.v)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', borderRadius: 6, fontSize: 11, cursor: 'pointer',
                        background: item.itemType === t.v ?'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.05)',
                        border: `1px solid ${item.itemType === t.v ?'rgba(99,102,241,0.5)' : 'var(--border-color)'}`,
                        color: item.itemType === t.v ?'#c4b5fd' : 'var(--text-muted)'
                      }}
                    >
                      {t.icon} {t.label}
                    </button>
                  ))}
                  <button type="button" onClick={() => handleRemoveReqItem(i)} disabled={reqItems.length === 1} style={{ marginLeft: 'auto', background: 'transparent', border: 'none', cursor: 'pointer', color: reqItems.length === 1 ?'transparent' : '#f87171' }}>
                    <Trash2 size={14} />
                  </button>
                </div>

                {/* Seletor de produto/serviço ou texto livre */}
                {item.itemType === 'product' && (
                  <>
                    <Select
                      label="Produto / Item do Cadastro Mestre"
                      value={item.item_id || ''}
                      onChange={e => {
                        const found = masterItems.find(m => m.id === e.target.value);
                        updateReqItem(i, { item_id: e.target.value, unit_of_measure: found?.unit_of_measure || 'un', free_text_description: found?.name || '' });
                      }}
                      options={[{ value: '', label: '— Selecione um produto —' }, ...masterItems.map(m => ({ value: m.id, label: `${m.name}${m.sku ?` (Código: ${m.sku})` : ''}` }))]}
                    />
                    {masterItems.length === 0 && (
                      <div style={{ fontSize: 11, color: '#fbbf24', marginTop: -6, marginBottom: 10 }}>
                        Nenhum produto encontrado. Cadastre primeiro em Cadastros Mestres.
                      </div>
                    )}
                  </>
                )}
                {item.itemType === 'service' && (
                  <>
                    <Select
                      label="Serviço do Cadastro Mestre"
                      value={item.service_id || ''}
                      onChange={e => {
                        const found = masterServices.find(s => s.id === e.target.value);
                        updateReqItem(i, { service_id: e.target.value, free_text_description: found?.name || '' });
                      }}
                      options={[{ value: '', label: '— Selecione um serviço —' }, ...masterServices.map(s => ({ value: s.id, label: s.name }))]}
                    />
                    {masterServices.length === 0 && (
                      <div style={{ fontSize: 11, color: '#fbbf24', marginTop: -6, marginBottom: 10 }}>
                        Nenhum serviço encontrado. Cadastre primeiro em Cadastros Mestres.
                      </div>
                    )}
                  </>
                )}
                {item.itemType === 'freetext' && (
                  <>
                    <Input
                      label="Descrição do Item *"
                      placeholder="Ex: Monitor Dell 27 polegadas Full HD"
                      value={item.free_text_description}
                      onChange={e => updateReqItem(i, { free_text_description: e.target.value })}
                    />
                    <div style={{ display: 'flex', gap: 6, marginTop: 6, padding: '6px 10px', background: 'rgba(245,158,11,0.08)', borderRadius: 6, fontSize: 11, color: '#fbbf24' }}>
                      <AlertTriangle size={12} style={{ marginTop: 1, flexShrink: 0 }} />
                      Este item não está no cadastro mestre. Após a compra, poderá ser convertido em Produto/Item oficial.
                    </div>
                  </>
                )}

                <div className="purchase-form-row" style={{ marginTop: 8 }}>
                  <Input label="Quantidade *" type="number" min="0.01" step="any" value={item.quantity} onChange={e => updateReqItem(i, { quantity: parseFloat(e.target.value) || 1 })} />
                  <Input label="Unidade" placeholder="un, kg, m..." value={item.unit_of_measure} onChange={e => updateReqItem(i, { unit_of_measure: e.target.value })} />
                  <Input label="Preço Unit. Est. (R$)" type="number" min="0" step="0.01" value={item.estimated_unit_price} onChange={e => updateReqItem(i, { estimated_unit_price: parseFloat(e.target.value) || 0 })} />
                </div>
                <Textarea label="Especificações técnicas" placeholder="Detalhe requisitos técnicos específicos..." value={item.specifications} onChange={e => updateReqItem(i, { specifications: e.target.value })} style={{ marginTop: 6 }} />
              </div>
            ))}
            <div className="items-total-summary">
              Total estimado: {fmt(estimatedTotal)}
            </div>
          </div>
        </form>
      </Modal>

      {/* ============================= MODAL: NOVA COTACAO ============================= */}
      <Modal
        isOpen={isRFQModalOpen}
        onClose={() => setIsRFQModalOpen(false)}
        title="Criar cotação"
        size="md"
        footer={
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', width: '100%' }}>
            <Button variant="secondary" onClick={() => setIsRFQModalOpen(false)}>Cancelar</Button>
            <Button id="btn-submit-rfq" variant="primary" onClick={handleSubmitRFQ} disabled={savingRFQ}>{savingRFQ ?'Criando...' : 'Criar cotação'}</Button>
          </div>
        }
      >
        <form onSubmit={handleSubmitRFQ} className="purchase-form-grid">
          <Input id="rfq-title" label="Título da cotação *" placeholder="Ex: Cotação de nobreaks - TI" value={rfqTitle} onChange={e => setRfqTitle(e.target.value)} required />
          <Input id="rfq-deadline" label="Prazo para Respostas" type="date" value={rfqDeadline} onChange={e => setRfqDeadline(e.target.value)} />
          <Textarea
            id="rfq-template"
            label="Template da mensagem (opcional)"
            placeholder="Deixe em branco para usar o template padrão. Use {supplier_name}, {request_title}, {items_list} como variáveis."
            value={rfqTemplate}
            onChange={e => setRfqTemplate(e.target.value)}
          />
          <div style={{ padding: '10px 14px', background: 'rgba(99,102,241,0.08)', borderRadius: 8, fontSize: 12, color: '#a78bfa' }}>
            <strong>Próximo passo:</strong> Depois de criar a cotação, adicione fornecedores e gere os rascunhos de mensagem para revisão.
          </div>
        </form>
      </Modal>

      {/* ============================= MODAL: ADICIONAR FORNECEDOR A COTACAO ============================= */}
      <Modal
        isOpen={isAddSupplierToRFQOpen}
        onClose={() => setIsAddSupplierToRFQOpen(false)}
        title="Adicionar fornecedor à cotação"
        size="sm"
        footer={
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', width: '100%' }}>
            <Button variant="secondary" onClick={() => setIsAddSupplierToRFQOpen(false)}>Cancelar</Button>
            <Button id="btn-confirm-add-supplier" variant="primary" onClick={handleAddSupplierToRFQ} disabled={addingSupplier}>
              {addingSupplier ?'Adicionando...' : 'Adicionar'}
            </Button>
          </div>
        }
      >
        <form onSubmit={handleAddSupplierToRFQ} className="purchase-form-grid">
          {masterSuppliers.length === 0 ?(
            <div style={{ padding: 16, textAlign: 'center', fontSize: 12, color: '#fbbf24' }}>
              <AlertTriangle size={18} style={{ marginBottom: 6 }} /><br />
              Nenhum fornecedor cadastrado no Master Data.<br />
              Acesse <strong>Cadastros Mestres &gt; Fornecedores</strong> para cadastrar.
            </div>
          ) : (
            <>
              <Select
                id="select-rfq-supplier"
                label="Fornecedor do Cadastro Mestre *"
                value={selectedSupplierId}
                onChange={e => {
                  setSelectedSupplierId(e.target.value);
                  const sup = masterSuppliers.find(s => s.id === e.target.value);
                  setSupplierContactEmail(sup?.preferred_contact_email || sup?.person.email || '');
                }}
                options={masterSuppliers.map(s => ({ value: s.id, label: s.person.name }))}
              />
              <Input id="supplier-contact-email" label="E-mail de contato (opcional)" type="email" placeholder="E-mail para este fornecedor nesta cotação" value={supplierContactEmail} onChange={e => setSupplierContactEmail(e.target.value)} />
              <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 8, fontSize: 11, color: '#f87171', display: 'flex', gap: 6 }}>
                <Lock size={12} style={{ marginTop: 1 }} /> Adicionar o fornecedor nao envia e-mail. O envio real acontece so depois da confirmacao.
              </div>
            </>
          )}
        </form>
      </Modal>

      {/* ============================= DRAWER: DETALHE DO RASCUNHO ============================= */}
      <Drawer
        open={isDraftDrawerOpen}
        onClose={() => { setIsDraftDrawerOpen(false); setSelectedDraft(null); }}
        title={selectedDraft ?`Rascunho — ${selectedDraft.supplier_name}` : 'Rascunho'}
        description="Visualização do rascunho de mensagem. O envio real está bloqueado."
      >
        {selectedDraft ?(
          <div>
            <EmailBlockedNotice />
            <div className="drawer-section">
              <h4 className="drawer-section-title">Destinatário</h4>
              <div style={{ fontSize: 13 }}>{selectedDraft.supplier_name}</div>
              {selectedDraft.contact_email && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>E-mail: {selectedDraft.contact_email}</div>}
            </div>
            <div className="drawer-section">
              <h4 className="drawer-section-title">Assunto</h4>
              <div style={{ fontWeight: 600, fontSize: 13, color: '#c4b5fd' }}>{selectedDraft.subject}</div>
            </div>
            <div className="drawer-section">
              <h4 className="drawer-section-title">Corpo da Mensagem</h4>
              <div style={{ whiteSpace: 'pre-wrap', fontSize: 12, lineHeight: 1.7, color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.04)', padding: 14, borderRadius: 8, border: '1px solid var(--border-color)' }}>
                {selectedDraft.body}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              <Button
                id="btn-copy-full-draft"
                variant="secondary"
                leftIcon={<Clipboard size={14} />}
                onClick={() => { navigator.clipboard.writeText(`Assunto: ${selectedDraft.subject}\n\n${selectedDraft.body}`); showToast('Rascunho copiado!'); }}
              >
                Copiar Rascunho
              </Button>
              <Button
                id="btn-confirm-send-from-draft"
                variant="secondary"
                leftIcon={<Send size={14} />}
                onClick={() => { setIsDraftDrawerOpen(false); handleRequestSendApproval(); }}
              >
                Confirmar envio
              </Button>
            </div>
            <div style={{ marginTop: 12, padding: '10px 14px', background: 'rgba(96,165,250,0.08)', borderRadius: 8, fontSize: 12, color: '#93c5fd' }}>
              Enviar cotação é uma tarefa sensível de Compras. O Portal registra auditoria e exige confirmação simples antes do envio.
            </div>
          </div>
        ) : null}
      </Drawer>

      {/* ============================= MODAL: REJEITAR SUGESTÃO DE PREÇO ============================= */}
      <Modal
        isOpen={isRejectModalOpen}
        onClose={() => { setIsRejectModalOpen(false); setRejectReason(''); setRejectingSuggestionId(null); }}
        title="Rejeitar Sugestão de Reajuste"
        size="md"
        footer={
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', width: '100%' }}>
            <Button variant="secondary" onClick={() => { setIsRejectModalOpen(false); setRejectReason(''); setRejectingSuggestionId(null); }}>Cancelar</Button>
            <Button variant="danger" onClick={handleRejectSuggestionSubmit}>
              Rejeitar
            </Button>
          </div>
        }
      >
        <form onSubmit={handleRejectSuggestionSubmit}>
          <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label className="form-label" style={{ fontWeight: '600', color: 'var(--text-primary)' }}>Justificativa / Motivo da Rejeição*</label>
            <Textarea
              placeholder="Descreva o motivo pelo qual este reajuste de preço está sendo rejeitado..."
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
              rows={4}
              required
            />
          </div>
        </form>
      </Modal>

      {/* ============================= MODAL: ATUALIZAR PREÇO DE VARIAÇÃO ============================= */}
      <Modal
        isOpen={isPriceModalOpen}
        onClose={() => setIsPriceModalOpen(false)}
        title="Atualizar preco atual"
        size="sm"
        footer={
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', width: '100%' }}>
            <Button variant="secondary" onClick={() => setIsPriceModalOpen(false)}>Cancelar</Button>
            <Button variant="primary" onClick={handleUpdatePriceSubmit}>Salvar Preço</Button>
          </div>
        }
      >
        <form onSubmit={handleUpdatePriceSubmit} className="purchase-form-grid">
          <div>
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }}>
              Insira o novo preco atual para a variacao <strong>{selectedItemForPriceUpdate?.name}</strong>.
            </div>
            <Input
              label="Novo preco atual (R$)*"
              type="number"
              min="0"
              step="0.01"
              value={newPriceValue}
              onChange={e => setNewPriceValue(e.target.value === '' ?'' : parseFloat(e.target.value))}
              required
            />
          </div>
        </form>
      </Modal>

      {/* ============================= MODAL: HISTÓRICO DE FLUTUAÇÃO DE PREÇOS ============================= */}
      <Modal
        isOpen={isHistoryModalOpen}
        onClose={() => { setIsHistoryModalOpen(false); setHistoryTimeline([]); }}
        title="Histórico de Flutuação de Preço"
        size="md"
        footer={
          <div style={{ display: 'flex', justifyContent: 'flex-end', width: '100%' }}>
            <Button variant="secondary" onClick={() => { setIsHistoryModalOpen(false); setHistoryTimeline([]); }}>Fechar</Button>
          </div>
        }
      >
        <div>
          {loadingHistoryTimeline ?(
            <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
              <div className="spinner" style={{ width: 24, height: 24, border: '2px solid rgba(255,255,255,0.1)', borderTopColor: '#a78bfa', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
            </div>
          ) : historyTimeline.length === 0 ?(
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              Nenhum registro de preço histórico encontrado para este item.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxHeight: '400px', overflowY: 'auto', paddingRight: '8px' }}>
              {historyTimeline.map((hist, idx) => (
                <div key={idx} style={{ padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'rgba(255,255,255,0.01)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 700, color: '#34d399', fontSize: '14px' }}>{fmt(hist.price)}</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{fmtDate(hist.created_at || hist.date)}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Fornecedor: <strong>{hist.supplier_name || 'Desconhecido'}</strong>
                  </div>
                  {hist.document_type && (
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                      Documento: {hist.document_type} {hist.document_number ?`#${hist.document_number}` : ''}
                    </div>
                  )}
                  {hist.notes && (
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', fontStyle: 'italic' }}>
                      Obs: {hist.notes}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
      
      {/* ============================= DRAWER: RESPOSTA RECEBIDA ============================= */}
      <Drawer
        open={responseDrawerOpen}
        onClose={() => setResponseDrawerOpen(false)}
        title={selectedResponseCandidate ?'Resposta recebida' : 'Resposta'}
        description="Revise o vinculo antes de usar os dados no comparativo."
      >
        {selectedResponseCandidate ?(
          <div className="response-review-drawer">
            <section>
              <div className="response-drawer-head">
                <div>
                  <span className="response-status-pill">{responseStatusLabel(selectedResponseCandidate)}</span>
                  <h3>{selectedResponseCandidate.supplier_name || selectedResponseCandidate.from_name || selectedResponseCandidate.from_email}</h3>
                  <p>{selectedResponseCandidate.subject || 'Sem assunto'}</p>
                </div>
                <span className={`response-confidence confidence-${selectedResponseCandidate.confidence_level}`}>
                  Confiança {responseConfidenceLabel(selectedResponseCandidate.confidence_level)}
                </span>
              </div>
              <div className="response-drawer-grid">
                <div>
                  <small>Cotação</small>
                  <strong>{selectedResponseCandidate.quote_code || 'A identificar'}</strong>
                </div>
                <div>
                  <small>Recebida em</small>
                  <strong>{fmtDateTime(selectedResponseCandidate.received_at)}</strong>
                </div>
                <div>
                  <small>Remetente</small>
                  <strong>{selectedResponseCandidate.from_email}</strong>
                </div>
              </div>
            </section>

            <section>
              <h4>Por que o Portal sugeriu este vínculo</h4>
              {selectedResponseCandidate.match_reasons.length > 0 ?(
                <ul className="response-reasons-list">
                  {selectedResponseCandidate.match_reasons.map(reason => <li key={reason}>{reason}</li>)}
                </ul>
              ) : (
                <p className="response-muted">Sem sinais suficientes. Faça o vínculo manual antes da extração.</p>
              )}
              {selectedResponseCandidate.risk_flags.length > 0 && (
                <div className="response-warning">
                  <AlertTriangle size={15} />
                  <span>{selectedResponseCandidate.risk_flags.includes('multiple_candidates') ?'Há mais de uma cotação possível. Confira antes de confirmar.' : 'Revisão manual necessária.'}</span>
                </div>
              )}
            </section>

            <section>
              <h4>Mensagem recebida</h4>
              <div className="response-message-box">
                {selectedResponseCandidate.body_text || 'Mensagem sem texto extraído pelo monitoramento.'}
              </div>
            </section>

            <section>
              <h4>Anexos</h4>
              {selectedResponseCandidate.attachments.length === 0 ?(
                <p className="response-muted">Nenhum anexo informado pelo monitoramento.</p>
              ) : (
                <div className="response-attachments-list">
                  {selectedResponseCandidate.attachments.map(attachment => (
                    <div key={attachment.id} className={`response-attachment ${attachment.scan_status === 'blocked' ?'blocked' : ''}`}>
                      <div>
                        <strong>{attachment.safe_filename}</strong>
                        <span>{attachment.content_type || attachment.detected_content_type || 'Tipo não informado'} · {(attachment.size_bytes / 1024).toFixed(1)} KB</span>
                      </div>
                      <small>{attachment.blocked_reason || 'Metadados salvos. Conteúdo aguardando revisão segura.'}</small>
                    </div>
                  ))}
                </div>
              )}
            </section>

            {isAdminOrMessias && (
              <section>
                <h4>Detalhes técnicos</h4>
                <div className="response-technical-grid">
                  <span>ID da mensagem: {selectedResponseCandidate.inbound_message_id}</span>
                  <span>Status: {selectedResponseCandidate.candidate_status}</span>
                  <span>Pontuação: {selectedResponseCandidate.confidence_score}</span>
                </div>
              </section>
            )}

            <section>
              <div className="response-extraction-title">
                <h4>Dados extraídos</h4>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => extractResponseCandidate(selectedResponseCandidate)}
                  disabled={!selectedResponseCandidate.quote_id || extractingResponseId === selectedResponseCandidate.id}
                >
                  {extractingResponseId === selectedResponseCandidate.id ?'Extraindo...' : 'Extrair dados'}
                </Button>
              </div>
              {responseExtractions[selectedResponseCandidate.id] ?(
                <div className="response-extraction-list">
                  {responseExtractions[selectedResponseCandidate.id].fields.length === 0 ?(
                    <p className="response-muted">Nenhum campo confiável foi identificado. Revise a mensagem manualmente.</p>
                  ) : responseExtractions[selectedResponseCandidate.id].fields.map(field => (
                    <div key={field.id} className={`response-extracted-field confidence-${field.confidence_level}`}>
                      <div>
                        <strong>{field.label}</strong>
                        <span>{field.normalized_value || field.raw_value || '-'}</span>
                      </div>
                      <small>{field.evidences[0]?.snippet || 'Sem trecho de evidência disponível.'}</small>
                    </div>
                  ))}
                  <div className="response-warning">
                    <AlertTriangle size={15} />
                    <span>Campos extraídos são sugestões. O Portal não atualiza preço, comparativo ou Catálogo sem revisão humana.</span>
                  </div>
                  {responseExtractions[selectedResponseCandidate.id].fields.length > 0 && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => reviewResponseExtraction(selectedResponseCandidate, responseExtractions[selectedResponseCandidate.id])}
                      disabled={reviewingExtractionId === responseExtractions[selectedResponseCandidate.id].id}
                    >
                      {reviewingExtractionId === responseExtractions[selectedResponseCandidate.id].id ?'Registrando...' : 'Marcar campos como revisados'}
                    </Button>
                  )}
                </div>
              ) : (
                <p className="response-muted">Gere sugestões a partir do corpo do e-mail e de anexos seguros já convertidos para texto pelo monitoramento.</p>
              )}
            </section>

            <div className="response-drawer-actions">
              <Button
                variant="primary"
                leftIcon={<Check size={15} />}
                onClick={() => decideResponseCandidate(selectedResponseCandidate, 'confirm')}
                disabled={!selectedResponseCandidate.quote_id || !!responseActionId}
              >
                {responseActionId === `${selectedResponseCandidate.id}:confirm` ?'Confirmando...' : 'Confirmar vínculo'}
              </Button>
              <Button
                variant="secondary"
                leftIcon={<X size={15} />}
                onClick={() => decideResponseCandidate(selectedResponseCandidate, 'reject')}
                disabled={!!responseActionId}
              >
                {responseActionId === `${selectedResponseCandidate.id}:reject` ?'Descartando...' : 'Descartar sugestão'}
              </Button>
              <Button
                variant="ghost"
                onClick={() => decideResponseCandidate(selectedResponseCandidate, 'ignore')}
                disabled={!!responseActionId}
              >
                Ignorar
              </Button>
            </div>
          </div>
        ) : null}
      </Drawer>

      {/* ============================= DRAWER: PREVIA DE ACAO UNIVERSAL ============================= */}
      <Drawer
        open={!!preparedActionDraft}
        onClose={() => setPreparedActionDraft(null)}
        title="Visualização da Ação Contextual"
        description="Confirme os detalhes da ação abaixo antes de prosseguir."
      >
        {preparedActionDraft ?(
          <div style={{ padding: '16px', display: 'flex', justifyContent: 'center' }}>
            <ActionCommandCard
              draft={preparedActionDraft}
              onConfirm={async (id, data): Promise<ActionCommandDraft> => {
                try {
                  const result = await confirmCommand(id, data);
                  setPreparedActionDraft(result);
                  return result;
                } catch (e: any) {
                  showToast(e.message || 'Erro ao processar.', true);
                  throw e;
                }
              }}
              onCancel={async (id): Promise<ActionCommandDraft> => {
                try {
                  const result = await cancelCommand(id);
                  setPreparedActionDraft(result);
                  return result;
                } catch (e) {
                  console.error(e);
                  setPreparedActionDraft(null);
                  throw e;
                }
              }}
              onSuccess={() => {
                setPreparedActionDraft(null);
                loadPriceTraceabilityData();
                loadAll();
              }}
            />
          </div>
        ) : null}
      </Drawer>
      <ConfirmDialog {...confirmDialogConfig} onClose={closeConfirm} />
    </div>
  );
};

export default PurchasesPage;
