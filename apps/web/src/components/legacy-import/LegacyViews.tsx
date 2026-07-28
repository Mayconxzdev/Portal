import React, { useState, useEffect } from 'react';
import { 
  Archive, Search, RefreshCw, FileText, Kanban, 
  AlertCircle, Clock, User, ExternalLink
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

interface LegacyRecord {
  id: string;
  legacy_row_id: string | null;
  source_app: string;
  entity_target: string;
  title: string;
  status: string | null;
  responsible: string | null;
  record_date: string | null;
  data_json: Record<string, any>;
  created_at: string;
}

interface LegacyFileRecord {
  id: string;
  file_name: string;
  file_path_masked: string;
  file_type: string;
  file_size_bytes: number | null;
  category: string | null;
  suggested_module: string | null;
  created_at: string;
}

interface LegacyViewsProps {
  mode: 'production' | 'projects' | 'proposals';
}

const entityTargetMap: Record<string, string> = {
  production: 'PRODUCTION_OP',
  projects: 'PROJECT_TASK',
  proposals: 'PROPOSAL_DOCUMENT'
};

const entityLabel: Record<string, string> = {
  production: 'OPs de Produção',
  projects: 'Tarefas de Projeto',
  proposals: 'Propostas'
};

const statusColor = (status?: string | null) => {
  if (!status) return 'var(--text-muted)';
  const lower = status.toLowerCase();
  if (lower.includes('conclu') || lower.includes('feito') || lower.includes('done')) return '#10b981';
  if (lower.includes('em andamento') || lower.includes('progress') || lower.includes('execu')) return '#38bdf8';
  if (lower.includes('atras') || lower.includes('overdue') || lower.includes('venci')) return '#f87171';
  if (lower.includes('aguard') || lower.includes('pend')) return '#fbbf24';
  return '#94a3b8';
};

export const LegacyViews: React.FC<LegacyViewsProps> = ({ mode }) => {
  const [records, setRecords] = useState<LegacyRecord[]>([]);
  const [files, setFiles] = useState<LegacyFileRecord[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const entityTarget = entityTargetMap[mode];

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const recRes = await fetch(`/api/v1/legacy-promotion/operational-records?entity_target=${entityTarget}`);
      if (recRes.ok) {
        const data = await recRes.json();
        setRecords(data);
      }

      // Para propostas, buscar também os arquivos indexados
      if (mode === 'proposals') {
        const filesRes = await fetch('/api/v1/legacy-promotion/file-index?suggested_module=proposals');
        if (filesRes.ok) {
          const filesData = await filesRes.json();
          setFiles(filesData);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar dados legados.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [mode]);

  const filteredRecords = records.filter(r => {
    const term = searchTerm.toLowerCase();
    return (
      r.title.toLowerCase().includes(term) ||
      (r.status && r.status.toLowerCase().includes(term)) ||
      (r.responsible && r.responsible.toLowerCase().includes(term))
    );
  });

  const filteredFiles = files.filter(f => {
    const term = searchTerm.toLowerCase();
    return (
      f.file_name.toLowerCase().includes(term) ||
      (f.category && f.category.toLowerCase().includes(term))
    );
  });

  const label = entityLabel[mode];

  if (loading && records.length === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
        <RefreshCw size={24} className="spin-anim" />
        <span>Carregando dados legados de {label.toLowerCase()}...</span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Banner de Contexto */}
      <div style={{ 
        padding: '12px 16px', 
        backgroundColor: 'rgba(139, 92, 246, 0.06)', 
        border: '1px solid rgba(139, 92, 246, 0.15)', 
        borderRadius: '10px',
        display: 'flex', alignItems: 'center', gap: '10px'
      }}>
        <Archive size={18} style={{ color: '#a78bfa', flexShrink: 0 }} />
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
          <strong style={{ color: 'var(--text-primary)', display: 'block' }}>Aba Legado — Dados históricos somente leitura</strong>
          Estes registros foram importados dos sistemas legados e estão disponíveis para consulta. 
          Eles não afetam o módulo oficial. Módulo real de {label.toLowerCase()} será construído futuramente.
        </div>
      </div>

      {/* Barra de Pesquisa e Atualização */}
      <div style={{ display: 'flex', gap: '10px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <span style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', pointerEvents: 'none' }}>
            <Search size={14} />
          </span>
          <input
            type="text"
            placeholder={`Pesquisar em ${label.toLowerCase()}...`}
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 10px 8px 32px',
              backgroundColor: 'rgba(0,0,0,0.2)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              fontSize: '13px',
              outline: 'none'
            }}
          />
        </div>
        <Button variant="secondary" size="sm" onClick={fetchData} leftIcon={<RefreshCw size={14} />}>
          Atualizar
        </Button>
      </div>

      {error && (
        <div style={{ padding: '10px 14px', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '8px', color: '#ef4444', fontSize: '12px', display: 'flex', gap: '8px', alignItems: 'center' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Lista de Registros Operacionais */}
      {filteredRecords.length === 0 && filteredFiles.length === 0 && !loading ? (
        <div style={{ textAlign: 'center', padding: '50px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          {mode === 'production' ? <Kanban size={40} /> : <FileText size={40} />}
          <div>
            <strong style={{ color: 'var(--text-secondary)', display: 'block' }}>Nenhum registro legado encontrado</strong>
            <span style={{ fontSize: '12px' }}>
              {searchTerm ? 'Tente um termo diferente.' : 'Execute a importação legada primeiro para popular esta visão.'}
            </span>
          </div>
        </div>
      ) : (
        <>
          {filteredRecords.length > 0 && (
            <div>
              <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                {label} ({filteredRecords.length})
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {filteredRecords.map(r => (
                  <Card key={r.id} style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                      <div style={{ flex: 1 }}>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>{r.source_app}</span>
                        <strong style={{ display: 'block', fontSize: '13px', color: 'var(--text-primary)', marginTop: '2px' }}>{r.title}</strong>
                      </div>
                      {r.status && (
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: '12px',
                          fontSize: '10px',
                          fontWeight: 'bold',
                          backgroundColor: 'rgba(0,0,0,0.2)',
                          border: `1px solid ${statusColor(r.status)}30`,
                          color: statusColor(r.status),
                          whiteSpace: 'nowrap',
                          flexShrink: 0
                        }}>
                          {r.status}
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '11px', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
                      {r.responsible && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <User size={11} />
                          {r.responsible}
                        </span>
                      )}
                      {r.record_date && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Clock size={11} />
                          {new Date(r.record_date).toLocaleDateString('pt-BR')}
                        </span>
                      )}
                      <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Archive size={11} />
                        Importado em {new Date(r.created_at).toLocaleDateString('pt-BR')}
                      </span>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Arquivos Indexados (apenas para propostas) */}
          {mode === 'proposals' && filteredFiles.length > 0 && (
            <div>
              <h4 style={{ margin: '16px 0 10px 0', fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Templates e Arquivos Indexados ({filteredFiles.length})
              </h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '8px' }}>
                {filteredFiles.map(f => (
                  <Card key={f.id} style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Badge variant="neutral" style={{ fontSize: '9px' }}>{f.file_type}</Badge>
                      {f.category && (
                        <span style={{ fontSize: '9px', color: 'var(--text-muted)' }}>{f.category}</span>
                      )}
                    </div>
                    <strong style={{ fontSize: '12px', color: 'var(--text-primary)', marginTop: '4px', wordBreak: 'break-word' }}>
                      {f.file_name}
                    </strong>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {f.file_size_bytes ? `${Math.round(f.file_size_bytes / 1024)} KB` : 'Tamanho desconhecido'}
                    </span>
                    <code style={{ fontSize: '9px', color: '#64748b', backgroundColor: 'rgba(0,0,0,0.2)', padding: '3px 6px', borderRadius: '4px', wordBreak: 'break-all', marginTop: '4px' }}>
                      {f.file_path_masked}
                    </code>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default LegacyViews;
