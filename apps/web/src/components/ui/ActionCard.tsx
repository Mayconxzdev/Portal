import React from 'react';
import { ArrowRight } from 'lucide-react';

interface ActionCardProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  badge?: string;
  actionLabel?: string;
  disabled?: boolean;
  tone?: 'violet' | 'cyan' | 'emerald' | 'amber' | 'rose' | 'slate';
  onClick?: () => void;
}

export const ActionCard: React.FC<ActionCardProps> = ({
  icon,
  title,
  description,
  badge,
  actionLabel = 'Abrir',
  disabled = false,
  tone = 'violet',
  onClick,
}) => (
  <button
    type="button"
    className={`action-card action-card-${tone}`}
    onClick={onClick}
    disabled={disabled}
  >
    <div className="action-card-top">
      {icon && <span className="action-card-icon">{icon}</span>}
      {badge && <span className="action-card-badge">{badge}</span>}
    </div>
    <div className="action-card-body">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
    <span className="action-card-link">
      {disabled ? 'Em breve' : actionLabel}
      {!disabled && <ArrowRight size={14} />}
    </span>
  </button>
);

export default ActionCard;
