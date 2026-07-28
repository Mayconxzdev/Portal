import React from 'react';
import { AuditLogItem } from './types';

interface AdminUserHistoryTabProps {
  filteredLogs: AuditLogItem[];
  userId: number;
  formatHumanAuditLog: (log: AuditLogItem) => string;
}

export const AdminUserHistoryTab: React.FC<AdminUserHistoryTabProps> = ({
  filteredLogs,
  userId,
  formatHumanAuditLog,
}) => {
  const userLogs = filteredLogs.filter(
    (log) =>
      log.user_id === userId ||
      (log.details &&
        (log.details.updated_user_id === userId ||
          log.details.target_user_id === userId ||
          log.details.created_user_id === userId))
  );

  return (
    <div className="admin-drawer-section">
      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Histórico</h3>
          <p>Eventos de auditoria que envolvem permissões e ciclo de vida deste usuário.</p>
        </div>
      </section>

      <div className="admin-history-timeline">
        {userLogs.slice(0, 15).map((log) => (
          <article
            key={log.id}
          >
            <span className="admin-history-dot" aria-hidden="true" />
            <div className="admin-history-card">
              <strong>{formatHumanAuditLog(log)}</strong>
              <span>{new Date(log.created_at).toLocaleString('pt-BR')}</span>
              {log.ip_address && (
                <details>
                  <summary>Detalhes técnicos</summary>
                  <span>Origem: {log.ip_address}</span>
                </details>
              )}
            </div>
          </article>
        ))}

        {userLogs.length === 0 && (
          <div className="admin-empty-state">
            Nenhum evento registrado especificamente para este usuário.
          </div>
        )}
      </div>
    </div>
  );
};
