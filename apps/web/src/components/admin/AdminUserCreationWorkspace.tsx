import React, { useState } from 'react';
import { Eye, EyeOff, RefreshCw } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Switch } from '../ui/Switch';
import { Select } from '../ui/Select';
import { ErrorSummary } from '../ui/ErrorSummary';
import { RoleItem, ModuleItem, AccessProfilePreset } from './types';
import { AdminProfileSelector } from './AdminProfileSelector';
import { AdminAccessCustomizer } from './AdminAccessCustomizer';
import { AdminAccessReview } from './AdminAccessReview';

interface AdminUserCreationWorkspaceProps {
  formFullName: string;
  setFormFullName: (val: string) => void;
  formUsername: string;
  setFormUsername: (val: string) => void;
  formEmail: string;
  setFormEmail: (val: string) => void;
  formPassword: string;
  setFormPassword: (val: string) => void;
  formMustChangePassword: boolean;
  setFormMustChangePassword: (val: boolean) => void;
  formIsActive: boolean;
  setFormIsActive: (val: boolean) => void;
  selectedProfileId: string;
  setSelectedProfileId: (val: string) => void;
  showAdvancedAccess: boolean;
  setShowAdvancedAccess: (val: boolean) => void;
  generatedPassword: string | null;
  copiedGeneratedPassword: boolean;
  formPermissions: Record<number, string>;
  setFormPermissions: (val: Record<number, string>) => void;
  formError: any;
  setFormError: (val: any) => void;
  roles: RoleItem[];
  modules: ModuleItem[];
  currentUser: any;
  loading: boolean;
  onSubmit: (e?: React.SyntheticEvent) => void;
  onCancel: () => void;
  selectProfilePreset: (id: string) => void;
  setTemporaryPassword: () => void;
  copyGeneratedPassword: () => void;
  validateStepOne: () => boolean;
  wizardStep: number;
  setWizardStep: (step: number) => void;
  profiles: AccessProfilePreset[];
  permissionLabels: Record<string, string>;
  permissionRisk: (level: string) => string;
}

export const AdminUserCreationWorkspace: React.FC<AdminUserCreationWorkspaceProps> = ({
  formFullName,
  setFormFullName,
  formUsername,
  setFormUsername,
  formEmail,
  setFormEmail,
  formPassword,
  setFormPassword,
  formMustChangePassword,
  setFormMustChangePassword,
  formIsActive,
  setFormIsActive,
  selectedProfileId,
  generatedPassword,
  copiedGeneratedPassword,
  formPermissions,
  setFormPermissions,
  formError,
  roles,
  modules,
  currentUser,
  loading,
  onSubmit,
  onCancel,
  selectProfilePreset,
  setTemporaryPassword,
  copyGeneratedPassword,
  validateStepOne,
  wizardStep,
  setWizardStep,
  profiles,
  permissionLabels,
  permissionRisk,
}) => {
  const [showPassword, setShowPassword] = useState(false);
  const [confirmCreate, setConfirmCreate] = useState(false);

  const goToNextStep = () => {
    if (wizardStep === 1 && !validateStepOne()) return;
    setWizardStep(wizardStep < 3 ? wizardStep + 1 : wizardStep);
  };

  const goToPreviousStep = () => {
    setWizardStep(wizardStep > 1 ? wizardStep - 1 : wizardStep);
  };

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId) || profiles[0];
  const selectedRole = roles.find((role) => selectedProfile.roleNames.includes(role.name)) || roles.find((role) => role.name === 'USER');
  const selectedRoleLabel = selectedRole ? selectedRole.name : 'USER';
  const steps = [
    { step: 1, label: 'Dados da pessoa', desc: 'Quem é essa pessoa?' },
    { step: 2, label: 'Perfil sugerido', desc: 'Qual acesso faz sentido?' },
    { step: 3, label: 'Revisão', desc: 'Confirme o resultado.' },
  ];
  const helpByStep: Record<number, { title: string; items: string[] }> = {
    1: {
      title: 'Dicas para os dados básicos',
      items: [
        'E-mail é opcional e pode ficar em branco.',
        'O perfil será escolhido na próxima etapa.',
        'A senha inicial pode ser digitada ou gerada automaticamente.',
      ],
    },
    2: {
      title: 'Dicas sobre perfil',
      items: [
        'Escolha o perfil mais próximo da função real.',
        'Exceções avançadas devem ser usadas com justificativa clara.',
        'A revisão final mostra o impacto antes da criação.',
      ],
    },
    3: {
      title: 'Dicas para revisar',
      items: [
        'Confira acessos críticos antes de confirmar.',
        'A senha gerada só aparece neste fluxo.',
        'Depois de criar, a auditoria registra a ação.',
      ],
    },
  };

  const selectedProfileWarnings: string[] = [...(selectedProfile.warnings || [])];
  Object.entries(formPermissions).forEach(([moduleId, level]) => {
    const module = modules.find((m) => m.id === Number(moduleId));
    if (!module || level === 'NO_ACCESS') return;
    if (module.code === 'admin' && ['MANAGER', 'ADMIN'].includes(level)) {
      selectedProfileWarnings.push('Este acesso permite administrar usuários ou configurações do Portal.');
    }
  });

  return (
    <section className="admin-guided-workspace" aria-label="Criar novo usuário">
      <div className="admin-guided-header">
        <div>
          <h2>Criar novo usuário</h2>
          <p>
            Informe os dados da pessoa, o perfil de acessos ideal e faça a revisão antes de persistir.
          </p>
        </div>
        <Button variant="ghost" onClick={onCancel}>
          Cancelar
        </Button>
      </div>

      <div
        className="admin-stepper"
        aria-label="Etapas de criação"
      >
        {steps.map((item) => {
          const isActive = wizardStep === item.step;
          const isDone = wizardStep > item.step;
          const canOpenStep =
            item.step === 1 ||
            (formFullName.trim() !== '' &&
              formUsername.trim() !== '' &&
              formPassword.trim() !== '');
          return (
            <button
              key={item.step}
              type="button"
              className={`admin-step ${isActive ? 'active' : ''} ${isDone ? 'done' : ''}`}
              disabled={!canOpenStep}
              aria-current={isActive ? 'step' : undefined}
              onClick={() => {
                if (item.step === 1 || validateStepOne()) setWizardStep(item.step);
              }}
            >
              <span className="admin-step-number">{item.step}</span>
              <span className="admin-step-copy">
                <small>Etapa {item.step}</small>
                <strong>{item.label}</strong>
                <em>{item.desc}</em>
              </span>
            </button>
          );
        })}
      </div>

      <form
        className="admin-guided-body"
        onSubmit={(e) => {
          e.preventDefault();
          if (wizardStep < 3 || !confirmCreate) {
            setConfirmCreate(false);
            goToNextStep();
            return;
          }
          setConfirmCreate(false);
          onSubmit(e);
        }}
      >
        {formError && <ErrorSummary error={formError} title="Revise este usuário antes de continuar" />}

        {wizardStep === 1 && (
          <div className="admin-guided-grid">
            <div className="admin-guided-fields">
              <div className="admin-two-columns">
                <Input
                  label="Nome completo"
                  value={formFullName}
                  onChange={(e) => setFormFullName(e.target.value)}
                  placeholder="Ex: Mariana Oliveira"
                  error={formError?.fieldErrors?.full_name}
                  required
                />
                <Input
                  label="Nome de usuario"
                  value={formUsername}
                  onChange={(e) => setFormUsername(e.target.value.trim())}
                  placeholder="Ex: mariana.oliveira"
                  error={formError?.fieldErrors?.username}
                  required
                />
              </div>
              <Input
                label="E-mail opcional"
                type="email"
                value={formEmail}
                onChange={(e) => setFormEmail(e.target.value.trim())}
                placeholder="Ex: nome.sobrenome@portal.local"
                error={formError?.fieldErrors?.email}
                helpText="Não impede a criação quando estiver vazio."
              />
              <div className="admin-password-row admin-password-row--wide">
                <div>
                  <Input
                    label="Senha inicial"
                    type={showPassword ? 'text' : 'password'}
                    value={formPassword}
                    onChange={(e) => setFormPassword(e.target.value)}
                    placeholder="Digite ou gere uma senha temporária"
                    error={formError?.fieldErrors?.password}
                    required
                  />
                </div>
                <Button type="button" variant="secondary" onClick={setTemporaryPassword} leftIcon={<RefreshCw size={14} />}>
                  Gerar
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowPassword(!showPassword)}
                  leftIcon={showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                >
                  {showPassword ? 'Ocultar' : 'Mostrar'}
                </Button>
              </div>

              <div className="admin-switch-stack admin-switch-stack--inline">
                <Switch
                  label="Solicitar troca de senha no primeiro acesso"
                  checked={formMustChangePassword}
                  onChange={(e) => setFormMustChangePassword(e.target.checked)}
                />
                <Switch
                  label="Usuário ativo"
                  checked={formIsActive}
                  onChange={(e) => setFormIsActive(e.target.checked)}
                />
              </div>
            </div>

            <aside className="admin-guided-note">
              <h4>{helpByStep[1].title}</h4>
              <ul>
                {helpByStep[1].items.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </aside>
          </div>
        )}

        {wizardStep === 2 && (
          <div className="admin-profile-stage admin-profile-stage--three">
            <AdminProfileSelector
              profiles={profiles}
              selectedProfileId={selectedProfileId}
              onSelectProfile={selectProfilePreset}
              selectedProfileWarnings={selectedProfileWarnings}
              permissionLabels={permissionLabels}
            />

            <AdminAccessCustomizer
              modules={modules.filter((m) => m.code !== 'chat')}
              formPermissions={formPermissions}
              onPermissionChange={(moduleId, level) =>
                setFormPermissions({ ...formPermissions, [moduleId]: level })
              }
              permissionRisk={permissionRisk}
            />
          </div>
        )}

        {wizardStep === 3 && (
          <div className="admin-review-stage">
            <AdminAccessReview
              formFullName={formFullName}
              formUsername={formUsername}
              selectedProfileLabel={selectedProfile.label}
              selectedRoleLabel={selectedRoleLabel}
              formPermissions={formPermissions}
              modules={modules}
              formIsActive={formIsActive}
              formMustChangePassword={formMustChangePassword}
              formEmail={formEmail}
              generatedPassword={generatedPassword}
              copiedGeneratedPassword={copiedGeneratedPassword}
              copyGeneratedPassword={copyGeneratedPassword}
              permissionLabels={permissionLabels}
            />
            <aside className="admin-guided-note">
              <h4>{helpByStep[3].title}</h4>
              <ul>
                {helpByStep[3].items.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </aside>
          </div>
        )}

        <footer className="admin-guided-footer">
          <Button type="button" variant="secondary" onClick={goToPreviousStep} disabled={wizardStep === 1 || loading}>
            Voltar
          </Button>
          {wizardStep < 3 ? (
            <Button type="button" variant="primary" onClick={goToNextStep}>
              Continuar
            </Button>
          ) : (
            <Button type="button" variant="primary" disabled={loading} onClick={onSubmit}>
              {loading ? 'Salvando...' : 'Criar usuário'}
            </Button>
          )}
        </footer>
      </form>
    </section>
  );
};
