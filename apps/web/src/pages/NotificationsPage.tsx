import React, { useEffect, useMemo, useState } from 'react';
import { Archive, Bell, Check, ExternalLink, Inbox, Loader2, RotateCcw } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { resolveNotificationDestination, NotificationNavigate } from '../components/notifications/notificationDestinations';
import { PortalNotification } from '../components/notifications/NotificationBell';

interface NotificationsPageProps {
  onNavigate: NotificationNavigate;
}

const statusLabels: Record<string, string> = {
  all: 'Todas',
  UNREAD: 'Nao lidas',
  READ: 'Lidas',
  ARCHIVED: 'Arquivadas',
};

const moduleLabels: Record<string, string> = {
  approvals: 'Aprovacoes',
  purchases: 'Compras',
  stock: 'Estoque',
  admin: 'Administracao',
  automations: 'Automacoes',
  kanban: 'Kanban',
  it: 'TI',
  chat: 'Chat',
  proposals: 'Propostas',
  files: 'Knowledge',
};

const formatDateTime = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Agora';
  return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
};

export const NotificationsPage: React.FC<NotificationsPageProps> = ({ onNavigate }) => {
  const [items, setItems] = useState<PortalNotification[]>([]);
  const [statusFilter, setStatusFilter] = useState<'all' | 'UNREAD' | 'READ' | 'ARCHIVED'>('all');
  const [loading, setLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const endpoint = useMemo(() => {
    const params = new URLSearchParams({ limit: '80' });
    if (statusFilter !== 'all') params.set('status', statusFilter);
    return `/api/v1/notifications?${params.toString()}`;
  }, [statusFilter]);

  const loadNotifications = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(endpoint);
      if (!response.ok) throw new Error('Nao foi possivel carregar notificacoes.');
      const payload = await response.json();
      setItems(Array.isArray(payload?.items) ? payload.items : []);
    } catch (err: any) {
      setError(err.message || 'Falha ao carregar notificacoes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, [endpoint]);

  const mutate = async (notification: PortalNotification, action: 'read' | 'unread' | 'archive') => {
    setUpdatingId(notification.id);
    setError(null);
    const nextStatus = action === 'archive' ? 'ARCHIVED' : action === 'read' ? 'READ' : 'UNREAD';
    setItems((current) =>
      current.map((item) =>
        item.id === notification.id
          ? {
              ...item,
              status: nextStatus,
              read_at: nextStatus === 'READ' || nextStatus === 'ARCHIVED' ? item.read_at || new Date().toISOString() : null,
              archived_at: nextStatus === 'ARCHIVED' ? new Date().toISOString() : null,
            }
          : item,
      ),
    );
    try {
      const response = await fetch(`/api/v1/notifications/${notification.id}/${action}`, { method: 'POST' });
      if (!response.ok) throw new Error('Nao foi possivel atualizar esta notificacao.');
      await loadNotifications();
    } catch (err: any) {
      setError(err.message || 'Falha ao atualizar notificacao.');
      await loadNotifications();
    } finally {
      setUpdatingId(null);
    }
  };

  const markAllRead = async () => {
    setError(null);
    try {
      const response = await fetch('/api/v1/notifications/read-all', { method: 'POST' });
      if (!response.ok) throw new Error('Nao foi possivel marcar todas como lidas.');
      await loadNotifications();
    } catch (err: any) {
      setError(err.message || 'Falha ao marcar todas como lidas.');
    }
  };

  const openDestination = async (notification: PortalNotification) => {
    if (notification.status === 'UNREAD') {
      await mutate(notification, 'read');
    }
    const destination = resolveNotificationDestination(notification);
    if (!destination) {
      setError('Esta notificacao nao possui destino seguro para abrir.');
      return;
    }
    if (destination.warning) setError(destination.warning);
    onNavigate(destination.moduleCode, destination.search ? { search: destination.search } : undefined);
  };

  return (
    <section className="notifications-page">
      <header className="notifications-page__header">
        <div>
          <span className="notifications-page__eyebrow">Central</span>
          <h1>Notificacoes</h1>
          <p>Acompanhe avisos importantes e abra rapidamente o que precisa da sua atencao.</p>
        </div>
        <div className="notifications-page__actions">
          <Button variant="secondary" size="sm" leftIcon={<RotateCcw size={15} />} onClick={loadNotifications} disabled={loading}>
            Atualizar
          </Button>
          <Button variant="primary" size="sm" leftIcon={<Check size={15} />} onClick={markAllRead}>
            Marcar todas como lidas
          </Button>
        </div>
      </header>

      <div className="notifications-page__filters" role="tablist" aria-label="Filtro de notificacoes">
        {Object.keys(statusLabels).map((status) => (
          <button
            key={status}
            type="button"
            className={statusFilter === status ? 'is-active' : ''}
            onClick={() => setStatusFilter(status as typeof statusFilter)}
          >
            {statusLabels[status]}
          </button>
        ))}
      </div>

      {error && <div className="notifications-page__error">{error}</div>}

      <div className="notifications-page__list">
        {loading ? (
          <div className="notifications-page__empty">
            <Loader2 size={20} className="spin-anim" />
            <span>Carregando notificacoes...</span>
          </div>
        ) : items.length === 0 ? (
          <div className="notifications-page__empty">
            <Inbox size={20} />
            <span>Nenhuma notificacao encontrada neste filtro.</span>
          </div>
        ) : (
          items.map((notification) => (
            <article key={notification.id} className={`notifications-page__item ${notification.status === 'UNREAD' ? 'is-unread' : ''}`}>
              <div className="notifications-page__icon">
                <Bell size={18} />
              </div>
              <button type="button" className="notifications-page__content" onClick={() => openDestination(notification)}>
                <span>
                  {moduleLabels[notification.module] || notification.module} · {formatDateTime(notification.created_at)}
                </span>
                <strong>{notification.title}</strong>
                <p>{notification.message}</p>
              </button>
              <div className="notifications-page__row-actions">
                {notification.action_url && (
                  <button type="button" aria-label="Abrir destino" onClick={() => openDestination(notification)}>
                    <ExternalLink size={15} />
                  </button>
                )}
                {notification.status === 'UNREAD' ? (
                  <button type="button" aria-label="Marcar como lida" disabled={updatingId === notification.id} onClick={() => mutate(notification, 'read')}>
                    <Check size={15} />
                  </button>
                ) : notification.status !== 'ARCHIVED' ? (
                  <button type="button" aria-label="Marcar como nao lida" disabled={updatingId === notification.id} onClick={() => mutate(notification, 'unread')}>
                    <RotateCcw size={15} />
                  </button>
                ) : null}
                {notification.status !== 'ARCHIVED' && (
                  <button type="button" aria-label="Arquivar" disabled={updatingId === notification.id} onClick={() => mutate(notification, 'archive')}>
                    <Archive size={15} />
                  </button>
                )}
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
};

export default NotificationsPage;
