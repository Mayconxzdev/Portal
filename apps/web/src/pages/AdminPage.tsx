import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { 
  UserPlus, 
  Activity, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  UserCog, 
  Search,
  ShieldCheck,
  GitMerge,
  Layers,
  XCircle,
  ArrowRightLeft,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Switch } from '../components/ui/Switch';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { Modal } from '../components/ui/Modal';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { ErrorSummary } from '../components/ui/ErrorSummary';
import { InlineFieldError } from '../components/ui/InlineFieldError';
import { AdminKanbanPermissions } from '../components/admin/AdminKanbanPermissions';
import { ModulePageLayout } from '../components/layout/ModulePageLayout';
import { HelpCard } from '../components/layout/HelpCard';
import { LegacyImportPage } from './LegacyImportPage';
import { AdminRealDataDashboard } from '../components/legacy-import/AdminRealDataDashboard';
import { type ApiErrorState, normalizeApiError, readApiError } from '../lib/apiErrors';

// Extracted admin components and types
import { 
  UserItem, 
  RoleItem, 
  ModuleItem, 
  AuditLogItem, 
  AdminSessionItem, 
  AdminTemporaryAccessItem, 
  AdminTemporarySubstitutionItem, 
  AdminOffboardingImpact, 
  AdminOffboardingCase, 
  AccessProfilePreset 
} from '../components/admin/types';
import { AdminUsersList } from '../components/admin/AdminUsersList';
import { AdminUserCreationWorkspace } from '../components/admin/AdminUserCreationWorkspace';
import { AdminUserDrawer } from '../components/admin/AdminUserDrawer';
import { AdminProfilesWorkspace } from '../components/admin/AdminProfilesWorkspace';

const humanizeRole = (role: string | null) => {
  if (!role) return 'Sem papel';
  const dict: Record<string, string> = {
    'ADMIN': 'Administrador',
    'USER': 'Usuário',
    'COLLABORATOR': 'Colaborador',
    'APPROVER': 'Aprovador',
    'IT_TECH': 'Técnico de TI',
    'IT_ADMIN': 'Administrador de TI',
    'MESSIAS': 'Messias',
    'PURCHASER': 'Comprador',
    'SALES': 'Vendedor',
    'MANAGER': 'Gerente',
  };
  return dict[role.toUpperCase()] || role;
};

const displayEmail = (email?: string | null) => email || 'E-mail nao informado';
const isChatModule = (module: ModuleItem) => module.code === 'chat';

const generateTemporaryPassword = () => {
  const chunks = new Uint32Array(3);
  window.crypto.getRandomValues(chunks);
  return `Vesper-${Array.from(chunks).map((value) => value.toString(36).slice(0, 4)).join('-')}`;
};

type GuidedStep = 1 | 2 | 3;
type DrawerTab = 'summary' | 'access' | 'security' | 'sessions' | 'history' | 'role-change' | 'temporary-access' | 'offboarding';

const permissionLabels: Record<string, string> = {
  NO_ACCESS: 'Sem acesso',
  READ_ONLY: 'Pode visualizar',
  NORMAL: 'Pode criar e editar',
  MANAGER: 'Pode gerir e aprovar',
  ADMIN: 'Pode administrar',
};

const permissionRisk = (level: string) => {
  if (level === 'ADMIN') return 'Alto';
  if (level === 'MANAGER') return 'Medio';
  return 'Baixo';
};

const displayName = (user: UserItem) => user.full_name || user.username;

const suggestedProfiles: AccessProfilePreset[] = [
  {
    id: 'common',
    label: 'Usuario comum',
    roleNames: ['USER', 'COLLABORATOR'],
    description: 'Acesso basico para navegar no Portal e acompanhar suas tarefas.',
    purpose: 'Ideal para usuarios que precisam consultar informacoes e usar o Chat global.',
    risk: 'Baixo',
    accessLevelByModule: { dashboard: 'NORMAL', kanban: 'READ_ONLY', approvals: 'READ_ONLY' },
    positive: ['consultar o Dashboard', 'acompanhar itens permitidos', 'usar Chat e Koda'],
    negative: ['administrar usuarios', 'aprovar compras', 'revelar credenciais'],
  },
  {
    id: 'purchases',
    label: 'Compras',
    roleNames: ['PURCHASER', 'USER'],
    description: 'Para quem pesquisa, cota e acompanha aquisicoes.',
    purpose: 'Prepara acesso operacional a Compras, Estoque e Aprovações sem poder aprovar sozinho.',
    risk: 'Medio',
    accessLevelByModule: { purchases: 'NORMAL', stock: 'READ_ONLY', approvals: 'NORMAL', knowledge: 'READ_ONLY', files: 'READ_ONLY' },
    positive: ['criar e acompanhar cotacoes', 'consultar Estoque e Catalogo', 'criar pedidos internos', 'usar Chat e Koda'],
    negative: ['aprovar compras', 'revelar senhas', 'administrar usuarios'],
  },
  {
    id: 'production',
    label: 'Producao',
    roleNames: ['USER', 'COLLABORATOR'],
    description: 'Para acompanhamento de OPs, quadros e execucao de fabrica.',
    purpose: 'Permite trabalhar no Kanban/Producao sem acesso administrativo.',
    risk: 'Medio',
    accessLevelByModule: { kanban: 'NORMAL', stock: 'READ_ONLY', approvals: 'READ_ONLY' },
    positive: ['acompanhar quadros de producao', 'consultar materiais', 'usar Chat e Koda'],
    negative: ['administrar quadros', 'aprovar compras', 'gerenciar usuarios'],
  },
  {
    id: 'it',
    label: 'TI',
    roleNames: ['IT_TECH', 'IT_ADMIN', 'USER'],
    description: 'Para atendimento tecnico, ativos, chamados e acessos de TI.',
    purpose: 'Concede acesso ao Help Desk e leitura de contexto tecnico autorizado.',
    risk: 'Alto',
    accessLevelByModule: { it: 'MANAGER', admin: 'READ_ONLY', knowledge: 'READ_ONLY', files: 'READ_ONLY' },
    positive: ['atender chamados', 'consultar ativos', 'preparar acessos de TI', 'usar Chat e Koda'],
    negative: ['administrar todos os usuarios', 'aprovar compras sem alçada'],
    warnings: ['Pode envolver dados tecnicos e acessos sensiveis. Revise excecoes antes de confirmar.'],
  },
  {
    id: 'approver',
    label: 'Aprovador',
    roleNames: ['APPROVER', 'MANAGER', 'USER'],
    description: 'Para quem revisa e decide solicitacoes dentro da sua alcada.',
    purpose: 'Libera Aprovações com visibilidade de contexto, mantendo Admin separado.',
    risk: 'Alto',
    accessLevelByModule: { approvals: 'MANAGER', purchases: 'READ_ONLY', stock: 'READ_ONLY', kanban: 'READ_ONLY' },
    positive: ['analisar solicitacoes', 'aprovar dentro da alcada', 'consultar contexto relacionado'],
    negative: ['administrar usuarios', 'revelar credenciais protegidas'],
    warnings: ['Este acesso permite aprovar solicitacoes. Confirme a alcada fora deste fluxo se necessario.'],
  },
  {
    id: 'director',
    label: 'Diretoria',
    roleNames: ['MANAGER', 'APPROVER', 'USER'],
    description: 'Visao ampla para decisao executiva e aprovacao.',
    purpose: 'Amplia leitura e decisoes sem transformar a pessoa em administradora tecnica.',
    risk: 'Alto',
    accessLevelByModule: { dashboard: 'NORMAL', approvals: 'MANAGER', purchases: 'READ_ONLY', kanban: 'READ_ONLY', stock: 'READ_ONLY' },
    positive: ['ver contexto executivo', 'aprovar solicitacoes', 'acompanhar operacao'],
    negative: ['alterar configuracoes globais', 'gerenciar usuarios'],
  },
  {
    id: 'admin',
    label: 'Administrador',
    roleNames: ['ADMIN'],
    description: 'Controle administrativo do Portal.',
    purpose: 'Usar somente para quem realmente administra pessoas, acessos e seguranca.',
    risk: 'Critico',
    accessLevelByModule: {},
    positive: ['administrar usuarios', 'gerenciar configuracoes', 'alterar acessos'],
    negative: ['receber senha de outros usuarios', 'burlar confirmacoes sensiveis'],
    warnings: ['Este acesso permite administrar outros usuarios. Use com criterio.'],
  },
  {
    id: 'custom',
    label: 'Personalizado',
    roleNames: ['USER'],
    description: 'Comece com acesso basico e personalize excecoes.',
    purpose: 'Para casos temporarios ou fora dos perfis padrao.',
    risk: 'Medio',
    accessLevelByModule: { dashboard: 'NORMAL' },
    positive: ['usar Chat e Koda', 'receber somente excecoes revisadas'],
    negative: ['herdar acessos sem revisao'],
    warnings: ['Perfil personalizado exige revisao cuidadosa antes de salvar.'],
  },
];

interface AdminPageProps {
  currentUser?: any;
  onNavigate?: (moduleCode: string) => void;
}

export const AdminPage: React.FC<AdminPageProps> = ({ currentUser, onNavigate }) => {
  const params = new URLSearchParams(window.location.search);
  const initialTab = (params.get('tab') || 'users') as string;
  const initialPermissionSubTab = params.get('subtab') === 'kanban' ? 'kanban' : 'modules';

  const initialActiveTab = ['users', 'permissions', 'profiles', 'audit'].includes(initialTab) ? initialTab : 'users';
  const [activeTab, setActiveTab] = useState<'users' | 'permissions' | 'profiles' | 'audit' | 'real-data' | 'deduplication'>(initialActiveTab as any);
  const [permissionSubTab, setPermissionSubTab] = useState<'modules' | 'kanban'>(initialPermissionSubTab);
  const [realDataSubTab, setRealDataSubTab] = useState<'matrix' | 'import'>(initialTab === 'legacy-import' ? 'import' : 'matrix');

  // Estado de Deduplicação
  const [dedupItems, setDedupItems] = useState<any[]>([]);
  const [dedupLoading, setDedupLoading] = useState(false);
  const [dedupFilter, setDedupFilter] = useState<'PENDING' | 'ALL'>('PENDING');
  const [dedupResolving, setDedupResolving] = useState<string | null>(null);
  const [dedupNotes, setDedupNotes] = useState<Record<string, string>>({});
  const [users, setUsers] = useState<UserItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [modules, setModules] = useState<ModuleItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [customProfiles, setCustomProfiles] = useState<AccessProfilePreset[]>(suggestedProfiles);
  
  const [loading, setLoading] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Busca e Filtros de Usuários
  const [userSearch, setUserSearch] = useState('');
  const [userFilterRole, setUserFilterRole] = useState('ALL');
  const [userFilterStatus, setUserFilterStatus] = useState('ALL');

  // Busca e Filtros de Logs de Auditoria
  const [logSearch, setLogSearch] = useState('');
  const [logFilterModule, setLogFilterModule] = useState('ALL');
  const [logFilterAction, setLogFilterAction] = useState('ALL');
  const [logFilterUser, setLogFilterUser] = useState('ALL');

  // Confirmador de Ativação / Inativação
  const [confirmUser, setConfirmUser] = useState<UserItem | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [deletingUser, setDeletingUser] = useState<UserItem | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Estados de formulário de Usuário
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [wizardStep, setWizardStep] = useState<number>(1);
  const [selectedProfileId, setSelectedProfileId] = useState('common');
  const [showAdvancedAccess, setShowAdvancedAccess] = useState(false);
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null);
  const [copiedGeneratedPassword, setCopiedGeneratedPassword] = useState(false);
  const [drawerUser, setDrawerUser] = useState<UserItem | null>(null);
  const [drawerTab, setDrawerTab] = useState<DrawerTab>('summary');
  const [formUsername, setFormUsername] = useState('');
  const [formEmail, setFormEmail] = useState('');
  const [formFullName, setFormFullName] = useState('');
  const [formDepartment, setFormDepartment] = useState('');
  const [formJobTitle, setFormJobTitle] = useState('');
  const [formPassword, setFormPassword] = useState('');
  const [formPasswordConfirm, setFormPasswordConfirm] = useState('');
  const [formRoleId, setFormRoleId] = useState<number>(2); // Default USER role
  const [formIsActive, setFormIsActive] = useState(true);
  const [formMustChangePassword, setFormMustChangePassword] = useState(true);
  const [formPermissions, setFormPermissions] = useState<Record<number, string>>({});
  const [formError, setFormError] = useState<ApiErrorState | null>(null);
  const [lifecycleLoading, setLifecycleLoading] = useState(false);
  const [adminSessions, setAdminSessions] = useState<AdminSessionItem[]>([]);
  const [temporaryAccesses, setTemporaryAccesses] = useState<AdminTemporaryAccessItem[]>([]);
  const [temporarySubstitutions, setTemporarySubstitutions] = useState<AdminTemporarySubstitutionItem[]>([]);
  const [temporaryAccessModuleId, setTemporaryAccessModuleId] = useState<number | ''>('');
  const [temporaryAccessLevel, setTemporaryAccessLevel] = useState('NORMAL');
  const [temporaryAccessReason, setTemporaryAccessReason] = useState('');
  const [temporaryAccessExpiresAt, setTemporaryAccessExpiresAt] = useState('');
  const [temporarySubstituteUserId, setTemporarySubstituteUserId] = useState<number | ''>('');
  const [temporarySubstitutionReason, setTemporarySubstitutionReason] = useState('');
  const [temporarySubstitutionExpiresAt, setTemporarySubstitutionExpiresAt] = useState('');
  const [offboardingImpact, setOffboardingImpact] = useState<AdminOffboardingImpact | null>(null);
  const [offboardingCase, setOffboardingCase] = useState<AdminOffboardingCase | null>(null);
  const [offboardingReason, setOffboardingReason] = useState('');
  const [offboardingReplacementId, setOffboardingReplacementId] = useState<number | ''>(1);
  const creationWorkspaceRef = useRef<HTMLDivElement>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const usersRes = await fetch('/api/v1/admin/users');
      if (!usersRes.ok) throw new Error('Falha ao carregar lista de usuários');
      const usersData = await usersRes.json();
      setUsers(usersData);

      const rolesRes = await fetch('/api/v1/admin/roles');
      if (rolesRes.ok) {
        const rolesData = await rolesRes.json();
        setRoles(rolesData);
      }

      const modulesRes = await fetch('/api/v1/admin/modules');
      if (modulesRes.ok) {
        const modulesData = await modulesRes.json();
        setModules(modulesData);
      }
    } catch (err: any) {
      setError(err.message || 'Erro de rede ao buscar configurações.');
    } finally {
      setLoading(false);
    }
  };

  const fetchAuditLogs = async () => {
    setLogsLoading(true);
    try {
      const res = await fetch('/api/v1/admin/audit-logs');
      if (!res.ok) throw new Error('Falha ao carregar logs de auditoria');
      const data = await res.json();
      setAuditLogs(data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLogsLoading(false);
    }
  };

  const fetchLifecycleData = useCallback(async (user: UserItem, tab: DrawerTab = drawerTab) => {
    setLifecycleLoading(true);
    setError(null);
    try {
      if (tab === 'sessions') {
        const response = await fetch(`/api/v1/admin/users/${user.id}/sessions`);
        if (!response.ok) throw await readApiError(response, 'Nao foi possivel carregar sessoes.');
        setAdminSessions(await response.json());
      }

      if (tab === 'temporary-access') {
        const [accessResponse, substitutionResponse] = await Promise.all([
          fetch(`/api/v1/admin/users/${user.id}/temporary-access`),
          fetch(`/api/v1/admin/users/${user.id}/temporary-substitutions`),
        ]);
        if (!accessResponse.ok) throw await readApiError(accessResponse, 'Nao foi possivel carregar acessos temporarios.');
        if (!substitutionResponse.ok) throw await readApiError(substitutionResponse, 'Nao foi possivel carregar substituicoes.');
        setTemporaryAccesses(await accessResponse.json());
        setTemporarySubstitutions(await substitutionResponse.json());
      }

      if (tab === 'offboarding') {
        const response = await fetch(`/api/v1/admin/users/${user.id}/offboarding/impact`);
        if (!response.ok) throw await readApiError(response, 'Nao foi possivel calcular impacto do desligamento.');
        setOffboardingImpact(await response.json());
      }
    } catch (err: any) {
      setError(normalizeApiError(err, 'Nao foi possivel carregar dados administrativos.').message);
    } finally {
      setLifecycleLoading(false);
    }
  }, [drawerTab]);

  const revokeSession = async (sessionId: number) => {
    if (!drawerUser) return;
    setLifecycleLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`/api/v1/admin/users/${drawerUser.id}/sessions/${sessionId}/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Revogada pela Administracao' }),
      });
      if (!response.ok) throw await readApiError(response, 'Nao foi possivel revogar a sessao.');
      setSuccess('Sessao revogada com sucesso.');
      await fetchLifecycleData(drawerUser, 'sessions');
      fetchAuditLogs();
    } catch (err: any) {
      setError(normalizeApiError(err, 'Nao foi possivel revogar a sessao.').message);
    } finally {
      setLifecycleLoading(false);
    }
  };

  const createTemporaryAccess = async () => {
    if (!drawerUser || !temporaryAccessModuleId || !temporaryAccessExpiresAt || !temporaryAccessReason.trim()) {
      setError('Informe modulo, validade e justificativa para o acesso temporario.');
      return;
    }
    setLifecycleLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`/api/v1/admin/users/${drawerUser.id}/temporary-access`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          module_id: temporaryAccessModuleId,
          permission_level: temporaryAccessLevel,
          reason: temporaryAccessReason,
          expires_at: new Date(temporaryAccessExpiresAt).toISOString(),
        }),
      });
      if (!response.ok) throw await readApiError(response, 'Nao foi possivel criar acesso temporario.');
      setTemporaryAccessReason('');
      setSuccess('Acesso temporario criado com auditoria.');
      await fetchLifecycleData(drawerUser, 'temporary-access');
      fetchAuditLogs();
    } catch (err: any) {
      setError(normalizeApiError(err, 'Nao foi possivel criar acesso temporario.').message);
    } finally {
      setLifecycleLoading(false);
    }
  };

  const revokeTemporaryAccess = async (accessId: number) => {
    if (!drawerUser) return;
    setLifecycleLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`/api/v1/admin/users/${drawerUser.id}/temporary-access/${accessId}/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Revogado pela Administracao' }),
      });
      if (!response.ok) throw await readApiError(response, 'Nao foi possivel revogar acesso temporario.');
      setSuccess('Acesso temporario revogado.');
      await fetchLifecycleData(drawerUser, 'temporary-access');
      fetchAuditLogs();
    } catch (err: any) {
      setError(normalizeApiError(err, 'Nao foi possivel revogar acesso temporario.').message);
    } finally {
      setLifecycleLoading(false);
    }
  };

  const createTemporarySubstitution = async () => {
    if (!drawerUser || !temporarySubstituteUserId || !temporarySubstitutionExpiresAt || !temporarySubstitutionReason.trim()) {
      setError('Informe substituto, validade e justificativa para a substituicao.');
      return;
    }
    setLifecycleLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`/api/v1/admin/users/${drawerUser.id}/temporary-substitutions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          substitute_user_id: temporarySubstituteUserId,
          reason: temporarySubstitutionReason,
          expires_at: new Date(temporarySubstitutionExpiresAt).toISOString(),
        }),
      });
      if (!response.ok) throw await readApiError(response, 'Nao foi possivel criar substituicao.');
      setTemporarySubstitutionReason('');
      setSuccess('Substituicao temporaria criada com auditoria.');
      await fetchLifecycleData(drawerUser, 'temporary-access');
      fetchAuditLogs();
    } catch (err: any) {
      setError(normalizeApiError(err, 'Nao foi possivel criar substituicao.').message);
    } finally {
      setLifecycleLoading(false);
    }
  };

  const createOffboardingCase = async () => {
    if (!drawerUser || !offboardingReason.trim()) {
      setError('Informe a justificativa do desligamento seguro.');
      return;
    }
    setLifecycleLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`/api/v1/admin/users/${drawerUser.id}/offboarding`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reason: offboardingReason,
          replacement_user_id: offboardingReplacementId || null,
        }),
      });
      if (!response.ok) throw await readApiError(response, 'Nao foi possivel criar caso de desligamento.');
      setOffboardingCase(await response.json());
      setSuccess('Caso de desligamento criado. Revise as tarefas antes de confirmar.');
      fetchAuditLogs();
    } catch (err: any) {
      setError(normalizeApiError(err, 'Nao foi possivel criar desligamento seguro.').message);
    } finally {
      setLifecycleLoading(false);
    }
  };

  const confirmOffboardingCase = async () => {
    if (!drawerUser || !offboardingCase) return;
    setLifecycleLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await fetch(`/api/v1/admin/offboarding/${offboardingCase.id}/confirm`, { method: 'POST' });
      if (!response.ok) throw await readApiError(response, 'Nao foi possivel confirmar desligamento.');
      const data = await response.json();
      setOffboardingCase(data.case);
      setSuccess('Desligamento confirmado: login bloqueado, sessoes revogadas e tarefas registradas.');
      await fetchData();
      await fetchLifecycleData(drawerUser, 'offboarding');
      fetchAuditLogs();
    } catch (err: any) {
      setError(normalizeApiError(err, 'Nao foi possivel confirmar desligamento.').message);
    } finally {
      setLifecycleLoading(false);
    }
  };

  const completeOffboardingTask = async (taskId: number) => {
    setLifecycleLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/admin/offboarding/tasks/${taskId}/complete`, { method: 'POST' });
      if (!res.ok) throw new Error('Falha ao concluir tarefa.');
      if (drawerUser) await fetchLifecycleData(drawerUser, 'offboarding');
      // Update local offboardingCase tasks
      if (offboardingCase) {
        setOffboardingCase({
          ...offboardingCase,
          tasks: offboardingCase.tasks.map(t => t.id === taskId ? { ...t, status: 'COMPLETED' } : t)
        });
      }
      setSuccess('Tarefa de offboarding marcada como concluída.');
    } catch (err: any) {
      setError(err.message || 'Erro ao atualizar tarefa.');
    } finally {
      setLifecycleLoading(false);
    }
  };

  const failOffboardingTask = async (taskId: number) => {
    setLifecycleLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/admin/offboarding/tasks/${taskId}/fail`, { method: 'POST' });
      if (!res.ok) throw new Error('Falha ao sinalizar falha na tarefa.');
      if (drawerUser) await fetchLifecycleData(drawerUser, 'offboarding');
      if (offboardingCase) {
        setOffboardingCase({
          ...offboardingCase,
          tasks: offboardingCase.tasks.map(t => t.id === taskId ? { ...t, status: 'FAILED' } : t)
        });
      }
      setSuccess('Tarefa de offboarding marcada com erro/impedimento.');
    } catch (err: any) {
      setError(err.message || 'Erro ao atualizar tarefa.');
    } finally {
      setLifecycleLoading(false);
    }
  };

  const cancelOffboardingCase = async (caseId: number) => {
    setLifecycleLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/admin/offboarding/${caseId}/cancel`, { method: 'POST' });
      if (!res.ok) throw new Error('Falha ao cancelar o caso.');
      const data = await res.json();
      setOffboardingCase(null);
      if (drawerUser) await fetchLifecycleData(drawerUser, 'offboarding');
      setSuccess('Caso de desligamento cancelado.');
    } catch (err: any) {
      setError(err.message || 'Erro ao cancelar caso.');
    } finally {
      setLifecycleLoading(false);
    }
  };

  // Buscar itens de deduplicação do catálogo
  const fetchDedupItems = useCallback(async () => {
    setDedupLoading(true);
    try {
      const statusParam = dedupFilter === 'ALL' ? '' : '?status=PENDING';
      const res = await fetch(`/api/v1/master-data/deduplication${statusParam}`);
      if (!res.ok) throw new Error('Falha ao carregar fila de deduplicação');
      const data = await res.json();
      setDedupItems(data);
    } catch (err: any) {
      console.error('Erro ao buscar deduplicação:', err);
    } finally {
      setDedupLoading(false);
    }
  }, [dedupFilter]);

  // Resolver um par de deduplicação
  const handleResolveDedup = async (id: string, decision: string) => {
    setDedupResolving(id);
    setError(null);
    setSuccess(null);
    try {
      const res = await fetch(`/api/v1/master-data/deduplication/${id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          notes: dedupNotes[id] || null
        })
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao resolver deduplicação.');
      }
      const decisionLabel = decision === 'APPROVED_MERGE' ? 'mesclados' : decision === 'REJECTED' ? 'mantidos como distintos' : 'resolvidos';
      setSuccess(`Itens ${decisionLabel} com sucesso!`);
      fetchDedupItems();
    } catch (err: any) {
      setError(err.message || 'Erro ao resolver deduplicação.');
    } finally {
      setDedupResolving(null);
    }
  };

  useEffect(() => {
    fetchData();
    fetchAuditLogs();
  }, []);

  useEffect(() => {
    if (activeTab === 'audit') {
      fetchAuditLogs();
    }
    if (activeTab === 'deduplication') {
      fetchDedupItems();
    }
  }, [activeTab, fetchDedupItems]);

  useEffect(() => {
    if (!drawerUser) return;
    if (drawerTab === 'sessions' || drawerTab === 'temporary-access' || drawerTab === 'offboarding') {
      fetchLifecycleData(drawerUser, drawerTab);
    }
  }, [drawerUser, drawerTab, fetchLifecycleData]);

  useEffect(() => {
    if (!drawerUser) return;
    const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 16);
    setTemporaryAccessModuleId((current) => current || modules.find((module) => module.code !== 'chat')?.id || '');
    setTemporaryAccessExpiresAt((current) => current || tomorrow);
    setTemporarySubstitutionExpiresAt((current) => current || tomorrow);
    setOffboardingReplacementId('');
    setOffboardingCase(null);
  }, [drawerUser, modules]);

  useEffect(() => {
    if (!showForm || activeTab !== 'users') return;
    requestAnimationFrame(() => {
      creationWorkspaceRef.current?.scrollIntoView?.({ block: 'start', behavior: 'smooth' });
      const firstField = creationWorkspaceRef.current?.querySelector<HTMLInputElement>('input:not([disabled])');
      firstField?.focus();
    });
  }, [showForm, activeTab, wizardStep]);

  // Filtro de usuários no frontend
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      // Hide MESSIAS role from frontend listing for standard admins
      const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
      if (u.role_name === 'MESSIAS' && !isCurrentUserMessias) return false;

      const searchMatch = !userSearch || 
        u.username.toLowerCase().includes(userSearch.toLowerCase()) || 
        (u.email || '').toLowerCase().includes(userSearch.toLowerCase()) ||
        (u.full_name || '').toLowerCase().includes(userSearch.toLowerCase()) ||
        (u.department || '').toLowerCase().includes(userSearch.toLowerCase()) ||
        (u.job_title || '').toLowerCase().includes(userSearch.toLowerCase());
      
      const roleMatch = userFilterRole === 'ALL' || 
        (u.role_name && u.role_name === userFilterRole);

      const statusMatch = userFilterStatus === 'ALL' || 
        (userFilterStatus === 'ACTIVE' && u.is_active) || 
        (userFilterStatus === 'INACTIVE' && !u.is_active);

      return searchMatch && roleMatch && statusMatch;
    });
  }, [users, userSearch, userFilterRole, userFilterStatus]);

  const editablePermissionModules = useMemo(() => modules.filter((module) => !isChatModule(module)), [modules]);

  const selectedProfile = useMemo(
    () => customProfiles.find((profile) => profile.id === selectedProfileId) || customProfiles[0],
    [customProfiles, selectedProfileId],
  );

  const selectedRole = useMemo(() => roles.find((role) => role.id === formRoleId), [roles, formRoleId]);

  const selectedProfileWarnings = useMemo(() => {
    const warnings = [...(selectedProfile.warnings || [])];
    Object.entries(formPermissions).forEach(([moduleId, level]) => {
      const module = modules.find((item) => item.id === Number(moduleId));
      if (!module || level === 'NO_ACCESS') return;
      if (module.code === 'admin' && ['MANAGER', 'ADMIN'].includes(level)) {
        warnings.push('Este acesso permite administrar usuarios ou configuracoes.');
      }
      if (module.code === 'it' && ['MANAGER', 'ADMIN'].includes(level)) {
        warnings.push('Este acesso pode permitir operar recursos sensiveis de TI e Cofre.');
      }
      if (module.code === 'approvals' && ['MANAGER', 'ADMIN'].includes(level)) {
        warnings.push('Este acesso pode permitir aprovar solicitacoes.');
      }
    });
    return Array.from(new Set(warnings));
  }, [formPermissions, modules, selectedProfile]);

  // Mapeamentos e Filtros de Logs
  const uniqueLogActions = useMemo(() => {
    const actions = new Set<string>();
    auditLogs.forEach(log => {
      if (log.action) actions.add(log.action);
    });
    return Array.from(actions);
  }, [auditLogs]);

  const uniqueLogModules = useMemo(() => {
    const mods = new Set<string>();
    auditLogs.forEach(log => {
      if (log.module) mods.add(log.module);
    });
    return Array.from(mods);
  }, [auditLogs]);

  const uniqueLogUsers = useMemo(() => {
    const usersSet = new Set<string>();
    auditLogs.forEach(log => {
      if (log.username) usersSet.add(log.username);
    });
    return Array.from(usersSet);
  }, [auditLogs]);

  const filteredLogs = useMemo(() => {
    return auditLogs.filter((log) => {
      const userMatch = logFilterUser === 'ALL' || log.username === logFilterUser;
      const moduleMatch = logFilterModule === 'ALL' || log.module === logFilterModule;
      const actionMatch = logFilterAction === 'ALL' || log.action === logFilterAction;
      
      const searchLower = logSearch.toLowerCase();
      const searchMatch = !logSearch || 
        (log.username && log.username.toLowerCase().includes(searchLower)) ||
        (log.action && log.action.toLowerCase().includes(searchLower)) ||
        (log.module && log.module.toLowerCase().includes(searchLower)) ||
        (log.details && JSON.stringify(log.details).toLowerCase().includes(searchLower));
        
      return userMatch && moduleMatch && actionMatch && searchMatch;
    });
  }, [auditLogs, logSearch, logFilterModule, logFilterAction, logFilterUser]);

  const applyProfilePreset = useCallback((profileId: string) => {
    const profile = customProfiles.find((item) => item.id === profileId) || customProfiles[0];
    const preferredRole = roles.find((role) => profile.roleNames.includes(role.name)) || roles.find((role) => role.name === 'USER') || roles[0];
    if (preferredRole) setFormRoleId(preferredRole.id);
    setFormDepartment(profile.label);
    setFormJobTitle('');

    const permissions: Record<number, string> = {};
    modules.forEach((module) => {
      if (isChatModule(module)) {
        permissions[module.id] = 'NORMAL';
        return;
      }
      if (profile.id === 'admin') {
        permissions[module.id] = 'ADMIN';
        return;
      }
      permissions[module.id] = profile.accessLevelByModule[module.code] || (module.is_restricted ? 'NO_ACCESS' : 'READ_ONLY');
    });
    setFormPermissions(permissions);
  }, [customProfiles, modules, roles]);

  const selectProfilePreset = (profileId: string) => {
    setSelectedProfileId(profileId);
    applyProfilePreset(profileId);
  };

  const useDraftProfileInCreation = (profile: AccessProfilePreset) => {
    setCustomProfiles((current) => {
      const withoutSame = current.filter((item) => item.id !== profile.id);
      return [...withoutSame, profile];
    });
    setActiveTab('users');
    setEditingUser(null);
    setDrawerUser(null);
    setShowForm(true);
    setWizardStep(1);
    setSelectedProfileId(profile.id);
    const preferredRole = roles.find((role) => profile.roleNames.includes(role.name)) || roles.find((role) => role.name === 'USER') || roles[0];
    if (preferredRole) setFormRoleId(preferredRole.id);
    setFormDepartment(profile.label);
    setFormJobTitle('');
    const permissions: Record<number, string> = {};
    modules.forEach((module) => {
      if (isChatModule(module)) {
        permissions[module.id] = 'NORMAL';
        return;
      }
      permissions[module.id] = profile.accessLevelByModule[module.code] || (module.is_restricted ? 'NO_ACCESS' : 'READ_ONLY');
    });
    setFormPermissions(permissions);
  };

  const validateStepOne = () => {
    const fieldErrors: Record<string, string> = {};
    if (!formFullName.trim()) fieldErrors.full_name = 'Informe o nome completo da pessoa.';
    if (!formUsername.trim()) fieldErrors.username = 'Informe um nome de usuario.';
    if (!editingUser && !formPassword.trim()) fieldErrors.password = 'Informe uma senha inicial ou gere uma senha temporaria.';
    if (editingUser && formPassword.trim() && formPassword !== formPasswordConfirm) {
      fieldErrors.password_confirm = 'A confirmacao precisa repetir a nova senha.';
    }
    if (formEmail && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formEmail)) {
      fieldErrors.email = 'O e-mail informado nao parece valido.';
    }
    if (Object.keys(fieldErrors).length > 0) {
      setFormError({
        code: 'VALIDATION_ERROR',
        message: 'Revise os campos destacados antes de continuar.',
        fieldErrors,
        retryable: false,
      });
      return false;
    }
    setFormError(null);
    return true;
  };

  const setTemporaryPassword = () => {
    try {
      const password = generateTemporaryPassword();
      setFormPassword(password);
      setFormPasswordConfirm(password);
      setGeneratedPassword(password);
      setCopiedGeneratedPassword(false);
    } catch {
      setFormError(normalizeApiError('Nao foi possivel gerar a senha. Tente novamente.'));
    }
  };

  const closeUserDrawer = () => {
    setDrawerUser(null);
    setEditingUser(null);
    setFormPassword('');
    setFormPasswordConfirm('');
    setGeneratedPassword(null);
    setCopiedGeneratedPassword(false);
    setFormError(null);
  };

  const copyGeneratedPassword = async () => {
    if (!generatedPassword) return;
    await navigator.clipboard.writeText(generatedPassword);
    setCopiedGeneratedPassword(true);
  };

  const handleEditClick = (user: UserItem) => {
    const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
    if (user.role_name === 'MESSIAS' && !isCurrentUserMessias) {
      setError('Ação não permitida: O super-usuário MESSIAS é blindado contra alterações por administradores comuns.');
      return;
    }
    setEditingUser(user);
    setDrawerUser(user);
    setDrawerTab('summary');
    setFormUsername(user.username);
    setFormEmail(user.email || '');
    setFormFullName(user.full_name || '');
    setFormDepartment(user.department || '');
    setFormJobTitle(user.job_title || '');
    setFormPassword('');
    setFormPasswordConfirm('');
    setGeneratedPassword(null);
    setCopiedGeneratedPassword(false);
    setFormRoleId(user.role_id || 2);
    setFormIsActive(user.is_active);
    setFormMustChangePassword(Boolean(user.must_change_password));
    
    const permsMap: Record<number, string> = {};
    user.module_permissions.forEach(p => {
      permsMap[p.module_id] = p.permission_level;
    });
    setFormPermissions(permsMap);
    setFormError(null);
    setShowForm(false);
  };

  const handleCreateClick = () => {
    setActiveTab('users');
    setSuccess(null);
    setError(null);
    setEditingUser(null);
    setDrawerUser(null);
    setFormUsername('');
    setFormEmail('');
    setFormFullName('');
    setFormDepartment(suggestedProfiles[0].label);
    setFormJobTitle('');
    setFormPassword('');
    setFormPasswordConfirm('');
    setFormRoleId(2); // Normal USER role
    setFormIsActive(true);
    setFormMustChangePassword(true);
    setGeneratedPassword(null);
    setCopiedGeneratedPassword(false);
    setWizardStep(1);
    setSelectedProfileId('common');
    setShowAdvancedAccess(false);
    
    const permsMap: Record<number, string> = {};
    modules.forEach(m => {
      permsMap[m.id] = isChatModule(m) ? 'NORMAL' : (m.is_restricted ? 'NO_ACCESS' : 'READ_ONLY');
    });
    setFormPermissions(permsMap);
    setFormError(null);
    
    setShowForm(true);
  };

  const handleFormSubmit = async (e?: React.SyntheticEvent) => {
    e?.preventDefault();
    setError(null);
    setSuccess(null);
    setFormError(null);

    if (!editingUser && wizardStep < 3) {
      if (wizardStep === 1 && !validateStepOne()) {
        return;
      }
      setWizardStep((step) => Math.min(3, step + 1));
      return;
    }

    if (!editingUser && !validateStepOne()) {
      setWizardStep(1);
      return;
    }

    if (!formUsername.trim() || (!editingUser && !formPassword.trim())) {
      setFormError(normalizeApiError('Preencha os dados obrigatorios antes de continuar.'));
      return;
    }

    if (editingUser && formPassword.trim() && formPassword !== formPasswordConfirm) {
      setFormError({
        code: 'VALIDATION_ERROR',
        message: 'Confirme a nova senha antes de salvar.',
        fieldErrors: {
          password_confirm: 'A confirmacao precisa repetir a nova senha.',
        },
        retryable: false,
      });
      return;
    }

    const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
    
    if (editingUser && editingUser.role_name === 'MESSIAS' && !isCurrentUserMessias) {
      setError('Ação não permitida: O super-usuário MESSIAS é blindado contra alterações.');
      return;
    }

    const messiasRole = roles.find(r => r.name === 'MESSIAS');
    if (messiasRole && formRoleId === messiasRole.id && !isCurrentUserMessias) {
      setError('Ação não permitida: Somente o super-usuário MESSIAS pode conceder o papel MESSIAS.');
      return;
    }

    try {
      setLoading(true);
      const permissionsList = Object.entries(formPermissions).map(([modId, lvl]) => ({
        module_id: parseInt(modId),
        permission_level: lvl
      }));

      if (editingUser) {
        // Atualização
        const updateRes = await fetch(`/api/v1/admin/users/${editingUser.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: formUsername,
            email: formEmail || null,
            full_name: formFullName || null,
            department: formDepartment || null,
            job_title: formJobTitle || null,
            password: formPassword || undefined,
            role_id: formRoleId,
            is_active: formIsActive,
            must_change_password: formMustChangePassword
          })
        });

        const updateData = await updateRes.json().catch(() => ({}));
        if (!updateRes.ok) {
          throw normalizeApiError(updateData, 'Nao foi possivel atualizar o usuario. Verifique os campos obrigatorios.', updateRes.status);
        }

        const permRes = await fetch(`/api/v1/admin/users/${editingUser.id}/module-access`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ permissions: permissionsList })
        });

        const permData = await permRes.json().catch(() => ({}));
        if (!permRes.ok) {
          throw normalizeApiError(permData, 'Nao foi possivel salvar as permissoes. Revise os niveis de acesso.', permRes.status);
        }

        setSuccess(formPassword.trim() ? 'Senha e dados do usuario atualizados com seguranca.' : 'Usuario atualizado com sucesso!');
        setFormPassword('');
        setFormPasswordConfirm('');
        setGeneratedPassword(null);
        setCopiedGeneratedPassword(false);
        setUsers((current) => current.map((item) => (item.id === updateData.id ? updateData : item)));
        setEditingUser(updateData);
        setDrawerUser(updateData);
      } else {
        // Criação
        const createRes = await fetch('/api/v1/admin/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: formUsername,
            email: formEmail || null,
            full_name: formFullName || null,
            department: formDepartment || null,
            job_title: formJobTitle || null,
            password: formPassword,
            role_id: formRoleId,
            is_active: formIsActive,
            must_change_password: formMustChangePassword,
            module_permissions: permissionsList
          })
        });

        const createData = await createRes.json().catch(() => ({}));
        if (!createRes.ok) {
          throw normalizeApiError(createData, 'Nao foi possivel criar o usuario. Verifique os campos obrigatorios.', createRes.status);
        }

        setSuccess('Usuário criado com sucesso!');
        setWizardStep(3);
      }
      fetchData();
    } catch (err: any) {
      setFormError(normalizeApiError(err, 'Ocorreu um erro ao salvar o usuario.'));
    } finally {
      setLoading(false);
    }
  };

  const handleToggleClick = (user: UserItem) => {
    const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
    if (user.role_name === 'MESSIAS' && !isCurrentUserMessias) {
      setError('Ação não permitida: O super-usuário MESSIAS é blindado contra alterações por administradores comuns.');
      return;
    }
    setConfirmUser(user);
    setShowConfirmDialog(true);
  };

  const handleConfirmToggle = async () => {
    if (!confirmUser) return;
    
    const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
    if (confirmUser.role_name === 'MESSIAS' && !isCurrentUserMessias) {
      setError('Ação não permitida: O super-usuário MESSIAS é blindado contra alterações.');
      setShowConfirmDialog(false);
      setConfirmUser(null);
      return;
    }

    setError(null);
    setSuccess(null);
    try {
      const res = await fetch(`/api/v1/admin/users/${confirmUser.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !confirmUser.is_active })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Falha ao alterar status do usuário.');
      }
      setSuccess(`Status do usuário "${confirmUser.username}" alterado com sucesso!`);
      fetchData();
    } catch (err: any) {
      setError(err.message || 'Erro ao alterar status.');
    } finally {
      setShowConfirmDialog(false);
      setConfirmUser(null);
    }
  };

  const handleSaveProfile = (profile: AccessProfilePreset) => {
    setCustomProfiles((current) => {
      const withoutSame = current.filter((item) => item.id !== profile.id);
      return [...withoutSame, profile];
    });
    setSuccess(`Perfil "${profile.label}" salvo com sucesso!`);
    setTimeout(() => setSuccess(null), 4000);
  };

  const handleDeleteProfile = (profileId: string) => {
    const profile = customProfiles.find(p => p.id === profileId);
    if (!profile) return;
    setCustomProfiles((current) => current.filter((item) => item.id !== profileId));
    setSuccess(`Perfil "${profile.label}" excluído da sessão.`);
    setTimeout(() => setSuccess(null), 4000);
  };

  const handleDeleteClick = (user: UserItem) => {
    const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
    if (user.role_name === 'MESSIAS' && !isCurrentUserMessias) {
      setError('Ação não permitida: O super-usuário MESSIAS é blindado contra exclusão por administradores comuns.');
      return;
    }
    if (user.id === currentUser?.id) {
      setError('Ação não permitida: Você não pode excluir sua própria conta administrativa.');
      return;
    }
    setDeletingUser(user);
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = async () => {
    if (!deletingUser) return;
    setError(null);
    setSuccess(null);
    try {
      const res = await fetch(`/api/v1/admin/users/${deletingUser.id}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || 'Falha ao excluir o usuário.');
      }
      setSuccess(`Usuário "${deletingUser.username}" excluído com sucesso!`);
      setShowDeleteDialog(false);
      setDeletingUser(null);
      fetchData();
    } catch (err: any) {
      setError(err.message || 'Erro ao excluir usuário.');
      setShowDeleteDialog(false);
      setDeletingUser(null);
    }
  };

  const humanizeAction = (action: string): string => {
    const dictionary: Record<string, string> = {
      'LOGIN_SUCCESS': 'Efetuou login com sucesso',
      'LOGIN_FAILED': 'Falha na tentativa de login',
      'LOGOUT': 'Efetuou logout',
      'CREATE_USER': 'Criou um novo usuário',
      'UPDATE_USER': 'Atualizou cadastro de usuário',
      'DELETE_USER': 'Inativou um usuário',
      'UPDATE_USER_MODULE_ACCESS': 'Alterou permissões de módulo',
      'CREATE_BOARD': 'Criou um novo quadro no Kanban',
      'UPDATE_BOARD': 'Atualizou configurações de quadro',
      'DELETE_BOARD': 'Excluiu permanentemente um quadro',
      'CREATE_CARD': 'Criou um cartão no Kanban',
      'UPDATE_CARD': 'Editou detalhes de cartão no Kanban',
      'MOVE_CARD': 'Alterou a etapa / coluna de um cartão',
      'DELETE_CARD': 'Excluiu um cartão do Kanban',
      'ARCHIVE_CARD': 'Arquivou um cartão no Kanban',
      'CREATE_APPROVAL': 'Abriu solicitação de aprovação',
      'APPROVE_REQUEST': 'Aprovou uma solicitação',
      'REJECT_REQUEST': 'Rejeitou uma solicitação',
      'CANCEL_REQUEST': 'Cancelou solicitação pendente',
      'CREATE_COMMENT': 'Escreveu comentário em solicitação',
      'ACCESS_DENIED': 'Tentativa de acesso não autorizado',
    };
    
    if (dictionary[action]) return dictionary[action];
    return action
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/^\w/, (c) => c.toUpperCase());
  };

  const humanizeModule = (moduleCode: string): string => {
    const dictionary: Record<string, string> = {
      'auth': 'Autenticação',
      'admin': 'Administração',
      'kanban': 'Kanban / Produção',
      'approvals': 'Aprovações',
      'purchases': 'Compras',
      'proposals': 'Propostas',
      'it': 'Tecnologia da Informação',
      'chat': 'Chat Interno',
      'files': 'Base de Conhecimento',
      'stock': 'Estoque',
      'automations': 'Automações IA',
    };
    return dictionary[moduleCode] || moduleCode.toUpperCase();
  };

  const activeUsersCount = useMemo(() => users.filter((u) => u.is_active).length, [users]);
  const configuredModulesCount = useMemo(() => modules.filter((m) => m.is_active).length, [modules]);
  const lastAuditDate = useMemo(() => {
    if (!auditLogs.length) return 'Sem registro';
    return new Date(auditLogs[0].created_at).toLocaleDateString('pt-BR');
  }, [auditLogs]);

  const humanizeDedupStatus = (st: string): string => {
    const dict: Record<string, string> = {
      'PENDING': 'Pendente',
      'APPROVED_MERGE': 'Mesclado',
      'REJECTED': 'Mantido Distinto',
      'RESOLVED': 'Resolvido',
    };
    return dict[st] || st;
  };

  const dedupStatusVariant = (st: string): 'warning' | 'success' | 'danger' | 'neutral' => {
    if (st === 'PENDING') return 'warning';
    if (st === 'APPROVED_MERGE') return 'success';
    if (st === 'REJECTED') return 'danger';
    return 'neutral';
  };

  const formatHumanAuditLog = (log: AuditLogItem): string => {
    const actor = log.username || 'O sistema';
    const details = log.details || {};
    const action = log.action;

    const getTargetUser = (): string => {
      const targetId = details.updated_user_id || details.target_user_id || details.user_id;
      if (details.target_username) return details.target_username;
      if (details.username) return details.username;
      if (targetId) {
        const found = users.find((u) => u.id === Number(targetId));
        return found ? found.username : `usuário #${targetId}`;
      }
      return 'um usuário';
    };

    switch (action) {
      case 'LOGIN_SUCCESS':
        return `${actor} efetuou login com sucesso no portal.`;
      case 'LOGIN_FAILED':
        return `Tentativa de login falhou para o usuário "${details.username || details.email || 'desconhecido'}".`;
      case 'LOGOUT':
        return `${actor} saiu do sistema.`;
      
      case 'CREATE_USER':
        return `${actor} criou o usuário "${details.username}" com o perfil de "${humanizeRole(details.role)}".`;
      case 'UPDATE_USER': {
        const target = getTargetUser();
        const oldActive = details.old_values?.is_active;
        const newActive = details.new_values?.is_active;
        if (oldActive !== undefined && newActive !== undefined && oldActive !== newActive) {
          return `${actor} ${newActive ? 'ativou' : 'inativou'} o acesso do usuário "${target}".`;
        }
        return `${actor} atualizou o cadastro do usuário "${target}".`;
      }
      case 'DELETE_USER':
        return `${actor} inativou o usuário "${getTargetUser()}".`;
      
      case 'UPDATE_USER_MODULE_ACCESS':
      case 'admin.module_access.updated':
        return `${actor} atualizou as permissões de acesso aos módulos do usuário "${getTargetUser()}".`;
      
      case 'admin.kanban_access.bulk_updated':
        return `${actor} atualizou em lote as permissões de acesso ao Kanban do usuário "${getTargetUser()}".`;
      case 'admin.kanban_access.granted':
        return `${actor} concedeu novas permissões de acesso ao Kanban para o usuário "${getTargetUser()}".`;
      case 'admin.kanban_access.updated':
        return `${actor} alterou as permissões de acesso ao Kanban do usuário "${getTargetUser()}".`;
      case 'admin.kanban_access.removed':
        return `${actor} removeu as permissões de acesso ao Kanban do usuário "${getTargetUser()}".`;
      
      case 'CREATE_BOARD':
        return `${actor} criou o novo quadro "${details.name || details.title || 'Sem título'}" no Kanban.`;
      case 'UPDATE_BOARD':
        return `${actor} atualizou as configurações do quadro "${details.name || details.title || 'Sem título'}" no Kanban.`;
      case 'DELETE_BOARD':
        return `${actor} excluiu permanentemente o quadro "${details.name || details.title || 'Sem título'}" do Kanban.`;
      
      case 'CREATE_CARD':
        return `${actor} criou o cartão "${details.title}" no Kanban (Quadro: ${details.board_name || 'Desconhecido'}).`;
      case 'UPDATE_CARD':
        return `${actor} atualizou detalhes do cartão "${details.title || 'sem título'}" no Kanban.`;
      case 'MOVE_CARD':
        return `${actor} moveu o cartão "${details.card_title || details.title || 'sem título'}" para a etapa "${details.new_column_name || details.new_column || 'finalizada'}".`;
      case 'DELETE_CARD':
        return `${actor} excluiu o cartão "${details.title || 'sem título'}" do Kanban.`;
      case 'ARCHIVE_CARD':
        return `${actor} arquivou o cartão "${details.title || 'sem título'}" no Kanban.`;
      
      case 'CREATE_APPROVAL':
        return `${actor} abriu a solicitação de aprovação: "${details.title || 'Sem título'}".`;
      case 'APPROVE_REQUEST':
        return `${actor} aprovou a solicitação de aprovação #${details.approval_id || details.id || ''}.`;
      case 'REJECT_REQUEST':
        return `${actor} rejeitou a solicitação de aprovação #${details.approval_id || details.id || ''} justificando: "${details.reason || 'Sem justificativa'}".`;
      case 'CANCEL_REQUEST':
        return `${actor} cancelou a solicitação de aprovação #${details.approval_id || details.id || ''}.`;
      case 'CREATE_COMMENT':
        return `${actor} adicionou um comentário na solicitação de aprovação #${details.approval_id || details.id || ''}.`;
      
      case 'ACCESS_DENIED':
        return `Tentativa de acesso negada para ${actor} ao tentar executar a ação "${details.action || action}" no módulo "${humanizeModule(details.module || log.module)}".`;
      
      default:
        return `${actor} realizou a ação "${humanizeAction(action)}" no módulo "${humanizeModule(log.module)}".`;
    }
  };

  return (
    <ModulePageLayout className="admin-page">
      <section className="admin-page-header">
        <div>
          <h1>Administração</h1>
          <p>Gerencie pessoas, acessos e segurança do Portal.</p>
        </div>
        <div className="admin-page-header__actions">
          <Button variant="primary" onClick={handleCreateClick} leftIcon={<UserPlus size={16} />}>
            Novo usuário
          </Button>
        </div>
      </section>

      {/* Alertas inline */}
      {error && (
        <div className="admin-inline-alert admin-inline-alert--danger">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="admin-inline-alert admin-inline-alert--success">
          <CheckCircle2 size={18} />
          <span>{success}</span>
        </div>
      )}

      {/* Split Layout Container */}
      <div className="admin-shell">
        
        {/* Left Column: Navigation Sidebar */}
        <nav className="admin-section-nav" aria-label="Navegação da Administração">
          {[
            { key: 'users', label: 'Usuários', icon: <UserCog size={16} /> },
            { key: 'permissions', label: 'Permissões', icon: <ShieldCheck size={16} /> },
            { key: 'profiles', label: 'Perfis', icon: <Layers size={16} /> },
            { key: 'audit', label: 'Auditoria', icon: <Activity size={16} /> },
          ].map((item) => {
            const isActive = activeTab === item.key;
            return (
              <button
                key={item.key}
                onClick={() => setActiveTab(item.key as any)}
                className={isActive ? 'is-active' : ''}
                aria-current={isActive ? 'page' : undefined}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Right Content Column */}
        <div className="admin-shell-content">
          
          {activeTab === 'users' ? (
            <div className="admin-users-workbench">
              
              {/* Center Column: Users List */}
              <AdminUsersList
                users={users}
                filteredUsers={filteredUsers}
                userSearch={userSearch}
                setUserSearch={setUserSearch}
                userFilterRole={userFilterRole}
                setUserFilterRole={setUserFilterRole}
                userFilterStatus={userFilterStatus}
                setUserFilterStatus={setUserFilterStatus}
                currentUser={currentUser}
                onEditClick={handleEditClick}
                onToggleClick={handleToggleClick}
                onDeleteClick={handleDeleteClick}
                loading={loading}
              />

              {/* Right Column: Creation Workspace or Selection Details Workspace */}
              <div className="admin-workspace-panel" ref={creationWorkspaceRef}>
                {showForm && !editingUser ? (
                  <AdminUserCreationWorkspace
                    formFullName={formFullName}
                    setFormFullName={setFormFullName}
                    formUsername={formUsername}
                    setFormUsername={setFormUsername}
                    formEmail={formEmail}
                    setFormEmail={setFormEmail}
                    formPassword={formPassword}
                    setFormPassword={setFormPassword}
                    formMustChangePassword={formMustChangePassword}
                    setFormMustChangePassword={setFormMustChangePassword}
                    formIsActive={formIsActive}
                    setFormIsActive={setFormIsActive}
                    selectedProfileId={selectedProfileId}
                    setSelectedProfileId={setSelectedProfileId}
                    showAdvancedAccess={showAdvancedAccess}
                    setShowAdvancedAccess={setShowAdvancedAccess}
                    generatedPassword={generatedPassword}
                    copiedGeneratedPassword={copiedGeneratedPassword}
                    formPermissions={formPermissions}
                    setFormPermissions={setFormPermissions}
                    formError={formError}
                    setFormError={setFormError}
                    roles={roles}
                    modules={modules}
                    currentUser={currentUser}
                    loading={loading}
                    onSubmit={handleFormSubmit}
                    onCancel={() => setShowForm(false)}
                    selectProfilePreset={selectProfilePreset}
                    setTemporaryPassword={setTemporaryPassword}
                    copyGeneratedPassword={copyGeneratedPassword}
                    validateStepOne={validateStepOne}
                    wizardStep={wizardStep}
                    setWizardStep={setWizardStep}
                    profiles={customProfiles}
                    permissionLabels={permissionLabels}
                    permissionRisk={permissionRisk}
                  />
                ) : (
                  <div className="admin-workspace-empty">
                    <h3>Precisa de ajuda?</h3>
                    <p>
                      Selecione um usuário na lista ou clique em <strong>Novo usuário</strong> para iniciar o cadastro assistido.
                    </p>
                    <HelpCard
                      description="As alterações de perfil e acessos geram eventos em tempo real para auditoria humana de conformidade."
                      actionLabel="Ver documentação"
                      onAction={() => setActiveTab('permissions')}
                    />
                  </div>
                )}
                <div className="admin-summary-strip" aria-label="Indicadores da Administração">
                  {[
                    ['Perfis ativos', roles.length],
                    ['Usuários ativos', activeUsersCount],
                    ['Módulos ativos', configuredModulesCount],
                    ['Última auditoria', lastAuditDate],
                  ].map(([label, value]) => (
                    <div className="admin-summary-mini-card" key={label}>
                      <span className="admin-summary-mini-label">{label}</span>
                      <strong className="admin-summary-mini-value">{value}</strong>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : activeTab === 'permissions' ? (
            <div className="admin-permissions-workspace">
              <div className="admin-permission-tabs" role="tablist" aria-label="Tipos de permissao">
                <button
                  type="button"
                  className={permissionSubTab === 'modules' ? 'is-active' : ''}
                  onClick={() => setPermissionSubTab('modules')}
                >
                  Módulos do Portal
                </button>
                <button
                  type="button"
                  className={permissionSubTab === 'kanban' ? 'is-active' : ''}
                  onClick={() => setPermissionSubTab('kanban')}
                >
                  Kanban por quadro
                </button>
              </div>
              {permissionSubTab === 'modules' && (
              <AdminModulePermissions 
                users={users} 
                modules={modules} 
                currentUser={currentUser}
                onSaveSuccess={() => {
                  fetchData();
                  setSuccess('Permissões de módulo atualizadas com sucesso!');
                  setTimeout(() => setSuccess(null), 4000);
                }} 
              />
              )}
              {permissionSubTab === 'kanban' && <AdminKanbanPermissions />}
            </div>
          ) : activeTab === 'profiles' ? (
            <AdminProfilesWorkspace
              profiles={customProfiles}
              modules={modules}
              users={users}
              onSaveProfile={handleSaveProfile}
              onDeleteProfile={handleDeleteProfile}
              onUseDraftProfile={useDraftProfileInCreation}
            />
          ) : activeTab === 'deduplication' ? (
            <div style={{ display: 'grid', gap: 20 }}>
              <Card variant="glass" style={{ padding: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
                  <div>
                    <h3 style={{ color: '#fff', margin: '0 0 4px', fontSize: 16, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Layers size={18} style={{ color: '#f59e0b' }} />
                      Deduplicação de Catálogo
                    </h3>
                    <p style={{ color: '#94a3b8', margin: 0, fontSize: 13, lineHeight: 1.45 }}>
                      Itens com nomes muito parecidos foram identificados automaticamente. Revise e decida se devem ser mesclados ou mantidos como registros distintos.
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <Button size="sm" variant={dedupFilter === 'PENDING' ? 'primary' : 'secondary'} onClick={() => setDedupFilter('PENDING')}>Pendentes</Button>
                    <Button size="sm" variant={dedupFilter === 'ALL' ? 'primary' : 'secondary'} onClick={() => setDedupFilter('ALL')}>Todos</Button>
                    <Button size="sm" variant="ghost" onClick={fetchDedupItems} disabled={dedupLoading} leftIcon={<RefreshCw size={14} className={dedupLoading ? 'spin-anim' : ''} />}>Atualizar</Button>
                  </div>
                </div>

                {dedupLoading && dedupItems.length === 0 ? (
                  <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8' }}>Buscando itens duplicados...</div>
                ) : dedupItems.length === 0 ? (
                  <EmptyState
                    icon={<CheckCircle2 size={40} style={{ color: '#34d399' }} />}
                    title="Nenhuma duplicidade pendente"
                    description="O catálogo está limpo! Todos os pares suspeitos já foram revisados ou não foram encontrados itens parecidos."
                  />
                ) : (
                  <div style={{ display: 'grid', gap: 16 }}>
                    {dedupItems.map((dup) => {
                      const itemA = dup.item_a;
                      const itemB = dup.item_b;
                      const isPending = dup.status === 'PENDING';
                      const similarityPct = Math.round((dup.similarity_score || 0) * 100);
                      const similarityColor = similarityPct >= 95 ? '#ef4444' : similarityPct >= 90 ? '#f59e0b' : '#22c55e';

                      return (
                        <div key={dup.id} style={{ background: isPending ? 'rgba(245, 158, 11, 0.04)' : 'rgba(255,255,255,0.015)', border: `1px solid ${isPending ? 'rgba(245, 158, 11, 0.15)' : 'var(--border-color)'}`, borderRadius: 12, padding: 20 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, gap: 12, flexWrap: 'wrap' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <Badge variant={dedupStatusVariant(dup.status)}>{humanizeDedupStatus(dup.status)}</Badge>
                              <span style={{ fontSize: 12, color: similarityColor, fontWeight: 700, background: `${similarityColor}15`, padding: '2px 8px', borderRadius: 6 }}>{similarityPct}% parecidos</span>
                              {dup.notes && <span style={{ fontSize: 11, color: '#94a3b8', fontStyle: 'italic' }}>{dup.notes}</span>}
                            </div>
                            <span style={{ fontSize: 11, color: '#64748b' }}>Identificado em {new Date(dup.created_at).toLocaleDateString('pt-BR')}</span>
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 12, alignItems: 'stretch' }}>
                            <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 8, padding: 14, border: '1px solid rgba(255,255,255,0.04)' }}>
                              <span style={{ fontSize: 10, color: '#60a5fa', fontWeight: 700, textTransform: 'uppercase' }}>Item A</span>
                              <h4 style={{ color: '#f8fafc', margin: '6px 0 4px', fontSize: 14, fontWeight: 600 }}>{itemA?.name || 'Item não encontrado'}</h4>
                              <div style={{ fontSize: 12, color: '#94a3b8', display: 'grid', gap: 3 }}>
                                <span>Código: <strong>{itemA?.sku || '—'}</strong></span>
                                <span>Categoria: <strong>{itemA?.category || 'Não definida'}</strong></span>
                              </div>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}><ArrowRightLeft size={20} style={{ color: '#64748b' }} /></div>
                            <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: 8, padding: 14, border: '1px solid rgba(255,255,255,0.04)' }}>
                              <span style={{ fontSize: 10, color: '#a78bfa', fontWeight: 700, textTransform: 'uppercase' }}>Item B</span>
                              <h4 style={{ color: '#f8fafc', margin: '6px 0 4px', fontSize: 14, fontWeight: 600 }}>{itemB?.name || 'Item não encontrado'}</h4>
                              <div style={{ fontSize: 12, color: '#94a3b8', display: 'grid', gap: 3 }}>
                                <span>Código: <strong>{itemB?.sku || '—'}</strong></span>
                                <span>Categoria: <strong>{itemB?.category || 'Não definida'}</strong></span>
                              </div>
                            </div>
                          </div>

                          {isPending && (
                            <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid rgba(255,255,255,0.04)' }}>
                              <div style={{ display: 'flex', gap: 10, alignItems: 'end', flexWrap: 'wrap' }}>
                                <div style={{ flex: 1, minWidth: 200 }}>
                                  <Input label="Observação (opcional)" value={dedupNotes[dup.id] || ''} onChange={(e) => setDedupNotes(prev => ({ ...prev, [dup.id]: e.target.value }))} placeholder="Ex: Variações do mesmo produto" />
                                </div>
                                <Button variant="primary" size="sm" disabled={dedupResolving === dup.id} onClick={() => handleResolveDedup(dup.id, 'APPROVED_MERGE')} leftIcon={<GitMerge size={14} />}>
                                  {dedupResolving === dup.id ? 'Processando...' : 'Mesclar'}
                                </Button>
                                <Button variant="secondary" size="sm" disabled={dedupResolving === dup.id} onClick={() => handleResolveDedup(dup.id, 'REJECTED')} leftIcon={<XCircle size={14} />}>Manter distintos</Button>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>
            </div>
          ) : activeTab === 'real-data' ? (
            <div style={{ display: 'grid', gap: 18 }}>
              <div className="tabs-header" style={{ marginBottom: 12, borderBottom: '1px solid var(--border-color)', paddingBottom: 8 }}>
                <button className={`tab-btn ${realDataSubTab === 'matrix' ? 'active' : ''}`} onClick={() => setRealDataSubTab('matrix')} style={{ fontSize: 13, padding: '6px 12px', background: 'transparent', border: 'none', cursor: 'pointer', color: realDataSubTab === 'matrix' ? 'var(--primary-color)' : 'var(--text-muted)', fontWeight: 600 }}>Matriz &amp; Ativações</button>
                <button className={`tab-btn ${realDataSubTab === 'import' ? 'active' : ''}`} onClick={() => setRealDataSubTab('import')} style={{ fontSize: 13, padding: '6px 12px', background: 'transparent', border: 'none', cursor: 'pointer', color: realDataSubTab === 'import' ? 'var(--primary-color)' : 'var(--text-muted)', fontWeight: 600 }}>Importação Legada</button>
              </div>
              {realDataSubTab === 'matrix' ? <AdminRealDataDashboard onBack={() => setActiveTab('users')} /> : <LegacyImportPage currentUser={currentUser} onBack={() => setActiveTab('users')} />}
            </div>
          ) : (
            /* Auditoria tab */
            <div style={{ display: 'grid', gap: 20 }}>
              <Card variant="glass" style={{ padding: 18 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
                  <Input label="Pesquisa Textual nos Logs" value={logSearch} onChange={(e) => setLogSearch(e.target.value)} placeholder="Ex: termo técnico, ip ou ação..." leftIcon={<Search size={16} />} />
                  <Select label="Filtrar Usuário" value={logFilterUser} onChange={(e) => setLogFilterUser(e.target.value)} options={[{ value: 'ALL', label: 'Todos os usuários' }, ...uniqueLogUsers.map(user => ({ value: user, label: user }))]} />
                  <Select label="Filtrar Módulo" value={logFilterModule} onChange={(e) => setLogFilterModule(e.target.value)} options={[{ value: 'ALL', label: 'Todos os módulos' }, ...uniqueLogModules.map(mod => ({ value: mod, label: humanizeModule(mod) }))]} />
                  <Select label="Filtrar Ação" value={logFilterAction} onChange={(e) => setLogFilterAction(e.target.value)} options={[{ value: 'ALL', label: 'Todas as ações' }, ...uniqueLogActions.map(action => ({ value: action, label: humanizeAction(action) }))]} />
                </div>
              </Card>

              <Card variant="glass" style={{ padding: 0, overflow: 'hidden' }}>
                <div style={{ padding: '18px 20px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Activity size={18} style={{ color: 'var(--primary-color)' }} />
                    <span>Auditoria de Operações Realizadas ({filteredLogs.length})</span>
                  </h3>
                </div>

                {logsLoading ? (
                  <div style={{ padding: 40, textAlign: 'center', color: '#94a3b8' }}>Buscando registros na base...</div>
                ) : filteredLogs.length === 0 ? (
                  <EmptyState icon={<AlertCircle size={40} style={{ color: '#94a3b8' }} />} title="Nenhum log de auditoria encontrado" description="Tente redefinir os filtros." />
                ) : (
                  <div className="admin-user-card-list" style={{ display: 'flex', flexDirection: 'column' }}>
                    {filteredLogs.map((log) => (
                      <article key={log.id} style={{ display: 'grid', gridTemplateColumns: '150px 120px 1fr 120px', gap: 12, padding: '12px 16px', borderBottom: '1px solid var(--border-color)', alignItems: 'center' }}>
                        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{new Date(log.created_at).toLocaleString('pt-BR')}</span>
                        <Badge variant="neutral">{humanizeModule(log.module)}</Badge>
                        <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{formatHumanAuditLog(log)}</span>
                        <span style={{ fontSize: 12, color: 'var(--text-muted)', textAlign: 'right' }}>{log.ip_address || '—'}</span>
                      </article>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          )}
        </div>
      </div>

      <AdminUserDrawer
        drawerUser={drawerUser}
        onClose={closeUserDrawer}
        drawerTab={drawerTab}
        setDrawerTab={setDrawerTab}
        formError={formError}
        contextError={drawerUser ? error : null}
        loading={loading}
        onSave={handleFormSubmit}
        formFullName={formFullName}
        setFormFullName={setFormFullName}
        formUsername={formUsername}
        setFormUsername={setFormUsername}
        formEmail={formEmail}
        setFormEmail={setFormEmail}
        formDepartment={formDepartment}
        setFormDepartment={setFormDepartment}
        formJobTitle={formJobTitle}
        setFormJobTitle={setFormJobTitle}
        formRoleId={formRoleId}
        setFormRoleId={setFormRoleId}
        roles={roles}
        currentUser={currentUser}
        humanizeRole={humanizeRole}
        editablePermissionModules={editablePermissionModules}
        formPermissions={formPermissions}
        setFormPermissions={setFormPermissions}
        permissionLabels={permissionLabels}
        formPassword={formPassword}
        setFormPassword={setFormPassword}
        formPasswordConfirm={formPasswordConfirm}
        setFormPasswordConfirm={setFormPasswordConfirm}
        setTemporaryPassword={setTemporaryPassword}
        formMustChangePassword={formMustChangePassword}
        setFormMustChangePassword={setFormMustChangePassword}
        formIsActive={formIsActive}
        setFormIsActive={setFormIsActive}
        adminSessions={adminSessions}
        lifecycleLoading={lifecycleLoading}
        onRevokeSession={revokeSession}
        filteredLogs={filteredLogs}
        formatHumanAuditLog={formatHumanAuditLog}
        users={users}
        temporaryAccessModuleId={temporaryAccessModuleId}
        setTemporaryAccessModuleId={setTemporaryAccessModuleId}
        temporaryAccessLevel={temporaryAccessLevel}
        setTemporaryAccessLevel={setTemporaryAccessLevel}
        temporaryAccessReason={temporaryAccessReason}
        setTemporaryAccessReason={setTemporaryAccessReason}
        temporaryAccessExpiresAt={temporaryAccessExpiresAt}
        setTemporaryAccessExpiresAt={setTemporaryAccessExpiresAt}
        temporarySubstituteUserId={temporarySubstituteUserId}
        setTemporarySubstituteUserId={setTemporarySubstituteUserId}
        temporarySubstitutionReason={temporarySubstitutionReason}
        setTemporarySubstitutionReason={setTemporarySubstitutionReason}
        temporarySubstitutionExpiresAt={temporarySubstitutionExpiresAt}
        setTemporarySubstitutionExpiresAt={setTemporarySubstitutionExpiresAt}
        temporaryAccesses={temporaryAccesses}
        temporarySubstitutions={temporarySubstitutions}
        onCreateTemporaryAccess={createTemporaryAccess}
        onRevokeTemporaryAccess={revokeTemporaryAccess}
        onCreateTemporarySubstitution={createTemporarySubstitution}
        offboardingImpact={offboardingImpact}
        offboardingCase={offboardingCase}
        offboardingReason={offboardingReason}
        setOffboardingReason={setOffboardingReason}
        offboardingReplacementId={offboardingReplacementId}
        setOffboardingReplacementId={setOffboardingReplacementId}
        onRecalculateImpact={() => drawerUser && fetchLifecycleData(drawerUser, 'offboarding')}
        onCreateOffboardingCase={createOffboardingCase}
        onConfirmOffboardingCase={confirmOffboardingCase}
        onCompleteTask={completeOffboardingTask}
        onFailTask={failOffboardingTask}
        onCancelCase={cancelOffboardingCase}
      />

      {confirmUser && (
        <ConfirmDialog 
          isOpen={showConfirmDialog}
          onClose={() => { setShowConfirmDialog(false); setConfirmUser(null); }}
          onConfirm={handleConfirmToggle}
          title={confirmUser.is_active ? 'Inativar Usuário' : 'Ativar Usuário'}
          message={`Tem certeza que deseja ${confirmUser.is_active ? 'inativar' : 'ativar'} a conta do usuário "${confirmUser.username}"?`}
          confirmText={confirmUser.is_active ? 'Sim, Inativar' : 'Sim, Ativar'}
          variant={confirmUser.is_active ? 'danger' : 'primary'}
        />
      )}

      {deletingUser && (
        <ConfirmDialog 
          isOpen={showDeleteDialog}
          onClose={() => { setShowDeleteDialog(false); setDeletingUser(null); }}
          onConfirm={handleConfirmDelete}
          title="Excluir Usuário"
          message={`Tem certeza que deseja excluir permanentemente o usuário "${deletingUser.username}"? Esta ação é irreversível e removerá todas as permissões e sessões ativas.`}
          confirmText="Sim, Excluir"
          variant="danger"
        />
      )}
    </ModulePageLayout>
  );
};

interface AdminModulePermissionsProps {
  users: UserItem[];
  modules: ModuleItem[];
  onSaveSuccess: () => void;
  currentUser?: any;
}

const AdminModulePermissions: React.FC<AdminModulePermissionsProps> = ({ users, modules, onSaveSuccess, currentUser }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState<UserItem | null>(null);
  const [formPermissions, setFormPermissions] = useState<Record<number, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredUsersList = useMemo(() => {
    const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
    return users.filter(u => 
      u.is_active && 
      (isCurrentUserMessias || u.role_name !== 'MESSIAS') &&
      (u.username.toLowerCase().includes(searchTerm.toLowerCase()) || 
       (u.email || '').toLowerCase().includes(searchTerm.toLowerCase()))
    ).slice(0, 8);
  }, [users, searchTerm, currentUser]);

  const selectUser = (user: UserItem) => {
    setSelectedUser(user);
    setError(null);
    const permsMap: Record<number, string> = {};
    user.module_permissions.forEach(p => {
      permsMap[p.module_id] = p.permission_level;
    });
    setFormPermissions(permsMap);
  };

  const handleSave = async () => {
    if (!selectedUser) return;
    setSaving(true);
    setError(null);

    const permissionsList = Object.entries(formPermissions).map(([modId, lvl]) => ({
      module_id: parseInt(modId),
      permission_level: lvl
    }));

    try {
      const res = await fetch(`/api/v1/admin/users/${selectedUser.id}/module-access`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ permissions: permissionsList })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Falha ao salvar permissões do usuário.');
      }

      onSaveSuccess();
    } catch (err: any) {
      setError(err.message || 'Erro ao salvar permissões.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: 'grid', gap: 18 }}>
      <Card variant="glass" style={{ padding: 18 }}>
        <h3 style={{ color: '#fff', margin: '0 0 6px', fontSize: 15, fontWeight: 700 }}>Acesso a Módulos do Portal</h3>
        <p style={{ color: '#94a3b8', margin: '0 0 16px', fontSize: 13, lineHeight: 1.4 }}>
          Defina o acesso de cada usuário aos módulos do sistema. Se o nível for configurado como <strong>Sem Acesso</strong>, o módulo não será exibido.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 10, marginBottom: 12 }}>
          <Input 
            label="Buscar usuário" 
            value={searchTerm} 
            onChange={(e) => setSearchTerm(e.target.value)} 
            placeholder="Nome, usuário ou e-mail" 
            leftIcon={<Search size={16} />} 
          />
        </div>

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
          {filteredUsersList.map((user) => (
            <button
              key={user.id}
              className={`tab-btn ${selectedUser?.id === user.id ? 'active' : ''}`}
              onClick={() => selectUser(user)}
              style={{ border: '1px solid var(--border-color)', borderRadius: 8, fontSize: 13, padding: '8px 12px', background: selectedUser?.id === user.id ? 'var(--primary-color-dim)' : 'transparent', color: 'var(--text-primary)', cursor: 'pointer' }}
            >
              <strong>{user.username}</strong>
            </button>
          ))}
        </div>
      </Card>

      {error && (
        <div style={{ color: '#fecaca', background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.25)', padding: 12, borderRadius: 8, fontSize: 13 }}>
          {error}
        </div>
      )}

      {selectedUser && (
        <Card variant="glass" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: 18, borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <h3 style={{ color: '#fff', margin: 0, fontSize: 14, fontWeight: 700 }}>{selectedUser.username}</h3>
            </div>
            <Button size="sm" onClick={handleSave} disabled={saving}>
              {saving ? 'Salvando...' : 'Salvar Alterações'}
            </Button>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'rgba(255,255,255,0.01)', borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: 12, textAlign: 'left', color: 'var(--text-muted)' }}>Módulo</th>
                  <th style={{ padding: 12, textAlign: 'left', color: 'var(--text-muted)' }}>Permissão</th>
                </tr>
              </thead>
              <tbody>
                {modules.filter((module) => !isChatModule(module)).map((m) => (
                  <tr key={m.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: 12, color: '#f8fafc', fontWeight: 600 }}>{m.name}</td>
                    <td style={{ padding: 12 }}>
                      <Select
                        value={formPermissions[m.id] || 'NO_ACCESS'}
                        onChange={(e) => setFormPermissions({ ...formPermissions, [m.id]: e.target.value })}
                        style={{ marginBottom: 0, minWidth: 200 }}
                        options={[
                          { value: 'NO_ACCESS', label: 'Sem Acesso (Bloqueado)' },
                          { value: 'READ_ONLY', label: 'Apenas Leitura' },
                          { value: 'NORMAL', label: 'Uso normal' },
                          { value: 'MANAGER', label: 'Gestor' },
                          { value: 'ADMIN', label: 'Controle Total (Admin)' }
                        ]}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};
