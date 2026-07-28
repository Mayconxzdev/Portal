import React from 'react';

export interface PriorityBadgeProps {
  priority: string;
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority }) => {
  const normalized = priority.toUpperCase();
  let variant = 'low';
  let label = priority;

  switch (normalized) {
    case 'LOW':
    case 'BAIXA':
      variant = 'low';
      label = 'Baixa';
      break;
    case 'MEDIUM':
    case 'MEDIO':
    case 'MÉDIA':
    case 'MEDIA':
      variant = 'medium';
      label = 'Média';
      break;
    case 'HIGH':
    case 'ALTA':
      variant = 'high';
      label = 'Alta';
      break;
    case 'CRITICA':
    case 'CRÍTICA':
      variant = 'urgent';
      label = 'Crítica';
      break;
    case 'URGENT':
    case 'URGENTE':
      variant = 'urgent';
      label = 'Urgente';
      break;
    default:
      variant = 'neutral';
      label = priority;
  }

  return <span className={`priority-badge priority-${variant}`}>{label}</span>;
};
