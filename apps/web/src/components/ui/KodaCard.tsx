import React from 'react';
import { KodaMascot } from './KodaMascot';
import { Button } from './Button';

interface KodaCardProps {
  title?: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  compact?: boolean;
  className?: string;
}

export const KodaCard: React.FC<KodaCardProps> = ({
  title = 'Koda recomenda',
  description,
  actionLabel,
  onAction,
  compact = false,
  className = '',
}) => (
  <section className={`koda-card ${compact ? 'koda-card-compact' : ''} ${className}`}>
    <KodaMascot size={compact ? 'sm' : 'md'} />
    <div className="koda-card-content">
      <span className="koda-card-eyebrow">Portal Vesper</span>
      <h3>{title}</h3>
      <p>{description}</p>
      {actionLabel && onAction && (
        <Button size="sm" variant="secondary" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  </section>
);

export default KodaCard;
