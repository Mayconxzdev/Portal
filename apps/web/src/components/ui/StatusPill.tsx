import React from 'react';

export interface StatusPillProps {
  status: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ status }) => {
  const normalized = status.toUpperCase();
  let variant = 'pending';
  let label = status;

  switch (normalized) {
    case 'PENDING':
    case 'PENDENTE':
      variant = 'pending';
      label = 'Pendente';
      break;
    case 'APPROVED':
    case 'APROVADO':
      variant = 'approved';
      label = 'Aprovado';
      break;
    case 'REJECTED':
    case 'REJEITADO':
      variant = 'rejected';
      label = 'Rejeitado';
      break;
    case 'EXPIRED':
    case 'EXPIRADO':
      variant = 'expired';
      label = 'Expirado';
      break;
    case 'CANCELLED':
    case 'CANCELADO':
      variant = 'cancelled';
      label = 'Cancelado';
      break;
    default:
      variant = 'neutral';
      label = status;
  }

  return <span className={`status-pill status-${variant}`}>{label}</span>;
};
