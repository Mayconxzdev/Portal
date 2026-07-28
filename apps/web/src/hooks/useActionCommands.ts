import { useState, useCallback } from 'react';

export interface ActionField {
  name: string;
  label: string;
  type: string;
  source_module?: string;
  source_entity?: string;
  options?: string[];
}

export interface ActionCommandDraft {
  id: string;
  user_id: number;
  source: string;
  source_module?: string;
  source_entity_type?: string;
  source_entity_id?: string;
  raw_text?: string;
  action_key: string;
  intent_type: string;
  module: string;
  status: 'DRAFT' | 'NEEDS_MORE_INFO' | 'READY_TO_CONFIRM' | 'CONFIRMED' | 'CANCELLED' | 'EXECUTED' | 'FAILED' | 'APPROVAL_REQUIRED';
  extracted_data: Record<string, any>;
  enriched_data: Record<string, any>;
  missing_fields: {
    fields: ActionField[];
  };
  preview: Record<string, any>;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  requires_confirmation: boolean;
  requires_approval: boolean;
  target_action_type: string;
  created_entity_type?: string;
  created_entity_id?: string;
  action_intent_id?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface AvailableAction {
  action_key: string;
  title: string;
  description: string;
  module: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export function useActionCommands() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parseCommand = useCallback(async (text: string, source: string, context?: any): Promise<ActionCommandDraft> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/action-commands/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, source, context }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao analisar comando de voz/texto.');
      }
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const prepareCommand = useCallback(async (
    actionKey: string,
    source: string,
    sourceModule?: string,
    sourceEntityType?: string,
    sourceEntityId?: string,
    initialData?: any
  ): Promise<ActionCommandDraft> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/action-commands/prepare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action_key: actionKey,
          source,
          source_module: sourceModule,
          source_entity_type: sourceEntityType,
          source_entity_id: sourceEntityId,
          initial_data: initialData,
        }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao preparar ação contextual.');
      }
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const confirmCommand = useCallback(async (draftId: string, overrideData?: any): Promise<ActionCommandDraft> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/action-commands/${draftId}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ override_data: overrideData }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao confirmar ação.');
      }
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const cancelCommand = useCallback(async (draftId: string): Promise<ActionCommandDraft> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/v1/action-commands/${draftId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao cancelar ação.');
      }
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRecentCommands = useCallback(async (): Promise<ActionCommandDraft[]> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/action-commands/recent');
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao buscar comandos recentes.');
      }
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAvailableActions = useCallback(async (moduleName?: string, entityType?: string): Promise<AvailableAction[]> => {
    setLoading(true);
    setError(null);
    try {
      let url = '/api/v1/action-commands/available-actions';
      const params = new URLSearchParams();
      if (moduleName) params.append('module', moduleName);
      if (entityType) params.append('entity_type', entityType);
      
      const queryStr = params.toString();
      if (queryStr) url += `?${queryStr}`;

      const res = await fetch(url);
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Falha ao buscar ações disponíveis.');
      }
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    parseCommand,
    prepareCommand,
    confirmCommand,
    cancelCommand,
    fetchRecentCommands,
    fetchAvailableActions,
  };
}
