import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle2,
  Clock,
  Eye,
  FilePlus2,
  Info,
  MessageSquare,
  Plus,
  RefreshCw,
  Send,
  ShoppingCart,
  X,
  XOctagon,
  ThumbsUp,
  ThumbsDown,
  ExternalLink,
  Search,
  CheckCircle,
  ClipboardCheck,
} from 'lucide-react';
import { ModuleHero } from '../components/ui/ModuleHero';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { ModulePageLayout } from '../components/layout/ModulePageLayout';
import { HelpCard } from '../components/layout/HelpCard';
import {
  approvalActionTypeLabels,
  approvalModuleLabels,
  approvalRiskLabels,
  approvalStatusLabels,
  labelOrValue,
} from '../lib/approvalLabels';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Textarea } from '../components/ui/Textarea';
import { Checkbox } from '../components/ui/Checkbox';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { MetricCard } from '../components/ui/MetricCard';
import { EmptyState } from '../components/ui/EmptyState';
import { Modal } from '../components/ui/Modal';
import { Drawer } from '../components/ui/Drawer';
import { StatusPill } from '../components/ui/StatusPill';
import { LoadingState } from '../components/ui/LoadingState';
import { getQueryNumber, getQueryParam, replaceQueryParams } from '../utils/urlState';

interface ApprovalComment {
  id: number;
  approval_id: number;
  user_id: number;
  username?: string;
  comment: string;
  created_at: string;
}

interface ApprovalDecision {
  id: number;
  approval_id: number;
  decided_by_user_id: number;
  username?: string;
  decision: string;
  reason?: string;
  created_at: string;
}

interface ApprovalItem {
  id: number;
  title: string;
  description?: string;
  module_slug: string;
  requester_user_id: number;
  requester_username?: string;
  approver_user_id?: number;
  approver_username?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | 'EXPIRED';
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  action_type: string;
  action_payload: Record<string, any>;
  result_payload?: Record<string, any>;
  expires_at?: string;
  decided_at?: string;
  created_at: string;
  updated_at: string;
  comments: ApprovalComment[];
  decisions: ApprovalDecision[];
}

interface ApprovalSummary {
  total_pending: number;
  my_requests_pending: number;
  waiting_my_decision: number;
  approved_recent: number;
  rejected_recent: number;
  by_risk: Record<string, number>;
  by_module: Record<string, number>;
}

interface CurrentUser {
  id: number;
  username: string;
  email: string;
  role: 'ADMIN' | 'USER' | 'APPROVER';
  module_permissions: Record<string, string>;
}

interface ApprovalsPageProps {
  backendOnline: boolean;
  currentUser: CurrentUser;
}

type TemplateKey =
  | 'FINANCIAL_RELEASE'
  | 'PURCHASE_QUOTE'
  | 'SUPPLIER_SELECTION'
  | 'PROPOSAL_SEND'
  | 'PERMISSION_CHANGE'
  | 'PASSWORD_RESET'
  | 'GENERAL_APPROVAL';

const requestTemplates: Record<TemplateKey, { module: string; risk: ApprovalItem['risk_level']; fields: Array<{ key: string; label: string; type?: string; textarea?: boolean; placeholder?: string }> }> = {
  FINANCIAL_RELEASE: {
    module: 'purchases',
    risk: 'MEDIUM',
    fields: [
      { key: 'item_or_service', label: 'Item ou serviço', placeholder: 'Ex: Licença de software de CAD' },
      { key: 'quantity', label: 'Quantidade', type: 'number', placeholder: '1' },
      { key: 'estimated_value', label: 'Valor estimado', type: 'number', placeholder: '1500.00' },
      { key: 'requesting_department', label: 'Setor solicitante', placeholder: 'Ex: Engenharia' },
      { key: 'reason', label: 'Motivo / Justificativa', textarea: true, placeholder: 'Descreva a necessidade da aquisição...' },
      { key: 'urgency', label: 'Urgência', placeholder: 'Ex: Alta (necessário para novo projeto)' },
      { key: 'notes', label: 'Observações adicionais', textarea: true, placeholder: 'Outros detalhes...' },
    ],
  },
  PURCHASE_QUOTE: {
    module: 'purchases',
    risk: 'LOW',
    fields: [
      { key: 'desired_item', label: 'Item desejado', placeholder: 'Ex: Bobina de filamento PLA' },
      { key: 'max_price', label: 'Valor máximo sugerido', type: 'number', placeholder: '180.00' },
      { key: 'quantity', label: 'Quantidade', type: 'number', placeholder: '5' },
      { key: 'criteria', label: 'Critérios importantes', textarea: true, placeholder: 'Ex: Entrega rápida, cor preta...' },
      { key: 'desired_deadline', label: 'Prazo desejado', placeholder: 'Ex: 5 dias úteis' },
      { key: 'notes', label: 'Observações', textarea: true, placeholder: 'Outras informações...' },
    ],
  },
  SUPPLIER_SELECTION: {
    module: 'purchases',
    risk: 'MEDIUM',
    fields: [
      { key: 'desired_item', label: 'Item desejado', placeholder: 'Ex: Cabeamento estruturado' },
      { key: 'found_options', label: 'Opções encontradas', textarea: true, placeholder: 'Descreva os fornecedores e valores cotados...' },
      { key: 'comparison', label: 'Comparativo técnico', textarea: true, placeholder: 'Comparação de prazos, qualidade e frete...' },
      { key: 'recommendation', label: 'Recomendação / Escolha da equipe', textarea: true, placeholder: 'Qual opção é a recomendada e por quê...' },
      { key: 'decision_owner', label: 'Quem deve decidir', placeholder: 'Ex: Diretor de Operações' },
    ],
  },
  PROPOSAL_SEND: {
    module: 'proposals',
    risk: 'MEDIUM',
    fields: [
      { key: 'client', label: 'Cliente', placeholder: 'Ex: Metalúrgica Vesper Ltda' },
      { key: 'value', label: 'Valor da proposta', type: 'number', placeholder: '45000.00' },
      { key: 'product_or_service', label: 'Produto/serviço', placeholder: 'Ex: Lote de flanges usinadas' },
      { key: 'proposal_link', label: 'Link ou Detalhes da Proposta', placeholder: 'Ex: Link do PDF no NAS ou texto da proposta...' },
      { key: 'notes', label: 'Observações adicionais', textarea: true, placeholder: 'Condições especiais, descontos concedidos...' },
    ],
  },
  PERMISSION_CHANGE: {
    module: 'it',
    risk: 'HIGH',
    fields: [
      { key: 'user', label: 'Usuário a alterar', placeholder: 'Ex: João Silva' },
      { key: 'system_access', label: 'Sistema / Módulo', placeholder: 'Ex: Acesso Admin ao ERP' },
      { key: 'access_type', label: 'Tipo de acesso / Permissão', placeholder: 'Ex: Escrita / Acesso total' },
      { key: 'reason', label: 'Motivo real do acesso', textarea: true, placeholder: 'Justifique a necessidade desse nível de acesso...' },
      { key: 'risk', label: 'Risco avaliado', placeholder: 'Ex: Médio (visualização de relatórios financeiros)' },
    ],
  },
  PASSWORD_RESET: {
    module: 'it',
    risk: 'LOW',
    fields: [
      { key: 'user', label: 'Usuário', placeholder: 'Ex: Maria Oliveira' },
      { key: 'system', label: 'Sistema / Serviço', placeholder: 'Ex: E-mail Corporativo' },
      { key: 'reason', label: 'Motivo do reset', textarea: true, placeholder: 'Ex: Senha expirada ou esquecida...' },
      { key: 'urgency', label: 'Urgência', placeholder: 'Ex: Imediata' },
    ],
  },
  GENERAL_APPROVAL: {
    module: 'approvals',
    risk: 'LOW',
    fields: [
      { key: 'subject', label: 'Assunto da solicitação', placeholder: 'Ex: Alteração de horário de expediente' },
      { key: 'reason', label: 'Motivo / Contexto', textarea: true, placeholder: 'Detalhe o motivo desta solicitação geral...' },
      { key: 'impact', label: 'Impacto / Setores afetados', textarea: true, placeholder: 'Como isso afeta a equipe ou processos...' },
      { key: 'notes', label: 'Observações gerais', textarea: true, placeholder: 'Qualquer informação complementar...' },
    ],
  },
};

const emptySummary: ApprovalSummary = {
  total_pending: 0,
  my_requests_pending: 0,
  waiting_my_decision: 0,
  approved_recent: 0,
  rejected_recent: 0,
  by_risk: { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 },
  by_module: {},
};

export const ApprovalsPage: React.FC<ApprovalsPageProps> = ({ backendOnline, currentUser }) => {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [summary, setSummary] = useState<ApprovalSummary>(emptySummary);
  const initialTab = getQueryParam('tab') === 'create' ? 'create' : 'list';
  const [activeTab, setActiveTab] = useState<'list' | 'create'>(initialTab);
  const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false);
  const [approvalToCancel, setApprovalToCancel] = useState<ApprovalItem | null>(null);
  const [formStep, setFormStep] = useState(1);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterRisk, setFilterRisk] = useState('ALL');
  const [filterModule, setFilterModule] = useState('ALL');
  const [templateKey, setTemplateKey] = useState<TemplateKey>('FINANCIAL_RELEASE');
  const [title, setTitle] = useState('');
  const [reason, setReason] = useState('');
  const [expiresDays, setExpiresDays] = useState(7);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [showTechnicalCreate, setShowTechnicalCreate] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [newComment, setNewComment] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [requestNewSearch, setRequestNewSearch] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [itemDecisions, setItemDecisions] = useState<Record<string, { approved: boolean; notes: string }>>({});
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const template = requestTemplates[templateKey];
  const canSeeTechnicalData = currentUser.role === 'ADMIN' || Boolean((import.meta as any).env?.DEV);

  const builtPayload = useMemo(() => {
    const details = template.fields.reduce<Record<string, any>>((acc, field) => {
      const raw = formValues[field.key]?.trim();
      if (!raw) return acc;
      acc[field.key] = field.type === 'number' ? Number(raw) : raw;
      return acc;
    }, {});
    return {
      request_template: templateKey,
      friendly_details: details,
      reason: reason.trim() || undefined,
    };
  }, [formValues, reason, template.fields, templateKey]);

  const showToast = (message: string) => {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 4500);
  };

  const fetchData = async () => {
    if (!backendOnline) return;
    setLoading(true);
    try {
      const [listRes, summaryRes] = await Promise.all([
        fetch('/api/v1/approvals/'),
        fetch('/api/v1/approvals/summary'),
      ]);
      if (listRes.ok) setApprovals(await listRes.json());
      if (summaryRes.ok) setSummary(await summaryRes.json());
    } catch {
      showToast('Não foi possível carregar as solicitações.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setFormValues({});
    setReason('');
  }, [templateKey]);

  useEffect(() => {
    if (!backendOnline) return;
    fetchData();
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProto}//${window.location.host}/api/v1/ws/notifications`);
    wsRef.current = ws;
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === 'approval_notification') {
          showToast('Solicitações atualizadas.');
          fetchData();
        }
      } catch {
        // A falha de WebSocket não deve quebrar a tela.
      }
    };
    ws.onerror = () => undefined;
    return () => ws.close();
  }, [backendOnline]);

  useEffect(() => {
    if (selectedApproval && selectedApproval.action_type === 'FINANCIAL_RELEASE') {
      const items = selectedApproval.action_payload?.items || [];
      const initial: Record<string, { approved: boolean; notes: string }> = {};
      items.forEach((item: any) => {
        initial[item.item_id] = { approved: true, notes: '' };
      });
      setItemDecisions(initial);
    } else {
      setItemDecisions({});
    }
  }, [selectedApproval]);

  const filteredApprovals = approvals.filter((approval) => {
    const search = `${approval.title} ${approval.description || ''}`.toLowerCase();
    return (
      search.includes(searchTerm.toLowerCase()) &&
      (filterStatus === 'ALL' || approval.status === filterStatus) &&
      (filterRisk === 'ALL' || approval.risk_level === filterRisk) &&
      (filterModule === 'ALL' || approval.module_slug === filterModule)
    );
  });

  const urgentApprovals = useMemo(
    () =>
      approvals
        .filter(
          (a) =>
            a.status === 'PENDING' &&
            (a.risk_level === 'CRITICAL' || a.risk_level === 'HIGH')
        )
        .slice(0, 6),
    [approvals]
  );

  const urgentCount = useMemo(
    () =>
      approvals.filter(
        (a) =>
          a.status === 'PENDING' &&
          (a.risk_level === 'CRITICAL' || a.risk_level === 'HIGH')
      ).length,
    [approvals]
  );

  const formatDate = (value?: string) => {
    if (!value) return 'Não informado';
    return new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  };

  const canDecide = (approval: ApprovalItem) => {
    if (approval.status !== 'PENDING') return false;
    if (currentUser.role === 'ADMIN') return true;
    const permission = currentUser.module_permissions?.[approval.module_slug];
    return approval.requester_user_id !== currentUser.id && (permission === 'MANAGER' || permission === 'ADMIN');
  };

  const canCancel = (approval: ApprovalItem) => {
    return approval.status === 'PENDING' && (currentUser.role === 'ADMIN' || approval.requester_user_id === currentUser.id);
  };

  const handleCreateApproval = async (event: React.FormEvent) => {
    event.preventDefault();
    setCreateError(null);
    if (!title.trim()) {
      setCreateError('Informe o título da solicitação.');
      return;
    }
    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + expiresDays);
    const response = await fetch('/api/v1/approvals/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        description: reason || undefined,
        module_slug: template.module,
        risk_level: template.risk,
        action_type: templateKey,
        action_payload: builtPayload,
        expires_at: expiresAt.toISOString(),
      }),
    });
    if (!response.ok) {
      const error = await response.json();
      setCreateError(error.detail || 'Não foi possível criar a solicitação.');
      return;
    }
    setTitle('');
    setFormValues({});
    setReason('');
    setFormStep(1);
    selectTab('list');
    showToast('Solicitação criada com sucesso.');
    fetchData();
  };

  const refreshSelected = async (id: number) => {
    const response = await fetch(`/api/v1/approvals/${id}`);
    if (response.ok) setSelectedApproval(await response.json());
  };

  const selectTab = (tab: 'list' | 'create') => {
    setActiveTab(tab);
    replaceQueryParams({ tab: tab === 'list' ? null : tab, approval: null });
    if (tab === 'create') setSelectedApproval(null);
  };

  const openApproval = (approval: ApprovalItem) => {
    setSelectedApproval(approval);
    replaceQueryParams({ tab: null, approval: approval.id });
  };

  const closeApproval = () => {
    setSelectedApproval(null);
    replaceQueryParams({ approval: null });
  };

  useEffect(() => {
    const approvalId = getQueryNumber('approval');
    if (approvalId) refreshSelected(approvalId);
  }, []);

  const approve = async (approval: ApprovalItem, resultPayload?: Record<string, any>) => {
    const response = await fetch(`/api/v1/approvals/${approval.id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: 'Aprovado', result_payload: resultPayload }),
    });
    if (!response.ok) {
      const error = await response.json();
      showToast(error.detail || 'Não foi possível aprovar.');
      return;
    }
    showToast('Solicitação aprovada.');
    fetchData();
    refreshSelected(approval.id);
  };

  const reject = async () => {
    if (!selectedApproval || !rejectReason.trim()) return;
    const resultPayload = selectedApproval.action_payload?.request_type === 'purchase_options'
      ? { decision_type: 'purchase_options_rejected', request_new_search: requestNewSearch }
      : undefined;
    const response = await fetch(`/api/v1/approvals/${selectedApproval.id}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: rejectReason, result_payload: resultPayload }),
    });
    if (!response.ok) {
      const error = await response.json();
      showToast(error.detail || 'Não foi possível rejeitar.');
      return;
    }
    setShowRejectModal(false);
    setRejectReason('');
    setRequestNewSearch(false);
    showToast('Solicitação rejeitada.');
    fetchData();
    refreshSelected(selectedApproval.id);
  };

  const proceedCancelApproval = async (approval: ApprovalItem) => {
    const response = await fetch(`/api/v1/approvals/${approval.id}/cancel`, { method: 'POST' });
    if (response.ok) {
      showToast('Solicitação cancelada.');
      fetchData();
      refreshSelected(approval.id);
    }
  };

  const cancel = async (approval: ApprovalItem) => {
    setApprovalToCancel(approval);
    setCancelConfirmOpen(true);
  };

  const addComment = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedApproval || !newComment.trim()) return;
    const response = await fetch(`/api/v1/approvals/${selectedApproval.id}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comment: newComment }),
    });
    if (response.ok) {
      setNewComment('');
      refreshSelected(selectedApproval.id);
    }
  };

  const renderFriendlyDetails = (payload: Record<string, any>) => {
    const details = payload?.friendly_details || payload || {};
    const entries = Object.entries(details).filter(([, value]) => value !== undefined && value !== null && value !== '');
    if (!entries.length) return <p style={{ color: '#94a3b8', fontSize: 13, margin: 0 }}>Sem detalhes adicionais.</p>;
    return (
      <div style={{ display: 'grid', gap: 10, marginTop: 12 }}>
        {entries.map(([key, value]) => (
          <div key={key} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '10px 0', borderBottom: '1px solid var(--border-color)' }}>
            <span style={{ color: '#94a3b8', fontSize: 13 }}>{humanizeKey(key)}</span>
            <strong style={{ color: '#f8fafc', textAlign: 'right', fontSize: 13 }}>
              {Array.isArray(value) ? value.join(', ') : String(value)}
            </strong>
          </div>
        ))}
      </div>
    );
  };

  const renderPurchaseOptions = (approval: ApprovalItem) => {
    const options = approval.action_payload?.options || [];
    if (!Array.isArray(options) || options.length === 0) return null;
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, marginTop: 12 }}>
        {options.map((option: any, index: number) => (
          <Card
            key={`${option.title}-${index}`}
            variant="glass"
            style={{
              padding: 16,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: 12,
              background: 'rgba(30, 41, 59, 0.4)'
            }}
          >
            <div>
              {option.image_url && (
                <img
                  src={option.image_url}
                  alt={option.title}
                  style={{ width: '100%', height: 140, objectFit: 'cover', borderRadius: 8, marginBottom: 12 }}
                />
              )}
              <h4 style={{ margin: 0, color: '#f8fafc', fontSize: 15, fontWeight: 600 }}>{option.title || `Opção ${index + 1}`}</h4>
              <p style={{ color: '#94a3b8', fontSize: 13, margin: '6px 0 12px' }}>{option.store || 'Loja não especificada'}</p>
              
              <div style={{ fontSize: 20, fontWeight: 700, color: '#34d399', marginBottom: 12 }}>
                {formatCurrency(option.price, approval.action_payload?.currency || 'BRL')}
              </div>
              
              <div style={{ color: '#cbd5e1', fontSize: 13, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Clock size={14} style={{ color: '#64748b' }} />
                <span>Frete/Prazo: <strong>{option.shipping || 'Não informado'}</strong></span>
              </div>

              {option.reason && (
                <p style={{ color: '#cbd5e1', fontSize: 13, backgroundColor: 'rgba(255, 255, 255, 0.03)', padding: 10, borderRadius: 6, margin: '8px 0', borderLeft: '3px solid var(--primary-color)' }}>
                  {option.reason}
                </p>
              )}

              {option.pros?.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#4ade80', display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                    <ThumbsUp size={12} /> Prós
                  </span>
                  <ul style={{ margin: 0, paddingLeft: 16, color: '#a7f3d0', fontSize: 12, lineHeight: 1.4 }}>
                    {option.pros.map((pro: string, idx: number) => <li key={idx}>{pro}</li>)}
                  </ul>
                </div>
              )}

              {option.cons?.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#f87171', display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                    <ThumbsDown size={12} /> Contras
                  </span>
                  <ul style={{ margin: 0, paddingLeft: 16, color: '#fecaca', fontSize: 12, lineHeight: 1.4 }}>
                    {option.cons.map((con: string, idx: number) => <li key={idx}>{con}</li>)}
                  </ul>
                </div>
              )}
            </div>

            <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {option.url && (
                <a
                  className="btn btn-ghost btn-sm"
                  href={option.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, minWidth: 100, border: '1px solid rgba(255, 255, 255, 0.1)' }}
                >
                  <span>Ver Produto</span>
                  <ExternalLink size={12} />
                </a>
              )}
              {canDecide(approval) && (
                <Button
                  variant="success"
                  size="sm"
                  style={{ flex: 1, minWidth: 120 }}
                  onClick={() => approve(approval, {
                    selected_option_index: index,
                    selected_option_title: option.title,
                    selected_option_url: option.url,
                    approved_price: option.price,
                    decision_type: 'selected_purchase_option',
                  })}
                  leftIcon={<Check size={14} />}
                >
                  Aprovar esta
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>
    );
  };

  const renderFinancialRelease = (approval: ApprovalItem) => {
    const items = approval.action_payload?.items || [];
    if (!Array.isArray(items) || items.length === 0) return <p style={{ color: '#94a3b8', fontSize: 13, margin: 0 }}>Sem itens na solicitação.</p>;
    
    const approvedTotal = items.reduce((acc, item) => {
      const dec = itemDecisions[item.item_id] || { approved: true, notes: '' };
      if (dec.approved) {
        return acc + (item.quantity * item.estimated_unit_price);
      }
      return acc;
    }, 0);

    const formatCurrency = (val: number) => {
      return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
    };

    return (
      <div style={{ display: 'grid', gap: 16, marginTop: 12 }}>
        <div style={{ padding: 12, borderRadius: 8, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-muted)' }}>
            <span>Total Estimado Original:</span>
            <strong style={{ color: '#fff' }}>{formatCurrency(approval.action_payload?.estimated_total || 0)}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', marginTop: '6px', color: 'var(--color-success)', fontWeight: 'bold' }}>
            <span>Total Aprovado Recalculado:</span>
            <span>{formatCurrency(approvedTotal)}</span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {items.map((item: any, index: number) => {
            const dec = itemDecisions[item.item_id] || { approved: true, notes: '' };
            const isPending = approval.status === 'PENDING';
            const canEdit = canDecide(approval) && isPending;

            return (
              <div
                key={item.item_id || index}
                style={{
                  padding: 16,
                  borderRadius: 10,
                  border: '1px solid var(--border-color)',
                  background: dec.approved ? 'rgba(255,255,255,0.01)' : 'rgba(239, 68, 68, 0.03)',
                  borderColor: dec.approved ? 'var(--border-color)' : 'rgba(239, 68, 68, 0.25)',
                  transition: 'all 0.2s ease',
                  position: 'relative'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16 }}>
                  <div>
                    <h5 style={{ margin: 0, fontSize: 13, color: '#fff', fontWeight: 600 }}>{item.description}</h5>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                      Qtd: <strong>{item.quantity} {item.unit}</strong> · Preço Unit. Est.: <strong>{formatCurrency(item.estimated_unit_price)}</strong>
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', marginTop: 4 }}>
                      Subtotal: {formatCurrency(item.quantity * item.estimated_unit_price)}
                    </div>
                  </div>
                  
                  {canEdit ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Checkbox
                        id={`item-dec-${item.item_id}`}
                        label={dec.approved ? 'Aprovado' : 'Reprovado'}
                        checked={dec.approved}
                        onChange={(checked) => {
                          setItemDecisions(prev => ({
                            ...prev,
                            [item.item_id]: { ...prev[item.item_id], approved: checked }
                          }));
                        }}
                      />
                      <label htmlFor={`item-dec-${item.item_id}`} style={{ fontSize: 12, fontWeight: 600, color: dec.approved ? 'var(--color-success)' : 'var(--danger-color)', cursor: 'pointer' }}>
                        {dec.approved ? 'Aprovado' : 'Rejeitado'}
                      </label>
                    </div>
                  ) : (
                    <Badge variant={dec.approved ? 'success' : 'danger'}>
                      {dec.approved ? 'Aprovado' : 'Rejeitado'}
                    </Badge>
                  )}
                </div>

                {canEdit ? (
                  <div style={{ marginTop: 12 }}>
                    <Input
                      placeholder="Adicione uma nota (ex: 'Ache mais barato', 'Substituir por marca Y')"
                      value={dec.notes}
                      onChange={(e) => {
                        setItemDecisions(prev => ({
                          ...prev,
                          [item.item_id]: { ...prev[item.item_id], notes: e.target.value }
                        }));
                      }}
                      style={{ fontSize: 12, padding: '6px 10px' }}
                    />
                  </div>
                ) : (
                  dec.notes && (
                    <div style={{ marginTop: 10, fontSize: 11, fontStyle: 'italic', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.02)', padding: '6px 10px', borderRadius: 4 }}>
                      Nota do Chefe: {dec.notes}
                    </div>
                  )
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const modalFooter = selectedApproval ? (
    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, width: '100%' }}>
      {canDecide(selectedApproval) && selectedApproval.action_payload?.request_type !== 'purchase_options' && (
        <Button
          variant="success"
          size="md"
          onClick={() => {
            if (selectedApproval.action_type === 'FINANCIAL_RELEASE') {
              const items = selectedApproval.action_payload?.items || [];
              const itemsPayload = items.map((item: any) => {
                const dec = itemDecisions[item.item_id] || { approved: true, notes: '' };
                return {
                  item_id: item.item_id,
                  decision: dec.approved ? 'APPROVED' : 'REJECTED',
                  notes: dec.notes
                };
              });
              approve(selectedApproval, {
                decision_type: 'partial_purchase_approval',
                items: itemsPayload
              });
            } else {
              approve(selectedApproval);
            }
          }}
          leftIcon={<Check size={14} />}
        >
          {selectedApproval.action_type === 'FINANCIAL_RELEASE' ? 'Confirmar Decisões' : 'Aprovar'}
        </Button>
      )}
      {canDecide(selectedApproval) && (
        <Button variant="danger" size="md" onClick={() => setShowRejectModal(true)} leftIcon={<X size={14} />}>
          Rejeitar
        </Button>
      )}
      {canCancel(selectedApproval) && (
        <Button variant="ghost" size="md" onClick={() => cancel(selectedApproval)} leftIcon={<XOctagon size={14} />} style={{ color: 'var(--danger-color)' }}>
          Cancelar solicitação
        </Button>
      )}
      <Button variant="secondary" size="md" onClick={closeApproval}>
        Fechar
      </Button>
    </div>
  ) : undefined;

  const listAside =
    activeTab === 'list' ? (
      <>
        <section className="module-side-card glass-card">
          <h3 className="module-side-title">
            <AlertTriangle size={16} style={{ display: 'inline', marginRight: 6, verticalAlign: 'middle' }} />
            Urgentes ({urgentCount})
          </h3>
          {urgentApprovals.length === 0 ? (
            <p style={{ margin: '12px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>
              Nenhuma solicitação crítica ou alta pendente no momento.
            </p>
          ) : (
            <div className="approval-urgent-list">
              {urgentApprovals.map((approval) => (
                <button
                  key={approval.id}
                  type="button"
                  className="approval-urgent-item"
                  onClick={() => openApproval(approval)}
                >
                  <strong>{approval.title}</strong>
                  <span>
                    {approvalRiskLabels[approval.risk_level]} ·{' '}
                    {labelOrValue(approvalModuleLabels, approval.module_slug)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
        <HelpCard
          description="O Koda pode orientar sobre tipos de solicitação. Use o Chat para tirar dúvidas com a equipe antes de abrir uma aprovação."
          actionLabel="Abrir Chat"
          onAction={() => {
            window.location.hash = '#/chat';
          }}
        />
      </>
    ) : undefined;

  return (
    <>
      {toastMessage && <div style={toastStyle}><Info size={16} /> {toastMessage}</div>}

      <ModulePageLayout className="approvals-page" aside={listAside}>
        <ModuleHero
          accent="rose"
          icon={<ClipboardCheck size={28} />}
          title="Central de Aprovações"
          description="Solicitações, decisões e liberações operacionais com linguagem simples e auditoria registrada."
          kodaMessage="Priorize o que está urgente no painel ao lado. Eu te ajudo a não perder prazos importantes."
          compact={activeTab === 'create'}
          actions={
            <>
              <Button variant="secondary" onClick={fetchData} title="Atualizar dados" leftIcon={<RefreshCw size={16} className={loading ? 'spin-anim' : ''} />}>
                Atualizar
              </Button>
              <Button variant="primary" onClick={() => { selectTab('create'); setFormStep(1); }} leftIcon={<Plus size={16} />}>
                Nova solicitação
              </Button>
            </>
          }
        />

        {activeTab !== 'create' && (
          <div className="metric-grid">
            <MetricCard icon={<Clock size={22} />} label="Pendentes" value={summary.total_pending} iconColor="amber" />
            <MetricCard icon={<AlertCircle size={22} />} label="Aguardando minha decisão" value={summary.waiting_my_decision} iconColor="violet" />
            <MetricCard icon={<AlertTriangle size={22} />} label="Urgentes" value={urgentCount} iconColor="rose" />
            <MetricCard icon={<CheckCircle2 size={22} />} label="Aprovadas recentemente" value={summary.approved_recent} iconColor="emerald" />
            <MetricCard icon={<XOctagon size={22} />} label="Rejeitadas recentemente" value={summary.rejected_recent} iconColor="rose" />
          </div>
        )}

        <div className="approvals-tabs">
          <button type="button" className={`approvals-tab-btn ${activeTab === 'list' ? 'active' : ''}`} onClick={() => selectTab('list')}>
            Todas as solicitações
          </button>
          <button type="button" className={`approvals-tab-btn ${activeTab === 'create' ? 'active' : ''}`} onClick={() => { selectTab('create'); setFormStep(1); }}>
            <Plus size={14} /> Nova solicitação
          </button>
        </div>

      {activeTab === 'create' ? (
        <Card variant="glass" style={{ maxWidth: 720, margin: '0 auto', padding: 24 }}>
          <h3 style={{ marginTop: 0, color: '#f8fafc', marginBottom: 24, fontSize: 18, fontWeight: 600 }}>Nova solicitação de aprovação</h3>
          
          {/* Stepper Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32, padding: '0 8px' }}>
            {[
              { num: 1, label: 'Tipo & Alocação' },
              { num: 2, label: 'Identificação' },
              { num: 3, label: 'Dados Adicionais' }
            ].map((s, index, arr) => (
              <React.Fragment key={s.num}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    backgroundColor: formStep >= s.num ? 'var(--primary-color)' : 'rgba(255,255,255,0.05)',
                    color: formStep >= s.num ? '#000' : '#94a3b8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 'bold',
                    fontSize: 12,
                    border: formStep === s.num ? '2px solid #fff' : 'none'
                  }}>
                    {s.num}
                  </div>
                  <span style={{ fontSize: 13, fontWeight: formStep === s.num ? 600 : 400, color: formStep >= s.num ? '#fff' : '#64748b' }}>
                    {s.label}
                  </span>
                </div>
                {index < arr.length - 1 && (
                  <div style={{ flex: 1, height: 2, backgroundColor: formStep > s.num ? 'var(--primary-color)' : 'rgba(255,255,255,0.05)', margin: '0 12px', minWidth: 20 }}></div>
                )}
              </React.Fragment>
            ))}
          </div>

          {createError && <div style={errorBoxStyle}><AlertTriangle size={16} /> {createError}</div>}
          
          <form onSubmit={handleCreateApproval} className="approval-form">
            {/* Step 1: Request Template and Context */}
            {formStep === 1 && (
              <div style={formGridStyle}>
                <Select 
                  label="Tipo de solicitação" 
                  value={templateKey} 
                  onChange={(event) => {
                    setTemplateKey(event.target.value as TemplateKey);
                    setFormValues({});
                  }}
                  options={Object.keys(requestTemplates).map((key) => ({
                    value: key,
                    label: approvalActionTypeLabels[key] || key
                  }))}
                />
                <Input label="Área responsável" value={approvalModuleLabels[template.module] || template.module} disabled />
                <Input label="Importância / Risco" value={approvalRiskLabels[template.risk] || template.risk} disabled />
                <Input 
                  label="Prazo para decisão (Dias)" 
                  type="number" 
                  min={1} 
                  max={90} 
                  value={expiresDays} 
                  onChange={(event) => setExpiresDays(Number(event.target.value) || 1)} 
                />
              </div>
            )}

            {/* Step 2: Identification and Purpose */}
            {formStep === 2 && (
              <div style={{ display: 'grid', gap: 20 }}>
                <Input 
                  label="Título curto e claro *" 
                  value={title} 
                  onChange={(event) => setTitle(event.target.value)} 
                  placeholder="Ex: Licença anual do software de CAD" 
                  required
                />
                <Textarea 
                  label="Motivo detalhado" 
                  value={reason} 
                  onChange={(event) => setReason(event.target.value)} 
                  rows={4}
                  placeholder="Explique resumidamente por que esta aprovação é necessária..."
                />
              </div>
            )}

            {/* Step 3: Dynamic Template Fields and Technical Details */}
            {formStep === 3 && (
              <div style={{ display: 'grid', gap: 20 }}>
                <h4 style={{ margin: '0 0 4px 0', color: 'var(--primary-color)', fontSize: 14, fontWeight: 600 }}>
                  Preencha as informações detalhadas da solicitação:
                </h4>
                
                {template.fields.length === 0 ? (
                  <p style={{ color: '#94a3b8', fontSize: 13, margin: '8px 0 16px' }}>Nenhum campo adicional é exigido para este tipo de solicitação.</p>
                ) : (
                  <div style={formGridStyle}>
                    {template.fields.map((field) => (
                      <div key={field.key}>
                        {field.textarea ? (
                          <Textarea 
                            label={field.label}
                            rows={3} 
                            value={formValues[field.key] || ''} 
                            onChange={(event) => setFormValues({ ...formValues, [field.key]: event.target.value })}
                            placeholder={field.placeholder}
                          />
                        ) : (
                          <Input 
                            label={field.label}
                            type={field.type || 'text'} 
                            value={formValues[field.key] || ''} 
                            onChange={(event) => setFormValues({ ...formValues, [field.key]: event.target.value })}
                            placeholder={field.placeholder}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                )}
                
                {canSeeTechnicalData && (
                  <details open={showTechnicalCreate} onToggle={(event) => setShowTechnicalCreate(event.currentTarget.open)} style={detailsStyle}>
                    <summary style={{ cursor: 'pointer', fontSize: 13, color: '#94a3b8', fontWeight: 500 }}>
                      Ver dados técnicos da solicitação
                    </summary>
                    <div style={{ marginTop: 12 }}>
                      <pre style={preStyle}>{JSON.stringify(builtPayload, null, 2)}</pre>
                    </div>
                  </details>
                )}
              </div>
            )}
            
            {/* Stepper Footer / Actions */}
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 32, borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
              {formStep > 1 ? (
                <Button 
                  variant="ghost" 
                  type="button" 
                  onClick={() => setFormStep(formStep - 1)}
                >
                  Voltar
                </Button>
              ) : (
                <div />
              )}
              
              {formStep < 3 ? (
                <Button 
                  variant="primary" 
                  type="button" 
                  onClick={() => {
                    if (formStep === 2 && !title.trim()) {
                      setCreateError('O título curto é obrigatório.');
                      return;
                    }
                    setCreateError(null);
                    setFormStep(formStep + 1);
                  }}
                >
                  Avançar
                </Button>
              ) : (
                <Button 
                  variant="primary" 
                  type="submit" 
                  disabled={!backendOnline} 
                  leftIcon={<Plus size={15} />}
                >
                  Criar solicitação
                </Button>
              )}
            </div>
          </form>
        </Card>
      ) : (
        <div style={{ display: 'grid', gap: 20 }}>
          <Card variant="glass" className="approval-filters-card">
            <div style={formGridStyle}>
              <Input 
                label="Pesquisar solicitação" 
                value={searchTerm} 
                onChange={(event) => setSearchTerm(event.target.value)} 
                placeholder="Ex: Título ou motivo..." 
                leftIcon={<Search size={16} />}
              />
              <Select 
                label="Status" 
                value={filterStatus} 
                onChange={(event) => setFilterStatus(event.target.value)}
                options={[
                  { value: 'ALL', label: 'Todos os status' },
                  ...Object.entries(approvalStatusLabels).map(([key, text]) => ({ value: key, label: text }))
                ]}
              />
              <Select 
                label="Importância / Risco" 
                value={filterRisk} 
                onChange={(event) => setFilterRisk(event.target.value)}
                options={[
                  { value: 'ALL', label: 'Todos os riscos' },
                  ...Object.entries(approvalRiskLabels).map(([key, text]) => ({ value: key, label: text }))
                ]}
              />
              <Select 
                label="Área responsável" 
                value={filterModule} 
                onChange={(event) => setFilterModule(event.target.value)}
                options={[
                  { value: 'ALL', label: 'Todas as áreas' },
                  ...Object.entries(approvalModuleLabels).map(([key, text]) => ({ value: key, label: text }))
                ]}
              />
            </div>
          </Card>

          <Card variant="glass" style={{ padding: 0, overflow: 'hidden' }}>
            {!backendOnline ? (
              <EmptyState 
                icon={<AlertCircle size={40} style={{ color: '#ef4444' }} />}
                title="API Desconectada" 
                description="O servidor de aprovações está offline no momento. Ative a API para continuar."
                actionText="Tentar reconectar"
                onAction={fetchData}
              />
            ) : loading ? (
              <div style={{ padding: 32 }}>
                <LoadingState variant="skeleton" text="Buscando solicitações..." />
              </div>
            ) : filteredApprovals.length === 0 ? (
              <EmptyState 
                icon={<CheckCircle size={40} style={{ color: '#10b981' }} />}
                title="Nenhuma pendência encontrada" 
                description={searchTerm ? "Nenhuma solicitação corresponde à sua busca atual." : "Todas as solicitações de aprovação foram processadas!"}
              />
            ) : (
              <div className="approval-card-list">
                {filteredApprovals.map((approval) => (
                  <article key={approval.id} className="approval-row-card glass-card">
                    <div>
                      <h3 className="approval-row-card__title">{approval.title}</h3>
                      <div className="approval-row-card__meta">
                        <Clock size={12} />
                        <span>{formatDate(approval.created_at)}</span>
                      </div>
                    </div>
                    <div className="approval-row-card__col">
                      {labelOrValue(approvalActionTypeLabels, approval.action_type)}
                    </div>
                    <div className="approval-row-card__col">
                      {labelOrValue(approvalModuleLabels, approval.module_slug)}
                    </div>
                    <div className="approval-row-card__col">
                      <span className={riskClass(approval.risk_level)}>{approvalRiskLabels[approval.risk_level]}</span>
                    </div>
                    <div className="approval-row-card__col">
                      <StatusPill status={approval.status} />
                    </div>
                    <div className="approval-row-card__col">
                      {approval.requester_username || 'Solicitante'}
                    </div>
                    <div className="approval-row-card__actions">
                      {canDecide(approval) && approval.status === 'PENDING' && (
                        <>
                          <Button variant="success" size="sm" onClick={() => approve(approval)} leftIcon={<Check size={13} />}>
                            Aprovar
                          </Button>
                          <Button variant="danger" size="sm" onClick={() => { openApproval(approval); setShowRejectModal(true); }} leftIcon={<X size={13} />}>
                            Rejeitar
                          </Button>
                        </>
                      )}
                      <Button variant="ghost" size="sm" onClick={() => openApproval(approval)} leftIcon={<Eye size={13} />}>
                        Ver
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
      </ModulePageLayout>

      {selectedApproval && (
        <Drawer
          open={!!selectedApproval}
          onClose={closeApproval}
          title={selectedApproval.title}
          description={`Solicitação #${selectedApproval.id}`}
          footer={modalFooter}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 24 }}>
            <div style={{ display: 'grid', gap: 20 }}>
              <section>
                <h4 style={sectionTitleStyle}>Justificativa da Solicitação</h4>
                <p style={{ color: '#e2e8f0', fontSize: 14, lineHeight: 1.6, marginTop: 8 }}>
                  {selectedApproval.description || 'Nenhuma justificativa textual fornecida.'}
                </p>
                
                <h4 style={{ ...sectionTitleStyle, marginTop: 20 }}>Conteúdo da Solicitação</h4>
                {selectedApproval.action_type === 'FINANCIAL_RELEASE'
                  ? renderFinancialRelease(selectedApproval)
                  : selectedApproval.action_payload?.request_type === 'purchase_options'
                  ? renderPurchaseOptions(selectedApproval)
                  : renderFriendlyDetails(selectedApproval.action_payload)}

                {selectedApproval.action_payload?.agent_recommendation && (
                  <div style={{ ...infoBoxStyle, display: 'flex', alignItems: 'center', gap: 12, border: '1px solid rgba(14,165,233,0.3)', background: 'rgba(14,165,233,0.06)', borderRadius: 10, padding: 16, marginTop: 16 }}>
                    <ShoppingCart size={20} style={{ color: '#0ea5e9', flexShrink: 0 }} />
                    <div>
                      <div style={{ fontSize: 12, color: '#0ea5e9', fontWeight: 600, textTransform: 'uppercase', letterSpacing: 0.5 }}>Recomendação do Supervisor IA</div>
                      <div style={{ color: '#e0f2fe', fontSize: 13, marginTop: 2 }}>{selectedApproval.action_payload.agent_recommendation}</div>
                    </div>
                  </div>
                )}

                {selectedApproval.result_payload && (
                  <div style={{ ...successBoxStyle, display: 'flex', alignItems: 'center', gap: 10, padding: 14, borderRadius: 10, marginTop: 16 }}>
                    <CheckCircle2 size={18} style={{ color: '#22c55e' }} />
                    <div style={{ fontSize: 13 }}>
                      <strong>Decisão registrada:</strong> {selectedApproval.result_payload.selected_option_title || selectedApproval.result_payload.decision_type || 'Decisão Salva com sucesso.'}
                    </div>
                  </div>
                )}
              </section>

              <section style={{ borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
                <h4 style={sectionTitleStyle}>
                  <MessageSquare size={14} /> <span>Comentários ({selectedApproval.comments?.length || 0})</span>
                </h4>
                <div style={{ display: 'grid', gap: 12, marginTop: 12, maxHeight: 200, overflowY: 'auto', paddingRight: 6 }}>
                  {selectedApproval.comments?.length ? (
                    selectedApproval.comments.map((comment) => (
                      <div key={comment.id} style={{ background: 'rgba(255, 255, 255, 0.02)', borderRadius: 8, padding: 12, border: '1px solid rgba(255, 255, 255, 0.04)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <strong style={{ color: '#f8fafc', fontSize: 12 }}>{comment.username || `Usuário #${comment.user_id}`}</strong>
                          <span style={{ color: '#64748b', fontSize: 11 }}>{formatDate(comment.created_at)}</span>
                        </div>
                        <div style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.4 }}>{comment.comment}</div>
                      </div>
                    ))
                  ) : (
                    <p style={{ color: '#64748b', fontSize: 13, margin: 0 }}>Nenhum comentário adicionado ainda.</p>
                  )}
                </div>
                <form onSubmit={addComment} style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                  <Input 
                    value={newComment} 
                    onChange={(event) => setNewComment(event.target.value)} 
                    placeholder="Escreva sua dúvida ou comentário técnico..." 
                    style={{ flex: 1, marginBottom: 0 }}
                  />
                  <Button variant="primary" type="submit" style={{ flexShrink: 0 }} disabled={!newComment.trim()}>
                    <Send size={14} />
                  </Button>
                </form>
              </section>
            </div>

            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: 20 }}>
              <h4 style={sectionTitleStyle}>Ficha de Metadados</h4>
              <div style={{ marginTop: 12, display: 'grid', gap: 4 }}>
                <InfoRow label="Identificador" value={`#${selectedApproval.id}`} />
                <InfoRow label="Tipo de Ação" value={labelOrValue(approvalActionTypeLabels, selectedApproval.action_type)} />
                <InfoRow label="Área / Módulo" value={labelOrValue(approvalModuleLabels, selectedApproval.module_slug)} />
                <InfoRow label="Importância" value={approvalRiskLabels[selectedApproval.risk_level]} />
                <InfoRow label="Solicitado por" value={selectedApproval.requester_username || `Usuário #${selectedApproval.requester_user_id}`} />
                <InfoRow label="Criado em" value={formatDate(selectedApproval.created_at)} />
                <InfoRow label="Expira em" value={formatDate(selectedApproval.expires_at)} />
              </div>

              <h4 style={{ ...sectionTitleStyle, marginTop: 24 }}>Linha do Tempo</h4>
              <div style={{ marginTop: 16, display: 'grid', gap: 16 }}>
                {selectedApproval.decisions?.map((decision) => (
                  <div key={decision.id} style={{ display: 'flex', gap: 12 }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <div style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: decision.decision === 'APPROVED' ? '#10b981' : '#ef4444',
                        marginTop: 6
                      }} />
                      <div style={{ width: 1, flex: 1, background: 'var(--border-color)', minHeight: 16 }} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>
                        {approvalStatusLabels[decision.decision] || decision.decision}
                      </div>
                      <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
                        por {decision.username || `Usuário #${decision.decided_by_user_id}`}
                      </div>
                      {decision.reason && (
                        <p style={{ margin: '4px 0 0', color: '#cbd5e1', fontSize: 12, fontStyle: 'italic' }}>
                          "{decision.reason}"
                        </p>
                      )}
                      <div style={{ fontSize: 10, color: '#64748b', marginTop: 4 }}>
                        {formatDate(decision.created_at)}
                      </div>
                    </div>
                  </div>
                ))}
                <div style={{ display: 'flex', gap: 12 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <div style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: '#3b82f6',
                      marginTop: 6
                    }} />
                  </div>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#f8fafc' }}>Abertura da Solicitação</div>
                    <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                      {formatDate(selectedApproval.created_at)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Drawer>
      )}

      {showRejectModal && selectedApproval && (
        <Modal
          isOpen={true}
          onClose={() => setShowRejectModal(false)}
          title="Rejeitar Solicitação"
          size="sm"
          footer={
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, width: '100%' }}>
              <Button variant="danger" onClick={reject} disabled={!rejectReason.trim()}>
                Confirmar rejeição
              </Button>
              <Button variant="secondary" onClick={() => setShowRejectModal(false)}>
                Cancelar
              </Button>
            </div>
          }
        >
          <div style={{ display: 'grid', gap: 14 }}>
            <p style={{ color: '#cbd5e1', fontSize: 13, margin: 0 }}>
              Explique brevemente por que você está rejeitando esta solicitação. Essa justificativa ficará salva no histórico de auditoria.
            </p>
            <Textarea 
              label="Justificativa da rejeição"
              rows={4} 
              value={rejectReason} 
              onChange={(event) => setRejectReason(event.target.value)} 
              placeholder="Ex: Fora do orçamento planejado para este mês..."
              required
            />
            {selectedApproval.action_payload?.request_type === 'purchase_options' && (
              <Checkbox 
                label="Solicitar nova cotação de compras" 
                checked={requestNewSearch} 
                onChange={(event) => setRequestNewSearch(event.target.checked)} 
              />
            )}
          </div>
        </Modal>
      )}

      <ConfirmDialog
        isOpen={cancelConfirmOpen}
        onClose={() => { setCancelConfirmOpen(false); setApprovalToCancel(null); }}
        onConfirm={async () => {
          if (approvalToCancel) {
            const approval = approvalToCancel;
            setCancelConfirmOpen(false);
            setApprovalToCancel(null);
            await proceedCancelApproval(approval);
          }
        }}
        title="Cancelar Solicitação"
        message={`Deseja realmente cancelar a solicitação "${approvalToCancel?.title}"?`}
        confirmText="Confirmar"
        cancelText="Voltar"
        variant="danger"
      />
    </>
  );
};

const InfoRow = ({ label, value }: { label: string; value: string }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, padding: '8px 0', borderBottom: '1px solid rgba(255, 255, 255, 0.04)', color: '#cbd5e1' }}>
    <span style={{ color: '#64748b', fontSize: 13 }}>{label}</span>
    <strong style={{ textAlign: 'right', fontSize: 13, color: '#f8fafc' }}>{value}</strong>
  </div>
);

const humanizeKey = (key: string) => {
  const dictionary: Record<string, string> = {
    item_or_service: 'Item ou Serviço',
    quantity: 'Quantidade',
    estimated_value: 'Valor Estimado',
    requesting_department: 'Setor Solicitante',
    reason: 'Justificativa',
    urgency: 'Urgência',
    notes: 'Observações',
    desired_item: 'Item Desejado',
    max_price: 'Preço Máximo',
    criteria: 'Critérios',
    desired_deadline: 'Prazo Desejado',
    found_options: 'Opções Encontradas',
    comparison: 'Comparação Comercial',
    recommendation: 'Recomendação',
    decision_owner: 'Responsável pela Decisão',
    client: 'Cliente',
    value: 'Valor',
    product_or_service: 'Produto / Serviço',
    proposal_link: 'Link da Proposta',
    user: 'Usuário',
    system_access: 'Sistema a Acessar',
    access_type: 'Tipo de Acesso',
    risk: 'Risco Avaliado',
    system: 'Sistema',
    subject: 'Assunto',
    impact: 'Impacto Planejado',
  };
  return dictionary[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
};

const formatCurrency = (value: any, currency: string) => {
  const number = Number(value);
  if (Number.isNaN(number)) return 'Preço não informado';
  return number.toLocaleString('pt-BR', { style: 'currency', currency });
};

const riskClass = (risk: string) => {
  if (risk === 'CRITICAL') return 'badge badge-danger';
  if (risk === 'HIGH') return 'badge badge-warning';
  if (risk === 'MEDIUM') return 'badge badge-primary';
  return 'badge badge-neutral';
};

const formGridStyle: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 };
const sectionTitleStyle: React.CSSProperties = { fontSize: 12, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', gap: 6, alignItems: 'center', fontWeight: 600, borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: 6 };
const detailsStyle: React.CSSProperties = { border: '1px solid var(--border-color)', borderRadius: 8, padding: 12, color: '#cbd5e1', marginTop: 14 };
const preStyle: React.CSSProperties = { background: 'rgba(0,0,0,0.3)', borderRadius: 8, padding: 12, overflowX: 'auto', color: '#67e8f9', fontSize: 12, fontFamily: 'monospace', border: '1px solid rgba(255,255,255,0.04)' };
const toastStyle: React.CSSProperties = { position: 'fixed', right: 24, bottom: 24, zIndex: 10000, display: 'flex', gap: 8, alignItems: 'center', padding: '14px 18px', borderRadius: 10, background: 'rgba(59,130,246,0.95)', color: '#fff', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', fontSize: 14, fontWeight: 500 };
const errorBoxStyle: React.CSSProperties = { display: 'flex', gap: 8, alignItems: 'center', color: '#fca5a5', background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 8, padding: 12, marginBottom: 14, fontSize: 13 };
const infoBoxStyle: React.CSSProperties = { display: 'flex', gap: 8, alignItems: 'center', color: '#bae6fd', background: 'rgba(14,165,233,0.12)', border: '1px solid rgba(14,165,233,0.25)', borderRadius: 8, padding: 12, marginTop: 12 };
const successBoxStyle: React.CSSProperties = { color: '#bbf7d0', background: 'rgba(34,197,94,0.12)', border: '1px solid rgba(34,197,94,0.25)', borderRadius: 8, padding: 12, marginTop: 12 };
