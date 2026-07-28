import React, { useState, useEffect } from 'react';
import { Layout } from './layout/Layout';
import { LoginPage } from './pages/LoginPage';
import { KanbanTVPage } from './pages/KanbanTVPage';
import { CommandPalette } from './components/CommandPalette';

type NavigateOptions = {
  replace?: boolean;
  search?: URLSearchParams | Record<string, string | number | boolean | undefined | null> | string;
};

const MODULE_PATHS: Record<string, string> = {
  dashboard: '/dashboard',
  kanban: '/kanban',
  proposals: '/proposals',
  purchases: '/purchases',
  it: '/it',
  chat: '/chat',
  files: '/files',
  stock: '/stock',
  approvals: '/approvals',
  automations: '/automations',
  admin: '/admin',
  notifications: '/notifications',
  'legacy-import': '/legacy-import',
};

const PATH_MODULES = Object.entries(MODULE_PATHS).reduce<Record<string, string>>((acc, [moduleCode, path]) => {
  acc[path] = moduleCode;
  return acc;
}, {});

const getModuleFromLocation = () => {
  const path = window.location.pathname.replace(/\/+$/, '') || '/';
  if (path === '/' || path.startsWith('/kanban/tv/')) return 'dashboard';
  return PATH_MODULES[path] || 'dashboard';
};

const buildModuleUrl = (moduleCode: string, options: NavigateOptions = {}) => {
  const path = MODULE_PATHS[moduleCode] || `/${moduleCode}`;
  if (!options.search) return path;
  if (typeof options.search === 'string') {
    return options.search ? `${path}${options.search.startsWith('?') ? options.search : `?${options.search}`}` : path;
  }

  const params = options.search instanceof URLSearchParams
    ? new URLSearchParams(options.search)
    : new URLSearchParams();

  if (!(options.search instanceof URLSearchParams)) {
    Object.entries(options.search).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.set(key, String(value));
      }
    });
  }

  const query = params.toString();
  return query ? `${path}?${query}` : path;
};

const DashboardPage = React.lazy(() => import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })));
const KanbanPage = React.lazy(() => import('./pages/KanbanPage').then((module) => ({ default: module.KanbanPage })));
const ProposalsPage = React.lazy(() => import('./pages/ProposalsPage').then((module) => ({ default: module.ProposalsPage })));
const PurchasesPage = React.lazy(() => import('./pages/PurchasesPage').then((module) => ({ default: module.PurchasesPage })));
const ITPage = React.lazy(() => import('./pages/ITPage').then((module) => ({ default: module.ITPage })));
const ChatPage = React.lazy(() => import('./pages/ChatPage').then((module) => ({ default: module.ChatPage })));
const FilesKnowledgePage = React.lazy(() => import('./pages/FilesKnowledgePage').then((module) => ({ default: module.FilesKnowledgePage })));
const StockPage = React.lazy(() => import('./pages/StockPage').then((module) => ({ default: module.StockPage })));
const ApprovalsPage = React.lazy(() => import('./pages/ApprovalsPage').then((module) => ({ default: module.ApprovalsPage })));
const AutomationsPage = React.lazy(() => import('./pages/AutomationsPage').then((module) => ({ default: module.AutomationsPage })));
const AdminPage = React.lazy(() => import('./pages/AdminPage').then((module) => ({ default: module.AdminPage })));
const NotificationsPage = React.lazy(() => import('./pages/NotificationsPage').then((module) => ({ default: module.NotificationsPage })));
const LegacyImportPage = React.lazy(() => import('./pages/LegacyImportPage').then((module) => ({ default: module.LegacyImportPage })));

export const App: React.FC = () => {
  const [activeModule, setActiveModule] = useState<string>(() => getModuleFromLocation());
  const [apiStatus, setApiStatus] = useState<'online' | 'offline' | 'loading'>('loading');
  const [modules, setModules] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [user, setUser] = useState<any>(null);
  const [initialLoading, setInitialLoading] = useState<boolean>(true);
  const [commandOpen, setCommandOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('vesper-theme') as 'light' | 'dark') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('vesper-theme', theme);
  }, [theme]);

  const navigateToModule = React.useCallback((moduleCode: string, options: NavigateOptions = {}) => {
    setActiveModule(moduleCode);

    const nextUrl = buildModuleUrl(moduleCode, options);
    const currentUrl = `${window.location.pathname}${window.location.search}`;
    if (nextUrl !== currentUrl) {
      const method = options.replace ? 'replaceState' : 'pushState';
      window.history[method](null, '', nextUrl);
    }
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setActiveModule(getModuleFromLocation());
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);


  // Consulta o backend para checar saúde e validar sessão do usuário
  const checkSession = async () => {
    try {
      const healthRes = await fetch('/api/v1/health');
      if (healthRes.ok) {
        setApiStatus('online');
        // Tenta obter informações da sessão ativa
        const userRes = await fetch('/api/v1/auth/me');
        if (userRes.ok) {
          const userData = await userRes.json();
          setUser({
            id: userData.id,
            username: userData.username,
            email: userData.email,
            role: userData.role,
            module_permissions: userData.module_permissions
          });
          
          // Carrega os módulos cadastrados e suas permissões
          const modulesRes = await fetch('/api/v1/modules');
          if (modulesRes.ok) {
            const modulesData = await modulesRes.json();
            if (modulesData.modules) {
              setModules(modulesData.modules);
            }
          }
          
          // Carrega estatísticas do Dashboard
          const hasDashboardAccess = userData.role === 'ADMIN' || (userData.module_permissions && userData.module_permissions.dashboard !== 'NO_ACCESS');
          if (hasDashboardAccess) {
            const dashboardRes = await fetch('/api/v1/dashboard/summary');
            if (dashboardRes.ok) {
              const dashboardData = await dashboardRes.json();
              if (dashboardData.metrics) {
                setMetrics(dashboardData.metrics);
              }
            }
          }
        } else {
          // Sessão expirada ou não autenticado
          setUser(null);
        }
      } else {
        throw new Error();
      }
    } catch (err) {
      setApiStatus('offline');
      setUser(null);
    } finally {
      setInitialLoading(false);
    }
  };

  const handleLoginSuccess = (userData: any) => {
    setUser({
      id: userData.id,
      username: userData.username,
      email: userData.email,
      role: userData.role,
      module_permissions: userData.module_permissions
    });
    // Recarrega todos os dados
    checkSession();
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/v1/auth/logout', { method: 'POST' });
    } catch (err) {
      console.error("Falha ao encerrar sessão no servidor:", err);
    } finally {
      setUser(null);
      setModules([]);
      setMetrics(null);
      navigateToModule('dashboard', { replace: true });
    }
  };

  useEffect(() => {
    checkSession();
    
    // Polling de contingência a cada 30 segundos (reduzido de 15s para economizar conexões redundantes quando o WebSocket está ativo)
    const interval = setInterval(checkSession, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!user || apiStatus !== 'online') return;
    
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProto}//${window.location.host}/api/v1/ws/notifications`);
    
    let pingInterval: number;
    
    ws.onopen = () => {
      pingInterval = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        }
      }, 25000);
    };
    
    ws.onmessage = (event) => {
      try {
        if (event.data === 'pong') return;
        const message = JSON.parse(event.data);
        if (['approval_notification', 'it_event', 'kanban_event', 'notification'].includes(message.type)) {
          checkSession();
        }
      } catch {
        // Ignora pings ou formatos simples
      }
    };
    
    ws.onclose = () => {
      window.clearInterval(pingInterval);
    };
    
    return () => {
      window.clearInterval(pingInterval);
      ws.close();
    };
  }, [user, apiStatus]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setCommandOpen(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Exibe tela de carregamento inicial
  if (initialLoading) {
    return (
      <div style={splashStyles.container}>
        <div style={splashStyles.logoContainer}>
          <span style={splashStyles.logoText}>V</span>
          <span style={splashStyles.logoSubtext}>ESPER</span>
        </div>
        <div style={splashStyles.spinner}></div>
        <span style={splashStyles.loadingText}>Iniciando Portal Vesper...</span>
      </div>
    );
  }

  // Exibe tela de login caso não esteja logado
  if (!user) {
    return (
      <LoginPage 
        onLoginSuccess={handleLoginSuccess} 
        apiStatus={apiStatus} 
      />
    );
  }

  const tvMatch = window.location.pathname.match(/^\/kanban\/tv\/(\d+)/);
  if (tvMatch) {
    return <KanbanTVPage boardId={Number(tvMatch[1])} onExit={() => window.location.assign('/kanban')} />;
  }

  // Verifica se o usuário tem permissão para visualizar o módulo ativo
  const hasAccessToActiveModule = () => {
    if (activeModule === 'notifications') return true;
    if (activeModule === 'it') return true;
    if (user.role === 'ADMIN') return true;
    if (activeModule === 'legacy-import') {
      return user.role === 'ADMIN' || user.role === 'MANAGER';
    }
    const level = user.module_permissions?.[activeModule];
    return level && level !== 'NO_ACCESS';
  };

  // Renderiza a página ativa do módulo
  const renderPage = () => {
    if (!hasAccessToActiveModule()) {
      return (
        <div style={errorPageStyles.container}>
          <div style={errorPageStyles.iconContainer}>
            <svg style={errorPageStyles.icon} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m0-8v6m0 5h.01M5.93 19.5h12.14a2 2 0 001.8-2.9L13.8 5.75a2 2 0 00-3.6 0L4.13 16.6a2 2 0 001.8 2.9z" />
            </svg>
          </div>
          <h2 style={errorPageStyles.title}>Acesso Negado</h2>
          <p style={errorPageStyles.message}>
            Você não possui a permissão necessária para acessar o módulo <strong>"{activeModule.toUpperCase()}"</strong>.
          </p>
          <p style={errorPageStyles.submessage}>
            Por favor, contate o administrador geral do sistema para solicitar permissão de acesso.
          </p>
          <button 
            style={errorPageStyles.button} 
            onClick={() => navigateToModule('dashboard')}
          >
            Voltar para o Dashboard
          </button>
        </div>
      );
    }

    switch (activeModule) {
      case 'dashboard':
        return (
          <DashboardPage 
            metrics={metrics || {
              users_total: 0,
              modules_total: 0,
              pending_approvals: 0,
              audit_logs_total: 0,
              active_tickets: 0,
              active_proposals: 0,
              low_stock_items: 0,
              active_workflows: 0,
              pending_action_intents: 0,
              active_kanban_boards: 0,
              total_kanban_cards: 0,
              open_kanban_cards: 0,
              overdue_kanban_cards: 0,
              unassigned_kanban_cards: 0,
              high_priority_kanban_cards: 0,
              recently_updated_kanban_cards: 0,
              due_today_kanban_cards: 0,
              critical_kanban_cards: 0,
              boards_with_pending: {},
              kanban_cards_by_priority: { LOW: 0, MEDIUM: 0, HIGH: 0, URGENT: 0 }
            }} 
            modules={modules} 
            currentUser={user}
            onOpenSearch={() => setCommandOpen(true)}
            onNavigate={navigateToModule} 
          />
        );
      case 'kanban':
        return <KanbanPage currentUser={user} onNavigate={navigateToModule} />;
      case 'proposals':
        return <ProposalsPage onBack={() => navigateToModule('dashboard')} />;
      case 'purchases':
        return <PurchasesPage currentUser={user} onBack={() => navigateToModule('dashboard')} onNavigate={navigateToModule} />;
      case 'it':
        return <ITPage currentUser={user} />;
      case 'chat':
        return <ChatPage currentUser={user} onBack={() => navigateToModule('dashboard')} />;
      case 'files':
        return <FilesKnowledgePage onBack={() => navigateToModule('dashboard')} />;
      case 'stock':
        return <StockPage currentUser={user} onBack={() => navigateToModule('dashboard')} onNavigate={navigateToModule} />;
      case 'approvals':
        return <ApprovalsPage backendOnline={apiStatus === 'online'} currentUser={user} />;
      case 'automations':
        return <AutomationsPage currentUser={user} onBack={() => navigateToModule('dashboard')} />;
      case 'admin':
        return <AdminPage currentUser={user} onNavigate={navigateToModule} />;
      case 'notifications':
        return <NotificationsPage onNavigate={navigateToModule} />;
      case 'legacy-import':
        return <LegacyImportPage currentUser={user} onBack={() => navigateToModule('dashboard')} />;
      default:
        return <DashboardPage metrics={metrics} modules={modules} currentUser={user} onOpenSearch={() => setCommandOpen(true)} onNavigate={navigateToModule} />;
    }
  };

  return (
    <Layout
      activeModule={activeModule}
      onNavigate={navigateToModule}
      backendOnline={apiStatus === 'online'}
      modules={modules}
      user={user}
      onLogout={handleLogout}
      onOpenSearch={() => setCommandOpen(true)}
      theme={theme}
      onToggleTheme={() => setTheme(prev => prev === 'light' ? 'dark' : 'light')}
    >
      <React.Suspense fallback={<ModuleLoadingFallback />}>
        {renderPage()}
      </React.Suspense>
      <CommandPalette
        open={commandOpen}
        onClose={() => setCommandOpen(false)}
        onNavigate={navigateToModule}
        onOpenBoard={(boardId) => {
          localStorage.setItem('vesper.kanban.openBoardId', String(boardId));
          navigateToModule('kanban');
        }}
      />
    </Layout>
  );
};

const ModuleLoadingFallback: React.FC = () => (
  <div style={moduleLoadingStyles.container} role="status" aria-live="polite">
    <div style={moduleLoadingStyles.spinner} />
    <span style={moduleLoadingStyles.text}>Carregando módulo...</span>
  </div>
);

const moduleLoadingStyles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '360px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '14px',
    color: 'var(--text-secondary)',
  },
  spinner: {
    width: '28px',
    height: '28px',
    border: '3px solid var(--border-color)',
    borderTopColor: 'var(--color-primary)',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  text: {
    fontSize: '14px',
    fontWeight: 700,
  },
};

const splashStyles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    width: '100vw',
    backgroundColor: '#0a0b10',
    fontFamily: 'Inter, system-ui, sans-serif',
    color: '#ffffff',
    gap: '24px',
  },
  logoContainer: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
    padding: '12px 24px',
    borderRadius: '12px',
    boxShadow: '0 8px 24px rgba(29, 78, 216, 0.25)',
  },
  logoText: {
    color: '#ffffff',
    fontWeight: 'bold',
    fontSize: '28px',
  },
  logoSubtext: {
    color: '#93c5fd',
    fontWeight: '600',
    fontSize: '16px',
    letterSpacing: '2px',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '50%',
    borderTopColor: '#3b82f6',
    animation: 'spin 1s linear infinite',
  },
  loadingText: {
    color: '#9ca3af',
    fontSize: '14px',
    letterSpacing: '0.5px',
  }
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
  icon: {
    width: '40px',
    height: '40px',
    color: '#ef4444',
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
    margin: '0 0 8px 0',
    lineHeight: '1.6',
  },
  submessage: {
    fontSize: '13px',
    color: '#9ca3af',
    margin: '0 0 28px 0',
  },
  button: {
    backgroundColor: '#3b82f6',
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

export default App;
