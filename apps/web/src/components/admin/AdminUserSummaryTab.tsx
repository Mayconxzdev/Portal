import React from 'react';
import { Clock, ShieldAlert } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { UserItem, RoleItem } from './types';

interface AdminUserSummaryTabProps {
  formFullName: string;
  setFormFullName: (val: string) => void;
  formUsername: string;
  setFormUsername: (val: string) => void;
  formEmail: string;
  setFormEmail: (val: string) => void;
  formDepartment: string;
  setFormDepartment: (val: string) => void;
  formJobTitle: string;
  setFormJobTitle: (val: string) => void;
  formRoleId: number;
  setFormRoleId: (val: number) => void;
  roles: RoleItem[];
  currentUser: any;
  setDrawerTab: (tab: any) => void;
  humanizeRole: (role: string | null) => string;
  drawerUser: UserItem;
  permissionLabels: Record<string, string>;
}

export const AdminUserSummaryTab: React.FC<AdminUserSummaryTabProps> = ({
  formFullName,
  setFormFullName,
  formUsername,
  setFormUsername,
  formEmail,
  setFormEmail,
  formDepartment,
  setFormDepartment,
  formJobTitle,
  setFormJobTitle,
  formRoleId,
  setFormRoleId,
  roles,
  currentUser,
  setDrawerTab,
  humanizeRole,
  drawerUser,
  permissionLabels,
}) => {
  const visibleAccesses = drawerUser.module_permissions
    .filter((permission) => permission.module_code !== 'chat')
    .slice(0, 6);
  const changedUsername = formUsername.trim() !== drawerUser.username;

  return (
    <div className="admin-drawer-section">
      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Informacoes pessoais</h3>
          <p>Dados usados para login, auditoria e sugestao de acessos.</p>
        </div>

        <dl className="admin-summary-grid">
          <div>
            <dt>Nome</dt>
            <dd>{drawerUser.full_name || drawerUser.username}</dd>
          </div>
          <div>
            <dt>Usuario</dt>
            <dd>{drawerUser.username}</dd>
          </div>
          <div>
            <dt>E-mail</dt>
            <dd>{drawerUser.email || 'Nao informado'}</dd>
          </div>
          <div>
            <dt>Perfil</dt>
            <dd>{humanizeRole(drawerUser.role_name)}</dd>
          </div>
          <div>
            <dt>Funcao ou setor</dt>
            <dd>{drawerUser.department || 'Nao informado'}</dd>
          </div>
          <div>
            <dt>Ultima atividade</dt>
            <dd>{drawerUser.last_login ? new Date(drawerUser.last_login).toLocaleString('pt-BR') : 'Sem login registrado'}</dd>
          </div>
        </dl>
      </section>

      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Editar dados</h3>
          <p>Salve no rodape do drawer depois de revisar o impacto.</p>
        </div>
        <div className="admin-two-columns">
          <Input name="admin-user-full-name" autoComplete="off" label="Nome completo" value={formFullName} onChange={(e) => setFormFullName(e.target.value)} />
          <Input name="admin-user-login-name" autoComplete="off" label="Nome de usuario" value={formUsername} onChange={(e) => setFormUsername(e.target.value.trim())} />
        </div>
        {changedUsername && (
          <div className="admin-warning-box">
            Alterar o nome de usuario pode afetar o login e integracoes que dependam deste identificador.
          </div>
        )}
        <Input name="admin-user-email" autoComplete="off" label="E-mail opcional" type="email" value={formEmail} onChange={(e) => setFormEmail(e.target.value.trim())} />
        <div className="admin-two-columns">
          <Input name="admin-user-department" autoComplete="off" label="Funcao ou setor" value={formDepartment} onChange={(e) => setFormDepartment(e.target.value)} />
          <Input name="admin-user-job-title" autoComplete="off" label="Cargo opcional" value={formJobTitle} onChange={(e) => setFormJobTitle(e.target.value)} />
        </div>
        <Select
          label="Perfil principal"
          value={formRoleId}
          onChange={(e) => setFormRoleId(parseInt(e.target.value))}
          options={roles
            .filter((role) => currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS' || role.name !== 'MESSIAS')
            .map((role) => ({ value: role.id, label: `${humanizeRole(role.name)} - ${role.description || 'Sem descricao'}` }))}
        />
      </section>

      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Resumo de acessos</h3>
          <p>Visao rapida dos principais modulos liberados para esta pessoa.</p>
        </div>
        <div className="admin-access-summary-list">
          {visibleAccesses.length === 0 ? (
            <span className="admin-empty-state admin-empty-state--compact">Sem acessos de modulo alem do Chat global.</span>
          ) : (
            visibleAccesses.map((permission) => (
              <div key={permission.module_id}>
                <strong>{permission.module_name}</strong>
                <span>{permissionLabels[permission.permission_level] || 'Pode acessar'}</span>
              </div>
            ))
          )}
        </div>
      </section>

      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Acoes rapidas</h3>
          <p>Use quando a alteracao faz parte do ciclo de vida da pessoa.</p>
        </div>
        <div className="admin-drawer-actions">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setDrawerTab('temporary-access')}
            leftIcon={<Clock size={14} />}
          >
            Acesso temporario
          </Button>
          <Button
            type="button"
            variant="danger"
            size="sm"
            onClick={() => setDrawerTab('offboarding')}
            leftIcon={<ShieldAlert size={14} />}
          >
            Iniciar desligamento
          </Button>
        </div>
      </section>
    </div>
  );
};
