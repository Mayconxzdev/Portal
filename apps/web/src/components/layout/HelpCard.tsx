import React from 'react';
import { KodaMascot } from '../ui/KodaMascot';
import { Button } from '../ui/Button';

export interface HelpCardProps {
  title?: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  disabled?: boolean;
}

export const HelpCard: React.FC<HelpCardProps> = ({
  title = 'Precisa de ajuda?',
  description,
  actionLabel,
  onAction,
  disabled = false,
}) => (
  <section className="help-card glass-card">
    <KodaMascot size="sm" />
    <div className="help-card-copy">
      <h4>{title}</h4>
      <p>{description}</p>
      {actionLabel && (
        <Button
          size="sm"
          variant="primary"
          onClick={onAction}
          disabled={disabled || !onAction}
        >
          {actionLabel}
        </Button>
      )}
    </div>
  </section>
);

export default HelpCard;
