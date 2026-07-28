import React from 'react';
import { ArrowRight } from 'lucide-react';

export type ModuleCardState = 'complete' | 'partial' | 'soon';

interface ModuleCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  badge: string;
  actionLabel: string;
  state: ModuleCardState;
  moduleCode: string;
  disabled?: boolean;
  onClick?: () => void;
}

export const ModuleCard: React.FC<ModuleCardProps> = ({
  icon,
  title,
  description,
  badge,
  actionLabel,
  state,
  moduleCode,
  disabled = false,
  onClick,
}) => (
  <button
    type="button"
    className={`module-card module-card-${state} module-card-${moduleCode}`}
    aria-disabled={disabled}
    onClick={(e) => {
      if (disabled) {
        e.preventDefault();
        e.stopPropagation();
        return;
      }
      onClick && onClick();
    }}
    aria-label={`${title} — ${badge}`}
  >
    <div className="module-card-header">
      <span className={`module-card-icon ${moduleCode}`}>{icon}</span>
      <span className={`module-card-badge ${state}`} aria-live="polite">{badge}</span>
    </div>
    <div className="module-card-copy">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
    <span className="module-card-action">
      {actionLabel}
      {!disabled && <ArrowRight size={14} />}
    </span>
  </button>
);

export default ModuleCard;
