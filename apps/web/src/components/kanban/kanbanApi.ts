import { humanizeEventAction } from '../../utils/humanizeEvents';
import { humanizeApiError } from '../../lib/apiErrors';

export async function apiJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: options.body instanceof FormData ? options.headers : { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  if (!response.ok) {
    let message = 'Nao foi possivel concluir a acao.';
    try {
      const payload = await response.json();
      message = humanizeApiError(payload, message, response.status);
    } catch {
      /* resposta sem JSON */
    }
    throw new Error(message);
  }
  return response.json();
}

export const priorityLabels = { LOW: 'Baixa', MEDIUM: 'Média', HIGH: 'Alta', URGENT: 'Urgente' };

export const accessRank = { READ_ONLY: 1, NORMAL: 2, MANAGER: 3, ADMIN: 4 };

export const activityLabel = (action: string) => {
  return humanizeEventAction(action);
};
