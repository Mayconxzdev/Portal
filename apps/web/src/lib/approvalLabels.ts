export const approvalStatusLabels: Record<string, string> = {
  PENDING: 'Pendente',
  APPROVED: 'Aprovado',
  REJECTED: 'Rejeitado',
  CANCELLED: 'Cancelado',
  EXPIRED: 'Expirado',
};

export const approvalRiskLabels: Record<string, string> = {
  LOW: 'Baixa',
  MEDIUM: 'Média',
  HIGH: 'Alta',
  CRITICAL: 'Crítica',
};

export const approvalModuleLabels: Record<string, string> = {
  dashboard: 'Dashboard',
  kanban: 'Kanban',
  proposals: 'Propostas',
  purchases: 'Compras',
  it: 'TI',
  chat: 'Chat Interno',
  files: 'Arquivos / Knowledge',
  stock: 'Estoque Básico',
  approvals: 'Aprovações',
  automations: 'Automações IA',
  admin: 'Administração',
};

export const approvalActionTypeLabels: Record<string, string> = {
  FINANCIAL_RELEASE: 'Liberação de compra',
  PURCHASE_QUOTE: 'Cotação de compra',
  SUPPLIER_SELECTION: 'Escolha de fornecedor/produto',
  PROPOSAL_SEND: 'Envio de proposta',
  PASSWORD_RESET: 'Reset de senha',
  PERMISSION_CHANGE: 'Alteração de permissão',
  IT_ACCESS_RELEASE: 'Liberação de acesso',
  CONTRACT_APPROVAL: 'Aprovação de contrato',
  GENERAL_APPROVAL: 'Aprovação geral',
};

export const labelOrValue = (labels: Record<string, string>, value?: string) => {
  if (!value) return 'Não informado';
  return labels[value] || value;
};
