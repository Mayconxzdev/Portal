import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Kanban,
  FileText,
  ShoppingCart,
  Laptop,
  MessageSquareText,
  Files,
  Package,
  CheckSquare,
  Cpu,
  Settings,
  Lock,
  Search,
  Ticket,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Sparkles,
  Sun,
  Moon,
  Menu as MenuIcon,
  X as CloseIcon,
} from 'lucide-react';
import { Tooltip } from '../components/ui/Tooltip';
import { Button } from '../components/ui/Button';
import { CreateTicketModal } from '../components/it/CreateTicketModal';
import { useMediaQuery, BREAKPOINTS } from '../hooks/useMediaQuery';
import { NotificationBell } from '../components/notifications/NotificationBell';

interface ModuleItem {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
  is_restricted: boolean;
  permission_level?: string;
}

interface LayoutProps {
  children: React.ReactNode;
  activeModule: string;
  onNavigate: (moduleCode: string, options?: { replace?: boolean; search?: URLSearchParams | Record<string, string | number | boolean | undefined | null> | string }) => void;
  backendOnline: boolean;
  modules: ModuleItem[];
  user: {
    username: string;
    email: string;
    role: string;
  } | null;
  onLogout: () => void;
  onOpenSearch: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

const getModuleIcon = (code: string) => {
  const iconStyle = { color: `var(--module-${code === 'proposals' ? 'proposals' : code})` };
  switch (code) {
    case 'dashboard': return <LayoutDashboard size={20} style={iconStyle} />;
    case 'kanban': return <Kanban size={20} style={iconStyle} />;
    case 'proposals': return <FileText size={20} style={iconStyle} />;
    case 'purchases': return <ShoppingCart size={20} style={iconStyle} />;
    case 'it': return <Laptop size={20} style={iconStyle} />;
    case 'chat': return <MessageSquareText size={20} style={iconStyle} />;
    case 'files': return <Files size={20} style={iconStyle} />;
    case 'stock': return <Package size={20} style={iconStyle} />;
    case 'approvals': return <CheckSquare size={20} style={iconStyle} />;
    case 'automations': return <Cpu size={20} style={iconStyle} />;
    case 'admin': return <Settings size={20} style={iconStyle} />;
    default: return <Files size={20} style={{ color: 'var(--text-muted)' }} />;
  }
};

const getModuleTooltip = (code: string, isRestricted: boolean) => {
  let desc = '';
  switch (code) {
    case 'dashboard': desc = 'Painel principal com resumo de atividades.'; break;
    case 'kanban': desc = 'Organize tarefas, produção e pendências.'; break;
    case 'proposals': desc = 'Elaboração de propostas comerciais e templates de documentos.'; break;
    case 'purchases': desc = 'Gerencie requisições, cotações e preços de referência.'; break;
    case 'it': desc = 'Suporte interno e abertura de chamados.'; break;
    case 'chat': desc = 'Comunicação interna em tempo real.'; break;
    case 'files': desc = 'Base de anexos pronta; biblioteca futura.'; break;
    case 'stock': desc = 'Consulte produtos, códigos, preços e fornecedores.'; break;
    case 'approvals': desc = 'Decisões pendentes e aprovações.'; break;
    case 'automations': desc = 'Revisão de ações propostas por automações.'; break;
    case 'admin': desc = 'Usuários, permissões e auditoria.'; break;
    default: desc = 'Módulo do sistema.';
  }
  return isRestricted ? `${desc} (Acesso restrito)` : desc;
};

const getModuleDisplayName = (mod: ModuleItem) => {
  switch (mod.code) {
    case 'dashboard': return 'Dashboard';
    case 'kanban': return 'Kanban';
    case 'proposals': return 'Propostas';
    case 'purchases': return 'Compras';
    case 'it': return 'TI';
    case 'chat': return 'Chat Interno';
    case 'files': return 'Arquivos / Knowledge';
    case 'stock': return 'Estoque & Catálogo';
    case 'approvals': return 'Aprovações';
    case 'automations': return 'Automações IA';
    case 'admin': return 'Administração';
    default: return mod.name;
  }
};

const getModuleFamily = (code: string) => {
  if (code === 'dashboard') return 'Operacional';
  if (['kanban', 'purchases', 'it', 'chat'].includes(code)) return 'Operacional';
  if (['approvals', 'automations', 'stock'].includes(code)) return 'Gestão';
  if (['admin', 'files'].includes(code)) return 'Administração';
  return 'Outros';
};

const familyOrder = ['Operacional', 'Gestão', 'Administração', 'Outros'];

export const Layout: React.FC<LayoutProps> = ({
  children,
  activeModule,
  onNavigate,
  backendOnline,
  modules,
  user,
  onLogout,
  onOpenSearch,
  theme,
  onToggleTheme,
}) => {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => localStorage.getItem('vesper-sidebar-collapsed') === 'true');
  const [ticketOpen, setTicketOpen] = useState(false);
  const [ticketMessage, setTicketMessage] = useState('');

  const isMobile = useMediaQuery(BREAKPOINTS.mobile);
  const [mobileNavOpen, setMobileNavOpen] = useState<boolean>(false);

  useEffect(() => {
    if (!isMobile && mobileNavOpen) {
      setMobileNavOpen(false);
    }
  }, [isMobile, mobileNavOpen]);

  const toggleSidebar = () => {
    if (isMobile) {
      setMobileNavOpen((prev) => !prev);
      return;
    }
    setIsCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('vesper-sidebar-collapsed', String(next));
      return next;
    });
  };

  const closeMobileNav = () => setMobileNavOpen(false);

  // Esc fecha o menu mobile.
  useEffect(() => {
    if (!mobileNavOpen) return;
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileNavOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [mobileNavOpen]);

  const accessibleModules = modules.filter((mod) => mod.permission_level !== 'NO_ACCESS');
  // Hide only non-functional modules for regular users. Stock is now an operational catalog.
  const isAdmin = user?.role === 'ADMIN' || user?.role === 'MANAGER';
  const functionalModules = accessibleModules.filter((mod) => {
    // Always show these modules
    if (['dashboard', 'kanban', 'purchases', 'it', 'chat', 'approvals', 'automations', 'admin', 'files'].includes(mod.code)) {
      return true;
    }
    return true;
  });
  const groupedModules = familyOrder
    .map((family) => ({
      family,
      modules: functionalModules.filter((mod) => getModuleFamily(mod.code) === family),
    }))
    .filter((group) => group.modules.length > 0);

  const sidebarClassName = [
    'sidebar',
    !isMobile && isCollapsed ? 'sidebar-collapsed' : '',
    isMobile && mobileNavOpen ? 'sidebar-mobile-open' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className="app-container">
      {isMobile && mobileNavOpen && (
        <div
          className="sidebar-backdrop"
          onClick={closeMobileNav}
          aria-hidden={true}
        />
      )}

      <aside className={sidebarClassName} aria-hidden={isMobile && !mobileNavOpen}>
        <div className="sidebar-header">
          {!isCollapsed && !isMobile && (
            <div className="sidebar-brand">
              <div className="sidebar-brand-mark">V</div>
              <span className="sidebar-logo">Portal Vesper</span>
            </div>
          )}

          {!isMobile && (
            <Tooltip text={isCollapsed ? 'Expandir barra lateral' : 'Recolher barra lateral'} placement={isCollapsed ? 'right' : 'top'}>
              <button
                type="button"
                onClick={toggleSidebar}
                className="sidebar-toggle-btn"
                aria-label={isCollapsed ? 'Abrir barra lateral' : 'Fechar barra lateral'}
              >
                {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
              </button>
            </Tooltip>
          )}

          {isMobile && (
            <Tooltip text="Fechar menu" placement="left">
              <button
                type="button"
                onClick={closeMobileNav}
                className="sidebar-toggle-btn"
                aria-label="Fechar menu"
              >
                <CloseIcon size={16} />
              </button>
            </Tooltip>
          )}
        </div>

        <nav className="sidebar-menu" aria-label="Módulos do Portal Vesper">
          {groupedModules.map((group) => (
            <div className="sidebar-menu-section" key={group.family}>
              {!isCollapsed && !isMobile && <div className="sidebar-menu-section-label">{group.family}</div>}
              <ul>
                {group.modules.map((mod) => {
                  const isActive = activeModule === mod.code;
                  const isRestricted = mod.is_restricted;
                  const isOfflineAndNotDashboard = !backendOnline && mod.code !== 'dashboard';
                  const tooltipText = isMobile
                    ? getModuleDisplayName(mod)
                    : getModuleTooltip(mod.code, isRestricted);

                  return (
                    <li key={mod.id}>
                      <Tooltip text={tooltipText} placement={isMobile ? 'right' : (isCollapsed ? 'right' : 'top')}>
                        <button
                          onClick={() => {
                            if (isOfflineAndNotDashboard) return;
                            onNavigate(mod.code);
                            if (isMobile) setMobileNavOpen(false);
                          }}
                          className={`menu-item ${isActive ? 'active' : ''} ${isOfflineAndNotDashboard ? 'disabled' : ''}`}
                          disabled={isOfflineAndNotDashboard}
                          aria-current={isActive ? 'page' : undefined}
                        >
                          <div className="menu-item-left">
                            {getModuleIcon(mod.code)}
                            <span>{getModuleDisplayName(mod)}</span>
                          </div>
                          <div className="menu-item-trailing">
                            {mod.code === 'admin' && user?.role === 'ADMIN' && (
                              <span className="menu-item-notification-dot" aria-hidden={true} />
                            )}
                            {isRestricted && <Lock className="lock-icon" />}
                          </div>
                        </button>
                      </Tooltip>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="user-avatar">
              {user ? user.username.substring(0, 2).toUpperCase() : 'US'}
            </div>
            {!isCollapsed && !isMobile && (
              <div className="user-info">
                <span className="user-name">{user ? user.username : 'Carregando...'}</span>
                <span className="user-role">{user ? (user.role === 'ADMIN' ? 'Administrador' : 'Colaborador') : 'Usuário Local'}</span>
              </div>
            )}
          </div>
          {user && (
            isCollapsed && !isMobile ? (
              <Tooltip text="Sair do Portal">
                <button type="button" onClick={onLogout} className="sidebar-logout-compact">
                  <LogOut size={16} />
                </button>
              </Tooltip>
            ) : (
              <Button variant="secondary" size="sm" onClick={onLogout} style={{ width: '100%', marginTop: '12px' }}>
                Sair do Portal
              </Button>
            )
          )}
        </div>
      </aside>

      <div className="main-content">
        <header className="topbar">
          {isMobile && (
            <Tooltip text={mobileNavOpen ? 'Fechar menu' : 'Abrir menu'} placement="bottom">
              <button
                type="button"
                className="topbar-hamburger"
                onClick={toggleSidebar}
                aria-label={mobileNavOpen ? 'Fechar menu' : 'Abrir menu'}
                aria-expanded={mobileNavOpen}
              >
                {mobileNavOpen ? <CloseIcon size={18} /> : <MenuIcon size={18} />}
              </button>
            </Tooltip>
          )}

          <div className="search-container cursor-pointer" onClick={onOpenSearch}>
            <Search size={16} style={{ color: '#a5b4fc' }} />
            <input
              type="text"
              className="search-input cursor-pointer"
              placeholder="Buscar no portal ou digite um atalho..."
              title="Atalho: Ctrl+K"
              readOnly
            />
          </div>

          <div className="topbar-right">
            <Tooltip text="Supervisor IA planejado para fase futura">
              <div className="ai-supervisor-box" style={{ opacity: 0.85, cursor: 'not-allowed' }}>
                <Sparkles size={16} />
                <span>Supervisor IA</span>
              </div>
            </Tooltip>

            <NotificationBell backendOnline={backendOnline} onNavigate={onNavigate} />

            <Tooltip text={theme === 'light' ? 'Mudar para Modo Escuro' : 'Mudar para Modo Claro'}>
              <button type="button" onClick={onToggleTheme} className="theme-toggle-btn" aria-label="Alternar tema">
                {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
              </button>
            </Tooltip>

            <Tooltip text="Abrir chamado de TI">
              <button type="button" className="ticket-btn" onClick={() => setTicketOpen(true)} aria-label="Abrir chamado de TI">
                <Ticket size={16} />
              </button>
            </Tooltip>

            <Tooltip text={backendOnline ? 'Servidor conectado e operacional.' : 'Falha na conexão com o servidor.'}>
              <div className="backend-status">
                <span className={`status-dot ${backendOnline ? 'online' : 'offline'}`}></span>
                <span>{backendOnline ? 'ONLINE' : 'OFFLINE'}</span>
              </div>
            </Tooltip>
          </div>
        </header>

        <main className="page-container">
          {!backendOnline && (
            <div className="offline-banner">
              <AlertTriangle size={20} />
              <div>
                <div className="offline-banner-title">Conexão com o servidor indisponível</div>
                <div className="offline-banner-text">
                  O Portal Vesper está desconectado do servidor. Exibindo dados locais de contingência. Por favor, reinicie a API local na porta 8000.
                </div>
              </div>
            </div>
          )}
          {children}
          {ticketMessage && <div className="global-toast">{ticketMessage}</div>}
        </main>
      </div>

      <CreateTicketModal
        open={ticketOpen}
        onClose={() => setTicketOpen(false)}
        onCreated={(ticket) => {
          setTicketMessage(`Chamado ${ticket.ticket_number} aberto com sucesso.`);
          window.setTimeout(() => setTicketMessage(''), 4000);
          onNavigate('it');
        }}
      />
    </div>
  );
};

export default Layout;


