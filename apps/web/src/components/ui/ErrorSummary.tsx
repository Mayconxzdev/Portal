import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import type { ApiErrorState } from '../../lib/apiErrors';

interface ErrorSummaryProps {
  error: ApiErrorState | string | null | undefined;
  title?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorSummary: React.FC<ErrorSummaryProps> = ({
  error,
  title = 'Revise antes de continuar',
  onRetry,
  className = '',
}) => {
  if (!error) return null;

  const message = typeof error === 'string' ? error : error.message;
  const fieldMessages = typeof error === 'string' ? [] : Object.values(error.fieldErrors || {});
  const requestId = typeof error === 'string' ? undefined : error.requestId;

  return (
    <div className={`error-summary ${className}`} role="alert" aria-live="assertive">
      <div className="error-summary__icon">
        <AlertCircle size={18} />
      </div>
      <div className="error-summary__content">
        <strong>{title}</strong>
        <p>{message}</p>
        {fieldMessages.length > 0 && (
          <ul>
            {Array.from(new Set(fieldMessages)).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
        {requestId && <small>Codigo de suporte: {requestId}</small>}
      </div>
      {onRetry && (
        <Button type="button" variant="secondary" size="sm" onClick={onRetry} leftIcon={<RefreshCw size={14} />}>
          Tentar novamente
        </Button>
      )}
    </div>
  );
};

export default ErrorSummary;
