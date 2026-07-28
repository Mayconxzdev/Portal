import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { Button } from './Button';

export interface SuccessStateProps {
  title?: string;
  message: string;
  actionText?: string;
  onAction?: () => void;
  compact?: boolean;
}

/**
 * Estado de sucesso usado para confirmar operações concluídas.
 * Diferente de EmptyState (que indica ausência de dados) e ErrorState (que indica falha).
 * - Anunciado por leitores de tela via `role="status"` + `aria-live="polite"`.
 * - Quando `compact`, é adequado para uso inline (ex: rodapé de modal).
 */
export const SuccessState: React.FC<SuccessStateProps> = ({
  title = 'Sucesso',
  message,
  actionText,
  onAction,
  compact = false,
}) => {
  return (
    <div
      className={
        compact
          ? 'success-state-container success-state-compact'
          : 'success-state-container'
      }
      role="status"
      aria-live="polite"
    >
      <div className="success-state-icon" aria-hidden={true}>
        <CheckCircle2 />
      </div>
      <h3 className="success-state-title">{title}</h3>
      <p className="success-state-message">{message}</p>
      {actionText && onAction && (
        <Button
          variant="primary"
          onClick={onAction}
          className="success-state-action"
        >
          {actionText}
        </Button>
      )}
    </div>
  );
};
