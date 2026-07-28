import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Ocorreu um erro',
  message,
  onRetry,
}) => {
  return (
    <div className="error-state-container">
      <div className="error-state-icon">
        <AlertTriangle />
      </div>
      <h3 className="error-state-title">{title}</h3>
      <p className="error-state-message">{message}</p>
      {onRetry && (
        <Button variant="danger" onClick={onRetry} className="error-state-retry-btn">
          Tentar novamente
        </Button>
      )}
    </div>
  );
};
