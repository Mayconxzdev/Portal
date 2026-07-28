import React from 'react';
import { Select } from '../ui/Select';
import { ModuleItem } from './types';

interface AdminAccessCustomizerProps {
  modules: ModuleItem[];
  formPermissions: Record<number, string>;
  onPermissionChange: (moduleId: number, level: string) => void;
  permissionRisk: (level: string) => string;
}

export const AdminAccessCustomizer: React.FC<AdminAccessCustomizerProps> = ({
  modules,
  formPermissions,
  onPermissionChange,
  permissionRisk,
}) => {
  return (
    <section className="admin-profile-panel admin-access-advanced-panel">
      <div className="admin-profile-panel-title">
        <h4>Ajustes avançados de acesso</h4>
        <p>Revise exceções por módulo. O Chat global não precisa de ajuste comum.</p>
      </div>
      <div className="admin-access-advanced-list">
        {modules.map((module) => {
          const currentLevel = formPermissions[module.id] || 'NO_ACCESS';
          const risk = permissionRisk(currentLevel);

          return (
            <div
              key={module.id}
              className="admin-access-advanced-item"
            >
              <div className="admin-access-advanced-head">
                <strong>{module.name}</strong>
                <span className={`risk-${risk.toLowerCase()}`}>Risco: {risk}</span>
              </div>
              <Select
                value={currentLevel}
                onChange={(e) => onPermissionChange(module.id, e.target.value)}
                style={{ marginBottom: 0 }}
                options={[
                  { value: 'NO_ACCESS', label: 'Sem acesso' },
                  { value: 'READ_ONLY', label: 'Pode visualizar' },
                  { value: 'NORMAL', label: 'Pode criar e editar' },
                  { value: 'MANAGER', label: 'Pode gerir e aprovar' },
                  { value: 'ADMIN', label: 'Pode administrar' },
                ]}
              />
            </div>
          );
        })}
      </div>
    </section>
  );
};
