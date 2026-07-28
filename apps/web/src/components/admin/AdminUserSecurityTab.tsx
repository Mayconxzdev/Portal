import React, { useState } from 'react';
import { RefreshCw, Eye, EyeOff } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Switch } from '../ui/Switch';

interface AdminUserSecurityTabProps {
  formPassword: string;
  setFormPassword: (val: string) => void;
  formPasswordConfirm: string;
  setFormPasswordConfirm: (val: string) => void;
  setTemporaryPassword: () => void;
  formMustChangePassword: boolean;
  setFormMustChangePassword: (val: boolean) => void;
  formIsActive: boolean;
  setFormIsActive: (val: boolean) => void;
  passwordError?: string;
  passwordConfirmError?: string;
  loading?: boolean;
  onSavePassword: (e?: React.SyntheticEvent) => void;
}

export const AdminUserSecurityTab: React.FC<AdminUserSecurityTabProps> = ({
  formPassword,
  setFormPassword,
  formPasswordConfirm,
  setFormPasswordConfirm,
  setTemporaryPassword,
  formMustChangePassword,
  setFormMustChangePassword,
  formIsActive,
  setFormIsActive,
  passwordError,
  passwordConfirmError,
  loading,
  onSavePassword,
}) => {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="admin-drawer-section">
      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Alterar senha</h3>
          <p>A senha atual nao pode ser visualizada. Defina uma nova senha somente quando for necessario.</p>
        </div>

        <div className="admin-password-reset-grid">
          <Input
            label="Nova senha"
            name="admin-new-password"
            autoComplete="new-password"
            type={showPassword ? 'text' : 'password'}
            value={formPassword}
            onChange={(event) => setFormPassword(event.target.value)}
            placeholder="Digite ou gere uma senha temporaria"
            error={passwordError}
          />
          <Input
            label="Confirmar nova senha"
            name="admin-confirm-new-password"
            autoComplete="new-password"
            type={showPassword ? 'text' : 'password'}
            value={formPasswordConfirm}
            onChange={(event) => setFormPasswordConfirm(event.target.value)}
            placeholder="Repita a nova senha"
            error={passwordConfirmError}
          />
        </div>

        <div className="admin-password-actions">
          <Button type="button" variant="secondary" onClick={setTemporaryPassword} leftIcon={<RefreshCw size={14} />}>
            Gerar senha temporaria
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => setShowPassword(!showPassword)}
            leftIcon={showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
          >
            {showPassword ? 'Ocultar' : 'Mostrar enquanto digito'}
          </Button>
          <Button
            type="button"
            variant="primary"
            onClick={onSavePassword}
            disabled={loading || !formPassword.trim() || !formPasswordConfirm.trim()}
          >
            {loading ? 'Salvando...' : 'Salvar nova senha'}
          </Button>
        </div>

        <div className="admin-muted-box">
          Ao salvar, os campos serao limpos. A auditoria registra a redefinicao sem armazenar senha antiga, senha nova ou hash.
        </div>
      </section>

      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Estado da conta</h3>
          <p>Controle se a pessoa pode entrar no Portal e se precisa trocar a senha.</p>
        </div>
        <div className="admin-switch-stack">
          <Switch
            label="Solicitar troca de senha no primeiro acesso"
            checked={formMustChangePassword}
            onChange={(event) => setFormMustChangePassword(event.target.checked)}
          />
          <Switch
            label="Usuario ativo"
            checked={formIsActive}
            onChange={(event) => setFormIsActive(event.target.checked)}
          />
        </div>
      </section>

      <section className="admin-drawer-card admin-danger-zone">
        <div className="admin-drawer-section-title">
          <h3>Acoes de impacto</h3>
          <p>Revogar sessoes ou desligar a pessoa exige confirmacao no contexto da acao.</p>
        </div>
        <div className="admin-human-list">
          <ul>
            <li>Inativar a conta impede novos logins depois de salvar.</li>
            <li>Revogacao de sessoes fica disponivel na aba Sessoes.</li>
            <li>Desligamento seguro fica disponivel na aba Desligamento.</li>
          </ul>
        </div>
      </section>
    </div>
  );
};
