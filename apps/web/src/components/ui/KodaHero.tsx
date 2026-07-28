import React from 'react';
import KodaMascot, { KodaVariant } from './KodaMascot';

interface KodaHeroProps {
  title: string;
  description: string;
  variant?: KodaVariant;
  size?: 'md' | 'lg' | 'hero';
  className?: string;
  actions?: React.ReactNode;
}

export const KodaHero: React.FC<KodaHeroProps> = ({
  title,
  description,
  variant = 'hello',
  size = 'lg',
  className = '',
  actions,
}) => {
  return (
    <div className={`relative overflow-hidden glass-panel rounded-3xl p-6 md:p-8 flex flex-col md:flex-row items-center justify-between gap-6 border border-slate-700/40 bg-slate-900/40 shadow-xl ${className}`}>
      {/* Glow effect in background */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-violet-600/10 rounded-full blur-3xl -z-10 pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 w-60 h-60 bg-sky-600/10 rounded-full blur-3xl -z-10 pointer-events-none"></div>

      <div className="flex-1 space-y-4 text-center md:text-left z-10">
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
          {title}
        </h1>
        <p className="text-sm md:text-base text-slate-300 max-w-xl leading-relaxed">
          {description}
        </p>
        {actions && <div className="flex flex-wrap gap-3 pt-2 justify-center md:justify-start">{actions}</div>}
      </div>

      <div className="flex-shrink-0 flex items-center justify-center z-10">
        <KodaMascot variant={variant} size={size === 'hero' ? 'hero' : size} withGlow />
      </div>
    </div>
  );
};

export default KodaHero;
