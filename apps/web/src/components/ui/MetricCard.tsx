import React from 'react';
import { Card } from './Card';
import { Tooltip } from './Tooltip';

export interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  iconColor?: 'violet' | 'emerald' | 'amber' | 'rose' | 'cyan';
  tooltipText?: string;
  onClick?: () => void;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  icon,
  iconColor = 'violet',
  tooltipText,
  onClick,
  className = '',
}) => {
  return (
    <Card
      variant={onClick ? 'interactive' : 'glass'}
      className={`metric-card-wrapper ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      <div className="metric-card">
        {icon && (
          <div className={`metric-icon-box ${iconColor}`}>
            {icon}
          </div>
        )}
        <div className="metric-details">
          <div className="metric-value">{value}</div>
          <div className="metric-label-container">
            <span className="metric-label">{label}</span>
            {tooltipText && <Tooltip text={tooltipText} />}
          </div>
        </div>
      </div>
    </Card>
  );
};
