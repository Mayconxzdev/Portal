import React from 'react';
import { Badge } from '../ui/Badge';

export type LegacyBatchStatus = 
  | 'DISCOVERED' 
  | 'EXTRACTED' 
  | 'NEEDS_REVIEW' 
  | 'READY_TO_IMPORT' 
  | 'IMPORTED' 
  | 'FAILED' 
  | 'CANCELLED';

export type LegacyRowStatus =
  | 'PENDING_REVIEW'
  | 'ACCEPTED'
  | 'REJECTED'
  | 'DUPLICATE'
  | 'NEEDS_MORE_INFO';

export type LegacyEntityTarget =
  | 'SUPPLIER'
  | 'PRODUCT_ITEM'
  | 'PRICE_HISTORY'
  | 'PRICE_REFERENCE'
  | 'CUSTOMER'
  | 'PROPOSAL'
  | 'OP'
  | 'PROJECT_TASK'
  | 'IT_TICKET'
  | 'IT_ASSET'
  | 'IT_NETWORK_PORT'
  | 'IT_REMOTE_ACCESS'
  | 'NAS_ACCESS'
  | 'EMAIL_ACCOUNT_ACCESS'
  | 'IT_SOFTWARE_CERTIFICATE'
  | 'VOIP_ACCOUNT'
  | 'FILE'
  | 'TEMPLATE'
  | 'CREDENTIAL_METADATA';

interface LegacyImportStatusBadgeProps {
  type: 'batch' | 'row' | 'entity';
  value: string;
}

export const humanizeBatchStatus = (status: string): string => {
  const dict: Record<string, string> = {
    DISCOVERED: 'Descoberto',
    EXTRACTED: 'Extraído',
    NEEDS_REVIEW: 'Precisa revisão',
    READY_TO_IMPORT: 'Pronto para importar',
    IMPORTED: 'Importado',
    FAILED: 'Falhou',
    CANCELLED: 'Cancelado',
  };
  return dict[status] || status;
};

export const humanizeRowStatus = (status: string): string => {
  const dict: Record<string, string> = {
    PENDING_REVIEW: 'Em Revisão',
    ACCEPTED: 'Aceito para importação',
    REJECTED: 'Rejeitado',
    DUPLICATE: 'Duplicado',
    NEEDS_MORE_INFO: 'Mais Informações',
  };
  return dict[status] || status;
};

export const humanizeEntityTarget = (entity: string): string => {
  const dict: Record<string, string> = {
    SUPPLIER: 'Fornecedor',
    PRODUCT_ITEM: 'Item / Produto',
    PRICE_HISTORY: 'Histórico de Preço',
    PRICE_REFERENCE: 'Referência de Preço',
    CUSTOMER: 'Cliente',
    PROPOSAL: 'Proposta',
    OP: 'Ordem de Produção',
    PROJECT_TASK: 'Tarefa do Projeto',
    IT_TICKET: 'Chamado de TI',
    IT_ASSET: 'Ativo de TI',
    IT_NETWORK_PORT: 'Porta de Rede',
    IT_REMOTE_ACCESS: 'Acesso Remoto',
    NAS_ACCESS: 'Acesso NAS',
    EMAIL_ACCOUNT_ACCESS: 'Conta de E-mail',
    IT_SOFTWARE_CERTIFICATE: 'Certificado/Programa',
    VOIP_ACCOUNT: 'Conta VOIP',
    IT_EXTENSION: 'Ramal',
    FILE: 'Arquivo',
    TEMPLATE: 'Template',
    CREDENTIAL_METADATA: 'Metadado de Credencial',
  };
  return dict[entity] || entity;
};

export const LegacyImportStatusBadge: React.FC<LegacyImportStatusBadgeProps> = ({ type, value }) => {
  if (type === 'batch') {
    const text = humanizeBatchStatus(value);
    let variant: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral' = 'neutral';
    
    switch (value) {
      case 'READY_TO_IMPORT':
      case 'IMPORTED':
        variant = 'success';
        break;
      case 'NEEDS_REVIEW':
      case 'EXTRACTED':
        variant = 'warning';
        break;
      case 'DISCOVERED':
        variant = 'info';
        break;
      case 'FAILED':
        variant = 'danger';
        break;
      case 'CANCELLED':
        variant = 'neutral';
        break;
    }
    
    return <Badge variant={variant}>{text}</Badge>;
  }
  
  if (type === 'row') {
    const text = humanizeRowStatus(value);
    let variant: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral' = 'neutral';
    
    switch (value) {
      case 'ACCEPTED':
        variant = 'success';
        break;
      case 'PENDING_REVIEW':
        variant = 'warning';
        break;
      case 'NEEDS_MORE_INFO':
        variant = 'info';
        break;
      case 'REJECTED':
        variant = 'danger';
        break;
      case 'DUPLICATE':
        variant = 'neutral';
        break;
    }
    
    return <Badge variant={variant}>{text}</Badge>;
  }
  
  if (type === 'entity') {
    const text = humanizeEntityTarget(value);
    return <Badge variant="primary" style={{ textTransform: 'none', letterSpacing: 'normal' }}>{text}</Badge>;
  }
  
  return <Badge variant="neutral">{value}</Badge>;
};
