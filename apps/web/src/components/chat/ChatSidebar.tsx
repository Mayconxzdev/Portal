import React, { useState } from 'react';
import { Search, Plus, MessageSquare, ShieldAlert, Users, Hash, ChevronRight } from 'lucide-react';

interface ChatSidebarProps {
  conversations: any[];
  selectedId: number | null;
  onSelectConversation: (id: number) => void;
  currentUser: any;
  isMessias: boolean;
  onOpenMessiasPanel: () => void;
  onCreateChannel: (data: { name: string; description: string; is_private: boolean }) => void;
  onCreateGroup: (data: { name: string; member_ids: number[] }) => void;
  onStartDM: (userId: number) => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  conversations,
  selectedId,
  onSelectConversation,
  currentUser,
  isMessias,
  onOpenMessiasPanel,
  onCreateChannel,
  onCreateGroup,
  onStartDM,
}) => {
  const [search, setSearch] = useState('');
  const [showChannelModal, setShowChannelModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showDMModal, setShowDMModal] = useState(false);

  // Estados dos formulários de criação
  const [channelForm, setChannelForm] = useState({ name: '', description: '', is_private: false });
  const [groupForm, setGroupForm] = useState({ name: '', member_ids: [] as number[] });
  
  const [dmSearch, setDmSearch] = useState('');
  const [dmUsers, setDmUsers] = useState<any[]>([]);

  // Carrega usuários para DM/Grupo
  const handleOpenDM = async () => {
    setShowDMModal(true);
    try {
      const res = await fetch('/api/v1/chat/users/search');
      if (res.ok) {
        const data = await res.json();
        setDmUsers(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleOpenGroup = async () => {
    setShowGroupModal(true);
    try {
      const res = await fetch('/api/v1/chat/users/search');
      if (res.ok) {
        const data = await res.json();
        setDmUsers(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDmSearch = async (val: string) => {
    setDmSearch(val);
    try {
      const res = await fetch(`/api/v1/chat/users/search?q=${encodeURIComponent(val)}`);
      if (res.ok) {
        const data = await res.json();
        setDmUsers(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleChannelSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!channelForm.name.trim()) return;
    onCreateChannel(channelForm);
    setChannelForm({ name: '', description: '', is_private: false });
    setShowChannelModal(false);
  };

  const handleGroupSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!groupForm.name.trim() || groupForm.member_ids.length === 0) return;
    onCreateGroup(groupForm);
    setGroupForm({ name: '', member_ids: [] });
    setShowGroupModal(false);
  };

  const handleToggleMember = (userId: number) => {
    setGroupForm((prev) => {
      const exists = prev.member_ids.includes(userId);
      if (exists) {
        return { ...prev, member_ids: prev.member_ids.filter((id) => id !== userId) };
      } else {
        return { ...prev, member_ids: [...prev.member_ids, userId] };
      }
    });
  };

  const handleDMSelect = (userId: number) => {
    onStartDM(userId);
    setShowDMModal(false);
    setDmSearch('');
  };

  // Filtra as conversas pela barra de busca
  const filteredConversations = conversations.filter((c) =>
    (c.name || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={styles.sidebar}>
      {/* Cabeçalho */}
      <div style={styles.header}>
        <div style={styles.titleWrapper}>
          <MessageSquare size={18} style={{ color: '#3b82f6' }} />
          <span style={styles.title}>Conversas</span>
        </div>
        <div style={styles.actions}>
          {isMessias && (
            <button onClick={onOpenMessiasPanel} style={styles.messiasBtn} title="Painel MESSIAS">
              <ShieldAlert size={15} />
            </button>
          )}
          {currentUser.role !== 'READ_ONLY' && (
            <>
              <button onClick={() => setShowChannelModal(true)} style={styles.actionBtn} title="Novo Canal">
                <Hash size={14} />
              </button>
              <button onClick={handleOpenGroup} style={styles.actionBtn} title="Novo Grupo">
                <Users size={14} />
              </button>
              <button onClick={handleOpenDM} style={styles.actionBtn} title="Nova Conversa Direta">
                <Plus size={14} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Busca */}
      <div style={styles.searchContainer}>
        <Search size={15} style={styles.searchIcon} />
        <input
          type="text"
          placeholder="Buscar no chat..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={styles.searchInput}
        />
      </div>

      {/* Lista de Conversas */}
      <div className="chat-channel-list" style={styles.conversationList}>
        {filteredConversations.length === 0 ? (
          <div style={styles.emptyText}>Nenhuma conversa encontrada.</div>
        ) : (
          filteredConversations.map((c) => {
            const isActive = c.id === selectedId;
            const isUnread = c.unread_count > 0;
            return (
              <div
                key={c.id}
                onClick={() => onSelectConversation(c.id)}
                className={`chat-channel-item ${isActive ? 'active' : ''}`}
                style={{
                  ...styles.convItem,
                  ...(isActive ? styles.convItemActive : {}),
                  ...(isUnread ? styles.convItemUnread : {}),
                }}
              >
                <div style={styles.convLeft}>
                  <span style={styles.convPrefix}>
                    {c.type === 'CHANNEL' ? '#' : c.type === 'GROUP' ? '👥' : '💬'}
                  </span>
                  <div style={styles.convInfo}>
                    <span style={styles.convName}>{c.name || 'Sem nome'}</span>
                    {c.last_message && (
                      <span style={styles.lastMsgBody}>
                        {c.last_message.is_deleted ? 'Mensagem apagada' : c.last_message.body}
                      </span>
                    )}
                  </div>
                </div>
                {isUnread && (
                  <span style={styles.unreadBadge}>{c.unread_count}</span>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* MODAL CRIAR CANAL */}
      {showChannelModal && (
        <div style={styles.modalOverlay}>
          <form onSubmit={handleChannelSubmit} style={styles.modal}>
            <div style={styles.modalHeader}>
              <span>Criar Canal</span>
              <button type="button" onClick={() => setShowChannelModal(false)} style={styles.closeBtn}>x</button>
            </div>
            <div style={styles.modalContent}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Nome do Canal</label>
                <input
                  type="text"
                  required
                  placeholder="ex: producao"
                  value={channelForm.name}
                  onChange={(e) => setChannelForm({ ...channelForm, name: e.target.value })}
                  style={styles.formInput}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Descrição</label>
                <textarea
                  placeholder="Do que se trata este canal?"
                  value={channelForm.description}
                  onChange={(e) => setChannelForm({ ...channelForm, description: e.target.value })}
                  style={styles.formTextarea}
                />
              </div>
              <div style={styles.checkboxGroup}>
                <input
                  type="checkbox"
                  id="is_private"
                  checked={channelForm.is_private}
                  onChange={(e) => setChannelForm({ ...channelForm, is_private: e.target.checked })}
                />
                <label htmlFor="is_private" style={styles.checkboxLabel}>Canal Privado</label>
              </div>
              <button type="submit" style={styles.submitBtn}>Criar Canal</button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL CRIAR GRUPO */}
      {showGroupModal && (
        <div style={styles.modalOverlay}>
          <form onSubmit={handleGroupSubmit} style={styles.modal}>
            <div style={styles.modalHeader}>
              <span>Criar Grupo</span>
              <button type="button" onClick={() => setShowGroupModal(false)} style={styles.closeBtn}>x</button>
            </div>
            <div style={styles.modalContent}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Nome do Grupo</label>
                <input
                  type="text"
                  required
                  placeholder="ex: Projeto Vesper"
                  value={groupForm.name}
                  onChange={(e) => setGroupForm({ ...groupForm, name: e.target.value })}
                  style={styles.formInput}
                />
              </div>
              <div style={styles.formGroup}>
                <label style={styles.label}>Selecionar Membros</label>
                <div style={styles.userSelectorBox}>
                  {dmUsers.map((u) => (
                    <div
                      key={u.id}
                      onClick={() => handleToggleMember(u.id)}
                      style={{
                        ...styles.selectorItem,
                        ...(groupForm.member_ids.includes(u.id) ? styles.selectorItemActive : {}),
                      }}
                    >
                      <span>{u.username}</span>
                    </div>
                  ))}
                </div>
              </div>
              <button type="submit" style={styles.submitBtn}>Criar Grupo</button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL INICIAR DM */}
      {showDMModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <div style={styles.modalHeader}>
              <span>Iniciar DM</span>
              <button type="button" onClick={() => setShowDMModal(false)} style={styles.closeBtn}>x</button>
            </div>
            <div style={styles.modalContent}>
              <input
                type="text"
                placeholder="Buscar usuário..."
                value={dmSearch}
                onChange={(e) => handleDmSearch(e.target.value)}
                style={styles.formInput}
              />
              <div style={styles.dmUserList}>
                {dmUsers.map((u) => (
                  <div
                    key={u.id}
                    onClick={() => handleDMSelect(u.id)}
                    style={styles.dmUserItem}
                  >
                    <span>{u.username}</span>
                    <ChevronRight size={14} style={{ color: '#64748b' }} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: '#0a0f1d',
    borderRight: '1px solid rgba(255, 255, 255, 0.05)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    padding: '16px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
    justifyContent: 'space-between',
  },
  titleWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  title: {
    fontSize: '15px',
    fontWeight: 700,
    color: '#ffffff',
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  messiasBtn: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.2)',
    borderRadius: '4px',
    color: '#ef4444',
    width: '26px',
    height: '26px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
  },
  actionBtn: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
    borderRadius: '4px',
    color: '#cbd5e1',
    width: '26px',
    height: '26px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  searchContainer: {
    padding: '12px 16px',
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#050811',
    borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
    gap: '8px',
  },
  searchIcon: {
    color: '#475569',
  },
  searchInput: {
    background: 'none',
    border: 'none',
    color: '#ffffff',
    fontSize: '13px',
    outline: 'none',
    width: '100%',
  },
  conversationList: {
    flex: 1,
    overflowY: 'auto',
    padding: '10px 8px',
  },
  emptyText: {
    fontSize: '12px',
    color: '#64748b',
    textAlign: 'center',
    padding: '20px 0',
  },
  convItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    borderRadius: '8px',
    cursor: 'pointer',
    marginBottom: '4px',
    transition: 'background-color 0.2s',
  },
  convItemActive: {
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
    color: '#3b82f6',
  },
  convItemUnread: {
    fontWeight: 700,
  },
  convLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    minWidth: 0,
  },
  convPrefix: {
    fontSize: '14px',
    color: '#94a3b8',
  },
  convInfo: {
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
  },
  convName: {
    fontSize: '13px',
    color: '#e2e8f0',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  lastMsgBody: {
    fontSize: '11px',
    color: '#64748b',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  unreadBadge: {
    backgroundColor: '#ef4444',
    color: '#white',
    fontSize: '10px',
    fontWeight: 700,
    borderRadius: '10px',
    padding: '2px 6px',
    minWidth: '18px',
    textAlign: 'center',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1100,
  },
  modal: {
    width: '340px',
    backgroundColor: '#0f172a',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '10px',
    display: 'flex',
    flexDirection: 'column',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '12px 16px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
    color: '#fff',
    fontWeight: 700,
    fontSize: '14px',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
    fontSize: '14px',
  },
  modalContent: {
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  label: {
    fontSize: '12px',
    color: '#94a3b8',
    fontWeight: 600,
  },
  formInput: {
    backgroundColor: '#020617',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '6px',
    color: '#ffffff',
    padding: '8px 12px',
    fontSize: '13px',
    outline: 'none',
  },
  formTextarea: {
    backgroundColor: '#020617',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '6px',
    color: '#ffffff',
    padding: '8px 12px',
    fontSize: '13px',
    outline: 'none',
    resize: 'none',
    height: '60px',
  },
  checkboxGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  checkboxLabel: {
    fontSize: '12.5px',
    color: '#cbd5e1',
  },
  submitBtn: {
    backgroundColor: '#3b82f6',
    border: 'none',
    color: 'white',
    padding: '10px',
    borderRadius: '6px',
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: '6px',
  },
  userSelectorBox: {
    maxHeight: '150px',
    overflowY: 'auto',
    border: '1px solid rgba(255,255,255,0.05)',
    borderRadius: '6px',
    backgroundColor: '#020617',
  },
  selectorItem: {
    padding: '8px 12px',
    cursor: 'pointer',
    fontSize: '12.5px',
    color: '#94a3b8',
    borderBottom: '1px solid rgba(255,255,255,0.02)',
  },
  selectorItemActive: {
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    color: '#60a5fa',
    fontWeight: 600,
  },
  dmUserList: {
    maxHeight: '200px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  dmUserItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 12px',
    borderRadius: '6px',
    cursor: 'pointer',
    backgroundColor: 'rgba(255,255,255,0.02)',
    fontSize: '13px',
    color: '#cbd5e1',
  },
};
