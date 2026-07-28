import React from 'react';
import { Select } from '../ui/Select';
import { ModuleItem, UserItem } from './types';

interface AdminUserAccessTabProps {
  editablePermissionModules: ModuleItem[];
  formPermissions: Record<number, string>;
  setFormPermissions: (val: Record<number, string>) => void;
  drawerUser: UserItem;
  permissionLabels: Record<string, string>;
}

export const AdminUserAccessTab: React.FC<AdminUserAccessTabProps> = ({
  editablePermissionModules,
  formPermissions,
  setFormPermissions,
  drawerUser,
  permissionLabels,
}) => {
  const changes = editablePermissionModules.reduce(
    (acc, module) => {
      const originalPerm = drawerUser.module_permissions.find((p) => p.module_id === module.id)?.permission_level || 'NO_ACCESS';
      const currentPerm = formPermissions[module.id] || 'NO_ACCESS';
      if (originalPerm === currentPerm) return acc;
      if (originalPerm === 'NO_ACCESS') acc.added += 1;
      else if (currentPerm === 'NO_ACCESS') acc.removed += 1;
      else acc.changed += 1;
      if (['MANAGER', 'ADMIN'].includes(currentPerm)) acc.critical += 1;
      return acc;
    },
    { added: 0, removed: 0, changed: 0, critical: 0 },
  );

  return (
    <div className="admin-drawer-section">
      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Acessos por módulo</h3>
          <p>Permissões permanentes ficam salvas no perfil desta pessoa. Acessos temporários têm aba própria.</p>
        </div>
        <div className="admin-impact-strip" aria-label="Resumo das alterações de acesso">
          <span>{changes.added} adicionados</span>
          <span>{changes.removed} removidos</span>
          <span>{changes.changed} alterados</span>
          <span className={changes.critical ? 'is-critical' : ''}>{changes.critical} críticos</span>
        </div>
      </section>

      <div className="admin-access-card-list">
        {editablePermissionModules.map((module) => {
          const originalPerm = drawerUser.module_permissions.find((p) => p.module_id === module.id)?.permission_level || 'NO_ACCESS';
          const currentPerm = formPermissions[module.id] || 'NO_ACCESS';
          const isChanged = originalPerm !== currentPerm;
          const isCritical = ['MANAGER', 'ADMIN'].includes(currentPerm);

          return (
            <article key={module.id} className={`admin-access-card ${isChanged ? 'is-changed' : ''} ${isCritical ? 'is-critical' : ''}`}>
              <div className="admin-access-card-head">
                <div>
                  <strong>{module.name}</strong>
                  <span>{module.is_restricted ? 'Módulo restrito' : 'Módulo operacional'}</span>
                </div>
                <div className="admin-access-badges">
                  <span>{isChanged ? 'Exceção personalizada' : 'Herdado do perfil'}</span>
                  {isCritical && <span className="is-critical">Acesso crítico</span>}
                  {currentPerm === 'NO_ACCESS' && <span>Sem acesso</span>}
                </div>
              </div>
              <Select
                value={currentPerm}
                onChange={(e) =>
                  setFormPermissions({ ...formPermissions, [module.id]: e.target.value })
                }
                style={{ marginBottom: 0 }}
                options={[
                  { value: 'NO_ACCESS', label: 'Sem acesso' },
                  { value: 'READ_ONLY', label: 'Pode visualizar' },
                  { value: 'NORMAL', label: 'Pode criar e editar' },
                  { value: 'MANAGER', label: 'Pode gerir e aprovar' },
                  { value: 'ADMIN', label: 'Pode administrar' },
                ]}
              />
              <small>Antes: {permissionLabels[originalPerm] || 'Sem acesso'}</small>
            </article>
          );
        })}
      </div>
    </div>
  );
};
