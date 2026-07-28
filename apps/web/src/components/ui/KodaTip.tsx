import React from 'react';
import KodaMascot, { KodaVariant } from './KodaMascot';

interface KodaTipProps {
  message: string;
  variant?: KodaVariant;
  className?: string;
}

export const KodaTip: React.FC<KodaTipProps> = ({
  message,
  variant = 'thinking',
  className = '',
}) => {
  return (
    <div className={`inline-flex items-center gap-2 text-xs text-slate-300 bg-slate-900/60 border border-slate-800/80 px-2.5 py-1 rounded-full ${className}`}>
      <KodaMascot variant={variant} size="xs" />
      <span>{message}</span>
    </div>
  );
};

export default KodaTip;
