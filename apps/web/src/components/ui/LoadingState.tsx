import React from 'react';

export interface LoadingStateProps {
  text?: string;
  variant?: 'spinner' | 'skeleton';
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  text = 'Carregando...',
  variant = 'spinner',
}) => {
  if (variant === 'skeleton') {
    return (
      <div className="skeleton-loading-container">
        <div className="skeleton-row skeleton-header" />
        <div className="skeleton-row skeleton-text" />
        <div className="skeleton-row skeleton-text" />
        <div className="skeleton-row skeleton-text" />
      </div>
    );
  }

  return (
    <div className="loading-state-container">
      <div className="loading-spinner" />
      {text && <span className="loading-text">{text}</span>}
    </div>
  );
};
