import React from 'react';
import { Clock, ArrowRightLeft, XCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { ModuleItem, UserItem, AdminTemporaryAccessItem, AdminTemporarySubstitutionItem } from './types';

interface AdminTemporaryAccessPanelProps {
  users: UserItem[];
  drawerUser: UserItem;
  editablePermissionModules: ModuleItem[];
  temporaryAccessModuleId: number | '';
  setTemporaryAccessModuleId: (val: number) => void;
  temporaryAccessLevel: string;
  setTemporaryAccessLevel: (val: string) => void;
  temporaryAccessReason: string;
  setTemporaryAccessReason: (val: string) => void;
  temporaryAccessExpiresAt: string;
  setTemporaryAccessExpiresAt: (val: string) => void;
  temporarySubstituteUserId: number | '';
  setTemporarySubstituteUserId: (val: number) => void;
  temporarySubstitutionReason: string;
  setTemporarySubstitutionReason: (val: string) => void;
  temporarySubstitutionExpiresAt: string;
  setTemporarySubstitutionExpiresAt: (val: string) => void;
  temporaryAccesses: AdminTemporaryAccessItem[];
  temporarySubstitutions: AdminTemporarySubstitutionItem[];
  lifecycleLoading: boolean;
  onCreateTemporaryAccess: () => void;
  onRevokeTemporaryAccess: (accessId: number) => void;
  onCreateTemporarySubstitution: () => void;
  permissionLabels: Record<string, string>;
}

export const AdminTemporaryAccessPanel: React.FC<AdminTemporaryAccessPanelProps> = ({
  users,
  drawerUser,
  editablePermissionModules,
  temporaryAccessModuleId,
  setTemporaryAccessModuleId,
  temporaryAccessLevel,
  setTemporaryAccessLevel,
  temporaryAccessReason,
  setTemporaryAccessReason,
  temporaryAccessExpiresAt,
  setTemporaryAccessExpiresAt,
  temporarySubstituteUserId,
  setTemporarySubstituteUserId,
  temporarySubstitutionReason,
  setTemporarySubstitutionReason,
  temporarySubstitutionExpiresAt,
  setTemporarySubstitutionExpiresAt,
  temporaryAccesses,
  temporarySubstitutions,
  lifecycleLoading,
  onCreateTemporaryAccess,
  onRevokeTemporaryAccess,
  onCreateTemporarySubstitution,
  permissionLabels,
}) => {
  const activeAccesses = temporaryAccesses.filter((access) => access.status === 'ACTIVE' && access.is_effective);
  const scheduledAccesses = temporaryAccesses.filter((access) => access.status === 'ACTIVE' && !access.is_effective);
  const closedAccesses = temporaryAccesses.filter((access) => access.status !== 'ACTIVE');

  return (
    <div className="admin-drawer-section">
      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Acessos temporários</h3>
          <p>Conceda acesso a um módulo específico com validade predefinida. O acesso expira após a data limite.</p>
        </div>

        <div className="admin-two-columns">
          <Select
            label="Módulo"
            value={temporaryAccessModuleId || ''}
            onChange={(e) => setTemporaryAccessModuleId(Number(e.target.value))}
            options={editablePermissionModules.map((m) => ({ value: m.id, label: m.name }))}
          />
          <Select
            label="Nível temporário"
            value={temporaryAccessLevel}
            onChange={(e) => setTemporaryAccessLevel(e.target.value)}
            options={[
              { value: 'READ_ONLY', label: 'Pode visualizar' },
              { value: 'NORMAL', label: 'Pode criar e editar' },
              { value: 'MANAGER', label: 'Pode gerir e aprovar' },
              { value: 'ADMIN', label: 'Pode administrar' },
            ]}
          />
        </div>
        <Input
          label="Válido até"
          type="datetime-local"
          value={temporaryAccessExpiresAt}
          onChange={(e) => setTemporaryAccessExpiresAt(e.target.value)}
        />
        <Input
          label="Justificativa do acesso"
          value={temporaryAccessReason}
          onChange={(e) => setTemporaryAccessReason(e.target.value)}
          placeholder="Ex: Cobertura de tarefas operacionais urgentes"
        />
        <Button
          type="button"
          variant="primary"
          onClick={onCreateTemporaryAccess}
          disabled={lifecycleLoading}
          leftIcon={<Clock size={14} />}
        >
          Criar acesso temporário
        </Button>
      </section>

      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Ativos</h3>
          <p>Acessos em vigor agora para esta pessoa.</p>
        </div>
        <div className="admin-temp-list">
          {activeAccesses.map((access) => (
            <article
              key={access.id}
              className="admin-temp-card is-active"
            >
              <div>
                <strong>{access.module_name}</strong>
                <span>{permissionLabels[access.permission_level] || access.permission_level}</span>
                <small>Até {new Date(access.expires_at).toLocaleString('pt-BR')} · Motivo: {access.reason}</small>
              </div>
              {access.status === 'ACTIVE' && (
                <Button
                  type="button"
                  variant="danger"
                  size="sm"
                  onClick={() => onRevokeTemporaryAccess(access.id)}
                  leftIcon={<XCircle size={12} />}
                >
                  Revogar
                </Button>
              )}
            </article>
          ))}
          {activeAccesses.length === 0 && <div className="admin-empty-state admin-empty-state--compact">Nenhum acesso temporário ativo.</div>}
        </div>
      </section>

      {(scheduledAccesses.length > 0 || closedAccesses.length > 0) && (
        <section className="admin-drawer-card">
          <div className="admin-drawer-section-title">
            <h3>Agendados, expirados ou revogados</h3>
            <p>Histórico de exceções que não estão em vigor agora.</p>
          </div>
          <div className="admin-temp-list">
            {[...scheduledAccesses, ...closedAccesses].map((access) => (
              <article key={access.id} className="admin-temp-card">
                <div>
                  <strong>{access.module_name}</strong>
                  <span>{permissionLabels[access.permission_level] || access.permission_level}</span>
                  <small>
                    {access.status === 'ACTIVE' ? 'Agendado' : 'Revogado ou expirado'} até {new Date(access.expires_at).toLocaleString('pt-BR')} · Motivo: {access.reason}
                  </small>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Substituição temporária</h3>
          <p>Escolha um substituto para responsabilidades durante férias ou afastamento.</p>
        </div>
        <div className="admin-two-columns">
          <Select
            label="Substituto"
            value={temporarySubstituteUserId || ''}
            onChange={(e) => setTemporarySubstituteUserId(Number(e.target.value))}
            options={[
              { value: '', label: 'Selecione um substituto...' },
              ...users
                .filter((u) => u.id !== drawerUser.id && u.is_active)
                .map((u) => ({ value: u.id, label: u.full_name || u.username })),
            ]}
          />
          <Input
            label="Válido até"
            type="datetime-local"
            value={temporarySubstitutionExpiresAt}
            onChange={(e) => setTemporarySubstitutionExpiresAt(e.target.value)}
          />
        </div>
        <Input
          label="Justificativa da substituição"
          value={temporarySubstitutionReason}
          onChange={(e) => setTemporarySubstitutionReason(e.target.value)}
          placeholder="Ex: Férias do titular de Compras"
        />
        <Button
          type="button"
          variant="secondary"
          onClick={onCreateTemporarySubstitution}
          disabled={lifecycleLoading}
          leftIcon={<ArrowRightLeft size={14} />}
        >
          Registrar substituição
        </Button>
      </section>

      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Substituições registradas</h3>
          <p>Períodos ativos ou históricos vinculados a esta pessoa.</p>
        </div>
        <div className="admin-temp-list">
          {temporarySubstitutions.map((sub) => (
            <article
              key={sub.id}
              className={`admin-temp-card ${sub.is_effective ? 'is-active' : ''}`}
            >
              <div>
                <strong>Substituto: {sub.substitute_username}</strong>
                <span>{sub.is_effective ? 'Em vigor' : sub.status === 'ACTIVE' ? 'Agendado' : 'Encerrado'} até {new Date(sub.expires_at).toLocaleString('pt-BR')}</span>
                <small>Motivo: {sub.reason}</small>
              </div>
            </article>
          ))}
          {temporarySubstitutions.length === 0 && (
            <div className="admin-empty-state admin-empty-state--compact">Nenhuma substituição registrada.</div>
          )}
        </div>
      </section>
    </div>
  );
};
