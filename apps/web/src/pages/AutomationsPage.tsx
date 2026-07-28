import React, { useEffect, useState, useMemo } from 'react';
import {
  Cpu,
  Clock,
  Eye,
  Check,
  X,
  AlertTriangle,
  Search,
  ShieldAlert,
  HelpCircle,
  RefreshCw,
  Info,
  Lock,
  Calendar,
  Layers,
  Activity,
  UserCheck,
} from 'lucide-react';
import { ModuleHero } from '../components/ui/ModuleHero';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { ModulePageLayout } from '../components/layout/ModulePageLayout';
import { HelpCard } from '../components/layout/HelpCard';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Card } from '../components/ui/Card';
import { MetricCard } from '../components/ui/MetricCard';
import { EmptyState } from '../components/ui/EmptyState';
import { Modal } from '../components/ui/Modal';
import { Drawer } from '../components/ui/Drawer';
import { LoadingState } from '../components/ui/LoadingState';
import { Textarea } from '../components/ui/Textarea';
import { getQueryParam, replaceQueryParams } from '../utils/urlState';

interface ActionIntentItem {
  id: string;
  source: string;
  source_ref_type?: string;
  source_ref_id?: string;
  proposed_action: string;
  target_module: string;
  target_type?: string;
  target_id?: string;
  title: string;
  summary: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'PENDING_REVIEW' | 'APPROVAL_REQUIRED' | 'APPROVED' | 'REJECTED' | 'CANCELLED' | 'EXECUTION_BLOCKED' | 'EXECUTED' | 'FAILED';
  action_payload: Record<string, any>;
  result_payload?: Record<string, any>;
  reason?: string;
  approval_id?: number;
  callback_log_id?: string;
  event_id?: string;
  created_by_user_id?: number;
  reviewed_by_user_id?: number;
  created_at: string;
  reviewed_at?: string;
  executed_at?: string;
  expires_at?: string;
  correlation_id?: string;
}

interface ReactionRuleItem {
  id: string;
  name: string;
  description?: string;
  event_type: string;
  module: string;
  enabled: boolean;
  priority: number;
  condition_json: Record<string, any>;
  action_type: string;
  action_payload: Record<string, any>;
  cooldown_seconds?: number;
  max_runs_per_hour?: number;
  created_at: string;
}

interface ReactionRuleRunItem {
  id: string;
  rule_id: string;
  event_id: string;
  status: 'SKIPPED' | 'MATCHED' | 'EXECUTED' | 'FAILED' | 'BLOCKED';
  condition_result: boolean;
  action_result?: Record<string, any>;
  error_message?: string;
  created_at: string;
  executed_at?: string;
  correlation_id?: string;
}

const humanizeRunStatus = (status: string) => {
  switch (status) {
    case 'SKIPPED': return { label: 'Ignorada', variant: 'neutral' };
    case 'MATCHED': return { label: 'Compatível', variant: 'pending' };
    case 'EXECUTED': return { label: 'Executada', variant: 'approved' };
    case 'FAILED': return { label: 'Falhou', variant: 'rejected' };
    case 'BLOCKED': return { label: 'Bloqueada', variant: 'expired' };
    default: return { label: status, variant: 'neutral' };
  }
};

interface AutomationsPageProps {
  currentUser: {
    id: number;
    username: string;
    email: string;
    role: string;
  } | null;
  onBack?: () => void;
}

// Mapeamentos de humanização
const humanizeStatus = (status: string) => {
  switch (status) {
    case 'PENDING_REVIEW': return { label: 'Revisão pendente', variant: 'pending' };
    case 'APPROVAL_REQUIRED': return { label: 'Aprovação necessária', variant: 'pending' };
    case 'APPROVED': return { label: 'Revisado', variant: 'approved' };
    case 'REJECTED': return { label: 'Rejeitado', variant: 'rejected' };
    case 'CANCELLED': return { label: 'Cancelado', variant: 'expired' };
    case 'EXECUTION_BLOCKED': return { label: 'Execução bloqueada', variant: 'expired' };
    case 'EXECUTED': return { label: 'Executado', variant: 'approved' };
    case 'FAILED': return { label: 'Falhou', variant: 'rejected' };
    default: return { label: status, variant: 'neutral' };
  }
};

const humanizeRisk = (risk: string) => {
  switch (risk) {
    case 'LOW': return { label: 'Baixo', className: 'risk-low' };
    case 'MEDIUM': return { label: 'Médio', className: 'risk-medium' };
    case 'HIGH': return { label: 'Alto', className: 'risk-high' };
    case 'CRITICAL': return { label: 'Crítico', className: 'risk-critical' };
    default: return { label: risk, className: '' };
  }
};

const humanizeModule = (mod: string) => {
  switch (mod) {
    case 'approvals': return 'Aprovações';
    case 'purchases': return 'Compras';
    case 'stock': return 'Estoque';
    case 'proposals': return 'Propostas';
    case 'it': return 'TI';
    case 'kanban': return 'Kanban';
    default: return mod;
  }
};

const humanizeAction = (action: string) => {
  switch (action) {
    case 'reveal_secret': return 'Revelar segredo';
    case 'change_permission': return 'Alterar permissão';
    case 'delete_file': return 'Apagar arquivo';
    case 'approve_payment': return 'Aprovar pagamento';
    case 'approve_approval': return 'Aprovar solicitação';
    case 'reject_approval': return 'Rejeitar solicitação';
    case 'create_purchase_order': return 'Criar ordem de compra';
    case 'update_stock': return 'Atualizar estoque';
    case 'send_email_to_client': return 'Enviar e-mail para cliente';
    case 'send_email_to_supplier': return 'Enviar e-mail para fornecedor';
    case 'create_kanban_card': return 'Criar card no Kanban';
    case 'create_it_ticket': return 'Abrir chamado de TI';
    case 'update_proposal_status': return 'Atualizar status de proposta';
    case 'create_draft': return 'Criar rascunho';
    case 'summarize': return 'Resumir texto';
    case 'classify': return 'Classificar';
    case 'notify': return 'Notificar';
    case 'suggest': return 'Sugerir';
    default: return action;
  }
};

const humanizeSource = (src: string) => {
  switch (src) {
    case 'n8n': return 'Automação n8n';
    case 'koda': return 'Supervisor Koda';
    case 'reaction_engine': return 'Motor de Reação';
    case 'system': return 'Sistema';
    case 'user': return 'Usuário';
    default: return src;
  }
};

export const getActionExecutability = (action: string) => {
  const act = action.toLowerCase();
  const safeActions = ["notify", "create_draft", "classify", "summarize", "suggest"];
  const blockedActions = [
    "send_email_to_client", "send_email_to_supplier", "update_stock", "create_purchase_order",
    "approve_approval", "reject_approval", "reveal_secret", "change_permission", "delete_file"
  ];
  if (safeActions.includes(act)) {
    return { label: 'Executável', variant: 'executable', className: 'badge-executable' };
  }
  if (blockedActions.includes(act)) {
    return { label: 'Bloqueada', variant: 'blocked', className: 'badge-blocked' };
  }
  return { label: 'Futura', variant: 'future', className: 'badge-future' };
};

const formatDate = (value?: string) => {
  if (!value) return 'Não informado';
  return new Date(value).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
};

export const AutomationsPage: React.FC<AutomationsPageProps> = ({ currentUser, onBack }) => {
  const [actionIntents, setActionIntents] = useState<ActionIntentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Abas
  const initialTabParam = getQueryParam('tab');
  const initialTab = initialTabParam === 'rules' || initialTabParam === 'runs' ? initialTabParam : 'intents';
  const [activeTab, setActiveTab] = useState<'intents' | 'rules' | 'runs'>(initialTab);

  // Regras de Automação
  const [rules, setRules] = useState<ReactionRuleItem[]>([]);
  const [loadingRules, setLoadingRules] = useState<boolean>(false);
  const [errorRules, setErrorRules] = useState<string | null>(null);
  const [filterRuleStatus, setFilterRuleStatus] = useState<string>('ALL');
  const [filterRuleEvent, setFilterRuleEvent] = useState<string>('ALL');
  const [filterRuleAction, setFilterRuleAction] = useState<string>('ALL');
  const [searchRuleTerm, setSearchRuleTerm] = useState<string>('');

  // Histórico de Reações (Runs)
  const [runs, setRuns] = useState<ReactionRuleRunItem[]>([]);
  const [loadingRuns, setLoadingRuns] = useState<boolean>(false);
  const [errorRuns, setErrorRuns] = useState<string | null>(null);
  const [filterRunStatus, setFilterRunStatus] = useState<string>('ALL');
  const [filterRunEvent, setFilterRunEvent] = useState<string>('ALL');
  const [searchRunTerm, setSearchRunTerm] = useState<string>('');
  const [selectedRun, setSelectedRun] = useState<ReactionRuleRunItem | null>(null);

  // Filtros de Ações Sugeridas
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterRisk, setFilterRisk] = useState('ALL');
  const [filterSource, setFilterSource] = useState('ALL');
  const [filterModule, setFilterModule] = useState('ALL');

  // Seleções & Modais
  const [selectedIntent, setSelectedIntent] = useState<ActionIntentItem | null>(null);
  const [showRejectModal, setShowRejectModal] = useState<boolean>(false);
  const [rejectReason, setRejectReason] = useState<string>('');
  const [showConfirmReviewed, setShowConfirmReviewed] = useState<boolean>(false);
  const [reviewReason, setReviewReason] = useState<string>('');

  const isAuthorized = currentUser?.role === 'ADMIN' || currentUser?.role === 'MANAGER';

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4500);
  };

  const selectTab = (tab: 'intents' | 'rules' | 'runs') => {
    setActiveTab(tab);
    setSelectedIntent(null);
    setSelectedRun(null);
    replaceQueryParams({ tab: tab === 'intents' ? null : tab, intent: null, run: null });
  };

  const openIntent = (intent: ActionIntentItem) => {
    setSelectedRun(null);
    setSelectedIntent(intent);
    replaceQueryParams({ tab: null, intent: intent.id, run: null });
  };

  const closeIntent = () => {
    setSelectedIntent(null);
    replaceQueryParams({ intent: null });
  };

  const openRun = (run: ReactionRuleRunItem) => {
    setSelectedIntent(null);
    setSelectedRun(run);
    replaceQueryParams({ tab: 'runs', run: run.id, intent: null });
  };

  const closeRun = () => {
    setSelectedRun(null);
    replaceQueryParams({ run: null });
  };

  const fetchIntents = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/action-intents');
      if (!response.ok) {
        if (response.status === 403) {
          setError('Acesso negado. Recurso restrito a administradores ou gerentes.');
        } else {
          setError('Erro ao carregar as ações sugeridas do servidor.');
        }
        return;
      }
      const data = await response.json();
      setActionIntents(data);
    } catch {
      setError('Não foi possível se conectar ao servidor.');
    } finally {
      setLoading(false);
    }
  };

  const fetchRules = async () => {
    setLoadingRules(true);
    setErrorRules(null);
    try {
      const response = await fetch('/api/v1/reactions/rules');
      if (!response.ok) {
        if (response.status === 403) {
          setErrorRules('Acesso negado. Recurso restrito a administradores ou gerentes.');
        } else {
          setErrorRules('Erro ao carregar as regras de reação.');
        }
        return;
      }
      const data = await response.json();
      setRules(data);
    } catch {
      setErrorRules('Erro de conexão ao carregar as regras.');
    } finally {
      setLoadingRules(false);
    }
  };

  const fetchRuns = async () => {
    setLoadingRuns(true);
    setErrorRuns(null);
    try {
      const response = await fetch('/api/v1/reactions/runs');
      if (!response.ok) {
        if (response.status === 403) {
          setErrorRuns('Acesso negado. Recurso restrito a administradores ou gerentes.');
        } else {
          setErrorRuns('Erro ao carregar o histórico de execuções.');
        }
        return;
      }
      const data = await response.json();
      setRuns(data);
    } catch {
      setErrorRuns('Erro de conexão ao carregar o histórico.');
    } finally {
      setLoadingRuns(false);
    }
  };

  const handleToggleRule = async (ruleId: string, currentEnabled: boolean) => {
    try {
      const response = await fetch(`/api/v1/reactions/rules/${ruleId}/enabled`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !currentEnabled }),
      });
      if (!response.ok) {
        const errData = await response.json();
        showToast(errData.detail || 'Falha ao alterar status da regra.');
        return;
      }
      showToast(`Regra ${!currentEnabled ? 'ativada' : 'desativada'} com sucesso.`);
      setRules(prevRules =>
        prevRules.map(r => r.id === ruleId ? { ...r, enabled: !currentEnabled } : r)
      );
    } catch {
      showToast('Erro de conexão ao alterar status da regra.');
    }
  };

  useEffect(() => {
    if (isAuthorized) {
      if (activeTab === 'intents') {
        fetchIntents();
      } else if (activeTab === 'rules') {
        fetchRules();
      } else if (activeTab === 'runs') {
        fetchRuns();
        if (rules.length === 0) {
          fetchRules();
        }
      }
    }
  }, [activeTab, isAuthorized]);

  useEffect(() => {
    const intentId = getQueryParam('intent');
    if (!intentId || selectedIntent) return;
    const intent = actionIntents.find((item) => item.id === intentId);
    if (intent) setSelectedIntent(intent);
  }, [actionIntents, selectedIntent]);

  useEffect(() => {
    const runId = getQueryParam('run');
    if (!runId || selectedRun) return;
    const run = runs.find((item) => item.id === runId);
    if (run) setSelectedRun(run);
  }, [runs, selectedRun]);

  // Ações da API
  const handleReject = async () => {
    if (!selectedIntent || !rejectReason.trim()) return;
    try {
      const response = await fetch(`/api/v1/action-intents/${selectedIntent.id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: rejectReason }),
      });
      if (!response.ok) {
        const errData = await response.json();
        showToast(errData.detail || 'Falha ao rejeitar ação sugerida.');
        return;
      }
      showToast('Ação sugerida rejeitada com sucesso.');
      setShowRejectModal(false);
      setRejectReason('');
      closeIntent();
      fetchIntents();
    } catch {
      showToast('Erro de conexão ao rejeitar ação.');
    }
  };

  const handleMarkReviewed = async () => {
    if (!selectedIntent) return;
    try {
      const response = await fetch(`/api/v1/action-intents/${selectedIntent.id}/mark-reviewed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reviewReason.trim() || undefined }),
      });
      if (!response.ok) {
        const errData = await response.json();
        showToast(errData.detail || 'Falha ao marcar como revisada.');
        return;
      }
      showToast('Ação marcada como revisada com sucesso.');
      setShowConfirmReviewed(false);
      setReviewReason('');
      closeIntent();
      fetchIntents();
    } catch {
      showToast('Erro de conexão ao salvar revisão.');
    }
  };

  const handleDryRun = async () => {
    if (!selectedIntent) return;
    try {
      const response = await fetch(`/api/v1/action-intents/${selectedIntent.id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dry_run: true }),
      });
      if (!response.ok) {
        const errData = await response.json();
        showToast(errData.detail || 'Falha ao executar dry run.');
        return;
      }
      const data = await response.json();
      if (data.status === 'BLOCKED') {
        showToast('Dry run concluído: Ação perigosa seria BLOQUEADA.');
      } else {
        showToast('Dry run concluído: Ação seria executada com sucesso.');
      }
    } catch {
      showToast('Erro de conexão ao testar dry run.');
    }
  };

  const handleExecute = async () => {
    if (!selectedIntent) return;
    try {
      const response = await fetch(`/api/v1/action-intents/${selectedIntent.id}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dry_run: false }),
      });
      if (!response.ok) {
        const errData = await response.json();
        showToast(errData.detail || 'Falha ao executar ação.');
        return;
      }
      showToast('Ação executada com sucesso de forma segura.');
      closeIntent();
      fetchIntents();
    } catch {
      showToast('Erro de conexão ao executar ação.');
    }
  };

  // Filtragem local
  const filteredIntents = useMemo(() => {
    return actionIntents.filter((intent) => {
      const matchesSearch =
        intent.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        intent.summary.toLowerCase().includes(searchTerm.toLowerCase()) ||
        intent.proposed_action.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = filterStatus === 'ALL' || intent.status === filterStatus;
      const matchesRisk = filterRisk === 'ALL' || intent.risk_level === filterRisk;
      const matchesSource = filterSource === 'ALL' || intent.source === filterSource;
      const matchesModule = filterModule === 'ALL' || intent.target_module === filterModule;

      return matchesSearch && matchesStatus && matchesRisk && matchesSource && matchesModule;
    });
  }, [actionIntents, searchTerm, filterStatus, filterRisk, filterSource, filterModule]);

  const filteredRules = useMemo(() => {
    return rules.filter((rule) => {
      const matchesSearch =
        rule.name.toLowerCase().includes(searchRuleTerm.toLowerCase()) ||
        (rule.description || '').toLowerCase().includes(searchRuleTerm.toLowerCase());
      const matchesStatus =
        filterRuleStatus === 'ALL' ||
        (filterRuleStatus === 'ACTIVE' && rule.enabled) ||
        (filterRuleStatus === 'INACTIVE' && !rule.enabled);
      const matchesEvent = filterRuleEvent === 'ALL' || rule.event_type === filterRuleEvent;
      const matchesAction = filterRuleAction === 'ALL' || rule.action_type === filterRuleAction;

      return matchesSearch && matchesStatus && matchesEvent && matchesAction;
    });
  }, [rules, searchRuleTerm, filterRuleStatus, filterRuleEvent, filterRuleAction]);

  const filteredRuns = useMemo(() => {
    return runs.filter((run) => {
      const rule = rules.find((r) => r.id === run.rule_id);
      const ruleName = rule ? rule.name : '';
      const matchesSearch =
        ruleName.toLowerCase().includes(searchRunTerm.toLowerCase()) ||
        run.rule_id.toLowerCase().includes(searchRunTerm.toLowerCase()) ||
        (run.error_message || '').toLowerCase().includes(searchRunTerm.toLowerCase());
      const matchesStatus = filterRunStatus === 'ALL' || run.status === filterRunStatus;
      const matchesEvent = filterRunEvent === 'ALL' || (rule ? rule.event_type === filterRunEvent : false);

      return matchesSearch && matchesStatus && matchesEvent;
    });
  }, [runs, rules, searchRunTerm, filterRunStatus, filterRunEvent]);

  // Lista de tipos de eventos e ações para opções dos seletores
  const ruleEventTypes = useMemo(() => {
    const events = new Set<string>();
    rules.forEach(r => events.add(r.event_type));
    return Array.from(events);
  }, [rules]);

  const runEventTypes = useMemo(() => {
    const events = new Set<string>();
    runs.forEach(run => {
      const rule = rules.find(r => r.id === run.rule_id);
      if (rule) {
        events.add(rule.event_type);
      }
    });
    return Array.from(events);
  }, [runs, rules]);

  const ruleActionTypes = useMemo(() => {
    const actions = new Set<string>();
    rules.forEach(r => actions.add(r.action_type));
    return Array.from(actions);
  }, [rules]);

  // Contagem para Métricas
  const metrics = useMemo(() => {
    const total = actionIntents.length;
    const pending = actionIntents.filter((i) => i.status === 'PENDING_REVIEW' || i.status === 'APPROVAL_REQUIRED').length;
    const reviewed = actionIntents.filter((i) => i.status === 'APPROVED' || i.status === 'EXECUTED').length;
    const critical = actionIntents.filter(
      (i) => (i.status === 'PENDING_REVIEW' || i.status === 'APPROVAL_REQUIRED') && (i.risk_level === 'CRITICAL' || i.risk_level === 'HIGH')
    ).length;

    return { total, pending, reviewed, critical };
  }, [actionIntents]);

  // Lista de itens urgentes
  const urgentIntents = useMemo(() => {
    return actionIntents
      .filter((i) => (i.status === 'PENDING_REVIEW' || i.status === 'APPROVAL_REQUIRED') && (i.risk_level === 'CRITICAL' || i.risk_level === 'HIGH'))
      .slice(0, 5);
  }, [actionIntents]);

  // Acesso negado visual
  if (!isAuthorized) {
    return (
      <div style={errorPageStyles.container}>
        <div style={errorPageStyles.iconContainer}>
          <ShieldAlert size={40} style={{ color: '#ef4444' }} />
        </div>
        <h2 style={errorPageStyles.title}>Acesso Negado</h2>
        <p style={errorPageStyles.message}>
          A seção de **Revisão de Automações** é restrita a administradores e gerentes para auditoria de segurança das ações sugeridas.
        </p>
        <button style={errorPageStyles.button} onClick={onBack}>
          Voltar para o Dashboard
        </button>
      </div>
    );
  }

  const execInfo = selectedIntent ? getActionExecutability(selectedIntent.proposed_action) : null;

  const drawerFooter = selectedIntent ? (
    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, width: '100%' }}>
      {(selectedIntent.status === 'PENDING_REVIEW' || selectedIntent.status === 'APPROVAL_REQUIRED') && (
        <>
          <Button
            variant="success"
            size="md"
            onClick={() => setShowConfirmReviewed(true)}
            leftIcon={<Check size={14} />}
          >
            Marcar como revisado
          </Button>
          <Button
            variant="danger"
            size="md"
            onClick={() => setShowRejectModal(true)}
            leftIcon={<X size={14} />}
          >
            Rejeitar
          </Button>
        </>
      )}
      {selectedIntent.status === 'APPROVED' && (
        <>
          <Button
            variant="secondary"
            size="md"
            onClick={handleDryRun}
            leftIcon={<Activity size={14} />}
          >
            Testar Simulação
          </Button>
          {execInfo?.variant === 'executable' && (
            <Button
              variant="success"
              size="md"
              onClick={handleExecute}
              leftIcon={<Check size={14} />}
            >
              Executar
            </Button>
          )}
        </>
      )}
      <Button variant="secondary" size="md" onClick={closeIntent}>
        Fechar
      </Button>
    </div>
  ) : undefined;

  const listAside = (
    <>
      {activeTab === 'intents' && (
        <section className="automation-side-card glass-card" style={{ padding: 16, borderRadius: 12, border: '1px solid var(--border-color)' }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: 6 }}>
            <ShieldAlert size={16} style={{ color: '#ef4444' }} />
            <span>Ações críticas ({metrics.critical})</span>
          </h3>
          {urgentIntents.length === 0 ? (
            <p style={{ margin: '12px 0 0', color: 'var(--text-muted)', fontSize: 13 }}>
              Nenhuma ação crítica ou de alto risco necessita de moderação urgente.
            </p>
          ) : (
            <div className="automation-urgent-list">
              {urgentIntents.map((intent) => (
                <button
                  key={intent.id}
                  type="button"
                  className="automation-urgent-item"
                  onClick={() => openIntent(intent)}
                >
                  <strong>{intent.title}</strong>
                  <span>
                    {humanizeRisk(intent.risk_level).label} · {humanizeModule(intent.target_module)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </section>
      )}

      {activeTab === 'rules' && (
        <section className="automation-side-card glass-card" style={{ padding: 16, borderRadius: 12, border: '1px solid var(--border-color)' }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Layers size={16} style={{ color: 'var(--color-primary)' }} />
            <span>Motor de Reações</span>
          </h3>
          <p style={{ margin: '12px 0 0', color: 'var(--text-muted)', fontSize: 13, lineHeight: 1.5 }}>
            O Reaction Engine opera sob o padrão <strong>Event-Condition-Action (ECA)</strong>. Ele observa o barramento de eventos internos e aciona reações pré-programadas de forma segura.
          </p>
          <div style={{ marginTop: 12, padding: 10, background: 'rgba(255,255,255,0.02)', borderRadius: 8, border: '1px solid var(--border-color)', fontSize: 12, color: 'var(--text-secondary)' }}>
            <strong>Ações Seguras:</strong> Notificar usuários, gerar rascunhos de propostas, criar Action Intents. Ações perigosas são bloqueadas automaticamente.
          </div>
        </section>
      )}

      {activeTab === 'runs' && (
        <section className="automation-side-card glass-card" style={{ padding: 16, borderRadius: 12, border: '1px solid var(--border-color)' }}>
          <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#fff', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Activity size={16} style={{ color: 'var(--color-primary)' }} />
            <span>Auditoria de Logs</span>
          </h3>
          <p style={{ margin: '12px 0 0', color: 'var(--text-muted)', fontSize: 13, lineHeight: 1.5 }}>
            Cada tentativa de execução é registrada detalhadamente. Você pode auditar se a condição foi atendida, quais dados foram coletados e se a ação foi disparada com sucesso ou bloqueada.
          </p>
        </section>
      )}

      <HelpCard
        description="O motor de intenções de ação (Action Intent) garante que nenhuma automação ou IA altere o banco de dados diretamente em ações sensíveis corporativas sem prévia auditoria."
        actionLabel="Ver Documentação"
        onAction={() => {
          showToast('Abrindo documentação do motor...');
        }}
      />
    </>
  );

  return (
    <>
      {toastMessage && <div style={toastStyle}><Info size={16} /> {toastMessage}</div>}

      <ModulePageLayout className="automations-page" aside={listAside}>
        <ModuleHero
          accent="violet"
          icon={<Cpu size={28} />}
          title="Revisão de Automações"
          description="Monitore e valide ações sugeridas pelo n8n, Koda ou robôs internos de forma segura."
          kodaMessage="Olá! Sou o Koda. Eu ajudo a preparar ações sugeridas, mas apenas você ou administradores podem aprovar as ações de alto risco!"
          actions={
            <Button
              variant="secondary"
              onClick={() => {
                if (activeTab === 'intents') fetchIntents();
                else if (activeTab === 'rules') fetchRules();
                else if (activeTab === 'runs') fetchRuns();
              }}
              title="Atualizar lista"
              leftIcon={<RefreshCw size={16} className={(loading || loadingRules || loadingRuns) ? 'spin-anim' : ''} />}
            >
              Atualizar
            </Button>
          }
        />

        {/* Abas de Navegação */}
        <div className="automations-tabs">
          <button
            type="button"
            className={`automations-tab-btn ${activeTab === 'intents' ? 'active' : ''}`}
            onClick={() => selectTab('intents')}
          >
            <Cpu size={16} />
            <span>Ações sugeridas</span>
          </button>
          <button
            type="button"
            className={`automations-tab-btn ${activeTab === 'rules' ? 'active' : ''}`}
            onClick={() => selectTab('rules')}
            id="tab-rules-btn"
          >
            <Layers size={16} />
            <span>Regras de Automação</span>
          </button>
          <button
            type="button"
            className={`automations-tab-btn ${activeTab === 'runs' ? 'active' : ''}`}
            onClick={() => selectTab('runs')}
            id="tab-runs-btn"
          >
            <Activity size={16} />
            <span>Histórico de Reações</span>
          </button>
        </div>

        {/* Métricas Adaptativas por Aba */}
        {activeTab === 'intents' && (
          <div className="metric-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 20 }}>
            <MetricCard icon={<Clock size={22} />} label="Ações pendentes" value={metrics.pending} iconColor="amber" />
            <MetricCard icon={<UserCheck size={22} />} label="Revisadas" value={metrics.reviewed} iconColor="emerald" />
            <MetricCard icon={<ShieldAlert size={22} />} label="Moderadas urgente" value={metrics.critical} iconColor="rose" />
            <MetricCard icon={<Activity size={22} />} label="Cadastradas no log" value={metrics.total} iconColor="cyan" />
          </div>
        )}

        {activeTab === 'rules' && (
          <div className="metric-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 20 }}>
            <MetricCard icon={<Layers size={22} />} label="Total de Regras" value={rules.length} iconColor="violet" />
            <MetricCard icon={<Check size={22} />} label="Regras Ativas" value={rules.filter(r => r.enabled).length} iconColor="emerald" />
            <MetricCard icon={<X size={22} />} label="Regras Inativas" value={rules.filter(r => !r.enabled).length} iconColor="rose" />
          </div>
        )}

        {activeTab === 'runs' && (
          <div className="metric-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 20 }}>
            <MetricCard icon={<Activity size={22} />} label="Total de Execuções" value={runs.length} iconColor="cyan" />
            <MetricCard icon={<Check size={22} />} label="Executadas" value={runs.filter(r => r.status === 'EXECUTED').length} iconColor="emerald" />
            <MetricCard icon={<X size={22} />} label="Falhas / Bloqueios" value={runs.filter(r => r.status === 'FAILED' || r.status === 'BLOCKED').length} iconColor="rose" />
          </div>
        )}

        <div style={{ display: 'grid', gap: 20 }}>
          {/* ABA 1: INTENTS (AÇÕES SUGERIDAS) */}
          {activeTab === 'intents' && (
            <>
              <Card variant="glass" className="automations-filters-card">
                <div style={filterGridStyle}>
                  <Input
                    label="Pesquisar ação sugerida"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder="Pesquise por título ou ação..."
                    leftIcon={<Search size={16} />}
                  />
                  <Select
                    label="Status da revisão"
                    value={filterStatus}
                    onChange={(event) => setFilterStatus(event.target.value)}
                    options={[
                      { value: 'ALL', label: 'Todos os status' },
                      { value: 'PENDING_REVIEW', label: 'Revisão pendente' },
                      { value: 'APPROVAL_REQUIRED', label: 'Aprovação necessária' },
                      { value: 'APPROVED', label: 'Aprovado' },
                      { value: 'REJECTED', label: 'Rejeitado' },
                      { value: 'EXECUTION_BLOCKED', label: 'Execução bloqueada' },
                      { value: 'EXECUTED', label: 'Executado' },
                      { value: 'FAILED', label: 'Falhou' }
                    ]}
                  />
                  <Select
                    label="Importância / Risco"
                    value={filterRisk}
                    onChange={(event) => setFilterRisk(event.target.value)}
                    options={[
                      { value: 'ALL', label: 'Todos os riscos' },
                      { value: 'LOW', label: 'Baixo' },
                      { value: 'MEDIUM', label: 'Médio' },
                      { value: 'HIGH', label: 'Alto' },
                      { value: 'CRITICAL', label: 'Crítico' }
                    ]}
                  />
                  <Select
                    label="Origem proposta"
                    value={filterSource}
                    onChange={(event) => setFilterSource(event.target.value)}
                    options={[
                      { value: 'ALL', label: 'Todas as origens' },
                      { value: 'n8n', label: 'Automação n8n' },
                      { value: 'koda', label: 'Supervisor Koda' },
                      { value: 'reaction_engine', label: 'Motor de Reação' },
                      { value: 'system', label: 'Sistema' }
                    ]}
                  />
                  <Select
                    label="Área alvo"
                    value={filterModule}
                    onChange={(event) => setFilterModule(event.target.value)}
                    options={[
                      { value: 'ALL', label: 'Todas as áreas' },
                      { value: 'approvals', label: 'Aprovações' },
                      { value: 'purchases', label: 'Compras' },
                      { value: 'stock', label: 'Estoque' },
                      { value: 'proposals', label: 'Propostas' },
                      { value: 'it', label: 'TI' },
                      { value: 'kanban', label: 'Kanban' }
                    ]}
                  />
                </div>
              </Card>

              <Card variant="glass" style={{ padding: 0, overflow: 'hidden' }}>
                {loading ? (
                  <div style={{ padding: 32 }}>
                    <LoadingState variant="skeleton" text="Buscando histórico de automações..." />
                  </div>
                ) : error ? (
                  <EmptyState
                    icon={<AlertTriangle size={40} style={{ color: '#ef4444' }} />}
                    title="Erro de Carregamento"
                    description={error}
                    actionText="Tentar novamente"
                    onAction={fetchIntents}
                  />
                ) : filteredIntents.length === 0 ? (
                  <EmptyState
                    icon={<Cpu size={40} style={{ color: 'var(--color-primary)' }} />}
                    title="Nenhuma ação sugerida encontrada"
                    description={searchTerm ? "Nenhuma intenção coincide com a busca atual." : "Sem ações pendentes das automações corporativas!"}
                  />
                ) : (
                  <div className="automation-card-list">
                    {filteredIntents.map((intent) => {
                      const statusInfo = humanizeStatus(intent.status);
                      const riskInfo = humanizeRisk(intent.risk_level);
                      const execInfo = getActionExecutability(intent.proposed_action);
                      return (
                        <article key={intent.id} className="automation-row-card glass-card">
                          <div>
                            <h3 className="automation-row-card__title">{intent.title}</h3>
                            <div className="automation-row-card__meta">
                              <Calendar size={12} />
                              <span>{formatDate(intent.created_at)}</span>
                            </div>
                          </div>
                          <div className="automation-row-card__col">
                            {humanizeSource(intent.source)}
                          </div>
                          <div className="automation-row-card__col">
                            {humanizeModule(intent.target_module)}
                          </div>
                          <div className="automation-row-card__col">
                            <span className={`risk-badge ${riskInfo.className}`}>{riskInfo.label}</span>
                          </div>
                          <div className="automation-row-card__col">
                            <span className={`status-pill status-${statusInfo.variant}`}>{statusInfo.label}</span>
                          </div>
                          <div className="automation-row-card__col">
                            <span className={`exec-badge ${execInfo.className}`}>{execInfo.label}</span>
                          </div>
                          <div className="automation-row-card__actions">
                            {(intent.status === 'PENDING_REVIEW' || intent.status === 'APPROVAL_REQUIRED') && (
                              <>
                                <Button
                                  variant="success"
                                  size="sm"
                                  onClick={() => {
                                    openIntent(intent);
                                    setShowConfirmReviewed(true);
                                  }}
                                  leftIcon={<Check size={13} />}
                                  title="Marcar revisado"
                                >
                                  Revisar
                                </Button>
                                <Button
                                  variant="danger"
                                  size="sm"
                                  onClick={() => {
                                    openIntent(intent);
                                    setShowRejectModal(true);
                                  }}
                                  leftIcon={<X size={13} />}
                                  title="Rejeitar"
                                >
                                  Rejeitar
                                </Button>
                              </>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openIntent(intent)}
                              leftIcon={<Eye size={13} />}
                            >
                              Ver
                            </Button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </Card>
            </>
          )}

          {/* ABA 2: REGRAS DE AUTOMAÇÃO */}
          {activeTab === 'rules' && (
            <>
              <Card variant="glass" className="automations-filters-card">
                <div style={filterGridStyle}>
                  <Input
                    label="Pesquisar regra de automação"
                    value={searchRuleTerm}
                    onChange={(event) => setSearchRuleTerm(event.target.value)}
                    placeholder="Pesquise por nome ou descrição..."
                    leftIcon={<Search size={16} />}
                  />
                  <Select
                    label="Status da regra"
                    value={filterRuleStatus}
                    onChange={(event) => setFilterRuleStatus(event.target.value)}
                    options={[
                      { value: 'ALL', label: 'Todos os status' },
                      { value: 'ACTIVE', label: 'Ativas' },
                      { value: 'INACTIVE', label: 'Inativas' }
                    ]}
                  />
                  <Select
                    label="Evento observado"
                    value={filterRuleEvent}
                    onChange={(event) => setFilterRuleEvent(event.target.value)}
                    options={[
                      { value: 'ALL', label: 'Todos os eventos' },
                      ...ruleEventTypes.map(e => ({ value: e, label: e }))
                    ]}
                  />
                  <Select
                    label="Ação executada"
                    value={filterRuleAction}
                    onChange={(event) => setFilterRuleAction(event.target.value)}
                    options={[
                      { value: 'ALL', label: 'Todas as ações' },
                      ...ruleActionTypes.map(a => ({ value: a, label: humanizeAction(a) }))
                    ]}
                  />
                </div>
              </Card>

              <Card variant="glass" style={{ padding: 0, overflow: 'hidden' }}>
                {loadingRules ? (
                  <div style={{ padding: 32 }}>
                    <LoadingState variant="skeleton" text="Carregando regras do motor de reações..." />
                  </div>
                ) : errorRules ? (
                  <EmptyState
                    icon={<AlertTriangle size={40} style={{ color: '#ef4444' }} />}
                    title="Erro de Carregamento"
                    description={errorRules}
                    actionText="Tentar novamente"
                    onAction={fetchRules}
                  />
                ) : filteredRules.length === 0 ? (
                  <EmptyState
                    icon={<Layers size={40} style={{ color: 'var(--color-primary)' }} />}
                    title="Nenhuma regra de reação encontrada"
                    description={searchRuleTerm ? "Nenhuma regra coincide com a busca." : "Sem regras de reações cadastradas no motor!"}
                  />
                ) : (
                  <div className="automation-card-list">
                    {filteredRules.map((rule) => {
                      const execInfo = getActionExecutability(rule.action_type);
                      return (
                        <article key={rule.id} className="automation-row-card glass-card">
                          <div>
                            <h3 className="automation-row-card__title">{rule.name}</h3>
                            {rule.description && (
                              <p style={{ margin: '2px 0 6px', color: 'var(--text-secondary)', fontSize: 13 }}>
                                {rule.description}
                              </p>
                            )}
                            <div className="automation-row-card__meta">
                              <Calendar size={12} />
                              <span>{formatDate(rule.created_at)}</span>
                            </div>
                          </div>
                          <div className="automation-row-card__col">
                            {humanizeModule(rule.module)}
                          </div>
                          <div className="automation-row-card__col" style={{ color: 'var(--color-primary)', fontWeight: 600 }}>
                            {rule.event_type}
                          </div>
                          <div className="automation-row-card__col">
                            {humanizeAction(rule.action_type)}
                          </div>
                          <div className="automation-row-card__col">
                            Prioridade: {rule.priority}
                          </div>
                          <div className="automation-row-card__col">
                            <span className={`rule-status-badge rule-${rule.enabled ? 'active' : 'inactive'}`}>
                              {rule.enabled ? 'Ativa' : 'Inativa'}
                            </span>
                          </div>
                          <div className="automation-row-card__col">
                            <span className={`exec-badge ${execInfo.className}`} title={execInfo.label === 'Bloqueada' ? 'Bloqueada por segurança' : 'Ação permitida'}>
                              {execInfo.label === 'Bloqueada' ? 'Restrita' : 'Segura'}
                            </span>
                          </div>
                          <div className="automation-row-card__actions" style={{ alignItems: 'center', gap: 12 }}>
                            <button
                              type="button"
                              className={`switch-toggle ${rule.enabled ? 'switch-on' : 'switch-off'}`}
                              onClick={() => handleToggleRule(rule.id, rule.enabled)}
                              aria-label={rule.enabled ? "Desativar regra" : "Ativar regra"}
                              id={`toggle-rule-${rule.id}`}
                            >
                              <span className="switch-slider" />
                            </button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </Card>
            </>
          )}

          {/* ABA 3: HISTÓRICO DE REAÇÕES */}
          {activeTab === 'runs' && (
            <>
              <Card variant="glass" className="automations-filters-card">
                <div style={filterGridStyle}>
                  <Input
                    label="Pesquisar no histórico"
                    value={searchRunTerm}
                    onChange={(event) => setSearchRunTerm(event.target.value)}
                    placeholder="Pesquise por ID, regra ou erro..."
                    leftIcon={<Search size={16} />}
                  />
                  <Select
                    label="Status do processamento"
                    value={filterRunStatus}
                    onChange={(event) => setFilterRunStatus(event.target.value)}
                    options={[
                      { value: 'ALL', label: 'Todos os status' },
                      { value: 'SKIPPED', label: 'Ignorada (Filtro condition)' },
                      { value: 'MATCHED', label: 'Compatível' },
                      { value: 'EXECUTED', label: 'Executada com sucesso' },
                      { value: 'FAILED', label: 'Falhou' },
                      { value: 'BLOCKED', label: 'Bloqueada por segurança' }
                    ]}
                  />
                  <Select
                    label="Evento de gatilho"
                    value={filterRunEvent}
                    onChange={(event) => setFilterRunEvent(event.target.value)}
                    options={[
                      { value: 'ALL', label: 'Todos os eventos' },
                      ...runEventTypes.map(e => ({ value: e, label: e }))
                    ]}
                  />
                </div>
              </Card>

              <Card variant="glass" style={{ padding: 0, overflow: 'hidden' }}>
                {loadingRuns ? (
                  <div style={{ padding: 32 }}>
                    <LoadingState variant="skeleton" text="Buscando logs históricos de reações..." />
                  </div>
                ) : errorRuns ? (
                  <EmptyState
                    icon={<AlertTriangle size={40} style={{ color: '#ef4444' }} />}
                    title="Erro de Carregamento"
                    description={errorRuns}
                    actionText="Tentar novamente"
                    onAction={fetchRuns}
                  />
                ) : filteredRuns.length === 0 ? (
                  <EmptyState
                    icon={<Activity size={40} style={{ color: 'var(--color-primary)' }} />}
                    title="Nenhuma execução registrada"
                    description={searchRunTerm ? "Nenhum log histórico coincide com a busca." : "Nenhum evento disparou reações ainda!"}
                  />
                ) : (
                  <div className="automation-card-list" id="runs-list-container">
                    {filteredRuns.map((run) => {
                      const rule = rules.find((r) => r.id === run.rule_id);
                      const statusInfo = humanizeRunStatus(run.status);
                      return (
                        <article key={run.id} className="automation-row-card glass-card">
                          <div>
                            <h3 className="automation-row-card__title" style={{ fontSize: 14 }}>
                              {rule ? rule.name : `Regra: ${run.rule_id}`}
                            </h3>
                            <div className="automation-row-card__meta">
                              <Clock size={12} />
                              <span>{formatDate(run.created_at)}</span>
                            </div>
                          </div>
                          <div className="automation-row-card__col">
                            {rule ? rule.event_type : 'Evento desconhecido'}
                          </div>
                          <div className="automation-row-card__col">
                            <span className={`status-pill status-${statusInfo.variant}`}>{statusInfo.label}</span>
                          </div>
                          <div className="automation-row-card__col" style={{ gridColumn: 'span 2', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {run.status === 'FAILED' && (
                              <span style={{ color: '#f87171', fontSize: 12 }}>
                                Erro: {run.error_message}
                              </span>
                            )}
                            {run.status === 'BLOCKED' && (
                              <span style={{ color: '#fecaca', fontSize: 12 }}>
                                Bloqueio de segurança
                              </span>
                            )}
                            {run.status === 'EXECUTED' && (
                              <span style={{ color: '#34d399', fontSize: 12 }}>
                                Executada com sucesso
                              </span>
                            )}
                            {run.status === 'SKIPPED' && (
                              <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                                Filtros lógicos não correspondentes
                              </span>
                            )}
                          </div>
                          <div className="automation-row-card__actions">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openRun(run)}
                              leftIcon={<Eye size={13} />}
                              id={`view-run-btn-${run.id}`}
                            >
                              Detalhes
                            </Button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </Card>
            </>
          )}
        </div>
      </ModulePageLayout>

      {/* Drawer de Detalhes */}
      {selectedIntent && (
        <Drawer
          open={!!selectedIntent}
          onClose={closeIntent}
          title={selectedIntent.title}
          description={`Identificador de Automação: ${selectedIntent.id}`}
          footer={drawerFooter}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 20 }}>
            <section>
              <h4 style={sectionTitleStyle}>Resumo da Ação</h4>
              <p style={{ color: '#e2e8f0', fontSize: 14, lineHeight: 1.6, marginTop: 6 }}>
                {selectedIntent.summary}
              </p>

              {/* Box de Ação Bloqueada */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, border: '1px solid rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.05)', borderRadius: 10, padding: 12, marginTop: 16 }}>
                <Lock size={16} style={{ color: '#f87171', flexShrink: 0 }} />
                <div style={{ fontSize: 13, color: '#fecaca' }}>
                  <strong>Ação de Negócio Bloqueada:</strong> A execução real de compras, estoque, e-mail e permissões está desativada nesta fase para proteção dos dados operacionais e será liberada no futuro. Ações seguras revisadas podem ser simuladas ou executadas via painel.
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 20, borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
                <div>
                  <span style={metadataLabelStyle}>Origem</span>
                  <strong style={metadataValueStyle}>{humanizeSource(selectedIntent.source)}</strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Executabilidade</span>
                  <strong style={metadataValueStyle}>
                    <span className={`exec-badge ${getActionExecutability(selectedIntent.proposed_action).className}`}>
                      {getActionExecutability(selectedIntent.proposed_action).label}
                    </span>
                  </strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Data de Entrada</span>
                  <strong style={metadataValueStyle}>{formatDate(selectedIntent.created_at)}</strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Área Alvo</span>
                  <strong style={metadataValueStyle}>{humanizeModule(selectedIntent.target_module)}</strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Ação Proposta</span>
                  <strong style={metadataValueStyle}>{humanizeAction(selectedIntent.proposed_action)}</strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Nível de Risco</span>
                  <strong style={metadataValueStyle}>{humanizeRisk(selectedIntent.risk_level).label}</strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Status da Revisão</span>
                  <strong style={metadataValueStyle}>{humanizeStatus(selectedIntent.status).label}</strong>
                </div>
                {selectedIntent.target_id && (
                  <div>
                    <span style={metadataLabelStyle}>Objeto Alvo (ID)</span>
                    <strong style={metadataValueStyle}>{selectedIntent.target_id} ({selectedIntent.target_type || 'Geral'})</strong>
                  </div>
                )}
                {selectedIntent.approval_id && (
                  <div>
                    <span style={metadataLabelStyle}>Relacionado à Solicitação</span>
                    <strong style={metadataValueStyle}>Aprovação de Negócio #{selectedIntent.approval_id}</strong>
                  </div>
                )}
              </div>

              {selectedIntent.reason && (
                <div style={{ marginTop: 16, padding: 12, backgroundColor: 'rgba(255,255,255,0.02)', borderLeft: '3px solid var(--color-primary)', borderRadius: 4 }}>
                  <span style={metadataLabelStyle}>Motivo / Justificativa da Moderação</span>
                  <p style={{ margin: '4px 0 0', color: '#e2e8f0', fontSize: 13 }}>{selectedIntent.reason}</p>
                </div>
              )}
            </section>

            <section style={{ borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
              <details style={detailsStyle}>
                <summary style={{ cursor: 'pointer', fontSize: 13, color: '#94a3b8', fontWeight: 500 }}>
                  Exibir dados brutos da intenção (Payload Técnico)
                </summary>
                <div style={{ marginTop: 12 }}>
                  <pre style={preStyle}>{JSON.stringify(selectedIntent.action_payload, null, 2)}</pre>
                </div>
              </details>
            </section>
          </div>
        </Drawer>
      )}

      {/* Drawer de Detalhes da Execução de Reação */}
      {selectedRun && (
        <Drawer
          open={!!selectedRun}
          onClose={closeRun}
          title="Auditoria de Execução de Reação"
          description={`Identificador da Execução: ${selectedRun.id}`}
          footer={
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, width: '100%' }}>
              <Button variant="secondary" size="md" onClick={closeRun}>
                Fechar Auditoria
              </Button>
            </div>
          }
        >
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 20 }}>
            <section>
              <h4 style={sectionTitleStyle}>Resumo do Disparo</h4>
              
              {/* Alerta de erro ou segurança */}
              {selectedRun.status === 'FAILED' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, border: '1px solid rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.05)', borderRadius: 10, padding: 12, marginTop: 12, marginBottom: 12 }}>
                  <AlertTriangle size={16} style={{ color: '#f87171', flexShrink: 0 }} />
                  <div style={{ fontSize: 13, color: '#fecaca' }}>
                    <strong>Falha de Execução:</strong> {selectedRun.error_message}
                  </div>
                </div>
              )}

              {selectedRun.status === 'BLOCKED' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, border: '1px solid rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.05)', borderRadius: 10, padding: 12, marginTop: 12, marginBottom: 12 }}>
                  <Lock size={16} style={{ color: '#f87171', flexShrink: 0 }} />
                  <div style={{ fontSize: 13, color: '#fecaca' }}>
                    <strong>Bloqueio de Segurança:</strong> Ação do tipo ECA perigosa foi impedida e bloqueada no motor de reação. Erro técnico: {selectedRun.error_message}
                  </div>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16, borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
                <div>
                  <span style={metadataLabelStyle}>Regra Mapeada</span>
                  <strong style={metadataValueStyle}>
                    {rules.find(r => r.id === selectedRun.rule_id)?.name || selectedRun.rule_id}
                  </strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Status da Execução</span>
                  <strong style={metadataValueStyle}>
                    <span className={`status-pill status-${humanizeRunStatus(selectedRun.status).variant}`}>
                      {humanizeRunStatus(selectedRun.status).label}
                    </span>
                  </strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Evento Observado</span>
                  <strong style={metadataValueStyle}>
                    {rules.find(r => r.id === selectedRun.rule_id)?.event_type || 'Desconhecido'}
                  </strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Avaliação da Condição</span>
                  <strong style={metadataValueStyle}>
                    {selectedRun.condition_result ? 'PASSOU (Verdadeira)' : 'PULADA (Falsa)'}
                  </strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Data de Entrada</span>
                  <strong style={metadataValueStyle}>{formatDate(selectedRun.created_at)}</strong>
                </div>
                <div>
                  <span style={metadataLabelStyle}>Data de Execução</span>
                  <strong style={metadataValueStyle}>{selectedRun.executed_at ? formatDate(selectedRun.executed_at) : 'N/A'}</strong>
                </div>
                {selectedRun.correlation_id && (
                  <div>
                    <span style={metadataLabelStyle}>ID de Correlação</span>
                    <strong style={{ ...metadataValueStyle, fontSize: 11, fontFamily: 'monospace' }}>{selectedRun.correlation_id}</strong>
                  </div>
                )}
                <div>
                  <span style={metadataLabelStyle}>ID do Evento Original</span>
                  <strong style={{ ...metadataValueStyle, fontSize: 11, fontFamily: 'monospace' }}>{selectedRun.event_id}</strong>
                </div>
              </div>
            </section>

            <section style={{ borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
              <details style={detailsStyle} id="details-technical-log">
                <summary style={{ cursor: 'pointer', fontSize: 13, color: '#94a3b8', fontWeight: 500 }}>
                  Exibir dados lógicos e resultado da ação
                </summary>
                <div style={{ marginTop: 12, display: 'grid', gap: 12 }}>
                  <div>
                    <span style={metadataLabelStyle}>Árvore de Condições (Regra)</span>
                    <pre style={preStyle}>
                      {JSON.stringify(rules.find(r => r.id === selectedRun.rule_id)?.condition_json || {}, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <span style={metadataLabelStyle}>Resultado Retornado (Action Result)</span>
                    <pre style={preStyle}>
                      {selectedRun.action_result ? JSON.stringify(selectedRun.action_result, null, 2) : '{}'}
                    </pre>
                  </div>
                </div>
              </details>
            </section>
          </div>
        </Drawer>
      )}

      {/* Modal de Rejeição */}
      <Modal
        isOpen={showRejectModal}
        onClose={() => {
          setShowRejectModal(false);
          setRejectReason('');
        }}
        title="Rejeitar Ação Sugerida"
      >
        <div className="modal-form-section">
          <p className="form-help-text" style={{ color: '#cbd5e1', fontSize: 13, marginBottom: 12 }}>
            Esta ação é sensível e será marcada como **REJEITADA** no Portal. Por favor, forneça o motivo da rejeição técnica para o histórico de auditoria:
          </p>
          <Textarea
            label="Justificativa da Rejeição *"
            value={rejectReason}
            onChange={(event) => setRejectReason(event.target.value)}
            placeholder="Ex: Callback n8n duplicado ou parâmetro incorreto..."
            required
            rows={3}
          />
          <div className="modal-actions" style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
            <Button
              variant="ghost"
              onClick={() => {
                setShowRejectModal(false);
                setRejectReason('');
              }}
            >
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={handleReject}
              disabled={!rejectReason.trim()}
            >
              Confirmar Rejeição
            </Button>
          </div>
        </div>
      </Modal>

      {/* ConfirmDialog de Revisão */}
      <ConfirmDialog
        isOpen={showConfirmReviewed}
        onClose={() => {
          setShowConfirmReviewed(false);
          setReviewReason('');
        }}
        onConfirm={handleMarkReviewed}
        title="Marcar Ação como Revisada"
        message="Deseja confirmar a revisão técnica desta intenção de automação? Isso atualizará o status para APROVADO, mas NÃO executará nenhuma operação de banco automática sobre o negócio real."
        confirmText="Confirmar Revisão"
        cancelText="Voltar"
      />
    </>
  );
};

// Estilizações inline de suporte
const sectionTitleStyle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 700,
  color: '#fff',
  borderBottom: '1px solid var(--border-color)',
  paddingBottom: '8px',
  margin: '0 0 10px 0',
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
};

const metadataLabelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '11px',
  color: '#94a3b8',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
};

const metadataValueStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '13px',
  color: '#fff',
  marginTop: '2px',
};

const detailsStyle: React.CSSProperties = {
  backgroundColor: 'rgba(0, 0, 0, 0.15)',
  border: '1px solid var(--border-color)',
  borderRadius: '8px',
  padding: '12px',
};

const preStyle: React.CSSProperties = {
  margin: 0,
  padding: '8px',
  backgroundColor: 'rgba(0, 0, 0, 0.25)',
  color: '#34d399',
  fontFamily: 'Fira Code, monospace',
  fontSize: '12px',
  overflowX: 'auto',
  borderRadius: '4px',
};

const toastStyle: React.CSSProperties = {
  position: 'fixed',
  bottom: '24px',
  right: '24px',
  backgroundColor: 'rgba(30, 41, 59, 0.9)',
  border: '1px solid rgba(168, 85, 247, 0.3)',
  color: '#fff',
  padding: '12px 18px',
  borderRadius: '8px',
  boxShadow: '0 10px 25px -5px rgba(0,0,0,0.3)',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  zIndex: 9999,
  fontFamily: 'Inter, sans-serif',
  fontSize: '13px',
};

const errorPageStyles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    textAlign: 'center',
    maxWidth: '520px',
    margin: '80px auto 0 auto',
    backgroundColor: 'rgba(30, 41, 59, 0.4)',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '16px',
    backdropFilter: 'blur(12px)',
  },
  iconContainer: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    padding: '16px',
    borderRadius: '50%',
    marginBottom: '24px',
    border: '1px solid rgba(239, 68, 68, 0.2)',
  },
  title: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#f9fafb',
    margin: '0 0 12px 0',
  },
  message: {
    fontSize: '15px',
    color: '#d1d5db',
    margin: '0 0 28px 0',
    lineHeight: '1.6',
  },
  button: {
    backgroundColor: '#8b5cf6',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 24px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  }
};

const filterGridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: '12px',
};

export default AutomationsPage;
