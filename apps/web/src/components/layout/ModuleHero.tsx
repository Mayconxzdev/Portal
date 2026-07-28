import React from 'react';
import { KodaMascot } from '../ui/KodaMascot';

export interface ModuleHeroProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  eyebrow?: string;
  actions?: React.ReactNode;
  kodaMessage?: string;
  showKoda?: boolean;
  accent?: 'violet' | 'sky' | 'emerald' | 'amber' | 'rose' | 'cyan' | 'slate';
}

export const ModuleHero: React.FC<ModuleHeroProps> = ({
  icon,
  title,
  description,
  eyebrow,
  actions,
  kodaMessage,
  showKoda = true,
  accent = 'violet',
}) => (
  <section className={`module-hero module-hero--${accent}`}>
    <div className="module-hero-main">
      {eyebrow && <span className="page-eyebrow">{eyebrow}</span>}
      <div className="module-hero-title-row">
        <div className="module-hero-icon" aria-hidden={true}>
          {icon}
        </div>
        <div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
      </div>
      {actions && <div className="hero-actions">{actions}</div>}
    </div>
    {showKoda && (
      <div className="module-hero-koda">
        <KodaMascot size="md" mood="hello" />
        {kodaMessage && <p className="module-hero-koda-message">{kodaMessage}</p>}
      </div>
    )}
  </section>
);

export default ModuleHero;
