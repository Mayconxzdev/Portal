import React, { useState } from 'react';
import { Search, AlertTriangle, Eye, ArrowRight, ArrowLeft, ShieldAlert, Sparkles, FilterX } from 'lucide-react';
import { LegacyImportStatusBadge } from './LegacyImportStatusBadge';

export interface RowItem {
  id: string;
  batch_id: string;
  source_app: string;
  source_table_or_sheet?: string;
  source_row_id?: string;
  module_target: string;
  entity_target: string;
  raw_data_json: Record<string, any>;
  normalized_data_json: Record<string, any>;
  detected_duplicates_json?: Record<string, any>;
  issues_json?: Record<string, any>;
  confidence_score?: number;
  status: string;
  created_at: string;
  reviewed_by_user_id?: number;
  reviewed_at?: string;
}

interface LegacyImportRowTableProps {
  rows: RowItem[];
  onSelectRow: (row: RowItem) => void;
  // Paginação e busca externas ou locais
  onPageChange?: (page: number) => void;
  currentPage?: number;
  totalCount?: number;
}

export const LegacyImportRowTable: React.FC<LegacyImportRowTableProps> = ({
  rows,
  onSelectRow,
}) => {
  // Filtros locais para a lista de linhas
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [entityFilter, setEntityFilter] = useState('ALL');
  const [lowConfidenceFilter, setLowConfidenceFilter] = useState(false);
  const [hasErrorsFilter, setHasErrorsFilter] = useState(false);
  const [duplicateFilter, setDuplicateFilter] = useState(false);

  // Paginação local
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 15;

  // Obter entidades únicas para o filtro
  const uniqueEntities = Array.from(new Set(rows.map(r => r.entity_target)));
  
  // Filtrar as linhas
  const filteredRows = rows.filter((row) => {
    // 1. Busca textual (nome ou campos normalizados principais)
    const displayName = row.normalized_data_json.name || row.normalized_data_json.title || row.normalized_data_json.description || row.normalized_data_json.sku || '';
    const email = row.normalized_data_json.email || '';
    const document = row.normalized_data_json.cnpj || row.normalized_data_json.cpf || '';
    
    const matchesSearch = 
      displayName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      document.toLowerCase().includes(searchTerm.toLowerCase());
      
    // 2. Filtro de Status
    const matchesStatus = statusFilter === 'ALL' || row.status === statusFilter;
    
    // 3. Filtro de Entidade Alvo
    const matchesEntity = entityFilter === 'ALL' || row.entity_target === entityFilter;
    
    // 4. Confiança Baixa (< 70%)
    const matchesConfidence = !lowConfidenceFilter || (row.confidence_score !== undefined && row.confidence_score < 0.7);
    
    // 5. Contém erros/problemas
    const hasErrors = row.issues_json && Object.keys(row.issues_json).length > 0;
    const matchesErrors = !hasErrorsFilter || hasErrors;
    
    // 6. Contém duplicidades detectadas
    const hasDuplicates = row.detected_duplicates_json && Object.keys(row.detected_duplicates_json).length > 0;
    const matchesDuplicates = !duplicateFilter || hasDuplicates;

    return matchesSearch && matchesStatus && matchesEntity && matchesConfidence && matchesErrors && matchesDuplicates;
  });

  // Paginação
  const totalItems = filteredRows.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedRows = filteredRows.slice(startIndex, startIndex + itemsPerPage);

  const handlePageClick = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const resetFilters = () => {
    setSearchTerm('');
    setStatusFilter('ALL');
    setEntityFilter('ALL');
    setLowConfidenceFilter(false);
    setHasErrorsFilter(false);
    setDuplicateFilter(false);
    setCurrentPage(1);
  };

  // Humanizar chaves de dados normalizados para visualização rápida na listagem
  const getQuickDetail = (row: RowItem) => {
    const data = row.normalized_data_json;
    if (row.entity_target === 'SUPPLIER') {
      return data.cnpj ? `CNPJ: ${data.cnpj}` : data.email || 'Sem documento';
    }
    if (row.entity_target === 'PRODUCT_ITEM') {
      return data.sku ? `Codigo: ${data.sku}` : data.category || 'Sem codigo';
    }
    if (row.entity_target === 'PRICE_HISTORY') {
      return `${data.supplier_name || 'Fornecedor'} · R$ ${data.price || '0.00'}`;
    }
    if (row.entity_target === 'IT_TICKET') {
      return `Prioridade: ${data.priority || 'Normal'}`;
    }
    if (row.entity_target === 'IT_ASSET') {
      return data.serial_number ? `S/N: ${data.serial_number}` : data.model || 'Sem serial';
    }
    return data.description || data.notes || '';
  };

  return (
    <div className="legacy-row-table-wrapper" style={{ display: 'grid', gap: '16px' }}>
      {/* Barra de Filtros */}
      <div 
        className="glass-card" 
        style={{ 
          padding: '16px', 
          borderRadius: '12px',
          backgroundColor: 'rgba(30, 41, 59, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {/* Busca */}
          <div style={{ flex: '1 1 240px', position: 'relative' }}>
            <Search 
              size={16} 
              style={{ 
                position: 'absolute', 
                left: '12px', 
                top: '50%', 
                transform: 'translateY(-50%)', 
                color: 'var(--text-muted)' 
              }} 
            />
            <input
              type="text"
              className="search-input"
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1); }}
              placeholder="Buscar por nome, documento ou codigo..."
              style={{ paddingLeft: '36px', width: '100%', height: '38px', borderRadius: '8px', fontSize: '13px' }}
            />
          </div>

          {/* Status */}
          <select
            className="search-input"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1); }}
            style={{ flex: '0 1 150px', height: '38px', borderRadius: '8px', fontSize: '13px' }}
          >
            <option value="ALL">Todos os status</option>
            <option value="PENDING_REVIEW">Em Revisão</option>
            <option value="ACCEPTED">Aceitos</option>
            <option value="REJECTED">Rejeitados</option>
            <option value="DUPLICATE">Duplicados</option>
            <option value="NEEDS_MORE_INFO">Precisa Informação</option>
          </select>

          {/* Entidade Alvo */}
          <select
            className="search-input"
            value={entityFilter}
            onChange={(e) => { setEntityFilter(e.target.value); setCurrentPage(1); }}
            style={{ flex: '0 1 180px', height: '38px', borderRadius: '8px', fontSize: '13px' }}
          >
            <option value="ALL">Todas as entidades</option>
            {uniqueEntities.map((ent) => (
              <option key={ent} value={ent}>
                {ent.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>

        {/* Checkboxes de Status Especiais */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '16px', fontSize: '12px', color: 'var(--text-secondary)' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={lowConfidenceFilter}
              onChange={(e) => { setLowConfidenceFilter(e.target.checked); setCurrentPage(1); }}
              style={{ accentColor: 'var(--color-primary)' }}
            />
            Confiança Baixa (&lt; 70%)
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={hasErrorsFilter}
              onChange={(e) => { setHasErrorsFilter(e.target.checked); setCurrentPage(1); }}
              style={{ accentColor: 'var(--color-danger)' }}
            />
            Com Avisos/Erros
          </label>

          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={duplicateFilter}
              onChange={(e) => { setDuplicateFilter(e.target.checked); setCurrentPage(1); }}
              style={{ accentColor: 'var(--color-warning)' }}
            />
            Duplicados Detectados
          </label>

          {(searchTerm || statusFilter !== 'ALL' || entityFilter !== 'ALL' || lowConfidenceFilter || hasErrorsFilter || duplicateFilter) && (
            <button 
              onClick={resetFilters} 
              style={{ 
                background: 'none', 
                border: 'none', 
                color: 'var(--color-primary-light, #a78bfa)', 
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '12px',
                fontWeight: 600,
                padding: 0
              }}
            >
              <FilterX size={12} /> Limpar Filtros
            </button>
          )}
        </div>
      </div>

      {/* Tabela de Linhas */}
      <div className="glass-card" style={{ padding: 0, borderRadius: '12px', overflow: 'hidden' }}>
        {paginatedRows.length === 0 ? (
          <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <p style={{ margin: 0, fontSize: '14px' }}>Nenhuma linha em staging corresponde aos filtros aplicados.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ backgroundColor: 'rgba(255, 255, 255, 0.02)', borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)' }}>Entidade</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)' }}>Nome / Detalhe Principal</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)' }}>Informações da Origem</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', textAlign: 'center' }}>Confiança</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', textAlign: 'center' }}>Auditoria</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)' }}>Status</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-muted)', textAlign: 'right' }}>Ação</th>
                </tr>
              </thead>
              <tbody>
                {paginatedRows.map((row) => {
                  const displayName = row.normalized_data_json.name || row.normalized_data_json.title || row.normalized_data_json.description || 'Sem nome';
                  const hasIssues = row.issues_json && Object.keys(row.issues_json).length > 0;
                  const hasDuplicates = row.detected_duplicates_json && Object.keys(row.detected_duplicates_json).length > 0;
                  const confidence = row.confidence_score !== undefined ? Math.round(row.confidence_score * 100) : null;
                  
                  return (
                    <tr 
                      key={row.id} 
                      className="table-row-hover"
                      style={{ 
                        borderBottom: '1px solid rgba(255, 255, 255, 0.02)',
                        transition: 'background-color 0.15s ease'
                      }}
                    >
                      <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                        <LegacyImportStatusBadge type="entity" value={row.entity_target} />
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{displayName}</span>
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{getQuickDetail(row)}</span>
                        </div>
                      </td>
                      <td style={{ padding: '14px 16px', color: 'var(--text-secondary)' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', fontSize: '12px' }}>
                          <span>Tabela: <strong style={{ color: 'var(--text-muted)' }}>{row.source_table_or_sheet || 'N/A'}</strong></span>
                          {row.source_row_id && <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>ID Origem: {row.source_row_id}</span>}
                        </div>
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                        {confidence !== null ? (
                          <span 
                            style={{ 
                              fontWeight: 700, 
                              color: confidence >= 90 
                                ? '#10b981' 
                                : confidence >= 70 
                                ? 'var(--color-primary-light, #a78bfa)' 
                                : '#f59e0b',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              justifyContent: 'center'
                            }}
                          >
                            {confidence >= 90 && <Sparkles size={11} />} {confidence}%
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>-</span>
                        )}
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' }}>
                          {hasIssues && (
                            <span title="Problemas de validação de dados detectados" style={{ color: '#ef4444' }}>
                              <AlertTriangle size={15} />
                            </span>
                          )}
                          {hasDuplicates && (
                            <span title="Candidatos a duplicados cadastrados no Master Data" style={{ color: '#f59e0b' }}>
                              <ShieldAlert size={15} />
                            </span>
                          )}
                          {!hasIssues && !hasDuplicates && <span style={{ color: '#10b981', fontSize: '12px' }}>✓ Íntegro</span>}
                        </div>
                      </td>
                      <td style={{ padding: '14px 16px', whiteSpace: 'nowrap' }}>
                        <LegacyImportStatusBadge type="row" value={row.status} />
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        <button
                          onClick={() => onSelectRow(row)}
                          className="btn btn-secondary"
                          style={{
                            padding: '6px 10px',
                            borderRadius: '6px',
                            backgroundColor: 'rgba(255, 255, 255, 0.04)',
                            border: '1px solid rgba(255, 255, 255, 0.05)',
                            color: 'var(--text-primary)',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '11px',
                            transition: 'all 0.15s ease'
                          }}
                        >
                          <Eye size={12} /> Revisar
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Rodapé de Paginação */}
        {totalPages > 1 && (
          <div 
            style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              padding: '12px 16px',
              borderTop: '1px solid rgba(255, 255, 255, 0.04)',
              backgroundColor: 'rgba(0, 0, 0, 0.05)',
              fontSize: '12px',
              color: 'var(--text-secondary)'
            }}
          >
            <span>Exibindo de {startIndex + 1} a {Math.min(startIndex + itemsPerPage, totalItems)} de {totalItems} registros</span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button 
                disabled={currentPage === 1}
                onClick={() => handlePageClick(currentPage - 1)}
                style={{ 
                  background: 'none', 
                  border: '1px solid rgba(255,255,255,0.06)', 
                  borderRadius: '4px', 
                  padding: '4px 8px', 
                  cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                  color: currentPage === 1 ? 'var(--text-muted)' : 'var(--text-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <ArrowLeft size={12} /> Anterior
              </button>
              <span style={{ display: 'inline-flex', alignItems: 'center', padding: '0 8px' }}>
                Página {currentPage} de {totalPages}
              </span>
              <button 
                disabled={currentPage === totalPages}
                onClick={() => handlePageClick(currentPage + 1)}
                style={{ 
                  background: 'none', 
                  border: '1px solid rgba(255,255,255,0.06)', 
                  borderRadius: '4px', 
                  padding: '4px 8px', 
                  cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                  color: currentPage === totalPages ? 'var(--text-muted)' : 'var(--text-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                Próximo <ArrowRight size={12} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
