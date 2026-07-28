import React, { useState } from 'react';
import { 
  X, ShieldAlert, AlertCircle, Info, Lock, Eye, CheckCircle2, XCircle, HelpCircle, Merge, PlusCircle, RefreshCw
} from 'lucide-react';
import { LegacyImportStatusBadge, humanizeEntityTarget } from './LegacyImportStatusBadge';
import { RowItem } from './LegacyImportRowTable';

interface LegacyImportRowDrawerProps {
  row: RowItem | null;
  onClose: () => void;
  currentUser: {
    role: string;
    username: string;
  };
  onDecisionSubmit: (rowId: string, decision: string, reason: string) => Promise<void>;
}

export const LegacyImportRowDrawer: React.FC<LegacyImportRowDrawerProps> = ({
  row,
  onClose,
  currentUser,
  onDecisionSubmit,
}) => {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!row) return null;

  const isAdmin = currentUser.role === 'ADMIN';

  // Verifica se um valor do JSON é um segredo mascarado ("******")
  const renderValue = (key: string, value: any): React.ReactNode => {
    if (value === '******') {
      return (
        <span 
          style={{ 
            display: 'inline-flex', 
            alignItems: 'center', 
            gap: '4px', 
            backgroundColor: 'rgba(239, 68, 68, 0.15)', 
            color: '#ef4444', 
            padding: '2px 8px', 
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 600,
            border: '1px solid rgba(239, 68, 68, 0.2)'
          }}
        >
          <Lock size={10} /> Protegido
        </span>
      );
    }
    
    if (typeof value === 'object' && value !== null) {
      return <pre style={{ margin: 0, fontSize: '11px', color: 'var(--text-secondary)' }}>{JSON.stringify(value, null, 2)}</pre>;
    }
    
    return String(value);
  };

  const handleDecision = async (decisionType: string) => {
    if (!reason.trim()) {
      setError('Por favor, informe a justificativa ou motivo antes de salvar.');
      return;
    }
    
    setError(null);
    setSubmitting(true);
    try {
      await onDecisionSubmit(row.id, decisionType, reason);
      setReason('');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Erro ao registrar decisão administrativa.');
    } finally {
      setSubmitting(false);
    }
  };

  const hasIssues = row.issues_json && Object.keys(row.issues_json).length > 0;
  const duplicateCandidates = row.detected_duplicates_json?.candidates || [];

  return (
    <div 
      className="legacy-drawer-container"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: '540px',
        backgroundColor: '#0f172a',
        borderLeft: '1px solid rgba(255, 255, 255, 0.08)',
        boxShadow: '-10px 0 30px rgba(0, 0, 0, 0.5)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        animation: 'slideIn 0.25s ease-out',
        fontFamily: 'Inter, system-ui, sans-serif'
      }}
    >
      {/* Cabeçalho */}
      <div 
        style={{ 
          padding: '18px 24px', 
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'rgba(30, 41, 59, 0.3)'
        }}
      >
        <div>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-muted)' }}>
            Revisão de Staging Legado
          </span>
          <h3 style={{ margin: '4px 0 0 0', fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Detalhes do Registro
          </h3>
        </div>
        <button 
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '4px',
            transition: 'background-color 0.15s'
          }}
          className="hover:bg-slate-800"
        >
          <X size={20} />
        </button>
      </div>

      {/* Corpo com Scroll */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Aviso Fixo sobre Mascaramento e Escrita de Dados */}
        <div 
          className="glass-card" 
          style={{ 
            padding: '12px 16px', 
            borderRadius: '8px', 
            backgroundColor: 'rgba(30, 41, 59, 0.4)',
            borderLeft: '4px solid var(--color-primary)',
            fontSize: '12px',
            color: 'var(--text-secondary)',
            lineHeight: '1.5'
          }}
        >
          <p style={{ margin: '0 0 6px 0', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Info size={14} style={{ color: 'var(--color-primary-light, #a78bfa)' }} /> Aviso de Governança
          </p>
          Senhas, segredos e credenciais foram mascarados automaticamente na extração. 
          Nenhuma promoção de dados oficial ou escrita no banco de dados ativo ocorrerá ao tomar sua decisão.
        </div>

        {/* Aviso específico de Credencial Protegida */}
        {(row.entity_target === 'CREDENTIAL_METADATA' || 
          row.entity_target === 'NAS_ACCESS' || 
          row.entity_target === 'EMAIL_ACCOUNT_ACCESS' || 
          row.entity_target === 'VOIP_ACCOUNT' ||
          row.normalized_data_json.has_secret === true) && (
          <div 
            style={{ 
              padding: '12px 16px', 
              borderRadius: '8px', 
              backgroundColor: 'rgba(239, 68, 68, 0.08)',
              borderLeft: '4px solid #ef4444',
              fontSize: '12px',
              color: '#fca5a5',
              lineHeight: '1.5'
            }}
          >
            <p style={{ margin: '0 0 6px 0', fontWeight: 600, color: '#fca5a5', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Lock size={14} style={{ color: '#ef4444' }} /> Registro de Segurança
            </p>
            Este registro contém credencial protegida. O valor real não é exibido nem importado nesta etapa.
          </div>
        )}

        {/* Resumo da Linha */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.04)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Entidade Destino</span>
            <div style={{ marginTop: '6px' }}>
              <LegacyImportStatusBadge type="entity" value={row.entity_target} />
            </div>
          </div>
          <div style={{ backgroundColor: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.04)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Status de Revisão</span>
            <div style={{ marginTop: '6px' }}>
              <LegacyImportStatusBadge type="row" value={row.status} />
            </div>
          </div>
        </div>

        {/* Problemas de Validação (issues_json) */}
        {hasIssues && (
          <div 
            style={{ 
              backgroundColor: 'rgba(239, 68, 68, 0.08)', 
              border: '1px solid rgba(239, 68, 68, 0.15)', 
              borderRadius: '8px', 
              padding: '16px' 
            }}
          >
            <h4 style={{ margin: '0 0 8px 0', color: '#ef4444', fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertCircle size={15} /> Problemas / Avisos de Validação
            </h4>
            <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12px', color: '#fca5a5', display: 'grid', gap: '4px' }}>
              {Object.entries(row.issues_json || {}).map(([key, msg]) => (
                <li key={key}>
                  <strong>{key}:</strong> {String(msg)}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Candidatos a Duplicado (detected_duplicates_json) */}
        {duplicateCandidates.length > 0 && (
          <div 
            style={{ 
              backgroundColor: 'rgba(245, 158, 11, 0.08)', 
              border: '1px solid rgba(245, 158, 11, 0.15)', 
              borderRadius: '8px', 
              padding: '16px' 
            }}
          >
            <h4 style={{ margin: '0 0 10px 0', color: '#f59e0b', fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldAlert size={15} /> Duplicados Potenciais no Portal
            </h4>
            <div style={{ display: 'grid', gap: '10px' }}>
              {duplicateCandidates.map((cand: any, idx: number) => (
                <div 
                  key={idx} 
                  style={{ 
                    backgroundColor: 'rgba(0,0,0,0.2)', 
                    padding: '10px 12px', 
                    borderRadius: '6px', 
                    fontSize: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '4px',
                    border: '1px solid rgba(245, 158, 11, 0.08)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-primary)' }}>
                    <span>Tipo de Colisão: <strong>{cand.match_type}</strong></span>
                    <span style={{ color: '#f59e0b', fontWeight: 700 }}>Score: {Math.round(cand.score * 100)}%</span>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    ID Registro Oficial: {cand.target_id}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px', borderTop: '1px dashed rgba(255,255,255,0.05)', paddingTop: '4px' }}>
                    <strong>Ação sugerida:</strong> {cand.match_type === 'DOCUMENT' || cand.score >= 0.9 ? 'Mesclar os dados futuramente' : 'Criar novo ou rejeitar se for incorreto'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dados Normalizados (normalized_data_json) */}
        <div>
          <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Campos Normalizados
          </h4>
          <div 
            style={{ 
              backgroundColor: 'rgba(255, 255, 255, 0.01)', 
              border: '1px solid rgba(255, 255, 255, 0.04)',
              borderRadius: '8px',
              padding: '12px 16px',
              display: 'grid',
              gap: '8px',
              fontSize: '12px'
            }}
          >
            {Object.entries(row.normalized_data_json || {}).map(([key, val]) => (
              <div 
                key={key} 
                style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  paddingBottom: '6px', 
                  borderBottom: '1px solid rgba(255, 255, 255, 0.02)' 
                }}
              >
                <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>{key}</span>
                <span style={{ color: 'var(--text-primary)', textAlign: 'right', wordBreak: 'break-all', maxWidth: '70%' }}>
                  {renderValue(key, val)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Histórico / Origem */}
        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          <p style={{ margin: '0 0 4px 0' }}>Origem: <strong>{row.source_app}</strong></p>
          {row.source_table_or_sheet && <p style={{ margin: '0 0 4px 0' }}>Planilha/Tabela: {row.source_table_or_sheet}</p>}
          {row.source_row_id && <p style={{ margin: '0 0 4px 0' }}>ID Linha Origem: {row.source_row_id}</p>}
          {row.reviewed_at && (
            <p style={{ margin: '10px 0 0 0', color: 'var(--color-success-light, #10b981)', fontWeight: 500 }}>
              Revisado por ID Usuário {row.reviewed_by_user_id} em {new Date(row.reviewed_at).toLocaleString('pt-BR')}
            </p>
          )}
        </div>

        {/* Dados Brutos (raw_data_json) - Detalhe técnico apenas para ADMIN */}
        {isAdmin && (
          <div style={{ marginTop: '10px' }}>
            <details style={{ cursor: 'pointer', outline: 'none' }}>
              <summary style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>
                Dados Brutos de Origem (JSON)
              </summary>
              <pre 
                style={{ 
                  marginTop: '10px',
                  backgroundColor: 'rgba(0, 0, 0, 0.3)', 
                  border: '1px solid rgba(255, 255, 255, 0.04)',
                  padding: '12px', 
                  borderRadius: '6px', 
                  fontSize: '11px',
                  color: '#a7f3d0',
                  overflowX: 'auto',
                  maxHeight: '180px',
                  overflowY: 'auto',
                  cursor: 'text'
                }}
              >
                {JSON.stringify(row.raw_data_json, null, 2)}
              </pre>
            </details>
          </div>
        )}

      </div>

      {/* Rodapé - Decisão Administrativa */}
      <div 
        style={{ 
          padding: '20px 24px', 
          borderTop: '1px solid rgba(255, 255, 255, 0.06)',
          backgroundColor: 'rgba(30, 41, 59, 0.5)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}
      >
        <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
          Registrar Decisão de Governança
        </span>

        {/* Caixa de Justificativa */}
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Escreva a justificativa para essa decisão... (Ex: Cadastro válido de fornecedor)"
          style={{
            width: '100%',
            height: '64px',
            backgroundColor: '#0b0f19',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '6px',
            padding: '8px 12px',
            color: '#ffffff',
            fontSize: '12px',
            resize: 'none',
            outline: 'none'
          }}
          disabled={submitting}
        />

        {error && (
          <div style={{ fontSize: '11px', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <AlertCircle size={12} /> {error}
          </div>
        )}

        {/* Botões de Ação */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <button
            onClick={() => handleDecision('ACCEPT')}
            disabled={submitting}
            style={{
              padding: '10px',
              borderRadius: '6px',
              backgroundColor: '#10b981',
              color: '#ffffff',
              border: 'none',
              fontWeight: 600,
              fontSize: '12px',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'background-color 0.15s'
            }}
            className="hover:bg-emerald-600 disabled:opacity-50"
          >
            <CheckCircle2 size={14} /> Aceitar Dados
          </button>
          
          <button
            onClick={() => handleDecision('REJECT')}
            disabled={submitting}
            style={{
              padding: '10px',
              borderRadius: '6px',
              backgroundColor: '#ef4444',
              color: '#ffffff',
              border: 'none',
              fontWeight: 600,
              fontSize: '12px',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'background-color 0.15s'
            }}
            className="hover:bg-red-600 disabled:opacity-50"
          >
            <XCircle size={14} /> Rejeitar
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
          <button
            onClick={() => handleDecision('MERGE')}
            disabled={submitting}
            style={{
              padding: '8px',
              borderRadius: '6px',
              backgroundColor: 'rgba(139, 92, 246, 0.15)',
              color: 'var(--color-primary-light, #a78bfa)',
              border: '1px solid rgba(139, 92, 246, 0.25)',
              fontWeight: 600,
              fontSize: '11px',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
            className="disabled:opacity-50"
          >
            <Merge size={12} /> Mesclar
          </button>
          
          <button
            onClick={() => handleDecision('NEEDS_MORE_INFO')}
            disabled={submitting}
            style={{
              padding: '8px',
              borderRadius: '6px',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              color: 'var(--text-secondary)',
              border: '1px solid rgba(255,255,255,0.06)',
              fontWeight: 600,
              fontSize: '11px',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
            className="disabled:opacity-50"
          >
            <HelpCircle size={12} /> Mais Infos
          </button>
        </div>

        {submitting && (
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'center', marginTop: '4px' }}>
            <RefreshCw size={12} className="spin-anim" /> Registrando governança no servidor...
          </div>
        )}
      </div>
    </div>
  );
};
