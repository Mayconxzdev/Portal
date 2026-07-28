import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckSquare,
  Cpu,
  Files,
  HardDrive,
  Laptop,
  MessageSquareText,
  Package,
  Settings,
  ShoppingCart,
  Kanban,
  FileText,
  PlusCircle,
  Search,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { ModuleCard, ModuleCardState } from '../components/ui/ModuleCard';
import { KodaCard } from '../components/ui/KodaCard';
import { FooterStatusBar } from '../components/ui/FooterStatusBar';
import { ModuleHero } from '../components/ui/ModuleHero';

interface MetricItem {
  users_total: number;
  modules_total: number;
  pending_approvals: number;
  audit_logs_total: number;
  active_tickets: number;
  active_proposals: number;
  low_stock_items: number;
  active_workflows: number;
  pending_action_intents?: number;
  active_kanban_boards: number;
  total_kanban_cards: number;
  open_kanban_cards: number;
  overdue_kanban_cards: number;
  unassigned_kanban_cards: number;
  high_priority_kanban_cards: number;
  recently_updated_kanban_cards: number;
  due_today_kanban_cards: number;
  critical_kanban_cards: number;
  boards_with_pending: Record<string, number>;
  kanban_cards_by_priority: Record<string, number>;
  expiring_it_certificates?: number;
}

interface DashboardPageProps {
  metrics: MetricItem;
  modules: Array<{
    id: number;
    name: string;
    code: string;
    is_active: boolean;
    is_restricted: boolean;
    permission_level?: string;
  }>;
  currentUser?: any;
  onNavigate: (moduleCode: string) => void;
  onOpenSearch?: () => void;
}

const moduleOrder = ['kanban', 'it', 'approvals', 'admin', 'files', 'stock', 'chat', 'purchases', 'proposals', 'automations'];

const moduleInfo: Record<string, { name: string; state: ModuleCardState; description: string; action: string }> = {
  kanban: { name: 'Kanban', state: 'complete', description: 'Quadros, listas, TV/Foco e produção.', action: 'Entrar' },
  it: { name: 'TI', state: 'complete', description: 'Chamados, SLA, inventário e cofre.', action: 'Abrir TI' },
  approvals: { name: 'Aprovações', state: 'complete', description: 'Solicitações e decisões auditadas.', action: 'Ver aprovações' },
  admin: { name: 'Administração', state: 'complete', description: 'Usuários, permissões e auditoria.', action: 'Administrar' },
  files: { name: 'Arquivos / Knowledge', state: 'partial', description: 'Base segura de anexos e conhecimento em evolução.', action: 'Ver base' },
  stock: { name: 'Estoque & Catálogo', state: 'complete', description: 'Consulte produtos, códigos, preços e fornecedores.', action: 'Entrar' },
  chat: { name: 'Chat Interno', state: 'complete', description: 'Canais, DMs, grupos e anexos em tempo real.', action: 'Entrar' },
  purchases: { name: 'Compras', state: 'complete', description: 'Cotações de fornecedores, requisições de compras e ordens.', action: 'Entrar' },
  proposals: { name: 'Propostas', state: 'soon', description: 'Fluxo comercial planejado para fase futura.', action: 'Em breve' },
  automations: { name: 'Automações IA', state: 'complete', description: 'Revisão de ações propostas por robôs e automações.', action: 'Entrar' },
};

const plural = (count: number, singular: string, pluralText: string) => `${count} ${count === 1 ? singular : pluralText}`;

const getModuleIcon = (code: string) => {
  switch (code) {
    case 'kanban': return <Kanban size={24} />;
    case 'proposals': return <FileText size={24} />;
    case 'purchases': return <ShoppingCart size={24} />;
    case 'it': return <Laptop size={24} />;
    case 'chat': return <MessageSquareText size={24} />;
    case 'files': return <Files size={24} />;
    case 'stock': return <Package size={24} />;
    case 'approvals': return <CheckSquare size={24} />;
    case 'automations': return <Cpu size={24} />;
    case 'admin': return <Settings size={24} />;
    default: return <HardDrive size={24} />;
  }
};

const getModuleBadge = (code: string, metrics: MetricItem, chatUnread: number | null) => {
  switch (code) {
    case 'kanban':
      return metrics.open_kanban_cards > 0 ? plural(metrics.open_kanban_cards, 'card aberto', 'cards abertos') : 'Sem pendências';
    case 'it':
      return metrics.active_tickets > 0 ? plural(metrics.active_tickets, 'chamado ativo', 'chamados ativos') : 'Sem chamados ativos';
    case 'approvals':
      return metrics.pending_approvals > 0 ? plural(metrics.pending_approvals, 'aprovação pendente', 'aprovações pendentes') : 'Sem aprovações pendentes';
    case 'admin':
      return plural(metrics.users_total || 0, 'usuário', 'usuários');
    case 'files':
      return 'Base preparada';
    case 'chat':
      return chatUnread !== null && chatUnread > 0
        ? `${chatUnread} ${chatUnread === 1 ? 'não lida' : 'não lidas'}`
        : 'Sem novas mensagens';
    case 'stock':
      return 'Base saneada';
    case 'purchases':
    case 'proposals':
      return 'Em breve';
    case 'automations':
      return (metrics.pending_action_intents || 0) > 0
        ? plural(metrics.pending_action_intents || 0, 'acao sugerida pendente', 'acoes sugeridas pendentes')
        : 'Sem acoes sugeridas pendentes';
    default:
      return 'Planejado';
  }
};

export const DashboardPage: React.FC<DashboardPageProps> = ({
  metrics,
  modules,
  currentUser,
  onNavigate,
  onOpenSearch,
}) => {
  const [accessModalOpen, setAccessModalOpen] = useState(false);
  const [selectedModuleForAccess, setSelectedModuleForAccess] = useState('');
  const [chatUnread, setChatUnread] = useState<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;
    const fetchUnread = async () => {
      try {
        if (typeof window !== 'undefined' && window.location.origin && window.location.origin.startsWith('http')) {
          const res = await fetch('/api/v1/chat/unread-summary', { signal: controller.signal });
          if (res.ok) {
            const data = await res.json();
            if (mounted && !controller.signal.aborted) {
              setChatUnread(data.unread_count);
            }
          }
        }
      } catch (e) {
        if (!mounted || controller.signal.aborted) return;
        if (e instanceof Error && e.name !== 'AbortError' && !e.message.includes('Failed to parse URL') && !e.message.includes('Failed to fetch')) {
          console.error('Erro ao buscar mensagens não lidas do chat:', e);
        }
      }
    };
    fetchUnread();
    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  const cards = useMemo(() => moduleOrder.map((code) => {
    const dbModule = modules.find((mod) => mod.code === code);
    const info = moduleInfo[code];
    return {
      id: dbModule?.id ?? code,
      code,
      permission_level: dbModule?.permission_level || (currentUser?.role === 'ADMIN' ? 'ADMIN' : 'NORMAL'),
      ...info,
      name: dbModule?.name || info.name,
    };
  }), [modules, currentUser?.role]);

  const handleModuleClick = (mod: typeof cards[number]) => {
    if (mod.permission_level === 'NO_ACCESS') {
      setSelectedModuleForAccess(mod.name);
      setAccessModalOpen(true);
      return;
    }
    if (mod.state === 'soon') return;
    onNavigate(mod.code);
  };

  const alerts = [
    metrics.pending_approvals > 0 ? { label: 'Aprovações', text: plural(metrics.pending_approvals, 'aprovação pendente', 'aprovações pendentes') } : null,
    (metrics.pending_action_intents || 0) > 0 ? { label: 'Automações', text: plural(metrics.pending_action_intents || 0, 'ação sugerida pendente', 'ações sugeridas pendentes') } : null,
    metrics.active_tickets > 0 ? { label: 'TI', text: plural(metrics.active_tickets, 'chamado ativo', 'chamados ativos') } : null,
    metrics.overdue_kanban_cards > 0 ? { label: 'Kanban', text: plural(metrics.overdue_kanban_cards, 'card atrasado', 'cards atrasados') } : null,
    (metrics.expiring_it_certificates || 0) > 0 ? { label: 'Certificados', text: plural(metrics.expiring_it_certificates || 0, 'certificado vencendo', 'certificados vencendo') } : null,
  ].filter(Boolean) as { label: string; text: string }[];

  const displayName = currentUser?.full_name || currentUser?.username || 'usuário';
  const isAdmin = currentUser?.role === 'ADMIN';

  return (
    <div className="dashboard-page">
      <ModuleHero
        title={`Bem-vindo, ${displayName}! 👋`}
        description="Painel operacional do Portal Vesper."
        eyebrow="Portal Vesper"
        compact={true}
        showKoda={false}
        actions={
          <>
            <Button variant="primary" size="sm" onClick={onOpenSearch} leftIcon={<Search size={15} />}>
              Buscar no Portal
            </Button>
            <Button variant="secondary" size="sm" onClick={() => onNavigate('it')} leftIcon={<PlusCircle size={15} />}>
              Abrir chamado
            </Button>
          </>
        }
      />

      <div className="dashboard-layout">
        <div className="dashboard-modules-grid">
          {cards.map((mod) => {
            const hasAccess = mod.permission_level !== 'NO_ACCESS';
            const isSoon = mod.state === 'soon';
            return (
              <ModuleCard
                key={mod.code}
                icon={getModuleIcon(mod.code)}
                title={mod.name}
                description={mod.description}
                badge={getModuleBadge(mod.code, metrics, chatUnread)}
                actionLabel={!hasAccess ? 'Sem acesso' : mod.action}
                state={mod.state}
                moduleCode={mod.code}
                disabled={isSoon || !hasAccess}
                onClick={() => handleModuleClick(mod)}
              />
            );
          })}
        </div>

        <aside className="dashboard-sidebar-container">
          <div className="glass-card dashboard-side-card">
            <h4 className="dashboard-side-title">Ações rápidas</h4>
            <div className="quick-action-list">
              <button type="button" className="shortcut-link-button" onClick={() => onNavigate('it')}>
                <span>Abrir chamado de TI</span>
                <PlusCircle size={14} />
              </button>
              <button type="button" className="shortcut-link-button" onClick={() => onNavigate('kanban')}>
                <span>Abrir Kanban</span>
                <PlusCircle size={14} />
              </button>
              <button type="button" className="shortcut-link-button" onClick={() => onNavigate('approvals')}>
                <span>Ver aprovações</span>
                <PlusCircle size={14} />
              </button>
              {isAdmin && (
                <button type="button" className="shortcut-link-button" onClick={() => onNavigate('admin')}>
                  <span>Administração</span>
                  <PlusCircle size={14} />
                </button>
              )}
            </div>
          </div>

          <div className="glass-card dashboard-side-card">
            <h4 className="dashboard-side-title">Alertas reais</h4>
            {alerts.length === 0 ? (
              <div className="dashboard-empty-alert">
                <AlertTriangle size={16} />
                <span>Sem alertas operacionais no momento.</span>
              </div>
            ) : (
              <div className="dashboard-notification-list">
                {alerts.map((alert) => (
                  <div className="dashboard-notification-item" key={`${alert.label}-${alert.text}`}>
                    <strong>{alert.label}</strong>
                    <span>{alert.text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <KodaCard
            title="Precisa de ajuda?"
            description="Comece por TI, Kanban ou Aprovações quando precisar agir agora. Módulos planejados não têm botões falsos."
            actionLabel="Falar com o Koda"
            onAction={() => onNavigate('chat')}
          />
        </aside>
      </div>

      <FooterStatusBar
        items={[
          'Dados exibidos a partir do backend local',
          'Ambiente de produção',
          'Nenhum card usa pendências simuladas',
          'Variação 5 • Premium Dark Glass',
        ]}
      />

      <Modal
        isOpen={accessModalOpen}
        onClose={() => setAccessModalOpen(false)}
        title="Acesso necessário"
      >
        <div className="modal-form-section">
          <p className="form-help-text">
            Você não possui acesso ao módulo {selectedModuleForAccess}. Solicite a liberação ao administrador do Portal.
            O Dashboard não exibe dados simulados para módulos sem permissão.
          </p>
          <div className="modal-actions">
            <Button variant="secondary" onClick={() => setAccessModalOpen(false)}>
              Entendi
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default DashboardPage;
