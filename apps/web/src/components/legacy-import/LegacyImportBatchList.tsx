import React from 'react';
import { Database, FileSpreadsheet, Server, Play, ChevronRight, AlertCircle, CheckCircle, Copy } from 'lucide-react';
import { LegacyImportStatusBadge } from './LegacyImportStatusBadge';

export interface BatchItem {
  id: string;
  source_app: string;
  source_name: string;
  source_path_masked: string;
  module_target: string;
  status: string;
  total_rows: number;
  valid_rows: number;
  duplicate_rows: number;
  error_rows: number;
  created_at: string;
  notes?: string;
}

interface LegacyImportBatchListProps {
  batches: BatchItem[];
  selectedBatchId: string | null;
  onSelectBatch: (batch: BatchItem) => void;
}

const getAppIcon = (app: string) => {
  const normalized = app.toUpperCase();
  if (normalized.includes('XLSX') || normalized.includes('CSV') || normalized.includes('PLANILHA')) {
    return <FileSpreadsheet size={20} className="text-emerald-400" style={{ color: 'var(--color-success)' }} />;
  }
  if (normalized.includes('NAS') || normalized.includes('SERVER')) {
    return <Server size={20} style={{ color: 'var(--color-primary)' }} />;
  }
  return <Database size={20} style={{ color: 'var(--color-secondary)' }} />;
};

const getModuleLabel = (mod: string) => {
  const dict: Record<string, string> = {
    purchases: 'Compras',
    it: 'Tecnologia da Informação',
    production: 'Produção / Kanban',
    projects: 'Projetos',
    proposals: 'Propostas comerciais',
    stock: 'Estoque',
  };
  return dict[mod] || mod.toUpperCase();
};

export const LegacyImportBatchList: React.FC<LegacyImportBatchListProps> = ({
  batches,
  selectedBatchId,
  onSelectBatch,
}) => {
  if (batches.length === 0) {
    return (
      <div className="empty-state-card glass-card" style={{ padding: '40px', textAlign: 'center' }}>
        <Database size={40} style={{ color: 'var(--text-muted)', marginBottom: '16px', opacity: 0.5 }} />
        <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
          Nenhum lote de staging encontrado
        </h3>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', maxWidth: '400px', margin: '0 auto' }}>
          Execute os adaptadores de importação legada via linha de comando ou n8n para popular a área de revisão.
        </p>
      </div>
    );
  }

  return (
    <div className="legacy-batch-list-container" style={{ display: 'grid', gap: '12px' }}>
      {batches.map((batch) => {
        const isSelected = selectedBatchId === batch.id;
        const formattedDate = new Date(batch.created_at).toLocaleString('pt-BR', {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });

        return (
          <div
            key={batch.id}
            onClick={() => onSelectBatch(batch)}
            className={`glass-card batch-list-item ${isSelected ? 'active-item' : ''}`}
            style={{
              padding: '16px 20px',
              cursor: 'pointer',
              border: isSelected 
                ? '1px solid rgba(139, 92, 246, 0.4)' 
                : '1px solid rgba(255, 255, 255, 0.05)',
              background: isSelected 
                ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(139, 92, 246, 0.02))' 
                : 'rgba(30, 41, 59, 0.25)',
              borderRadius: '12px',
              transition: 'all 0.2s ease',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              boxShadow: isSelected ? '0 8px 20px rgba(139, 92, 246, 0.1)' : 'none',
            }}
          >
            {/* Linha superior */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div 
                  style={{ 
                    padding: '8px', 
                    borderRadius: '8px', 
                    backgroundColor: isSelected ? 'rgba(139, 92, 246, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {getAppIcon(batch.source_app)}
                </div>
                <div>
                  <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {batch.source_name}
                  </h4>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Origem: <strong style={{ color: 'var(--text-secondary)' }}>{batch.source_app}</strong> · {formattedDate}
                  </span>
                </div>
              </div>
              <div>
                <LegacyImportStatusBadge type="batch" value={batch.status} />
              </div>
            </div>

            {/* Linha central - Detalhes e Estatísticas */}
            <div 
              style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', 
                gap: '10px',
                backgroundColor: 'rgba(0, 0, 0, 0.12)',
                padding: '10px 14px',
                borderRadius: '8px',
                border: '1px solid rgba(255, 255, 255, 0.02)'
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Destino</span>
                <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-secondary)' }}>
                  {getModuleLabel(batch.module_target)}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Total Linhas</span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {batch.total_rows}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: 'var(--color-success)', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                  <CheckCircle size={10} /> Válidas
                </span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-success-light, #10b981)' }}>
                  {batch.valid_rows}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                  <Copy size={10} /> Duplicados
                </span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)' }}>
                  {batch.duplicate_rows}
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '10px', color: 'var(--color-danger)', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                  <AlertCircle size={10} /> Erros
                </span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-danger-light, #ef4444)' }}>
                  {batch.error_rows}
                </span>
              </div>
            </div>

            {/* Linha inferior - Notas & Ação */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
              <span style={{ color: 'var(--text-muted)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '80%' }}>
                {batch.notes || 'Sem observações adicionais.'}
              </span>
              <span 
                style={{ 
                  color: isSelected ? 'var(--color-primary-light, #a78bfa)' : 'var(--text-muted)', 
                  fontWeight: 600, 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '2px',
                }}
              >
                {isSelected ? 'Lote Aberto' : 'Abrir lote'} <ChevronRight size={14} />
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
