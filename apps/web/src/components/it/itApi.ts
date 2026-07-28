import { humanizeApiError } from '../../lib/apiErrors';

export interface ITTicket {
  id: number;
  ticket_number: string;
  title: string;
  description: string;
  requester_user_id: number;
  requester_name?: string;
  assigned_to_user_id?: number | null;
  assignee_name?: string | null;
  status: string;
  priority: string;
  category: string;
  suspension_reason?: string | null;
  due_at?: string | null;
  kanban_card_id?: number | null;
  sla?: { state?: string; minutes_remaining?: number | null; overdue?: boolean };
  total_time_seconds?: number;
  comments?: ITComment[];
  checklists?: ITChecklist[];
  attachments?: ITAttachment[];
  created_at: string;
  updated_at: string;
}

export interface ITComment {
  id: number;
  ticket_id: number;
  user_id: number;
  author_name?: string;
  comment: string;
  is_internal: boolean;
  created_at: string;
}

export interface ITChecklist {
  id: number;
  title: string;
  category?: string;
  items: { id: number; text: string; is_done: boolean }[];
}

export interface ITAttachment {
  id: number;
  ticket_id: number;
  filename?: string;
  content_type?: string;
  size_bytes?: number;
  created_at: string;
}

export interface ITSummary {
  open_tickets: number;
  in_progress_tickets: number;
  suspended_tickets: number;
  closed_today: number;
  overdue_tickets: number;
  critical_tickets: number;
  expiring_certificates: number;
  assets_in_maintenance: number;
  my_tickets: number;
  assigned_to_me: number;
}

export async function itRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1/it${path}`, {
    credentials: 'include',
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const errMsg = humanizeApiError(detail, 'Nao foi possivel concluir a acao.', response.status);
    throw new Error(errMsg);
  }
  return response.json();
}

export const ticketStatusLabels: Record<string, string> = {
  ABERTO: 'Aberto',
  EM_ATENDIMENTO: 'Em atendimento',
  SUSPENSO: 'Suspenso',
  FECHADO: 'Fechado',
};

export const categoryOptions = [
  { value: 'INTERNET_REDE', label: 'Internet / Rede' },
  { value: 'COMPUTADOR', label: 'Computador' },
  { value: 'IMPRESSORA', label: 'Impressora' },
  { value: 'EMAIL', label: 'E-mail' },
  { value: 'SISTEMA_SOFTWARE', label: 'Sistema / Software' },
  { value: 'ACESSO', label: 'Acesso' },
  { value: 'EQUIPAMENTO', label: 'Equipamento' },
  { value: 'CERTIFICADO', label: 'Certificado' },
  { value: 'OUTRO', label: 'Outro' },
];

export const priorityLabels: Record<string, string> = {
  BAIXA: 'Baixa',
  MEDIA: 'Média',
  ALTA: 'Alta',
  CRITICA: 'Crítica',
};

export const suspensionReasonLabels: Record<string, string> = {
  AGUARDANDO_USUARIO: 'Aguardando usuário',
  AGUARDANDO_TERCEIRO: 'Aguardando terceiro',
  AGUARDANDO_PECA: 'Aguardando peça',
  AGUARDANDO_COMPRA: 'Aguardando compra',
  OUTRO: 'Outro',
};

export function categoryLabel(value?: string | null) {
  if (!value) return 'Não informado';
  return categoryOptions.find((item) => item.value === value)?.label || value;
}

export function statusLabel(value?: string | null) {
  if (!value) return 'Não informado';
  return ticketStatusLabels[value] || value;
}

export function priorityLabel(value?: string | null) {
  if (!value) return 'Não informado';
  return priorityLabels[value] || value;
}
