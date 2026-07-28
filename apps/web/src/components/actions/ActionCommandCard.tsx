import React, { useState, useEffect } from 'react';
import { Check, X, AlertTriangle, AlertCircle, Info, ChevronDown, ChevronUp, Lock } from 'lucide-react';
import { Button } from '../ui/Button';
import { Select } from '../ui/Select';
import { Input } from '../ui/Input';
import { ActionCommandDraft, ActionField } from '../../hooks/useActionCommands';

interface ActionCommandCardProps {
  draft: ActionCommandDraft;
  onConfirm: (draftId: string, overrideData?: any) => Promise<ActionCommandDraft>;
  onCancel: (draftId: string) => Promise<ActionCommandDraft>;
  onSuccess?: (resultDraft: ActionCommandDraft) => void;
  onOpenModule?: (moduleName: string, entityId?: string) => void;
  isAdmin?: boolean;
}

export const ActionCommandCard: React.FC<ActionCommandCardProps> = ({
  draft: initialDraft,
  onConfirm,
  onCancel,
  onSuccess,
  onOpenModule,
  isAdmin = false
}) => {
  const [draft, setDraft] = useState<ActionCommandDraft>(initialDraft);
  const [showTechDetails, setShowTechDetails] = useState(false);
  const [overrideForm, setOverrideForm] = useState<Record<string, any>>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [confirming, setConfirming] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [successResult, setSuccessResult] = useState<any | null>(null);

  // Master Data Options for dynamic fields
  const [suppliers, setSuppliers] = useState<Array<{ id: string; label: string }>>([]);
  const [productItems, setProductItems] = useState<Array<{ id: string; label: string }>>([]);
  const [loadingOptions, setLoadingOptions] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setDraft(initialDraft);
    // Reset forms
    setOverrideForm({});
    setFormErrors({});
    setSuccessResult(null);
  }, [initialDraft]);

  // Load Master Data options if missing fields require them
  useEffect(() => {
    const missing = draft.missing_fields?.fields || [];
    missing.forEach(async (field) => {
      if (field.source_module === 'master_data') {
        if (field.source_entity === 'supplier' && suppliers.length === 0 && !loadingOptions.suppliers) {
          setLoadingOptions(prev => ({ ...prev, suppliers: true }));
          try {
            const res = await fetch('/api/v1/master-data/suppliers');
            if (res.ok) {
              const data = await res.json();
              const mapped = data.map((s: any) => ({
                id: s.id,
                label: s.person?.name || s.company_name || s.name || 'Fornecedor sem nome'
              }));
              setSuppliers(mapped);
            }
          } catch (e) {
            console.error('Erro ao buscar fornecedores para a ação:', e);
          } finally {
            setLoadingOptions(prev => ({ ...prev, suppliers: false }));
          }
        }
        if (field.source_entity === 'product_item' && productItems.length === 0 && !loadingOptions.productItems) {
          setLoadingOptions(prev => ({ ...prev, productItems: true }));
          try {
            const res = await fetch('/api/v1/master-data/items');
            if (res.ok) {
              const data = await res.json();
              const mapped = data.map((i: any) => ({
                id: i.id,
                label: `${i.name} ${i.sku ? `(Codigo: ${i.sku})` : ''}`
              }));
              setProductItems(mapped);
            }
          } catch (e) {
            console.error('Erro ao buscar itens de produto para a ação:', e);
          } finally {
            setLoadingOptions(prev => ({ ...prev, productItems: false }));
          }
        }
      }
    });
  }, [draft.missing_fields, suppliers.length, productItems.length, loadingOptions]);

  const handleFieldChange = (name: string, value: any) => {
    setOverrideForm(prev => ({ ...prev, [name]: value }));
    if (formErrors[name]) {
      setFormErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};
    const missing = draft.missing_fields?.fields || [];
    
    missing.forEach(field => {
      const value = overrideForm[field.name];
      if (value === undefined || value === null || String(value).trim() === '') {
        errors[field.name] = `${field.label} é obrigatório.`;
      }
    });

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleConfirmClick = async () => {
    if (draft.status === 'NEEDS_MORE_INFO' && !validateForm()) {
      return;
    }

    setConfirming(true);
    try {
      // Mescla override form com o enriched_data
      const dataToSend = { ...draft.enriched_data, ...overrideForm };
      const result = await onConfirm(draft.id, dataToSend);
      setDraft(result);
      if (result.status === 'EXECUTED') {
        setSuccessResult(result.preview?.Resultado || 'Ação executada com sucesso.');
      }
      if (onSuccess) {
        onSuccess(result);
      }
    } catch (e: any) {
      console.error(e);
    } finally {
      setConfirming(false);
    }
  };

  const handleCancelClick = async () => {
    setCancelling(true);
    try {
      const result = await onCancel(draft.id);
      setDraft(result);
    } catch (e) {
      console.error(e);
    } finally {
      setCancelling(false);
    }
  };

  const renderFieldInput = (field: ActionField) => {
    const value = overrideForm[field.name] || '';
    const errorMsg = formErrors[field.name];

    if (field.source_module === 'master_data') {
      if (field.source_entity === 'supplier') {
        return (
          <div key={field.name} className="mb-3">
            <label className="block text-xs font-semibold text-gray-400 mb-1">{field.label}</label>
            <Select
              value={value}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className={errorMsg ? 'border-red-500' : ''}
              options={[
                { value: '', label: 'Selecione o Fornecedor...' },
                ...suppliers.map(s => ({ value: s.id, label: s.label }))
              ]}
            />
            {errorMsg && <p className="text-red-400 text-xs mt-1">{errorMsg}</p>}
          </div>
        );
      }
      if (field.source_entity === 'product_item') {
        return (
          <div key={field.name} className="mb-3">
            <label className="block text-xs font-semibold text-gray-400 mb-1">{field.label}</label>
            <Select
              value={value}
              onChange={(e) => handleFieldChange(field.name, e.target.value)}
              className={errorMsg ? 'border-red-500' : ''}
              options={[
                { value: '', label: 'Selecione o Item...' },
                ...productItems.map(i => ({ value: i.id, label: i.label }))
              ]}
            />
            {errorMsg && <p className="text-red-400 text-xs mt-1">{errorMsg}</p>}
          </div>
        );
      }
    }

    if (field.type === 'select' && field.options) {
      return (
        <div key={field.name} className="mb-3">
          <label className="block text-xs font-semibold text-gray-400 mb-1">{field.label}</label>
          <Select
            value={value}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className={errorMsg ? 'border-red-500' : ''}
            options={[
              { value: '', label: 'Selecione...' },
              ...field.options.map(opt => ({ value: opt, label: opt }))
            ]}
          />
          {errorMsg && <p className="text-red-400 text-xs mt-1">{errorMsg}</p>}
        </div>
      );
    }

    // Default: text, number, currency, etc.
    return (
      <div key={field.name} className="mb-3">
        <label className="block text-xs font-semibold text-gray-400 mb-1">{field.label}</label>
        <Input
          type={field.type === 'number' || field.type === 'currency' ? 'number' : 'text'}
          step={field.type === 'currency' ? '0.01' : 'any'}
          value={value}
          onChange={(e) => handleFieldChange(field.name, e.target.value)}
          placeholder={`Preencha o campo ${field.label}...`}
          className={errorMsg ? 'border-red-500' : ''}
        />
        {errorMsg && <p className="text-red-400 text-xs mt-1">{errorMsg}</p>}
      </div>
    );
  };

  // Human risk details
  const getRiskMetadata = (risk: string) => {
    switch (risk) {
      case 'LOW':
        return { label: 'Risco Baixo', bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' };
      case 'MEDIUM':
        return { label: 'Risco Médio', bg: 'bg-blue-500/10 text-blue-400 border-blue-500/30' };
      case 'HIGH':
        return { label: 'Risco Alto', bg: 'bg-amber-500/10 text-amber-400 border-amber-500/30' };
      case 'CRITICAL':
        return { label: 'Crítico (Restrito)', bg: 'bg-rose-500/10 text-rose-400 border-rose-500/30' };
      default:
        return { label: 'Risco Normal', bg: 'bg-gray-500/10 text-gray-400 border-gray-500/30' };
    }
  };

  const riskMeta = getRiskMetadata(draft.risk_level);

  // Status mapping to color/label
  const getStatusMetadata = (status: string) => {
    switch (status) {
      case 'NEEDS_MORE_INFO':
        return { label: 'Ação Incompleta', color: 'text-amber-400' };
      case 'READY_TO_CONFIRM':
        return { label: 'Pronto para Confirmar', color: 'text-blue-400' };
      case 'APPROVAL_REQUIRED':
        return { label: 'Requer Aprovação', color: 'text-amber-400' };
      case 'EXECUTED':
        return { label: 'Executado', color: 'text-emerald-400' };
      case 'FAILED':
        return { label: 'Falhou', color: 'text-rose-400' };
      case 'CANCELLED':
        return { label: 'Cancelado', color: 'text-gray-400' };
      default:
        return { label: status, color: 'text-gray-300' };
    }
  };

  const statusMeta = getStatusMetadata(draft.status);
  const isFinalState = ['EXECUTED', 'FAILED', 'CANCELLED'].includes(draft.status);
  const missingFieldsList = draft.missing_fields?.fields || [];

  return (
    <div className="border border-gray-800 bg-[#0f111a] rounded-xl overflow-hidden shadow-2xl transition-all duration-300 max-w-lg w-full mb-4">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-900 bg-gray-950/40 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Info size={16} className={statusMeta.color} />
          <div>
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Ação Recomendada</span>
            <h4 className="text-sm font-bold text-gray-100 leading-tight">
              {draft.preview?.Produto ? `Registrar ação: ${draft.action_key.split('.').pop()}` : 'Comando Analisado'}
            </h4>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] px-2 py-0.5 border rounded-full font-bold ${riskMeta.bg}`}>
            {riskMeta.label}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="p-5">
        {/* Title & Description */}
        <div className="mb-4">
          <h3 className="text-base font-semibold text-gray-200 mb-1">
            {draft.preview?.Produto ? `Ação para: ${draft.preview.Produto}` : 'Ação de Sistema'}
          </h3>
          <p className="text-xs text-gray-400">
            Módulo: <span className="text-gray-300 capitalize font-medium">{draft.module}</span>
          </p>
        </div>

        {/* Found data chips */}
        {Object.keys(draft.preview).length > 0 && (
          <div className="mb-4">
            <h5 className="text-[10px] uppercase font-bold text-gray-500 tracking-wider mb-2">Dados Identificados</h5>
            <div className="flex flex-wrap gap-2">
              {Object.entries(draft.preview).map(([key, value]) => {
                if (key === 'Resultado') return null; // Não mostra resultado na lista de chips
                return (
                  <div key={key} className="bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-lg text-xs flex items-center gap-1.5">
                    <span className="text-gray-500 font-medium">{key}:</span>
                    <span className="text-gray-200 font-semibold">{String(value)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Success / Result View */}
        {successResult && (
          <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl p-4 mb-4 flex items-start gap-3">
            <Check size={18} className="text-emerald-400 mt-0.5 shrink-0" />
            <div>
              <h5 className="text-xs font-bold text-emerald-400">Executado com Sucesso</h5>
              <p className="text-xs text-gray-300 mt-1 leading-relaxed">{successResult}</p>
            </div>
          </div>
        )}

        {/* Blocked / Error View */}
        {draft.status === 'FAILED' && (
          <div className="bg-rose-500/5 border border-rose-500/20 rounded-xl p-4 mb-4 flex items-start gap-3">
            <AlertCircle size={18} className="text-rose-400 mt-0.5 shrink-0" />
            <div>
              <h5 className="text-xs font-bold text-rose-400">Operação Falhou / Bloqueada</h5>
              <p className="text-xs text-gray-300 mt-1 leading-relaxed">
                {draft.error_message || 'Um erro de segurança ou permissão impediu a execução desta ação.'}
              </p>
            </div>
          </div>
        )}

        {/* Warning: Approval required */}
        {draft.status === 'APPROVAL_REQUIRED' && !successResult && (
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 mb-4 flex items-start gap-3">
            <Lock size={18} className="text-amber-400 mt-0.5 shrink-0" />
            <div>
              <h5 className="text-xs font-bold text-amber-400">Aprovação Necessária (Alçada)</h5>
              <p className="text-xs text-gray-300 mt-1 leading-relaxed">
                Esta ação foi encaminhada para aprovação gerencial devido ao nível de risco ({draft.risk_level}). Você será notificado assim que for homologada.
              </p>
              {draft.action_intent_id && (
                <div className="mt-2 text-[10px] text-gray-500">
                  Solicitação de Ação registrada.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Forms for Missing Fields */}
        {draft.status === 'NEEDS_MORE_INFO' && missingFieldsList.length > 0 && (
          <div className="bg-gray-950/50 border border-gray-900 rounded-xl p-4 mb-4">
            <div className="flex items-center gap-1.5 mb-3 text-amber-400">
              <AlertTriangle size={14} />
              <h5 className="text-xs font-bold uppercase tracking-wider">Informações Faltantes</h5>
            </div>
            <p className="text-xs text-gray-400 mb-3 leading-relaxed">
              O sistema identificou a intenção, mas precisa dos dados abaixo para prosseguir de forma segura:
            </p>
            <div className="space-y-1">
              {missingFieldsList.map(field => renderFieldInput(field))}
            </div>
          </div>
        )}

        {/* Tech Details (For Admin Mode) */}
        {isAdmin && (
          <div className="border-t border-gray-900 mt-4 pt-3">
            <button
              onClick={() => setShowTechDetails(!showTechDetails)}
              className="text-[10px] text-gray-500 hover:text-gray-400 flex items-center gap-1 uppercase tracking-wider font-bold transition-colors"
            >
              {showTechDetails ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
              Detalhes Técnicos (Admin)
            </button>
            {showTechDetails && (
              <div className="bg-gray-950/80 p-3 rounded-lg border border-gray-900 mt-2 text-[10px] font-mono text-gray-400 space-y-1">
                <div><span className="text-gray-500">Draft ID:</span> {draft.id}</div>
                <div><span className="text-gray-500">Ação Chave:</span> {draft.action_key}</div>
                <div><span className="text-gray-500">Mapeamento:</span> {draft.target_action_type}</div>
                <div><span className="text-gray-500">Risco:</span> {draft.risk_level}</div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer / Buttons */}
      {!isFinalState && (
        <div className="px-5 py-3.5 border-t border-gray-900 bg-gray-950/40 flex items-center justify-end gap-2.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCancelClick}
            disabled={confirming || cancelling}
            className="text-gray-400 hover:text-gray-200 text-xs px-3.5 py-1.5"
          >
            {cancelling ? 'Cancelando...' : 'Cancelar'}
          </Button>

          {draft.status === 'APPROVAL_REQUIRED' ? (
            <Button
              size="sm"
              disabled
              className="bg-amber-600/35 border border-amber-600/30 text-amber-300 text-xs px-4 py-1.5 font-semibold"
            >
              Aprovação Solicitada
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={handleConfirmClick}
              disabled={confirming || cancelling}
              className="bg-blue-600 hover:bg-blue-500 text-white border border-blue-500/30 text-xs px-4 py-1.5 font-semibold shadow-lg shadow-blue-500/10 flex items-center gap-1.5"
            >
              {confirming ? (
                'Processando...'
              ) : (
                <>
                  <Check size={14} />
                  {draft.status === 'NEEDS_MORE_INFO' ? 'Enviar Dados e Confirmar' : 'Confirmar Execução'}
                </>
              )}
            </Button>
          )}

          {draft.created_entity_type && draft.created_entity_id && onOpenModule && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onOpenModule(draft.module, draft.created_entity_id)}
              className="text-xs text-gray-300 border-gray-800 hover:bg-gray-900 px-3.5 py-1.5"
            >
              Abrir no Módulo
            </Button>
          )}
        </div>
      )}

      {/* Finalized view status banner */}
      {isFinalState && (
        <div className="px-5 py-3 border-t border-gray-900 bg-gray-950/80 flex items-center justify-between text-xs text-gray-500 font-medium">
          <span>Status Final: <span className={statusMeta.color}>{statusMeta.label}</span></span>
          {draft.created_entity_type && draft.created_entity_id && onOpenModule && (
            <button
              onClick={() => onOpenModule(draft.module, draft.created_entity_id)}
              className="text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1"
            >
              Visualizar Registro
            </button>
          )}
        </div>
      )}
    </div>
  );
};
