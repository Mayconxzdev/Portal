export type ApiFieldErrors = Record<string, string>;

export interface ApiErrorState {
  code: string;
  message: string;
  fieldErrors: ApiFieldErrors;
  requestId?: string;
  status?: number;
  retryable: boolean;
  technicalDetails?: unknown;
}

const fieldLabels: Record<string, string> = {
  username: 'nome de usuario',
  email: 'e-mail',
  password: 'senha',
  role_id: 'perfil',
  module_permissions: 'permissoes',
  permission_level: 'nivel de acesso',
  title: 'titulo',
  description: 'descricao',
  reason: 'justificativa',
  comment: 'comentario',
  name: 'nome',
};

const pydanticTechnicalFragments = [
  'field required',
  'input should be',
  'string should have',
  'value is not a valid',
  'json decode',
  'valid email',
];

const fieldFromLoc = (loc: unknown): string | null => {
  if (!Array.isArray(loc)) return null;
  const known = [...loc].reverse().find((part) => typeof part === 'string');
  return typeof known === 'string' ? known : null;
};

const labelForField = (field: string) => fieldLabels[field] || field.replace(/_/g, ' ');

const humanMessageForField = (field: string, rawMessage: string) => {
  const label = labelForField(field);
  const normalized = rawMessage.toLowerCase();

  if (field === 'email') return 'Informe um e-mail valido ou deixe em branco.';
  if (field === 'username') return 'Informe um nome de usuario valido.';
  if (field === 'password') return 'Informe uma senha inicial ou gere uma senha temporaria.';
  if (field === 'role_id') return 'Selecione um perfil valido para este usuario.';
  if (field === 'module_permissions' || field === 'permission_level') return 'Revise as permissoes selecionadas.';

  if (pydanticTechnicalFragments.some((fragment) => normalized.includes(fragment))) {
    return `Verifique o campo ${label}.`;
  }

  return rawMessage || `Verifique o campo ${label}.`;
};

const messageForStatus = (status?: number) => {
  if (!status) return 'Nao foi possivel concluir a acao agora.';
  if (status === 400) return 'Revise as informacoes e tente novamente.';
  if (status === 401) return 'Sua sessao expirou. Entre novamente para continuar.';
  if (status === 403) return 'Voce nao tem permissao para realizar esta acao.';
  if (status === 404) return 'Nao encontrei o registro solicitado.';
  if (status === 409) return 'Ja existe um registro conflitante com essas informacoes.';
  if (status === 422) return 'Revise os campos destacados antes de continuar.';
  if (status === 429) return 'Muitas tentativas em pouco tempo. Aguarde alguns minutos.';
  if (status >= 500) return 'O servidor nao conseguiu concluir a acao agora.';
  return 'Nao foi possivel concluir a acao agora.';
};

const asRecord = (value: unknown): Record<string, unknown> | null => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
};

export const normalizeApiError = (
  input: unknown,
  fallback = 'Nao foi possivel concluir a acao agora.',
  status?: number,
): ApiErrorState => {
  if (input instanceof Response) {
    return {
      code: `HTTP_${input.status}`,
      message: messageForStatus(input.status) || fallback,
      fieldErrors: {},
      status: input.status,
      retryable: input.status >= 500 || input.status === 429,
      technicalDetails: input,
    };
  }

  if (input instanceof Error) {
    return {
      code: 'CLIENT_ERROR',
      message: input.message || fallback,
      fieldErrors: {},
      status,
      retryable: false,
      technicalDetails: input,
    };
  }

  if (typeof input === 'string') {
    return {
      code: status ? `HTTP_${status}` : 'API_ERROR',
      message: input || fallback,
      fieldErrors: {},
      status,
      retryable: Boolean(status && (status >= 500 || status === 429)),
      technicalDetails: input,
    };
  }

  const record = asRecord(input);
  const detail = record && 'detail' in record ? record.detail : input;
  const fieldErrors: ApiFieldErrors = {};
  const messages: string[] = [];

  if (Array.isArray(detail)) {
    detail.forEach((item) => {
      if (typeof item === 'string') {
        messages.push(item);
        return;
      }
      const detailRecord = asRecord(item);
      if (!detailRecord) return;
      const field = fieldFromLoc(detailRecord.loc);
      const msg = typeof detailRecord.msg === 'string' ? detailRecord.msg : '';
      if (field) {
        const fieldMessage = humanMessageForField(field, msg);
        fieldErrors[field] = fieldMessage;
        messages.push(fieldMessage);
      } else if (msg) {
        messages.push(msg);
      }
    });
  } else if (typeof detail === 'string') {
    messages.push(detail);
  } else {
    const detailRecord = asRecord(detail);
    if (detailRecord) {
      const message = detailRecord.message || detailRecord.error || detailRecord.detail;
      if (typeof message === 'string') messages.push(message);
      const rawFieldErrors = asRecord(detailRecord.field_errors);
      if (rawFieldErrors) {
        Object.entries(rawFieldErrors).forEach(([field, value]) => {
          if (typeof value === 'string') fieldErrors[field] = value;
        });
      }
    }
  }

  const requestId =
    record && typeof record.request_id === 'string'
      ? record.request_id
      : record && typeof record.requestId === 'string'
        ? record.requestId
        : undefined;

  const code =
    record && typeof record.code === 'string'
      ? record.code
      : status
        ? `HTTP_${status}`
        : Object.keys(fieldErrors).length > 0
          ? 'VALIDATION_ERROR'
          : 'API_ERROR';

  return {
    code,
    message: Array.from(new Set(messages)).join(' ') || messageForStatus(status) || fallback,
    fieldErrors,
    requestId,
    status,
    retryable: Boolean(status && (status >= 500 || status === 429)),
    technicalDetails: input,
  };
};

export const humanizeApiError = (input: unknown, fallback?: string, status?: number) =>
  normalizeApiError(input, fallback, status).message;

export const readApiError = async (
  response: Response,
  fallback = 'Nao foi possivel concluir a acao agora.',
): Promise<ApiErrorState> => {
  const payload = await response.json().catch(() => undefined);
  return normalizeApiError(payload ?? response, fallback, response.status);
};
