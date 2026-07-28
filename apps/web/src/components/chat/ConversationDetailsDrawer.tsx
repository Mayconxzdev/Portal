import React, { useState, useEffect } from 'react';
import { X, Users, FolderOpen, AlertCircle, Plus, Trash2, Pin, Shield } from 'lucide-react';

interface Member {
  user_id: number;
  username: string;
  role: string;
  system_role: string;
  joined_at: string;
}

interface Attachment {
  id: number;
  file_id: number;
  original_filename: string;
  size_bytes: number;
  content_type: string;
  attachment_type: string;
  created_at: string;
}

interface ConversationDetailsDrawerProps {
  conversation: any;
  currentUser: any;
  onClose: () => void;
  onArchive: () => void;
  onRemoveMember: (userId: number) => void;
  onAddMembers: (userIds: number[]) => void;
  pinnedMessages: any[];
  onUnpin: (messageId: number) => void;
}

export const ConversationDetailsDrawer: React.FC<ConversationDetailsDrawerProps> = ({
  conversation,
  currentUser,
  onClose,
  onArchive,
  onRemoveMember,
  onAddMembers,
  pinnedMessages,
  onUnpin,
}) => {
  const [members, setMembers] = useState<Member[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [loadingAttachments, setLoadingAttachments] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [searchUserQuery, setSearchUserQuery] = useState('');
  const [availableUsers, setAvailableUsers] = useState<any[]>([]);

  const isGroupOrChannel = conversation.type === 'CHANNEL' || conversation.type === 'GROUP';
  
  // Verifica se o usuário logado tem privilégios de moderação nesta conversa
  const userMember = conversation.members?.find((m: any) => m.user_id === currentUser.id);
  const isModerator = currentUser.role === 'ADMIN' || currentUser.role === 'MESSIAS' || 
                      userMember?.role === 'OWNER' || userMember?.role === 'MODERATOR';

  const fetchMembers = async () => {
    setLoadingMembers(true);
    try {
      const res = await fetch(`/api/v1/chat/conversations/${conversation.id}/members`);
      if (res.ok) {
        const data = await res.json();
        setMembers(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingMembers(false);
    }
  };

  const fetchAttachments = async () => {
    setLoadingAttachments(true);
    try {
      // Puxa as últimas 50 mensagens para extrair anexos ou implementa busca de anexos.
      // Como o endpoint de mensagens retorna os anexos vinculados, podemos buscar as mensagens
      // e compilar os anexos.
      const res = await fetch(`/api/v1/chat/conversations/${conversation.id}/messages?limit=100`);
      if (res.ok) {
        const messages = await res.json();
        const compiled: Attachment[] = [];
        messages.forEach((msg: any) => {
          if (msg.attachments && msg.attachments.length > 0) {
            compiled.push(...msg.attachments);
          }
        });
        setAttachments(compiled);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAttachments(false);
    }
  };

  const loadAvailableUsers = async (q: string) => {
    try {
      const res = await fetch(`/api/v1/chat/users/search?q=${encodeURIComponent(q)}`);
      if (res.ok) {
        const data = await res.json();
        // Filtra quem já é membro
        const memberIds = new Set(members.map(m => m.user_id));
        setAvailableUsers(data.filter((u: any) => !memberIds.has(u.id)));
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchMembers();
    fetchAttachments();
  }, [conversation.id]);

  useEffect(() => {
    if (showAddMemberModal) {
      loadAvailableUsers(searchUserQuery);
    }
  }, [showAddMemberModal, searchUserQuery]);

  const handleAddMember = async (userId: number) => {
    try {
      const res = await fetch(`/api/v1/chat/conversations/${conversation.id}/members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([userId]),
      });
      if (res.ok) {
        fetchMembers();
        setShowAddMemberModal(false);
        setSearchUserQuery('');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemoveMemberClick = async (userId: number) => {
    try {
      const res = await fetch(`/api/v1/chat/conversations/${conversation.id}/members/${userId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        fetchMembers();
        onRemoveMember(userId);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const getFormatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div style={styles.drawer}>
      <div style={styles.header}>
        <span style={styles.headerTitle}>Detalhes da Conversa</span>
        <button onClick={onClose} style={styles.closeBtn}>
          <X size={18} />
        </button>
      </div>

      <div style={styles.content}>
        {/* Informações Básicas */}
        <div style={styles.section}>
          <h3 style={styles.convName}>
            {conversation.type === 'DM' 
              ? (conversation.name || 'Conversa Direta') 
              : `${conversation.type === 'CHANNEL' ? '#' : '👥'} ${conversation.name}`
            }
          </h3>
          {conversation.description && (
            <p style={styles.convDesc}>{conversation.description}</p>
          )}
          
          <div style={styles.metaList}>
            <div style={styles.metaItem}>
              <span style={styles.metaLabel}>Tipo:</span>
              <span style={styles.metaValue}>
                {conversation.type === 'CHANNEL' ? 'Canal' : conversation.type === 'GROUP' ? 'Grupo' : 'Mensagem Direta'}
              </span>
            </div>
            {isGroupOrChannel && (
              <div style={styles.metaItem}>
                <span style={styles.metaLabel}>Privacidade:</span>
                <span style={styles.metaValue}>{conversation.is_private ? 'Privado' : 'Público'}</span>
              </div>
            )}
          </div>

          {isModerator && isGroupOrChannel && (
            <div style={styles.adminActions}>
              <button onClick={onArchive} style={styles.archiveBtn}>
                Arquivar Conversa
              </button>
            </div>
          )}
        </div>

        {/* Mensagens Fixadas */}
        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <Pin size={15} style={styles.sectionIcon} />
            <span>Mensagens Fixadas ({pinnedMessages.length})</span>
          </div>
          <div style={styles.pinnedList}>
            {pinnedMessages.length === 0 ? (
              <div style={styles.emptyText}>Nenhuma mensagem fixada.</div>
            ) : (
              pinnedMessages.map((msg) => (
                <div key={msg.id} style={styles.pinnedItem}>
                  <div style={styles.pinnedAuthor}>{msg.sender_username}</div>
                  <div style={styles.pinnedBody}>{msg.body || '[Mídia]'}</div>
                  {isModerator && (
                    <button onClick={() => onUnpin(msg.id)} style={styles.unpinBtn}>
                      Desafixar
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Membros */}
        {isGroupOrChannel && (
          <div style={styles.section}>
            <div style={styles.sectionHeader}>
              <Users size={15} style={styles.sectionIcon} />
              <span>Membros ({members.length})</span>
              {isModerator && (
                <button onClick={() => setShowAddMemberModal(true)} style={styles.addMemberBtn}>
                  <Plus size={14} />
                </button>
              )}
            </div>
            {loadingMembers ? (
              <div style={styles.emptyText}>Carregando membros...</div>
            ) : (
              <div style={styles.memberList}>
                {members.map((m) => (
                  <div key={m.user_id} style={styles.memberItem}>
                    <div style={styles.memberInfo}>
                      <span style={styles.memberName}>{m.username}</span>
                      <span style={styles.memberRole}>
                        {m.role === 'OWNER' ? 'Dono' : m.role === 'MODERATOR' ? 'Moderador' : 'Membro'}
                      </span>
                    </div>
                    {isModerator && m.user_id !== currentUser.id && m.role !== 'OWNER' && (
                      <button
                        onClick={() => handleRemoveMemberClick(m.user_id)}
                        style={styles.removeMemberBtn}
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Arquivos / Mídia */}
        <div style={styles.section}>
          <div style={styles.sectionHeader}>
            <FolderOpen size={15} style={styles.sectionIcon} />
            <span>Arquivos e Mídia ({attachments.length})</span>
          </div>
          {loadingAttachments ? (
            <div style={styles.emptyText}>Carregando arquivos...</div>
          ) : attachments.length === 0 ? (
            <div style={styles.emptyText}>Nenhum arquivo compartilhado.</div>
          ) : (
            <div style={styles.fileList}>
              {attachments.map((att) => (
                <a
                  key={att.id}
                  href={`/api/v1/chat/attachments/${att.id}/download`}
                  target="_blank"
                  rel="noreferrer"
                  style={styles.fileItem}
                >
                  <div style={styles.fileIcon}>
                    {att.attachment_type === 'IMAGE' ? '🖼️' : att.attachment_type === 'VIDEO' ? '🎥' : att.attachment_type === 'AUDIO' ? '🎵' : '📄'}
                  </div>
                  <div style={styles.fileDetails}>
                    <div style={styles.fileName}>{att.original_filename}</div>
                    <div style={styles.fileMeta}>{getFormatSize(att.size_bytes)}</div>
                  </div>
                </a>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modal de Adicionar Membros */}
      {showAddMemberModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <div style={styles.modalHeader}>
              <span style={styles.modalTitle}>Adicionar Membro</span>
              <button onClick={() => setShowAddMemberModal(false)} style={styles.closeBtn}>
                <X size={18} />
              </button>
            </div>
            <div style={styles.modalContent}>
              <input
                type="text"
                placeholder="Buscar usuário por nome..."
                value={searchUserQuery}
                onChange={(e) => setSearchUserQuery(e.target.value)}
                style={styles.searchInput}
              />
              <div style={styles.userSearchList}>
                {availableUsers.length === 0 ? (
                  <div style={styles.emptyText}>Nenhum usuário disponível.</div>
                ) : (
                  availableUsers.map((u) => (
                    <div key={u.id} style={styles.userSearchItem}>
                      <span>{u.username}</span>
                      <button onClick={() => handleAddMember(u.id)} style={styles.inviteBtn}>
                        Adicionar
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
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
    fontSize: '14px',
    fontWeight: 700,
    color: '#f1f5f9',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  section: {
    borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
    paddingBottom: '16px',
  },
  convName: {
    fontSize: '16px',
    fontWeight: 700,
    color: '#ffffff',
    margin: '0 0 6px 0',
  },
  convDesc: {
    fontSize: '13px',
    color: '#94a3b8',
    margin: '0 0 12px 0',
    lineHeight: '1.4',
  },
  metaList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  metaItem: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '12px',
  },
  metaLabel: {
    color: '#64748b',
  },
  metaValue: {
    color: '#cbd5e1',
    fontWeight: 500,
  },
  adminActions: {
    marginTop: '12px',
  },
  archiveBtn: {
    width: '100%',
    backgroundColor: 'rgba(239, 68, 68, 0.08)',
    border: '1px solid rgba(239, 68, 68, 0.2)',
    color: '#ef4444',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: 600,
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    fontWeight: 700,
    color: '#94a3b8',
    marginBottom: '10px',
  },
  sectionIcon: {
    color: '#64748b',
  },
  emptyText: {
    fontSize: '12px',
    color: '#64748b',
    padding: '8px 0',
    textAlign: 'center',
  },
  pinnedList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  pinnedItem: {
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.04)',
    borderRadius: '6px',
    padding: '8px 10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    position: 'relative',
  },
  pinnedAuthor: {
    fontSize: '11px',
    fontWeight: 600,
    color: '#60a5fa',
  },
  pinnedBody: {
    fontSize: '12px',
    color: '#e2e8f0',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  },
  unpinBtn: {
    alignSelf: 'flex-end',
    background: 'none',
    border: 'none',
    color: '#64748b',
    fontSize: '10px',
    cursor: 'pointer',
    padding: '2px 0 0 0',
  },
  addMemberBtn: {
    marginLeft: 'auto',
    background: 'none',
    border: 'none',
    color: '#3b82f6',
    cursor: 'pointer',
  },
  memberList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    maxHeight: '160px',
    overflowY: 'auto',
  },
  memberItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 8px',
    backgroundColor: 'rgba(255, 255, 255, 0.01)',
    borderRadius: '4px',
  },
  memberInfo: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '8px',
  },
  memberName: {
    fontSize: '12.5px',
    color: '#e2e8f0',
    fontWeight: 500,
  },
  memberRole: {
    fontSize: '10px',
    color: '#64748b',
  },
  removeMemberBtn: {
    background: 'none',
    border: 'none',
    color: '#ef4444',
    cursor: 'pointer',
    opacity: 0.7,
  },
  fileList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    maxHeight: '200px',
    overflowY: 'auto',
  },
  fileItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px',
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    borderRadius: '6px',
    textDecoration: 'none',
    border: '1px solid rgba(255, 255, 255, 0.03)',
  },
  fileIcon: {
    fontSize: '16px',
  },
  fileDetails: {
    flex: 1,
    minWidth: 0,
  },
  fileName: {
    fontSize: '12px',
    color: '#e2e8f0',
    fontWeight: 500,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  fileMeta: {
    fontSize: '10px',
    color: '#64748b',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    width: '320px',
    backgroundColor: '#0f172a',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '8px',
    display: 'flex',
    flexDirection: 'column',
  },
  modalHeader: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 16px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
    justifyContent: 'space-between',
  },
  modalTitle: {
    fontSize: '13px',
    fontWeight: 700,
    color: '#ffffff',
  },
  modalContent: {
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  searchInput: {
    backgroundColor: '#020617',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '6px',
    color: '#ffffff',
    padding: '8px',
    fontSize: '12.5px',
    outline: 'none',
  },
  userSearchList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    maxHeight: '180px',
    overflowY: 'auto',
  },
  userSearchItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 8px',
    backgroundColor: 'rgba(255, 255, 255, 0.01)',
    borderRadius: '4px',
    fontSize: '12.5px',
    color: '#e2e8f0',
  },
  inviteBtn: {
    backgroundColor: '#3b82f6',
    border: 'none',
    color: '#white',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    cursor: 'pointer',
  },
};
