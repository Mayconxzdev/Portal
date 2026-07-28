import React from 'react';
import { Copy } from 'lucide-react';
import { Button } from '../ui/Button';
import { ModuleItem } from './types';

interface AdminAccessReviewProps {
  formFullName: string;
  formUsername: string;
  selectedProfileLabel: string;
  selectedRoleLabel: string;
  formPermissions: Record<number, string>;
  modules: ModuleItem[];
  formIsActive: boolean;
  formMustChangePassword: boolean;
  formEmail: string;
  generatedPassword: string | null;
  copiedGeneratedPassword: boolean;
  copyGeneratedPassword: () => void;
  permissionLabels: Record<string, string>;
}

export const AdminAccessReview: React.FC<AdminAccessReviewProps> = ({
  formFullName,
  formUsername,
  selectedProfileLabel,
  selectedRoleLabel,
  formPermissions,
  modules,
  formIsActive,
  formMustChangePassword,
  formEmail,
  generatedPassword,
  copiedGeneratedPassword,
  copyGeneratedPassword,
  permissionLabels,
}) => {
  const grantedPermissions = modules.filter(
    (m) => formPermissions[m.id] && formPermissions[m.id] !== 'NO_ACCESS' && m.code !== 'chat'
  );

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 24 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <h3 style={{ margin: '0 0 4px 0', fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
            {formFullName || formUsername}
          </h3>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
            Função sugerida: <strong>{selectedProfileLabel}</strong> ({selectedRoleLabel}).
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>Módulos liberados</strong>
          <ul
            style={{
              margin: 0,
              paddingLeft: 20,
              fontSize: 13,
              color: 'var(--text-muted)',
              display: 'flex',
              flexDirection: 'column',
              gap: 4,
            }}
          >
            {grantedPermissions.map((module) => (
              <li key={module.id}>
                {permissionLabels[formPermissions[module.id]] || 'Pode acessar'}: {module.name}
              </li>
            ))}
            <li>Uso comum do Chat e Koda (padrão)</li>
          </ul>
        </div>

        <div
          style={{
            display: 'flex',
            gap: 12,
            borderTop: '1px solid var(--border-color)',
            paddingTop: 16,
            flexWrap: 'wrap',
          }}
        >
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: '4px 8px',
              borderRadius: 6,
              background: 'rgba(255,255,255,0.03)',
              color: 'var(--text-primary)',
            }}
          >
            Status: {formIsActive ? 'Ativo imediato' : 'Criado inativo'}
          </span>
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: '4px 8px',
              borderRadius: 6,
              background: 'rgba(255,255,255,0.03)',
              color: 'var(--text-primary)',
            }}
          >
            Senha: {formMustChangePassword ? 'Exige alteração no primeiro login' : 'Senha permanente'}
          </span>
          <span
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: '4px 8px',
              borderRadius: 6,
              background: 'rgba(255,255,255,0.03)',
              color: 'var(--text-primary)',
            }}
          >
            Comunicação: {formEmail ? 'E-mail cadastrado' : 'Sem e-mail cadastrado'}
          </span>
        </div>

        {generatedPassword && (
          <div
            style={{
              background: 'var(--primary-color-dim, rgba(124, 58, 237, 0.08))',
              border: '1px dashed var(--primary-color)',
              borderRadius: 8,
              padding: 16,
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              marginTop: 12,
            }}
            role="status"
          >
            <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>Senha temporária gerada</strong>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <code style={{ fontSize: 14, fontFamily: 'monospace', fontWeight: 700, color: 'var(--primary-color)' }}>
                {generatedPassword}
              </code>
              <Button type="button" variant="secondary" size="sm" onClick={copyGeneratedPassword} leftIcon={<Copy size={13} />}>
                {copiedGeneratedPassword ? 'Copiado!' : 'Copiar'}
              </Button>
            </div>
            <small style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Esta senha não poderá ser recuperada ou visualizada novamente depois de concluir o cadastro.
            </small>
          </div>
        )}
      </div>

      <div
        style={{
          background: 'rgba(255,255,255,0.01)',
          border: '1px solid var(--border-color)',
          borderRadius: 12,
          padding: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <h4 style={{ margin: 0, fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>Onboarding de Novo Usuário</h4>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.45 }}>
          Ao clicar em <strong>Criar usuário</strong>, a conta será persistida com os privilégios indicados ao lado.
        </p>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.45 }}>
          Se a pessoa precisar de equipamentos, contas monitoradas adicionais ou acessos a pastas do NAS, as tarefas correspondentes deverão ser solicitadas na aba Segurança / TI após a ativação.
        </p>
      </div>
    </div>
  );
};
