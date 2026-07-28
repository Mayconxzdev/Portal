import React from 'react';
import KodaMascot, { KodaVariant } from './KodaMascot';

interface KodaEmptyStateProps {
  title: string;
  description: string;
  variant?: KodaVariant;
  action?: React.ReactNode;
  className?: string;
}

export const KodaEmptyState: React.FC<KodaEmptyStateProps> = ({
  title,
  description,
  variant = 'guide',
  action,
  className = '',
}) => {
  return (
    <div className={`flex flex-col items-center justify-center text-center p-8 glass-panel rounded-2xl border border-slate-800/40 bg-slate-900/20 max-w-md mx-auto ${className}`}>
      <KodaMascot variant={variant} size="md" className="mb-4" />
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-sm text-slate-400 mb-6 leading-relaxed max-w-sm">{description}</p>
      {action && <div className="z-10 pointer-events-auto">{action}</div>}
    </div>
  );
};

export default KodaEmptyState;
