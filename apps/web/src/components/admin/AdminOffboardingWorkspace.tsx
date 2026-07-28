import React, { useState } from 'react';
import { ShieldAlert, RefreshCw, CheckCircle2, XCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { UserItem, AdminOffboardingImpact, AdminOffboardingCase } from './types';

interface AdminOffboardingWorkspaceProps {
  users: UserItem[];
  drawerUser: UserItem;
  offboardingImpact: AdminOffboardingImpact | null;
  offboardingCase: AdminOffboardingCase | null;
  offboardingReason: string;
  setOffboardingReason: (val: string) => void;
  offboardingReplacementId: number | '';
  setOffboardingReplacementId: (val: number | '') => void;
  lifecycleLoading: boolean;
  onRecalculateImpact: () => void;
  onCreateOffboardingCase: () => void;
  onConfirmOffboardingCase: () => void;
  onCompleteTask: (taskId: number) => void;
  onFailTask: (taskId: number) => void;
  onCancelCase: (caseId: number) => void;
}

export const AdminOffboardingWorkspace: React.FC<AdminOffboardingWorkspaceProps> = ({
  users,
  drawerUser,
  offboardingImpact,
  offboardingCase,
  offboardingReason,
  setOffboardingReason,
  offboardingReplacementId,
  setOffboardingReplacementId,
  lifecycleLoading,
  onRecalculateImpact,
  onCreateOffboardingCase,
  onConfirmOffboardingCase,
  onCompleteTask,
  onFailTask,
  onCancelCase,
}) => {
  const [typedConfirmation, setTypedConfirmation] = useState('');

  const isConfirmed = offboardingCase?.status === 'CONFIRMED';
  const isCancelled = offboardingCase?.status === 'CANCELLED';

  const isConfirmationAllowed =
    typedConfirmation.trim().toLowerCase() === drawerUser.username.trim().toLowerCase();
  const visibleImpactItems = offboardingImpact?.items?.filter((item) => item.count > 0) || [];
  const statusLabel: Record<string, string> = {
    DRAFT: 'Em preparação',
    CONFIRMED: 'Confirmado',
    CANCELLED: 'Cancelado',
  };

  return (
    <div className="admin-drawer-section">
      <section className="admin-drawer-card">
        <div className="admin-drawer-section-title">
          <h3>Desligamento seguro</h3>
          <p>Bloqueie login, encerre sessões e redistribua responsabilidades de forma auditada.</p>
        </div>
        <div className="admin-offboarding-steps" aria-label="Fluxo de desligamento">
          <span>Impacto</span>
          <span>Transferências</span>
          <span>Segurança</span>
          <span>Revisão</span>
        </div>
      </section>

      {offboardingImpact && (
        <section className="admin-drawer-card">
          <div className="admin-drawer-section-title">
            <h3>Impacto detectado</h3>
            <p>Responsabilidades e acessos que precisam de atenção antes do bloqueio.</p>
          </div>
          <div className="admin-impact-list">
            {visibleImpactItems.map((item) => (
                <article
                  key={item.key}
                  className={item.can_auto_apply ? 'can-auto-apply' : 'needs-review'}
                >
                  <strong>
                    {item.label}: {item.count}
                  </strong>
                  <span>{item.action}</span>
                  <small>
                    {item.can_auto_apply
                      ? 'Pode ser resolvido automaticamente no bloqueio'
                      : 'Requer ação e confirmação manual'}
                  </small>
                </article>
            ))}
            {visibleImpactItems.length === 0 && (
              <div className="admin-empty-state admin-empty-state--compact">
                Nenhum vínculo ou responsabilidade ativa detectada. O bloqueio será limpo.
              </div>
            )}
          </div>
        </section>
      )}

      {!offboardingCase && (
        <section className="admin-drawer-card">
          <div className="admin-drawer-section-title">
            <h3>Preparar desligamento</h3>
            <p>Defina substituto, motivo e recalcule o impacto antes de criar o caso.</p>
          </div>
          <Select
            label="Redistribuir responsabilidades automáticas para"
            value={offboardingReplacementId}
            onChange={(e) => setOffboardingReplacementId(e.target.value ? Number(e.target.value) : '')}
            options={[
              { value: '', label: 'Sem substituto automático' },
              ...(users || [])
                .filter((u) => u.id !== drawerUser.id && u.is_active)
                .map((u) => ({ value: u.id, label: u.full_name || u.username })),
            ]}
          />
          <Input
            label="Justificativa do desligamento"
            value={offboardingReason}
            onChange={(e) => setOffboardingReason(e.target.value)}
            placeholder="Ex: Encerramento de contrato de prestação de serviço"
          />
          <div className="admin-drawer-actions">
            <Button
              type="button"
              variant="secondary"
              onClick={onRecalculateImpact}
              disabled={lifecycleLoading}
              leftIcon={<RefreshCw size={14} />}
            >
              Recalcular
            </Button>
            <Button
              type="button"
              variant="primary"
              onClick={onCreateOffboardingCase}
              disabled={lifecycleLoading}
            >
              Criar Caso de Desligamento
            </Button>
          </div>
        </section>
      )}

      {offboardingCase && (
        <section className="admin-drawer-card">
          <div className="admin-offboarding-case-head">
            <div>
              <strong>Processo de desligamento registrado</strong>
              <span>Status: {statusLabel[offboardingCase.status] || offboardingCase.status}</span>
            </div>
            {!isConfirmed && !isCancelled && (
              <Button type="button" variant="ghost" size="sm" onClick={() => onCancelCase(offboardingCase.id)}>
                Cancelar caso
              </Button>
            )}
          </div>

          <div className="admin-task-list">
            <strong>Fila de pendências geradas</strong>
            {(offboardingCase.tasks || []).map((task) => {
              const isTaskCompleted = task.status === 'COMPLETED';
              const isTaskFailed = task.status === 'FAILED';

              return (
                <article
                  key={task.id}
                  className={`admin-task-card ${isTaskCompleted ? 'is-complete' : ''} ${isTaskFailed ? 'is-failed' : ''}`}
                >
                  <div>
                    <strong>{task.title}</strong>
                    <span>{task.description}</span>
                    <small>
                      Status: {task.status === 'COMPLETED' ? 'Concluída' : task.status === 'FAILED' ? 'Falhou' : 'Pendente'}
                    </small>
                  </div>
                  {!isConfirmed && !isCancelled && (
                    <div className="admin-task-actions">
                      <Button
                        type="button"
                        variant="success"
                        size="sm"
                        onClick={() => onCompleteTask(task.id)}
                        disabled={isTaskCompleted}
                        title="Marcar como resolvida"
                      >
                        <CheckCircle2 size={14} />
                      </Button>
                      <Button
                        type="button"
                        variant="danger"
                        size="sm"
                        onClick={() => onFailTask(task.id)}
                        disabled={isTaskFailed}
                        title="Sinalizar impedimento/falha"
                      >
                        <XCircle size={14} />
                      </Button>
                    </div>
                  )}
                </article>
              );
            })}
            {(offboardingCase.tasks || []).length === 0 && (
              <div className="admin-empty-state admin-empty-state--compact">Nenhuma tarefa pendente para este desligamento.</div>
            )}
          </div>

          {!isConfirmed && !isCancelled && (
            <div className="admin-confirm-block">
              <div className="admin-warning-box admin-warning-box--danger">
                <strong>Ação de alto impacto:</strong> ao confirmar, o login será bloqueado e sessões/acessos temporários ativos serão encerrados.
              </div>

              <Input
                label={`Confirme digitando o login do usuário ("${drawerUser.username}")`}
                value={typedConfirmation}
                onChange={(e) => setTypedConfirmation(e.target.value)}
                placeholder={drawerUser.username}
              />

              <Button
                type="button"
                variant="danger"
                onClick={onConfirmOffboardingCase}
                disabled={lifecycleLoading || !isConfirmationAllowed}
                leftIcon={<ShieldAlert size={14} />}
              >
                Bloquear e Confirmar Desligamento
              </Button>
            </div>
          )}
        </section>
      )}
    </div>
  );
};
