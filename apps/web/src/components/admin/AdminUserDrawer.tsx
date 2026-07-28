import React, { useEffect, useState } from 'react';
import { Drawer } from '../ui/Drawer';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { ErrorSummary } from '../ui/ErrorSummary';
import { normalizeApiError } from '../../lib/apiErrors';
import { UserItem, RoleItem, ModuleItem, AdminSessionItem, AdminTemporaryAccessItem, AdminTemporarySubstitutionItem, AdminOffboardingImpact, AdminOffboardingCase, AuditLogItem } from './types';
import { AdminUserSummaryTab } from './AdminUserSummaryTab';
import { AdminUserAccessTab } from './AdminUserAccessTab';
import { AdminUserSecurityTab } from './AdminUserSecurityTab';
import { AdminUserSessionsTab } from './AdminUserSessionsTab';
import { AdminUserHistoryTab } from './AdminUserHistoryTab';
import { AdminTemporaryAccessPanel } from './AdminTemporaryAccessPanel';
import { AdminOffboardingWorkspace } from './AdminOffboardingWorkspace';

interface AdminUserDrawerProps {
  drawerUser: UserItem | null;
  onClose: () => void;
  drawerTab: 'summary' | 'access' | 'security' | 'sessions' | 'history' | 'role-change' | 'temporary-access' | 'offboarding';
  setDrawerTab: (tab: any) => void;
  formError: any;
  contextError?: string | null;
  loading: boolean;
  onSave: (e?: React.SyntheticEvent) => void;
  
  // Tab props
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
  humanizeRole: (role: string | null) => string;

  editablePermissionModules: ModuleItem[];
  formPermissions: Record<number, string>;
  setFormPermissions: (val: Record<number, string>) => void;
  permissionLabels: Record<string, string>;

  formPassword: string;
  setFormPassword: (val: string) => void;
  formPasswordConfirm: string;
  setFormPasswordConfirm: (val: string) => void;
  setTemporaryPassword: () => void;
  formMustChangePassword: boolean;
  setFormMustChangePassword: (val: boolean) => void;
  formIsActive: boolean;
  setFormIsActive: (val: boolean) => void;

  adminSessions: AdminSessionItem[];
  lifecycleLoading: boolean;
  onRevokeSession: (sessionId: number) => void;

  filteredLogs: AuditLogItem[];
  formatHumanAuditLog: (log: AuditLogItem) => string;

  users: UserItem[];
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
  onCreateTemporaryAccess: () => void;
  onRevokeTemporaryAccess: (accessId: number) => void;
  onCreateTemporarySubstitution: () => void;

  offboardingImpact: AdminOffboardingImpact | null;
  offboardingCase: AdminOffboardingCase | null;
  offboardingReason: string;
  setOffboardingReason: (val: string) => void;
  offboardingReplacementId: number | '';
  setOffboardingReplacementId: (val: number | '') => void;
  onRecalculateImpact: () => void;
  onCreateOffboardingCase: () => void;
  onConfirmOffboardingCase: () => void;
  onCompleteTask: (taskId: number) => void;
  onFailTask: (taskId: number) => void;
  onCancelCase: (caseId: number) => void;
}

export const AdminUserDrawer: React.FC<AdminUserDrawerProps> = ({
  drawerUser,
  onClose,
  drawerTab,
  setDrawerTab,
  formError,
  contextError,
  loading,
  onSave,

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
  humanizeRole,

  editablePermissionModules,
  formPermissions,
  setFormPermissions,
  permissionLabels,

  formPassword,
  setFormPassword,
  formPasswordConfirm,
  setFormPasswordConfirm,
  setTemporaryPassword,
  formMustChangePassword,
  setFormMustChangePassword,
  formIsActive,
  setFormIsActive,

  adminSessions,
  lifecycleLoading,
  onRevokeSession,

  filteredLogs,
  formatHumanAuditLog,

  users,
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
  onCreateTemporaryAccess,
  onRevokeTemporaryAccess,
  onCreateTemporarySubstitution,

  offboardingImpact,
  offboardingCase,
  offboardingReason,
  setOffboardingReason,
  offboardingReplacementId,
  setOffboardingReplacementId,
  onRecalculateImpact,
  onCreateOffboardingCase,
  onConfirmOffboardingCase,
  onCompleteTask,
  onFailTask,
  onCancelCase,
}) => {
  const [showCloseReview, setShowCloseReview] = useState(false);
  const [baseline, setBaseline] = useState<{
    fullName: string;
    username: string;
    email: string;
    department: string;
    jobTitle: string;
    roleId: number;
    isActive: boolean;
    mustChangePassword: boolean;
    permissions: Record<number, string>;
  } | null>(null);

  useEffect(() => {
    if (!drawerUser) {
      setBaseline(null);
      setShowCloseReview(false);
      return;
    }
    const permissions: Record<number, string> = {};
    drawerUser.module_permissions.forEach((permission) => {
      permissions[permission.module_id] = permission.permission_level;
    });
    setBaseline({
      fullName: drawerUser.full_name || '',
      username: drawerUser.username,
      email: drawerUser.email || '',
      department: drawerUser.department || '',
      jobTitle: drawerUser.job_title || '',
      roleId: drawerUser.role_id || 2,
      isActive: drawerUser.is_active,
      mustChangePassword: Boolean(drawerUser.must_change_password),
      permissions,
    });
    setShowCloseReview(false);
  }, [drawerUser]);

  if (!drawerUser) return null;

  const originalPermissions = baseline?.permissions || {};

  const hasPermissionChanges = Object.keys({ ...originalPermissions, ...formPermissions }).some(
    (moduleId) => (originalPermissions[Number(moduleId)] || 'NO_ACCESS') !== (formPermissions[Number(moduleId)] || 'NO_ACCESS'),
  );

  const hasProfileChanges = baseline ? (
    formFullName !== baseline.fullName ||
    formUsername !== baseline.username ||
    formEmail !== baseline.email ||
    formDepartment !== baseline.department ||
    formJobTitle !== baseline.jobTitle ||
    formRoleId !== baseline.roleId ||
    formIsActive !== baseline.isActive ||
    formMustChangePassword !== baseline.mustChangePassword ||
    Boolean(formPassword.trim()) ||
    Boolean(formPasswordConfirm.trim())
  ) : false;

  const hasChanges = hasProfileChanges || hasPermissionChanges;
  const showFooter = ['summary', 'access', 'security'].includes(drawerTab) && hasChanges;
  const initials = (drawerUser.full_name || drawerUser.username)
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('');

  const requestClose = () => {
    if (hasChanges) {
      setShowCloseReview(true);
      return;
    }
    onClose();
  };

  const discardAndClose = () => {
    setShowCloseReview(false);
    onClose();
  };

  return (
    <Drawer
      open={Boolean(drawerUser)}
      title={drawerUser.full_name || drawerUser.username}
      description={`${drawerUser.username} · ${humanizeRole(drawerUser.role_name)}`}
      onClose={requestClose}
      className="admin-user-drawer"
      headerContent={
        <div className="admin-drawer-identity">
          <span className="admin-user-avatar admin-user-avatar--large">{initials}</span>
          <div>
            <h2>{drawerUser.full_name || drawerUser.username}</h2>
            <p>{drawerUser.username}</p>
            <div className="admin-drawer-identity-meta">
              <Badge variant={drawerUser.is_active ? 'success' : 'neutral'}>
                {drawerUser.is_active ? 'Ativo' : 'Inativo'}
              </Badge>
              <span>{humanizeRole(drawerUser.role_name)}</span>
              {(drawerUser.department || drawerUser.job_title) && (
                <span>{[drawerUser.department, drawerUser.job_title].filter(Boolean).join(' · ')}</span>
              )}
            </div>
          </div>
        </div>
      }
      footer={
        showFooter ? (
          <div className="admin-drawer-footer">
            <Button variant="secondary" onClick={requestClose}>
              Cancelar
            </Button>
            <Button variant="ghost" onClick={() => setDrawerTab('access')}>
              Revisar alterações
            </Button>
            <Button variant="primary" onClick={onSave} disabled={loading}>
              {loading ? 'Salvando...' : 'Salvar alterações'}
            </Button>
          </div>
        ) : undefined
      }
    >
      {showCloseReview && (
        <div className="admin-unsaved-review" role="alert">
          <strong>Existem alterações não salvas.</strong>
          <span>Salve antes de fechar ou descarte as mudanças desta edição.</span>
          <div>
            <Button size="sm" variant="primary" onClick={onSave} disabled={loading}>
              Salvar
            </Button>
            <Button size="sm" variant="secondary" onClick={discardAndClose}>
              Descartar
            </Button>
          </div>
        </div>
      )}

      {formError && <ErrorSummary error={formError} title="Revise os dados deste usuário" />}
      {!formError && contextError && <ErrorSummary error={normalizeApiError(contextError)} title="Não foi possível concluir a ação" />}

      <div
        className="admin-drawer-tabs"
        role="tablist"
        aria-label="Áreas do usuário"
      >
        {[
          { key: 'summary', label: 'Resumo' },
          { key: 'access', label: 'Acessos' },
          { key: 'security', label: 'Segurança' },
          { key: 'sessions', label: 'Sessões' },
          { key: 'temporary-access', label: 'Acessos temporários' },
          { key: 'offboarding', label: 'Desligamento' },
          { key: 'history', label: 'Histórico' },
        ].map((tab) => {
          const isActive = drawerTab === tab.key;
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={isActive ? 'active' : ''}
              onClick={() => setDrawerTab(tab.key)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {drawerTab === 'summary' && (
        <AdminUserSummaryTab
          formFullName={formFullName}
          setFormFullName={setFormFullName}
          formUsername={formUsername}
          setFormUsername={setFormUsername}
          formEmail={formEmail}
          setFormEmail={setFormEmail}
          formDepartment={formDepartment}
          setFormDepartment={setFormDepartment}
          formJobTitle={formJobTitle}
          setFormJobTitle={setFormJobTitle}
          formRoleId={formRoleId}
          setFormRoleId={setFormRoleId}
          roles={roles}
          currentUser={currentUser}
          setDrawerTab={setDrawerTab}
          humanizeRole={humanizeRole}
          drawerUser={drawerUser}
          permissionLabels={permissionLabels}
        />
      )}

      {drawerTab === 'access' && (
        <AdminUserAccessTab
          editablePermissionModules={editablePermissionModules}
          formPermissions={formPermissions}
          setFormPermissions={setFormPermissions}
          drawerUser={drawerUser}
          permissionLabels={permissionLabels}
        />
      )}

      {drawerTab === 'security' && (
        <AdminUserSecurityTab
          formPassword={formPassword}
          setFormPassword={setFormPassword}
          formPasswordConfirm={formPasswordConfirm}
          setFormPasswordConfirm={setFormPasswordConfirm}
          setTemporaryPassword={setTemporaryPassword}
          formMustChangePassword={formMustChangePassword}
          setFormMustChangePassword={setFormMustChangePassword}
          formIsActive={formIsActive}
          setFormIsActive={setFormIsActive}
          passwordError={formError?.fieldErrors?.password}
          passwordConfirmError={formError?.fieldErrors?.password_confirm}
          loading={loading}
          onSavePassword={onSave}
        />
      )}

      {drawerTab === 'sessions' && (
        <AdminUserSessionsTab
          adminSessions={adminSessions}
          lifecycleLoading={lifecycleLoading}
          onRevokeSession={onRevokeSession}
        />
      )}

      {drawerTab === 'history' && (
        <AdminUserHistoryTab
          filteredLogs={filteredLogs}
          userId={drawerUser.id}
          formatHumanAuditLog={formatHumanAuditLog}
        />
      )}

      {drawerTab === 'temporary-access' && (
        <AdminTemporaryAccessPanel
          users={users}
          drawerUser={drawerUser}
          editablePermissionModules={editablePermissionModules}
          temporaryAccessModuleId={temporaryAccessModuleId}
          setTemporaryAccessModuleId={setTemporaryAccessModuleId}
          temporaryAccessLevel={temporaryAccessLevel}
          setTemporaryAccessLevel={setTemporaryAccessLevel}
          temporaryAccessReason={temporaryAccessReason}
          setTemporaryAccessReason={setTemporaryAccessReason}
          temporaryAccessExpiresAt={temporaryAccessExpiresAt}
          setTemporaryAccessExpiresAt={setTemporaryAccessExpiresAt}
          temporarySubstituteUserId={temporarySubstituteUserId}
          setTemporarySubstituteUserId={setTemporarySubstituteUserId}
          temporarySubstitutionReason={temporarySubstitutionReason}
          setTemporarySubstitutionReason={setTemporarySubstitutionReason}
          temporarySubstitutionExpiresAt={temporarySubstitutionExpiresAt}
          setTemporarySubstitutionExpiresAt={setTemporarySubstitutionExpiresAt}
          temporaryAccesses={temporaryAccesses}
          temporarySubstitutions={temporarySubstitutions}
          lifecycleLoading={lifecycleLoading}
          onCreateTemporaryAccess={onCreateTemporaryAccess}
          onRevokeTemporaryAccess={onRevokeTemporaryAccess}
          onCreateTemporarySubstitution={onCreateTemporarySubstitution}
          permissionLabels={permissionLabels}
        />
      )}

      {drawerTab === 'offboarding' && (
        <AdminOffboardingWorkspace
          users={users}
          drawerUser={drawerUser}
          offboardingImpact={offboardingImpact}
          offboardingCase={offboardingCase}
          offboardingReason={offboardingReason}
          setOffboardingReason={setOffboardingReason}
          offboardingReplacementId={offboardingReplacementId}
          setOffboardingReplacementId={setOffboardingReplacementId}
          lifecycleLoading={lifecycleLoading}
          onRecalculateImpact={onRecalculateImpact}
          onCreateOffboardingCase={onCreateOffboardingCase}
          onConfirmOffboardingCase={onConfirmOffboardingCase}
          onCompleteTask={onCompleteTask}
          onFailTask={onFailTask}
          onCancelCase={onCancelCase}
        />
      )}
    </Drawer>
  );
};
