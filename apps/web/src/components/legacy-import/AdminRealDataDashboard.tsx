import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, RefreshCw, Download, Search, CheckCircle, 
  Users, ShoppingBag, DollarSign, Database, FileText, Lock, FileSpreadsheet, Sparkles, AlertCircle
} from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { MetricCard } from '../ui/MetricCard';

interface DashboardData {
  suppliers_count: number;
  customers_count: number;
  products_count: number;
  services_count: number;
  price_history_count: number;
  it_access_count: number;
  legacy_ops_count: number;
  legacy_projects_count: number;
  legacy_proposals_count: number;
  legacy_files_count: number;
  pending_review_count: number;
  blocked_duplicates_count: number;
}

interface AccessRecord {
  id: number;
  legacy_user_name: string | null;
  system_name: string;
  access_profile: string | null;
  status: string;
  origin: string;
  has_secret: boolean;
  last_updated_at: string;
  user_name: string;
  user_email: string;
}

interface AdminRealDataDashboardProps {
  onBack: () => void;
}

export const AdminRealDataDashboard: React.FC<AdminRealDataDashboardProps> = ({ onBack }) => {
  const [stats, setStats] = useState<DashboardData | null>(null);
  const [accessRecords, setAccessRecords] = useState<AccessRecord[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSystem, setSelectedSystem] = useState('Todos');
  const [exportingNetwork, setExportingNetwork] = useState(false);
  
  const [loadingStats, setLoadingStats] = useState(false);
  const [loadingAccess, setLoadingAccess] = useState(false);
  const [syncingAccess, setSyncingAccess] = useState(false);
  const [syncResult, setSyncResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const res = await fetch('/api/v1/legacy-promotion/real-data-dashboard');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      } else {
        throw new Error('Falha ao obter métricas de ativação');
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar dados do dashboard.');
    } finally {
      setLoadingStats(false);
    }
  };

  const fetchAccessRecords = async () => {
    setLoadingAccess(true);
    try {
      const res = await fetch('/api/v1/legacy-promotion/access-matrix');
      if (res.ok) {
        const data = await res.json();
        setAccessRecords(data);
      } else {
        throw new Error('Falha ao buscar registros da Matriz de Acessos');
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao carregar matriz de acessos.');
    } finally {
      setLoadingAccess(false);
    }
  };

  const handleSyncPortalAccess = async () => {
    setSyncingAccess(true);
    setError(null);
    setSyncResult(null);
    try {
      const res = await fetch('/api/v1/legacy-promotion/sync-portal-access', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setSyncResult(data);
        setSuccess(`Sincronização concluída! ${data.users_synced} usuários mapeados.`);
        fetchStats();
        fetchAccessRecords();
      } else {
        throw new Error('Falha na sincronização com os acessos internos');
      }
    } catch (err: any) {
      setError(err.message || 'Erro durante a sincronização.');
    } finally {
      setSyncingAccess(false);
    }
  };

  const handleExportCSV = () => {
    window.open('/api/v1/legacy-promotion/export-access-matrix', '_blank');
  };

  const handleExportToNetwork = async () => {
    setExportingNetwork(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await fetch('/api/v1/legacy-promotion/export-to-network', {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setSuccess(data.message || 'Matriz de Acessos exportada para K:\\Maycon\\Portal-Vesper-Dados com sucesso!');
      } else {
        throw new Error('Falha ao exportar para o diretório configurado.');
      }
    } catch (err: any) {
      setError(err.message || 'Erro ao exportar para a rede.');
    } finally {
      setExportingNetwork(false);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchAccessRecords();
  }, []);

  const filteredAccess = accessRecords.filter(r => {
    if (selectedSystem !== 'Todos') {
      const matchName = selectedSystem.toLowerCase().replace(/\s+/g, '');
      const sysName = r.system_name.toLowerCase().replace(/\s+/g, '');
      if (sysName !== matchName) {
        return false;
      }
    }
    const term = searchTerm.toLowerCase();
    return (
      r.user_name.toLowerCase().includes(term) ||
      r.user_email.toLowerCase().includes(term) ||
      r.system_name.toLowerCase().includes(term) ||
      (r.access_profile && r.access_profile.toLowerCase().includes(term)) ||
      r.origin.toLowerCase().includes(term)
    );
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left' }}>
      
      {/* Mensagens de Feedback */}
      {error && (
        <div style={{ padding: '12px 16px', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '8px', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div style={{ padding: '12px 16px', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: '8px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
          <CheckCircle size={18} />
          <span>{success}</span>
        </div>
      )}

      {/* Cards de Métricas */}
      <div>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: 600, color: 'var(--text-secondary)' }}>
          Dados Reais Ativados na Base Oficial
        </h3>
        {loadingStats && !stats ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>Carregando dados...</div>
        ) : (
          <div className="metric-grid">
            <MetricCard 
              icon={<Users size={22} />} 
              label="Fornecedores Criados" 
              value={stats?.suppliers_count || 0} 
              iconColor="emerald" 
            />
            <MetricCard 
              icon={<Users size={22} />} 
              label="Clientes Criados" 
              value={stats?.customers_count || 0} 
              iconColor="emerald" 
            />
            <MetricCard 
              icon={<ShoppingBag size={22} />} 
              label="Itens oficiais" 
              value={stats?.products_count || 0} 
              iconColor="cyan" 
            />
            <MetricCard 
              icon={<DollarSign size={22} />} 
              label="Preços Históricos" 
              value={stats?.price_history_count || 0} 
              iconColor="amber" 
            />
            <MetricCard 
              icon={<Lock size={22} />} 
              label="Contas/Acessos TI" 
              value={stats?.it_access_count || 0} 
              iconColor="violet" 
            />
            <MetricCard 
              icon={<Database size={22} />} 
              label="Arquivos Indexados" 
              value={stats?.legacy_files_count || 0} 
              iconColor="violet" 
            />
          </div>
        )}
      </div>

      {/* Cards de Visão Legada Operacional */}
      <div>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '15px', fontWeight: 600, color: 'var(--text-secondary)' }}>
          Registros Operacionais Legados Consultáveis (Aba Legado)
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
          <Card style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Produção (OPs)</span>
            <strong style={{ fontSize: '24px', color: 'var(--text-primary)' }}>{stats?.legacy_ops_count || 0}</strong>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Ordens de produção importadas do legado.</span>
          </Card>
          <Card style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Projetos / Tarefas</span>
            <strong style={{ fontSize: '24px', color: 'var(--text-primary)' }}>{stats?.legacy_projects_count || 0}</strong>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Tarefas e prazos consolidados.</span>
          </Card>
          <Card style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Propostas &amp; Templates</span>
            <strong style={{ fontSize: '24px', color: 'var(--text-primary)' }}>{stats?.legacy_proposals_count || 0}</strong>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Propostas e metadados de modelos indexados.</span>
          </Card>
        </div>
      </div>

      {/* Governança e Matriz de Acessos */}
      <Card style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
              👥 Matriz de Acessos e softwares de TI (ISO 9001)
            </h4>
            <p style={{ margin: '4px 0 0 0', fontSize: '11px', color: 'var(--text-muted)' }}>
              Visualização consolidada de perfis e acessos ativos dos colaboradores de todas as ferramentas.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <Button 
              variant="secondary" 
              size="sm" 
              onClick={handleSyncPortalAccess} 
              disabled={syncingAccess}
              leftIcon={<RefreshCw size={14} className={syncingAccess ? 'spin-anim' : ''} />}
            >
              {syncingAccess ? 'Sincronizando...' : 'Sincronizar Acessos do Portal'}
            </Button>
            <Button 
              variant="primary" 
              size="sm" 
              onClick={handleExportCSV}
              leftIcon={<Download size={14} />}
            >
              Exportar Matriz (CSV)
            </Button>
            <Button 
              variant="primary" 
              size="sm" 
              onClick={handleExportToNetwork}
              disabled={exportingNetwork}
              leftIcon={<FileSpreadsheet size={14} />}
              style={{ backgroundColor: '#10b981', borderColor: '#10b981' }}
            >
              {exportingNetwork ? 'Salvando...' : 'Salvar na Rede (K:)'}
            </Button>
          </div>
        </div>

        {/* Barra de Pesquisa */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <span style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>
              <Search size={16} />
            </span>
            <input
              type="text"
              placeholder="Pesquisar por colaborador, e-mail, sistema ou perfil..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px 8px 36px',
                backgroundColor: 'rgba(0, 0, 0, 0.2)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '8px',
                color: 'var(--text-primary)',
                fontSize: '13px',
                outline: 'none'
              }}
            />
          </div>
        </div>

        {/* Filtros por Sistema */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 600 }}>Filtrar por Sistema:</span>
          {['Todos', 'Portal', 'Kanban', 'Help Desk', 'Abacus'].map((system) => {
            const isActive = selectedSystem.toLowerCase() === system.toLowerCase();
            return (
              <button
                key={system}
                onClick={() => setSelectedSystem(system)}
                style={{
                  padding: '4px 12px',
                  borderRadius: '16px',
                  border: isActive ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.08)',
                  backgroundColor: isActive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(0, 0, 0, 0.2)',
                  color: isActive ? '#10b981' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: isActive ? 'bold' : 'normal',
                  transition: 'all 0.2s ease-in-out',
                }}
              >
                {system}
              </button>
            );
          })}
        </div>

        {/* Tabela de Acessos */}
        <div style={{ overflowX: 'auto', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px' }}>
          {loadingAccess && accessRecords.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <RefreshCw size={24} className="spin-anim" style={{ margin: '0 auto 10px auto' }} />
              <span>Carregando matriz de acessos...</span>
            </div>
          ) : filteredAccess.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
              Nenhum acesso encontrado.
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
              <thead>
                <tr style={{ backgroundColor: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.06)', textAlign: 'left' }}>
                  <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Colaborador</th>
                  <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>E-mail</th>
                  <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Sistema / Módulo</th>
                  <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Perfil de Acesso</th>
                  <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Origem</th>
                  <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Credencial Protegida</th>
                  <th style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredAccess.map(r => (
                  <tr key={r.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                    <td style={{ padding: '10px 12px', color: 'var(--text-primary)', fontWeight: 'bold' }}>{r.user_name}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{r.user_email || '—'}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>{r.system_name}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-primary)' }}>
                      <code style={{ backgroundColor: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: '4px' }}>
                        {r.access_profile || 'USER'}
                      </code>
                    </td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{r.origin}</td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ color: r.has_secret ? '#a78bfa' : 'var(--text-muted)', fontWeight: r.has_secret ? 'bold' : 'normal' }}>
                        {r.has_secret ? '🔒 Sim (Oculta)' : 'Não'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '10px',
                        fontWeight: 'bold',
                        backgroundColor: r.status === 'ACTIVE' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        color: r.status === 'ACTIVE' ? '#10b981' : '#ef4444'
                      }}>
                        {r.status === 'ACTIVE' ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
};
