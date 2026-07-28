import React from 'react';
import { Lock } from 'lucide-react';
import { Button } from '../ui/Button';
import { AdminSessionItem } from './types';

interface AdminUserSessionsTabProps {
  adminSessions: AdminSessionItem[];
  lifecycleLoading: boolean;
  onRevokeSession: (sessionId: number) => void;
}

export const AdminUserSessionsTab: React.FC<AdminUserSessionsTabProps> = ({
  adminSessions,
  lifecycleLoading,
  onRevokeSession,
}) => {
  return (
    <div className="admin-drawer-section">
      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Sessões</h3>
          <p>
          Encerre as sessões do usuário para forçar o logout em dispositivos específicos.
          </p>
        </div>
      </section>

      {lifecycleLoading && <div className="admin-empty-state admin-empty-state--compact">Buscando sessões...</div>}

      <div className="admin-session-list">
        {adminSessions.map((session) => (
          <article
            key={session.id}
            className={`admin-session-card ${session.is_active ? 'is-active' : 'is-ended'}`}
          >
            <div className="admin-session-card-main">
              <strong>{session.is_active ? 'Sessão ativa' : 'Sessão encerrada ou expirada'}</strong>
              <dl>
                <div>
                  <dt>Início</dt>
                  <dd>{new Date(session.created_at).toLocaleString('pt-BR')}</dd>
                </div>
                <div>
                  <dt>Última atividade</dt>
                  <dd>{new Date(session.last_activity_at).toLocaleString('pt-BR')}</dd>
                </div>
                <div>
                  <dt>Expiração</dt>
                  <dd>{new Date(session.expires_at).toLocaleString('pt-BR')}</dd>
                </div>
                <div>
                  <dt>Contexto</dt>
                  <dd>{session.ip_address || 'IP não informado'}</dd>
                </div>
              </dl>
              {session.user_agent && <span className="admin-session-agent">{session.user_agent}</span>}
              {session.revocation_reason && (
                <span className="admin-danger-text">
                  Motivo: {session.revocation_reason}
                </span>
              )}
            </div>

            {session.is_active && (
              <Button
                type="button"
                variant="danger"
                size="sm"
                onClick={() => onRevokeSession(session.id)}
                leftIcon={<Lock size={12} />}
              >
                Encerrar
              </Button>
            )}
          </article>
        ))}
        {adminSessions.length === 0 && (
          <div className="admin-empty-state">Nenhuma sessão ativa encontrada.</div>
        )}
      </div>
    </div>
  );
};
