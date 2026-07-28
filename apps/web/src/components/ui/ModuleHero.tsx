import React from 'react';
import { KodaMascot } from './KodaMascot';

export interface ModuleHeroProps {
  title: string;
  description: string;
  eyebrow?: string;
  kodaMood?: 'hello' | 'help' | 'thinking' | 'alert' | 'success' | 'empty' | 'chat' | 'supervisor';
  kodaText?: string;
  kodaMessage?: string; // Retrocompatibilidade
  actions?: React.ReactNode;
  chips?: React.ReactNode[];
  className?: string;
  icon?: React.ReactNode; // Retrocompatibilidade
  accent?: 'violet' | 'sky' | 'emerald' | 'amber' | 'rose' | 'cyan' | 'slate'; // Retrocompatibilidade
  showKoda?: boolean; // Retrocompatibilidade
  compact?: boolean;
}

export const ModuleHero: React.FC<ModuleHeroProps> = ({
  title,
  description,
  eyebrow = 'Portal Vesper',
  kodaMood = 'hello',
  kodaText,
  kodaMessage,
  actions,
  chips,
  className = '',
  icon,
  accent = 'violet',
  showKoda = true,
  compact = false,
}) => {
  const finalKodaText = kodaText || kodaMessage;
  
  return (
    <div className={`page-hero ${compact ? 'page-hero--compact' : `page-hero--${accent}`} ${className}`}>
      <div className="page-hero-copy">
        <div className="flex flex-wrap items-center gap-2 mb-1">
          {icon && <span className="page-hero-icon" aria-hidden={true}>{icon}</span>}
          <span className="page-eyebrow">{eyebrow}</span>
          {chips && chips.map((chip, idx) => (
            <React.Fragment key={idx}>{chip}</React.Fragment>
          ))}
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
        {actions && <div className="hero-actions">{actions}</div>}
      </div>
      {showKoda && !compact && (
        <div className="hidden md:flex items-center justify-end relative select-none">
          <KodaMascot size={compact ? 'md' : 'lg'} mood={kodaMood} className="transform hover:scale-105 transition-transform duration-300" />
          {finalKodaText && !compact && (
            <div className="absolute right-[160px] top-[20px] bg-slate-950/80 border border-violet-500/20 backdrop-blur-md rounded-xl p-3 max-w-[200px] shadow-xl text-xs text-slate-200 after:content-[''] after:absolute after:top-[20px] after:right-[-6px] after:border-t-[6px] after:border-t-transparent after:border-b-[6px] after:border-b-transparent after:border-l-[6px] after:border-l-slate-950/80">
              {finalKodaText}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ModuleHero;
