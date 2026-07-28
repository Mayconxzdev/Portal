import React, { useEffect, useRef, useState } from 'react';
import { Archive, Bell, Check, ExternalLink, Inbox, Loader2 } from 'lucide-react';
import { Tooltip } from '../ui/Tooltip';
import { NotificationNavigate, resolveNotificationDestination } from './notificationDestinations';

export interface PortalNotification {
  id: string;
  user_id?: number | null;
  role_target?: string | null;
  module: string;
  event_type: string;
  title: string;
  message: string;
  severity: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR' | 'CRITICAL';
  status: 'UNREAD' | 'READ' | 'ARCHIVED';
  source_type?: string | null;
  source_id?: string | null;
  action_url?: string | null;
  created_at: string;
  read_at?: string | null;
  archived_at?: string | null;
}

interface NotificationBellProps {
  backendOnline: boolean;
  onNavigate: NotificationNavigate;
}

const moduleLabels: Record<string, string> = {
  automations: 'Automacoes',
  approvals: 'Aprovacoes',
  kanban: 'Kanban',
  it: 'TI',
  chat: 'Chat',
  files: 'Arquivos',
  purchases: 'Compras',
  proposals: 'Propostas',
  stock: 'Estoque',
  admin: 'Administracao',
};

const severityLabels: Record<string, string> = {
  INFO: 'Informacao',
  SUCCESS: 'Sucesso',
  WARNING: 'Atencao',
  ERROR: 'Erro',
  CRITICAL: 'Critico',
};

const formatRelativeTime = (value: string) => {
  const createdAt = new Date(value).getTime();
  if (Number.isNaN(createdAt)) return 'Agora';
  const diffMs = Date.now() - createdAt;
  const diffMinutes = Math.max(0, Math.floor(diffMs / 60000));
  if (diffMinutes < 1) return 'Agora';
  if (diffMinutes < 60) return `${diffMinutes} min`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} h`;
  return new Date(value).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
};

export const NotificationBell: React.FC<NotificationBellProps> = ({ backendOnline, onNavigate }) => {
  const [notifications, setNotifications] = useState<PortalNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  const loadUnreadCount = async () => {
    if (!backendOnline) return;
    try {
      const response = await fetch('/api/v1/notifications/unread-count');
      if (!response.ok) {
        setError('Nao foi possivel atualizar o contador de notificacoes.');
        return;
      }
      const data = await response.json();
      setUnreadCount(typeof data?.count === 'number' ? data.count : 0);
    } catch {
      setError('Falha ao atualizar o contador de notificacoes.');
    }
  };

  const loadNotifications = async () => {
    if (!backendOnline) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/v1/notifications?limit=20');
      if (!response.ok) {
        setError('Nao foi possivel carregar notificacoes.');
        return;
      }
      const data = await response.json();
      const items = Array.isArray(data?.items) ? data.items : [];
      setNotifications(items);
    } catch {
      setError('Servidor indisponivel para notificacoes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUnreadCount();
    if (open) {
      loadNotifications();
    }
  }, [backendOnline]);

  useEffect(() => {
    if (!backendOnline || typeof WebSocket === 'undefined') return;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const socket = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws/events`);
    let pingInterval: number | undefined;

    socket.onopen = () => {
      pingInterval = window.setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) socket.send('ping');
      }, 25000);
    };

    socket.onmessage = (event) => {
      try {
        if (event.data === 'pong') return;
        const message = JSON.parse(event.data);
        if (message.type !== 'notification' || !message.data) return;
        setNotifications((current) => {
          const incoming = message.data as PortalNotification;
          const withoutDuplicate = current.filter((item) => item.id !== incoming.id);
          const next = [incoming, ...withoutDuplicate].slice(0, 20);
          return next;
        });
        loadUnreadCount();
      } catch {
        // Mantem fallback via API.
      }
    };

    socket.onclose = () => {
      if (pingInterval) window.clearInterval(pingInterval);
    };

    return () => {
      if (pingInterval) window.clearInterval(pingInterval);
      socket.close();
    };
  }, [backendOnline]);

  useEffect(() => {
    if (!backendOnline) return;
    const interval = window.setInterval(loadUnreadCount, 60000);
    const handleFocus = () => loadUnreadCount();
    window.addEventListener('focus', handleFocus);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener('focus', handleFocus);
    };
  }, [backendOnline]);

  useEffect(() => {
    if (!open) return;
    const handlePointer = (event: MouseEvent) => {
      if (!panelRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handlePointer);
    return () => document.removeEventListener('mousedown', handlePointer);
  }, [open]);

  const markRead = async (notificationId: string) => {
    setUpdating(true);
    setError(null);
    setNotifications((current) =>
      current.map((notification) =>
        notification.id === notificationId
          ? { ...notification, status: 'READ', read_at: new Date().toISOString() }
          : notification,
      ),
    );
    setUnreadCount((current) => Math.max(0, current - 1));
    try {
      const response = await fetch(`/api/v1/notifications/${notificationId}/read`, { method: 'POST' });
      if (!response.ok) {
        setError('Nao foi possivel marcar a notificacao como lida.');
        await loadNotifications();
        await loadUnreadCount();
      } else {
        await loadUnreadCount();
      }
    } catch {
      setError('Falha ao marcar notificacao como lida.');
      await loadNotifications();
      await loadUnreadCount();
    } finally {
      setUpdating(false);
    }
  };

  const markAllRead = async () => {
    setUpdating(true);
    setError(null);
    setNotifications((current) =>
      current.map((notification) => ({
        ...notification,
        status: 'READ',
        read_at: notification.read_at || new Date().toISOString(),
      })),
    );
    setUnreadCount(0);
    try {
      const response = await fetch('/api/v1/notifications/read-all', { method: 'POST' });
      if (!response.ok) {
        setError('Nao foi possivel marcar todas as notificacoes como lidas.');
        await loadNotifications();
        await loadUnreadCount();
      } else {
        await loadUnreadCount();
      }
    } catch {
      setError('Falha ao marcar todas as notificacoes como lidas.');
      await loadNotifications();
      await loadUnreadCount();
    } finally {
      setUpdating(false);
    }
  };

  const openDestination = async (notification: PortalNotification) => {
    if (notification.status === 'UNREAD') {
      await markRead(notification.id);
    }
    const destination = resolveNotificationDestination(notification);
    if (destination) {
      onNavigate(destination.moduleCode, destination.search ? { search: destination.search } : undefined);
      if (destination.warning) {
        setError(destination.warning);
      }
      setOpen(false);
      loadUnreadCount();
      return;
    }
    setError('Nao foi possivel abrir o destino desta notificacao. Abra pela Central de Notificacoes.');
  };

  return (
    <div className="notification-bell" ref={panelRef}>
      <Tooltip text="Notificacoes do portal">
        <button
          type="button"
          className={`topbar-notify-btn ${open ? 'is-active' : ''}`}
          aria-label={`Notificacoes${unreadCount ? `, ${unreadCount} nao lidas` : ''}`}
          aria-expanded={open}
          onClick={() => {
            setOpen((current) => !current);
            if (!open) {
              loadNotifications();
              loadUnreadCount();
            }
          }}
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className="topbar-notify-count" aria-hidden={true}>
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </button>
      </Tooltip>

      {open && (
        <section className="notification-panel" aria-label="Lista de notificacoes">
          <div className="notification-panel__header">
            <div>
              <strong>Notificacoes</strong>
              <span>{unreadCount > 0 ? `${unreadCount} nao lidas` : 'Tudo lido'}</span>
            </div>
            <button
              type="button"
              className="notification-panel__link"
              onClick={markAllRead}
              disabled={unreadCount === 0 || updating}
            >
              Marcar todas como lidas
            </button>
            <button
              type="button"
              className="notification-panel__link"
              onClick={() => {
                setOpen(false);
                onNavigate('notifications');
              }}
            >
              Central
            </button>
          </div>

          <div className="notification-panel__body">
            {loading || updating ? (
              <div className="notification-empty">
                <Loader2 size={18} className="spin-anim" />
                <span>{loading ? 'Carregando notificacoes...' : 'Atualizando notificacoes...'}</span>
              </div>
            ) : error ? (
              <div className="notification-empty is-error">
                <Inbox size={18} />
                <span>{error}</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="notification-empty">
                <Inbox size={18} />
                <span>Sem notificacoes reais no momento.</span>
              </div>
            ) : (
              notifications.map((notification) => (
                <article
                  key={notification.id}
                  className={`notification-item notification-item--${notification.severity.toLowerCase()} ${
                    notification.status === 'UNREAD' ? 'is-unread' : ''
                  }`}
                >
                  <button
                    type="button"
                    className="notification-item__main"
                    onClick={() => openDestination(notification)}
                  >
                    <span className="notification-item__meta">
                      {moduleLabels[notification.module] || notification.module}
                      <span aria-hidden={true}>.</span>
                      {severityLabels[notification.severity] || notification.severity}
                      <span aria-hidden={true}>.</span>
                      {formatRelativeTime(notification.created_at)}
                    </span>
                    <strong>{notification.title}</strong>
                    <span>{notification.message}</span>
                  </button>
                  <div className="notification-item__actions">
                    {notification.action_url && (
                      <button
                        type="button"
                        aria-label="Abrir destino"
                        onClick={() => openDestination(notification)}
                      >
                        <ExternalLink size={14} />
                      </button>
                    )}
                    {notification.status === 'UNREAD' && (
                      <button
                        type="button"
                        aria-label="Marcar como lida"
                        onClick={() => markRead(notification.id)}
                      >
                        <Check size={14} />
                      </button>
                    )}
                    {notification.status !== 'ARCHIVED' && (
                      <button
                        type="button"
                        aria-label="Arquivar notificacao"
                        onClick={async () => {
                          setUpdating(true);
                          setNotifications((current) => current.filter((item) => item.id !== notification.id));
                          try {
                            await fetch(`/api/v1/notifications/${notification.id}/archive`, { method: 'POST' });
                            await loadUnreadCount();
                          } catch {
                            setError('Nao foi possivel arquivar a notificacao.');
                            await loadNotifications();
                          } finally {
                            setUpdating(false);
                          }
                        }}
                      >
                        <Archive size={14} />
                      </button>
                    )}
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
      )}
    </div>
  );
};

export default NotificationBell;
