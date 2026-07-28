import React from 'react';
import KodaMascot, { KodaVariant } from './KodaMascot';

interface KodaHelpCardProps {
  title?: string;
  description: string;
  variant?: KodaVariant;
  className?: string;
}

export const KodaHelpCard: React.FC<KodaHelpCardProps> = ({
  title = 'Dica do Koda',
  description,
  variant = 'guide',
  className = '',
}) => {
  return (
    <div className={`glass-card p-4 rounded-2xl border border-slate-700/30 bg-slate-900/30 flex items-start gap-4 ${className}`}>
      <div className="flex-shrink-0 pt-0.5">
        <KodaMascot variant={variant} size="sm" />
      </div>
      <div className="space-y-1">
        <h4 className="text-sm font-semibold text-sky-400">{title}</h4>
        <p className="text-xs text-slate-300 leading-relaxed">{description}</p>
      </div>
    </div>
  );
};

export default KodaHelpCard;
