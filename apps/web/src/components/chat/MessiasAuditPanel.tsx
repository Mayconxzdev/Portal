import React, { useState, useEffect } from 'react';
import { Eye, ShieldAlert, X, Search, UserCheck } from 'lucide-react';

interface AuditLog {
  id: number;
  messias_username: string;
  action: string;
  target_username: string | null;
  conversation_id: number | null;
  message_id: number | null;
  metadata: any;
  created_at: string;
}

interface UserSearchItem {
  id: number;
  username: string;
  email: string;
  role_name: string;
}

interface MessiasAuditPanelProps {
  onClose: () => void;
  onStartSimulation: (targetUserId: number, targetUsername: string) => void;
  activeSimulationUser: string | null;
  onStopSimulation: () => void;
}

export const MessiasAuditPanel: React.FC<MessiasAuditPanelProps> = ({
  onClose,
  onStartSimulation,
  activeSimulationUser,
  onStopSimulation,
}) => {
  const [activeTab, setActiveTab] = useState<'logs' | 'simulate'>('logs');
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  
  const [userQuery, setUserQuery] = useState('');
  const [users, setUsers] = useState<UserSearchItem[]>([]);
  const [searchingUsers, setSearchingUsers] = useState(false);

  // Carrega logs de auditoria
  const fetchLogs = async () => {
    setLoadingLogs(true);
    try {
      const res = await fetch('/api/v1/chat/messias/audit');
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
      }
    } catch (err) {
      console.error('Erro ao buscar logs MESSIAS:', err);
    } finally {
      setLoadingLogs(false);
    }
  };

  // Busca usuários para simulação
  const searchUsers = async (query: string) => {
    setSearchingUsers(true);
    try {
      const res = await fetch(`/api/v1/chat/users/search?q=${encodeURIComponent(query)}`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data);
      }
    } catch (err) {
      console.error('Erro ao buscar usuários:', err);
    } finally {
      setSearchingUsers(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs();
    } else {
      searchUsers(userQuery);
    }
  }, [activeTab]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setUserQuery(val);
    searchUsers(val);
  };

  const formatAction = (action: string) => {
    const map: Record<string, string> = {
      'chat.messias.audit.opened': 'Abriu o painel de auditoria',
      'chat.messias.message_deleted_viewed': 'Visualizou mensagem apagada',
      'chat.messias.message_edit_history_viewed': 'Visualizou histórico de edições',
      'chat.messias.ephemeral_message_viewed': 'Visualizou mensagem temporária',
      'chat.messias.dm_viewed': 'Visualizou DM privada',
      'chat.messias.group_viewed': 'Visualizou grupo privado',
      'chat.messias.channel_viewed': 'Visualizou canal privado',
      'chat.messias.export_created': 'Exportou relatório',
      'chat.messias.view_as_user.started': 'Iniciou simulação de usuário',
      'chat.messias.view_as_user.ended': 'Finalizou simulação de usuário',
    };
    return map[action] || action;
  };

  return (
    <div style={styles.drawer}>
      <div style={styles.header}>
        <div style={styles.headerTitle}>
          <ShieldAlert size={18} style={styles.shieldIcon} />
          <span>Painel MESSIAS</span>
        </div>
        <button onClick={onClose} style={styles.closeBtn}>
          <X size={18} />
        </button>
      </div>

      {/* Abas */}
      <div style={styles.tabs}>
        <button
          onClick={() => setActiveTab('logs')}
          style={{
            ...styles.tabBtn,
            ...(activeTab === 'logs' ? styles.tabBtnActive : {}),
          }}
        >
          Logs de Auditoria
        </button>
        <button
          onClick={() => setActiveTab('simulate')}
          style={{
            ...styles.tabBtn,
            ...(activeTab === 'simulate' ? styles.tabBtnActive : {}),
          }}
        >
          Simular Usuário
        </button>
      </div>

      <div style={styles.content}>
        {activeTab === 'logs' && (
          <div style={styles.logsContainer}>
            <button onClick={fetchLogs} style={styles.refreshBtn}>
              Atualizar Logs
            </button>
            {loadingLogs ? (
              <div style={styles.loading}>Carregando logs de auditoria...</div>
            ) : logs.length === 0 ? (
              <div style={styles.empty}>Nenhum log registrado.</div>
            ) : (
              <div style={styles.logList}>
                {logs.map((log) => (
                  <div key={log.id} style={styles.logItem}>
                    <div style={styles.logMeta}>
                      <span style={styles.logUser}>{log.messias_username}</span>
                      <span style={styles.logDate}>
                        {new Date(log.created_at).toLocaleString('pt-BR')}
                      </span>
                    </div>
                    <div style={styles.logAction}>{formatAction(log.action)}</div>
                    {log.target_username && (
                      <div style={styles.logTarget}>
                        Alvo: <strong>{log.target_username}</strong>
                      </div>
                    )}
                    {log.metadata && Object.keys(log.metadata).length > 0 && (
                      <pre style={styles.logMetadata}>
                        {JSON.stringify(log.metadata, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'simulate' && (
          <div style={styles.simulateContainer}>
            {activeSimulationUser ? (
              <div style={styles.activeSimBox}>
                <div style={styles.simStatus}>
                  <UserCheck size={18} style={styles.simIcon} />
                  <span>
                    Simulação ativa: <strong>{activeSimulationUser}</strong>
                  </span>
                </div>
                <button onClick={onStopSimulation} style={styles.stopSimBtn}>
                  Parar Simulação
                </button>
              </div>
            ) : (
              <div style={styles.searchWrapper}>
                <div style={styles.searchBar}>
                  <Search size={16} style={styles.searchIcon} />
                  <input
                    type="text"
                    placeholder="Buscar usuário para simular..."
                    value={userQuery}
                    onChange={handleSearchChange}
                    style={styles.searchInput}
                  />
                </div>
                
                {searchingUsers ? (
                  <div style={styles.loading}>Buscando usuários...</div>
                ) : users.length === 0 ? (
                  <div style={styles.empty}>Nenhum usuário encontrado.</div>
                ) : (
                  <div style={styles.userList}>
                    {users.map((u) => (
                      <div key={u.id} style={styles.userItem}>
                        <div style={styles.userInfo}>
                          <span style={styles.userName}>{u.username}</span>
                          <span style={styles.userEmail}>{u.email}</span>
                        </div>
                        <button
                          onClick={() => onStartSimulation(u.id, u.username)}
                          style={styles.simulateBtn}
                        >
                          <Eye size={14} style={{ marginRight: '4px' }} />
                          Simular
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  drawer: {
    display: 'flex',
    flexDirection: 'column',
    width: '100%',
    height: '100%',
    backgroundColor: '#0f172a', // slate-900
    borderLeft: '1px solid rgba(255, 255, 255, 0.05)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    padding: '16px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
    justifyContent: 'space-between',
  },
  headerTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '15px',
    fontWeight: 700,
    color: '#ef4444', // red-500
  },
  shieldIcon: {
    color: '#ef4444',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
  },
  tabs: {
    display: 'flex',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
  },
  tabBtn: {
    flex: 1,
    padding: '12px',
    background: 'none',
    border: 'none',
    color: '#64748b',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    borderBottom: '2px solid transparent',
    transition: 'all 0.2s',
  },
  tabBtnActive: {
    color: '#ef4444',
    borderBottomColor: '#ef4444',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
  },
  logsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  refreshBtn: {
    alignSelf: 'flex-end',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '6px',
    color: '#cbd5e1',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  loading: {
    color: '#94a3b8',
    textAlign: 'center',
    padding: '20px 0',
    fontSize: '13px',
  },
  empty: {
    color: '#64748b',
    textAlign: 'center',
    padding: '20px 0',
    fontSize: '13px',
  },
  logList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  logItem: {
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.04)',
    borderRadius: '8px',
    padding: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  logMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '11px',
  },
  logUser: {
    color: '#f87171',
    fontWeight: 600,
  },
  logDate: {
    color: '#64748b',
  },
  logAction: {
    fontSize: '13px',
    color: '#e2e8f0',
    fontWeight: 500,
  },
  logTarget: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  logMetadata: {
    margin: '6px 0 0 0',
    padding: '6px',
    backgroundColor: '#020617',
    borderRadius: '4px',
    fontSize: '10px',
    color: '#38bdf8',
    overflowX: 'auto',
    fontFamily: 'monospace',
  },
  simulateContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  activeSimBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
    padding: '24px 16px',
    backgroundColor: 'rgba(245, 158, 11, 0.05)',
    border: '1px dashed rgba(245, 158, 11, 0.2)',
    borderRadius: '12px',
    textAlign: 'center',
  },
  simStatus: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '8px',
    color: '#fbbf24',
    fontSize: '14px',
  },
  simIcon: {
    color: '#fbbf24',
  },
  stopSimBtn: {
    backgroundColor: '#d97706',
    border: 'none',
    borderRadius: '8px',
    color: '#ffffff',
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  searchWrapper: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  searchBar: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#020617',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '8px',
    padding: '8px 12px',
    gap: '8px',
  },
  searchIcon: {
    color: '#64748b',
  },
  searchInput: {
    background: 'none',
    border: 'none',
    color: '#ffffff',
    outline: 'none',
    fontSize: '13px',
    width: '100%',
  },
  userList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    maxHeight: '400px',
    overflowY: 'auto',
  },
  userItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 12px',
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.04)',
    borderRadius: '8px',
    gap: '10px',
  },
  userInfo: {
    display: 'flex',
    flexDirection: 'column',
  },
  userName: {
    fontSize: '13.5px',
    fontWeight: 600,
    color: '#cbd5e1',
  },
  userEmail: {
    fontSize: '11px',
    color: '#64748b',
  },
  simulateBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    border: '1px solid rgba(59, 130, 246, 0.2)',
    borderRadius: '6px',
    color: '#60a5fa',
    padding: '6px 10px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
};
