export type NotificationNavigateOptions = {
  replace?: boolean;
  search?: URLSearchParams | Record<string, string | number | boolean | undefined | null> | string;
};

export type NotificationNavigate = (moduleCode: string, options?: NotificationNavigateOptions) => void;

export interface NotificationDestinationInput {
  module: string;
  action_url?: string | null;
  source_type?: string | null;
  source_id?: string | null;
}

export interface ResolvedNotificationDestination {
  moduleCode: string;
  search?: Record<string, string>;
  warning?: string;
}

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const numericPattern = /^\d+$/;

const validId = (value: string | null, kind: 'uuid' | 'number' | 'any') => {
  if (!value) return false;
  if (kind === 'uuid') return uuidPattern.test(value);
  if (kind === 'number') return numericPattern.test(value);
  return /^[A-Za-z0-9_.:-]{1,120}$/.test(value);
};

const parseInternalUrl = (actionUrl?: string | null) => {
  if (!actionUrl || !actionUrl.startsWith('/') || actionUrl.startsWith('//')) return null;
  try {
    const parsed = new URL(actionUrl, window.location.origin);
    if (parsed.origin !== window.location.origin) return null;
    return parsed;
  } catch {
    return null;
  }
};

export const resolveNotificationDestination = (
  notification: NotificationDestinationInput,
): ResolvedNotificationDestination | null => {
  const parsed = parseInternalUrl(notification.action_url);
  const path = parsed?.pathname.replace(/\/+$/, '') || '';
  const params = parsed?.searchParams;

  if (path === '/approvals') {
    const approvalId = params?.get('approval') || params?.get('approval_id') || notification.source_id || null;
    if (!validId(approvalId, 'number')) {
      return { moduleCode: 'approvals', warning: 'A aprovacao vinculada nao esta disponivel neste link.' };
    }
    return { moduleCode: 'approvals', search: { approval: approvalId ?? '' } };
  }

  if (path === '/stock') {
    const itemId = params?.get('item') || params?.get('item_id') || notification.source_id || null;
    const alertId = params?.get('alert') || null;
    if (!validId(itemId, 'uuid')) {
      return { moduleCode: 'stock', warning: 'O item de estoque vinculado nao esta disponivel neste link.' };
    }
    const search: Record<string, string> = { item: itemId ?? '' };
    if (validId(alertId, 'uuid')) search.alert = alertId ?? '';
    return { moduleCode: 'stock', search };
  }

  if (path === '/purchases') {
    const requestId = params?.get('request') || params?.get('request_id') || params?.get('need') || params?.get('id') || null;
    const quoteId = params?.get('quote') || params?.get('quote_id') || params?.get('rfq') || null;
    const step = params?.get('step');
    if (validId(requestId, 'uuid')) {
      return {
        moduleCode: 'purchases',
        search: {
          request: requestId ?? '',
          ...(step && ['overview', 'approval', 'order', 'delivery'].includes(step) ? { step } : {}),
        },
      };
    }
    if (validId(quoteId, 'uuid')) {
      return {
        moduleCode: 'purchases',
        search: {
          quote: quoteId ?? '',
          ...(step && ['products', 'suppliers', 'preview'].includes(step) ? { step } : {}),
        },
      };
    }
    if (notification.source_type === 'purchase_request' && validId(notification.source_id || null, 'uuid')) {
      return {
        moduleCode: 'purchases',
        search: { request: notification.source_id ?? '' },
      };
    }
    return { moduleCode: 'purchases', warning: 'A compra vinculada nao esta disponivel neste link.' };
  }

  const safeModuleFallbacks = new Set([
    'dashboard',
    'automations',
    'chat',
    'files',
    'kanban',
    'it',
    'proposals',
    'admin',
  ]);
  if (safeModuleFallbacks.has(notification.module)) {
    return {
      moduleCode: notification.module,
      warning: 'Esta notificacao abre o modulo relacionado porque ainda nao ha link profundo validado.',
    };
  }

  return null;
};
