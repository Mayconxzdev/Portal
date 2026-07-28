import React, { useState, useEffect } from 'react';
import { 
  Database, RefreshCw, AlertTriangle, ArrowLeft, ShieldAlert, Sparkles, CheckCircle2, XCircle, Info, Archive, HelpCircle
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { MetricCard } from '../components/ui/MetricCard';
import { ModuleHero } from '../components/ui/ModuleHero';
import { ModulePageLayout } from '../components/layout/ModulePageLayout';
import { HelpCard } from '../components/layout/HelpCard';
import { LegacyImportBatchList, BatchItem } from '../components/legacy-import/LegacyImportBatchList';
import { LegacyImportRowTable, RowItem } from '../components/legacy-import/LegacyImportRowTable';
import { LegacyImportRowDrawer } from '../components/legacy-import/LegacyImportRowDrawer';

interface LegacyImportPageProps {
  currentUser: {
    role: string;
    username: string;
  };
  onBack: () => void;
}

interface SummaryData {
  total_batches: number;
  total_rows: number;
  status_counts: Record<string, number>;
  module_counts: Record<string, number>;
}

export const LegacyImportPage: React.FC<LegacyImportPageProps> = ({ currentUser, onBack }) => {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [batches, setBatches] = useState<BatchItem[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<BatchItem | null>(null);
  const [rows, setRows] = useState<RowItem[]>([]);
  const [selectedRow, setSelectedRow] = useState<RowItem | null>(null);
  
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingBatches, setLoadingBatches] = useState(false);
  const [loadingRows, setLoadingRows] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Carregar sumário e lotes na montagem
  const loadInitialData = async () => {
    setLoadingSummary(true);
    setLoadingBatches(true);
    setError(null);
    try {
      // 1. Carrega resumo estatístico
      const summaryRes = await fetch('/api/v1/legacy-import/summary');
      if (summaryRes.ok) {
        const summaryData = await summaryRes.json();
        setSummary(summaryData);
      } else {
        throw new Error('Falha ao obter resumo das importações');
      }

      // 2. Carrega lista de lotes
      const batchesRes = await fetch('/api/v1/legacy-import/batches');
      if (batchesRes.ok) {
        const batchesData = await batchesRes.json();
        setBatches(batchesData);
      } else {
        throw new Error('Falha ao obter lotes de staging');
      }
    } catch (err: any) {
      setError(err.message || 'Erro de rede ao buscar dados do staging legado.');
    } finally {
      setLoadingSummary(false);
      setLoadingBatches(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  // Carregar linhas quando um lote for selecionado
  const handleSelectBatch = async (batch: BatchItem) => {
    setSelectedBatch(batch);
    setSelectedRow(null);
    setLoadingRows(true);
    setError(null);
    try {
      const rowsRes = await fetch(`/api/v1/legacy-import/batches/${batch.id}/rows?limit=500`);
      if (rowsRes.ok) {
        const rowsData = await rowsRes.json();
        setRows(rowsData);
      } else {
        throw new Error(`Falha ao obter linhas do lote ${batch.source_name}`);
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar linhas do lote selecionado.');
    } finally {
      setLoadingRows(false);
    }
  };

  // Enviar decisão administrativa de governança
  const handleDecisionSubmit = async (rowId: string, decision: string, reason: string) => {
    const res = await fetch(`/api/v1/legacy-import/rows/${rowId}/decision`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        decision,
        reason,
      }),
    });

    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Falha ao registrar decisão.');
    }

    // Recarregar os dados do lote atual e do sumário para refletir a decisão
    if (selectedBatch) {
      handleSelectBatch(selectedBatch);
    }
    
    // Atualiza o sumário global
    const summaryRes = await fetch('/api/v1/legacy-import/summary');
    if (summaryRes.ok) {
      const summaryData = await summaryRes.json();
      setSummary(summaryData);
    }
  };

  // Contadores derivados do status_counts
  const pendingReviewCount = summary 
    ? (summary.status_counts.PENDING_REVIEW || 0) + (summary.status_counts.DUPLICATE_CANDIDATE || 0) 
    : 0;
  const readyToImportCount = summary ? (summary.status_counts.READY || 0) : 0;
  const duplicateCandidatesCount = summary ? (summary.status_counts.DUPLICATE_CANDIDATE || 0) : 0;
  const rejectedCount = summary ? (summary.status_counts.REJECTED || 0) : 0;

  const asideContent = (
    <>
      <section className="module-side-card glass-card">
        <h3 className="module-side-title">Relação com UAL</h3>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5', margin: '0 0 10px 0' }}>
          Estes dados do staging legado ajudam a Camada Universal de Ações (UAL) e a barra global a sugerirem fornecedores, itens e históricos antigos aos usuários antes do cadastro oficial.
        </p>
        <div style={{ padding: '8px 12px', borderRadius: '6px', backgroundColor: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255, 255, 255, 0.04)', fontSize: '11px', color: 'var(--text-muted)' }}>
          🔍 O Portal pesquisa registros em staging e alerta: <em>"Encontramos itens similares nas tabelas legadas. Solicite sua importação."</em>
        </div>
      </section>

      <HelpCard
        description="A promoção e fusão oficial dos dados de staging para as tabelas principais (Master Data, Compras) será realizada em um pacote futuro após conclusão das auditorias."
        actionLabel="Voltar para Dashboard"
        onAction={onBack}
      />
    </>
  );

  return (
    <ModulePageLayout className="legacy-import-page" aside={asideContent}>
      {/* Banner de aviso e segurança */}
      <div 
        style={{ 
          margin: '0 0 20px 0', 
          padding: '12px 18px', 
          backgroundColor: 'rgba(139, 92, 246, 0.06)', 
          border: '1px solid rgba(139, 92, 246, 0.15)',
          borderRadius: '12px',
          display: 'flex',
          gap: '12px',
          alignItems: 'center'
        }}
      >
        <div style={{ backgroundColor: 'rgba(139, 92, 246, 0.12)', padding: '8px', borderRadius: '50%' }}>
          <Sparkles size={20} style={{ color: 'var(--color-primary-light, #a78bfa)' }} />
        </div>
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
          <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '2px' }}>
            Ambiente Isolado de Staging Legado
          </strong>
          Esta tela é uma área exclusiva de revisão humana. Ela <strong>não</strong> importa dados diretamente para as tabelas oficiais do Portal Vesper nesta fase de desenvolvimento, servindo para higienização e governança.
        </div>
      </div>

      <ModuleHero
        accent="violet"
        icon={<Database size={28} style={{ color: '#818cf8' }} />}
        title="Importação Legada"
        description="Revisão administrativa e governança de dados legados higienizados para promoção futura."
        kodaMessage="Estou monitorando as duplicidades por CPF/CNPJ e SKU. Revise cada colisão para garantir a saúde cadastral!"
        actions={
          <div style={{ display: 'flex', gap: '8px' }}>
            <Button
              variant="secondary"
              leftIcon={<ArrowLeft size={16} />}
              onClick={onBack}
            >
              Voltar
            </Button>
            <Button
              variant="secondary"
              leftIcon={<RefreshCw size={16} className={loadingSummary || loadingBatches ? 'spin-anim' : ''} />}
              onClick={loadInitialData}
              disabled={loadingSummary || loadingBatches}
            >
              Atualizar
            </Button>
          </div>
        }
      />

      {/* Cards de Métricas */}
      <div className="metric-grid" style={{ marginBottom: '24px' }}>
        <MetricCard 
          icon={<Database size={22} />} 
          label="Lotes de Origem" 
          value={summary?.total_batches || 0} 
          iconColor="violet" 
        />
        <MetricCard 
          icon={<Info size={22} />} 
          label="Linhas em Revisão" 
          value={pendingReviewCount} 
          iconColor="amber" 
        />
        <MetricCard 
          icon={<CheckCircle2 size={22} />} 
          label="Prontos para Importar" 
          value={readyToImportCount} 
          iconColor="emerald" 
        />
        <MetricCard 
          icon={<ShieldAlert size={22} />} 
          label="Duplicidades" 
          value={duplicateCandidatesCount} 
          iconColor="violet" 
        />
      </div>

      {/* Alerta de erro da API se houver */}
      {error && (
        <div 
          style={{ 
            backgroundColor: 'rgba(239, 68, 68, 0.1)', 
            border: '1px solid rgba(239, 68, 68, 0.2)', 
            borderRadius: '8px', 
            padding: '12px 16px', 
            color: '#ef4444', 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            marginBottom: '20px',
            fontSize: '13px'
          }}
        >
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Seção de Ações de Promoção Assistida */}
      {currentUser.role === 'ADMIN' && (
        <div style={{ marginBottom: '24px' }}>
          <div style={{
            padding: '16px 20px',
            backgroundColor: 'rgba(16, 185, 129, 0.04)',
            border: '1px solid rgba(16, 185, 129, 0.15)',
            borderRadius: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ backgroundColor: 'rgba(16, 185, 129, 0.12)', padding: '6px', borderRadius: '50%' }}>
                  <CheckCircle2 size={16} style={{ color: '#10b981' }} />
                </div>
                <div>
                  <strong style={{ fontSize: '13px', color: 'var(--text-primary)', display: 'block' }}>
                    Promoção Assistida — Dados Validados
                  </strong>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Promova registros auditados (status READY) para as tabelas oficiais do Portal. Ação irreversível sem backup.
                  </span>
                </div>
              </div>
              <span style={{ padding: '3px 10px', backgroundColor: 'rgba(16, 185, 129, 0.12)', borderRadius: '20px', fontSize: '10px', fontWeight: 700, color: '#10b981', whiteSpace: 'nowrap' }}>
                {readyToImportCount} prontos
              </span>
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<CheckCircle2 size={13} />}
                disabled={readyToImportCount === 0}
                onClick={async () => {
                  if (!confirm(`Promover ${readyToImportCount} registros READY para o módulo Master Data? Esta ação é registrada em auditoria.`)) return;
                  try {
                    const res = await fetch('/api/v1/legacy-promotion/promote-batch', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ module: 'MASTER_DATA' })
                    });
                    const data = await res.json();
                    if (res.ok) {
                      alert(`✅ ${data.promoted_count || 0} registros promovidos com sucesso.`);
                      loadInitialData();
                    } else {
                      alert(`Erro: ${data.detail || 'Falha na promoção.'}`);
                    }
                  } catch (e: any) {
                    alert('Erro de rede ao promover.');
                  }
                }}
                style={{ borderColor: 'rgba(16, 185, 129, 0.3)', color: '#10b981' }}
              >
                Promover Fornecedores / Itens (Master Data)
              </Button>

              <Button
                variant="secondary"
                size="sm"
                leftIcon={<Archive size={13} />}
                onClick={async () => {
                  try {
                    const res = await fetch('/api/v1/legacy-promotion/sync-portal-access', {
                      method: 'POST',
                    });
                    const data = await res.json();
                    if (res.ok) {
                      alert(`✅ Matriz de acessos sincronizada: ${data.synced_count || 0} registros.`);
                    } else {
                      alert(`Erro: ${data.detail || 'Falha na sincronização.'}`);
                    }
                  } catch (e: any) {
                    alert('Erro de rede ao sincronizar acessos.');
                  }
                }}
              >
                Sincronizar Acessos de TI
              </Button>

              <Button
                variant="secondary"
                size="sm"
                leftIcon={<Database size={13} />}
                onClick={() => window.open('/api/v1/legacy-promotion/export-access-matrix-csv', '_blank')}
              >
                Exportar Matriz CSV
              </Button>
            </div>
          </div>
        </div>
      )}



      {/* Layout Principal Dividido */}
      <div 
        style={{ 
          display: 'grid', 
          gridTemplateColumns: selectedBatch ? '1fr 2fr' : '1fr', 
          gap: '20px',
          alignItems: 'start'
        }}
      >
        
        {/* Esquerda: Seletor de Lotes */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Database size={15} /> Lotes de Staging
          </h3>
          
          {loadingBatches ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
              <RefreshCw size={24} className="spin-anim" style={{ margin: '0 auto 10px auto' }} />
              <span>Carregando lotes de staging...</span>
            </div>
          ) : (
            <LegacyImportBatchList
              batches={batches}
              selectedBatchId={selectedBatch?.id || null}
              onSelectBatch={handleSelectBatch}
            />
          )}
        </div>

        {/* Direita: Linhas do Lote Selecionado */}
        {selectedBatch && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Linhas do Lote: <strong style={{ color: 'var(--text-primary)' }}>{selectedBatch.source_name}</strong>
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Caminho: <code style={{ color: 'var(--text-secondary)', backgroundColor: 'rgba(0,0,0,0.2)', padding: '2px 6px', borderRadius: '4px' }}>{selectedBatch.source_path_masked}</code>
              </span>
            </div>

            {loadingRows ? (
              <div className="glass-card" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <RefreshCw size={28} className="spin-anim" style={{ margin: '0 auto 12px auto' }} />
                <span>Carregando linhas do lote para auditoria...</span>
              </div>
            ) : (
              <LegacyImportRowTable
                rows={rows}
                onSelectRow={setSelectedRow}
              />
            )}
          </div>
        )}
      </div>

      {/* Drawer Lateral de Detalhes da Linha */}
      <LegacyImportRowDrawer
        row={selectedRow}
        onClose={() => setSelectedRow(null)}
        currentUser={currentUser}
        onDecisionSubmit={handleDecisionSubmit}
      />
    </ModulePageLayout>
  );
};

export default LegacyImportPage;
