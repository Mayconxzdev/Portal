import React, { useState } from 'react';
import { Pin, MessageSquare, Edit2, Trash2, Smile, AlertCircle, FileText, CornerDownRight, History, Ticket, Kanban } from 'lucide-react';

interface MessageBubbleProps {
  message: any;
  currentUser: any;
  isMessias: boolean;
  onReact: (messageId: number, emoji: string) => void;
  onRemoveReact: (messageId: number, emoji: string) => void;
  onEdit: (messageId: number, newBody: string) => void;
  onDelete: (messageId: number) => void;
  onPin: (messageId: number) => void;
  onUnpin: (messageId: number) => void;
  onOpenThread: (message: any) => void;
  onCreateTicket: (messageId: number) => void;
  onCreateCard: (messageId: number) => void;
  onNavigateModule: (slug: string) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  currentUser,
  isMessias,
  onReact,
  onRemoveReact,
  onEdit,
  onDelete,
  onPin,
  onUnpin,
  onOpenThread,
  onCreateTicket,
  onCreateCard,
  onNavigateModule,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editVal, setEditVal] = useState(message.body || '');
  const [showReactionsMenu, setShowReactionsMenu] = useState(false);
  const [showEditHistory, setShowEditHistory] = useState(false);

  const isOwn = message.sender_user_id === currentUser.id;
  const isDeleted = message.is_deleted;
  const isEdited = message.is_edited;

  // Renderização seletiva para mensagens apagadas
  if (isDeleted && !isMessias) {
    return (
      <div style={{ ...styles.bubbleContainer, ...(isOwn ? styles.bubbleContainerOwn : {}) }}>
        <div style={{ ...styles.bubble, ...styles.deletedBubble }}>
          <span style={styles.deletedText}>Mensagem apagada</span>
        </div>
      </div>
    );
  }

  const handleEditSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editVal.trim()) return;
    onEdit(message.id, editVal.trim());
    setIsEditing(false);
  };

  const hasReacted = (emoji: string) => {
    return message.reactions?.some((r: any) => r.emoji === emoji && r.user_id === currentUser.id);
  };

  const handleReactionClick = (emoji: string) => {
    if (hasReacted(emoji)) {
      onRemoveReact(message.id, emoji);
    } else {
      onReact(message.id, emoji);
    }
  };

  // Renderiza o corpo da mensagem com menções
  const renderMessageBody = () => {
    if (isEditing) {
      return (
        <form onSubmit={handleEditSubmit} style={styles.editForm}>
          <input
            type="text"
            value={editVal}
            onChange={(e) => setEditVal(e.target.value)}
            style={styles.editInput}
          />
          <div style={styles.editActions}>
            <button type="button" onClick={() => setIsEditing(false)} style={styles.editCancelBtn}>
              Cancelar
            </button>
            <button type="submit" style={styles.editSaveBtn}>
              Salvar
            </button>
          </div>
        </form>
      );
    }

    const textContent = message.body || '';

    // Regex simples para capturar menções inteligentes a módulos (@TI, @Kanban, etc.)
    const parts = textContent.split(/(\s+)/);
    const renderedBody = parts.map((part: string, idx: number) => {
      if (part.startsWith('@')) {
        const clean = part.substring(1).replace(/[.,/#!$%^&*;:{}=\-_`~()]/g, '');
        
        // Verifica se é módulo
        const modulesMap: Record<string, string> = {
          'TI': 'it', 'Kanban': 'kanban', 'Aprovações': 'approvals',
          'Compras': 'purchases', 'Propostas': 'proposals', 'Arquivos': 'files',
          'Estoque': 'stock', 'Chat': 'chat'
        };

        if (modulesMap[clean]) {
          return (
            <span
              key={idx}
              onClick={() => onNavigateModule(modulesMap[clean])}
              style={styles.mentionChip}
              title={`Acessar módulo ${clean}`}
            >
              @{clean}
            </span>
          );
        }

        return <span key={idx} style={styles.mentionUser}>@{clean}</span>;
      }
      return part;
    });

    return (
      <div style={{
        ...styles.bodyText,
        ...(isDeleted ? styles.messiasDeletedText : {})
      }}>
        {renderedBody}
      </div>
    );
  };

  return (
    <div 
      className={`chat-message-bubble-container ${isOwn ? 'own' : ''}`}
      style={isOwn ? styles.bubbleContainerOwn : styles.bubbleContainer}
    >
      {/* Informações acima do balão */}
      <div style={styles.metaHeader}>
        <span style={{
          ...styles.author,
          ...(isOwn ? styles.authorOwn : styles.authorIncoming)
        }}>
          {message.sender_username}
        </span>
        <span style={styles.time}>
          {new Date(message.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
        </span>
        {isEdited && <span style={styles.editedLabel}>(editado)</span>}
        {isDeleted && isMessias && (
          <span style={styles.messiasAlertBadge}>
            <AlertCircle size={10} style={{ marginRight: '3px' }} />
            APAGADA (Auditoria)
          </span>
        )}
      </div>

      {/* Balão Principal */}
      <div style={{
        ...styles.bubble,
        ...(isOwn ? styles.bubbleOwn : styles.bubbleIncoming),
        ...(isDeleted ? styles.bubbleDeletedAuditoria : {}),
      }}>
        {renderMessageBody()}

        {/* Renderiza anexos */}
        {message.attachments && message.attachments.length > 0 && (
          <div style={styles.attachmentsGrid}>
            {message.attachments.map((att: any) => {
              const url = `/api/v1/chat/attachments/${att.id}/download`;
              
              if (att.attachment_type === 'IMAGE') {
                return (
                  <div key={att.id} style={styles.imageAttachmentBox}>
                    <img src={url} alt={att.original_filename} style={styles.imageAttachment} />
                  </div>
                );
              }
              
              if (att.attachment_type === 'VIDEO') {
                return (
                  <video key={att.id} src={url} controls style={styles.videoAttachment} />
                );
              }
              
              if (att.attachment_type === 'AUDIO') {
                return (
                  <audio key={att.id} src={url} controls style={styles.audioAttachment} />
                );
              }

              return (
                <a key={att.id} href={url} target="_blank" rel="noreferrer" style={styles.fileAttachment}>
                  <FileText size={16} />
                  <div style={styles.fileAttachmentDetails}>
                    <div style={styles.fileAttachmentName}>{att.original_filename}</div>
                    <div style={styles.fileAttachmentSize}>
                      {parseFloat((att.size_bytes / 1024).toFixed(1))} KB
                    </div>
                  </div>
                </a>
              );
            })}
          </div>
        )}

        {/* Seção inferior do balão (pins, replies, etc.) */}
        <div style={styles.bubbleFooter}>
          {message.is_pinned && (
            <div style={styles.pinnedIndicator}>
              <Pin size={10} />
              <span>Mensagem Fixada</span>
            </div>
          )}

          {message.reply_count > 0 && (
            <button onClick={() => onOpenThread(message)} style={styles.threadRepliesBtn}>
              <CornerDownRight size={12} />
              <span>{message.reply_count} respostas</span>
            </button>
          )}
        </div>
      </div>

      {/* Barra de Reações Agrupadas */}
      {message.reactions && message.reactions.length > 0 && (
        <div style={styles.reactionsBox}>
          {Array.from(new Set(message.reactions.map((r: any) => r.emoji))).map((emoji: any) => {
            const count = message.reactions.filter((r: any) => r.emoji === emoji).length;
            const active = hasReacted(emoji);
            return (
              <button
                key={emoji}
                onClick={() => handleReactionClick(emoji)}
                style={{
                  ...styles.reactionBadge,
                  ...(active ? styles.reactionBadgeActive : {})
                }}
              >
                <span>{emoji}</span>
                <span style={styles.reactionCount}>{count}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Menu de Ações Hover */}
      {!isDeleted && (
        <div className="chat-message-actions-menu">
          {/* Reação Rápida */}
          <button
            onClick={() => setShowReactionsMenu(!showReactionsMenu)}
            style={styles.actionBtn}
            title="Reagir"
          >
            <Smile size={14} />
          </button>
          {showReactionsMenu && (
            <div style={styles.reactionsPickerPopup}>
              {['👍', '❤️', '😂', '🔥', '👏', '💡'].map(emoji => (
                <button
                  key={emoji}
                  onClick={() => {
                    handleReactionClick(emoji);
                    setShowReactionsMenu(false);
                  }}
                  style={styles.reactionPickerEmoji}
                >
                  {emoji}
                </button>
              ))}
            </div>
          )}

          {/* Thread */}
          <button onClick={() => onOpenThread(message)} style={styles.actionBtn} title="Responder em Thread">
            <MessageSquare size={14} />
          </button>

          {/* Fixar/Desafixar */}
          {message.is_pinned ? (
            <button onClick={() => onUnpin(message.id)} style={styles.actionBtn} title="Desafixar">
              <Pin size={14} style={{ color: '#fbbf24' }} />
            </button>
          ) : (
            <button onClick={() => onPin(message.id)} style={styles.actionBtn} title="Fixar">
              <Pin size={14} />
            </button>
          )}

          {/* Editar próprio */}
          {isOwn && !isEditing && (
            <button onClick={() => { setIsEditing(true); setEditVal(message.body || ''); }} style={styles.actionBtn} title="Editar">
              <Edit2 size={14} />
            </button>
          )}

          {/* Excluir (próprio ou moderação) */}
          {(isOwn || currentUser.role === 'ADMIN' || currentUser.role === 'MESSIAS') && (
            <button onClick={() => onDelete(message.id)} style={styles.actionBtn} title="Excluir">
              <Trash2 size={14} style={{ color: '#ef4444' }} />
            </button>
          )}

          {/* Criar TI */}
          <button onClick={() => onCreateTicket(message.id)} style={styles.actionBtn} title="Criar Chamado de TI">
            <Ticket size={14} style={{ color: '#3b82f6' }} />
          </button>

          {/* Criar Kanban */}
          <button onClick={() => onCreateCard(message.id)} style={styles.actionBtn} title="Criar Card Kanban">
            <Kanban size={14} style={{ color: '#8b5cf6' }} />
          </button>

          {/* Histórico para o MESSIAS */}
          {isMessias && isEdited && (
            <button onClick={() => setShowEditHistory(!showEditHistory)} style={styles.actionBtn} title="Histórico de Edições">
              <History size={14} style={{ color: '#a855f7' }} />
            </button>
          )}
        </div>
      )}

      {/* Painel de Histórico de Edição do MESSIAS */}
      {showEditHistory && isMessias && message.edit_history && (
        <div style={styles.editHistoryBox}>
          <div style={styles.editHistoryHeader}>
            <span>Histórico de Edição (Auditoria)</span>
            <button onClick={() => setShowEditHistory(false)} style={styles.editHistoryClose}>X</button>
          </div>
          <div style={styles.editHistoryList}>
            {message.edit_history.map((ver: any) => (
              <div key={ver.id} style={styles.editHistoryItem}>
                <div style={styles.editHistoryMeta}>
                  <span>Editado por {ver.edited_by_username}</span>
                  <span>{new Date(ver.edited_at).toLocaleString('pt-BR')}</span>
                </div>
                <div style={styles.editHistoryDiff}>
                  <div style={styles.diffPrev}>- {ver.previous_body}</div>
                  <div style={styles.diffNew}>+ {ver.new_body}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  bubbleContainer: {
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    maxWidth: '75%',
    alignSelf: 'flex-start',
    gap: '2px',
    marginBottom: '8px',
  },
  bubbleContainerOwn: {
    alignSelf: 'flex-end',
  },
  metaHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '11px',
    color: '#64748b',
    padding: '0 4px',
  },
  author: {
    fontWeight: 600,
  },
  authorIncoming: {
    color: '#60a5fa',
  },
  authorOwn: {
    color: '#a78bfa',
  },
  time: {
    fontSize: '10px',
  },
  editedLabel: {
    fontSize: '10px',
    fontStyle: 'italic',
  },
  messiasAlertBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    color: '#f87171',
    padding: '1px 5px',
    borderRadius: '4px',
    fontWeight: 700,
    fontSize: '9px',
  },
  bubble: {
    borderRadius: '12px',
    padding: '10px 14px',
    fontSize: '13px',
    lineHeight: '1.45',
    color: '#f1f5f9',
    position: 'relative',
  },
  bubbleIncoming: {
    backgroundColor: '#1e293b', // slate-800
    border: '1px solid rgba(255, 255, 255, 0.03)',
  },
  bubbleOwn: {
    backgroundColor: '#1e1b4b', // indigo-950
    border: '1px solid rgba(99, 102, 241, 0.15)',
    color: '#e0d7ff',
  },
  bubbleDeletedAuditoria: {
    backgroundColor: 'rgba(239, 68, 68, 0.08)',
    border: '1px dashed rgba(239, 68, 68, 0.3)',
  },
  deletedBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.01)',
    border: '1px solid rgba(255, 255, 255, 0.03)',
    borderRadius: '12px',
    padding: '8px 12px',
  },
  deletedText: {
    fontStyle: 'italic',
    color: '#475569',
  },
  messiasDeletedText: {
    textDecoration: 'line-through',
    color: '#f87171',
  },
  bodyText: {
    wordBreak: 'break-word',
    whiteSpace: 'pre-wrap',
  },
  mentionChip: {
    backgroundColor: 'rgba(6, 182, 212, 0.15)',
    color: '#22d3ee',
    padding: '1px 5px',
    borderRadius: '4px',
    fontWeight: 600,
    cursor: 'pointer',
    marginRight: '2px',
    border: '1px solid rgba(6, 182, 212, 0.25)',
  },
  mentionUser: {
    color: '#60a5fa',
    fontWeight: 600,
    marginRight: '2px',
  },
  attachmentsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    marginTop: '10px',
  },
  imageAttachmentBox: {
    borderRadius: '8px',
    overflow: 'hidden',
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  imageAttachment: {
    maxWidth: '100%',
    maxHeight: '200px',
    objectFit: 'contain',
    display: 'block',
  },
  videoAttachment: {
    maxWidth: '100%',
    maxHeight: '200px',
    borderRadius: '8px',
  },
  audioAttachment: {
    width: '100%',
    maxHeight: '40px',
  },
  fileAttachment: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '8px 12px',
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    textDecoration: 'none',
    color: '#cbd5e1',
  },
  fileAttachmentDetails: {
    display: 'flex',
    flexDirection: 'column',
  },
  fileAttachmentName: {
    fontSize: '12px',
    fontWeight: 600,
  },
  fileAttachmentSize: {
    fontSize: '10px',
    color: '#64748b',
  },
  bubbleFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: '6px',
    fontSize: '10px',
    color: '#64748b',
  },
  pinnedIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    color: '#fbbf24',
  },
  threadRepliesBtn: {
    background: 'none',
    border: 'none',
    color: '#8b5cf6',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    cursor: 'pointer',
    fontWeight: 600,
  },
  reactionsBox: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
    marginTop: '4px',
  },
  reactionBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '20px',
    padding: '2px 8px',
    fontSize: '11px',
    cursor: 'pointer',
    color: '#94a3b8',
    transition: 'all 0.2s',
  },
  reactionBadgeActive: {
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    borderColor: '#3b82f6',
    color: '#60a5fa',
  },
  reactionCount: {
    fontWeight: 600,
  },
  hoverActions: {
    position: 'absolute',
    top: '50%',
    transform: 'translateY(-50%)',
    right: '-160px',
    display: 'none',
    alignItems: 'center',
    gap: '4px',
    backgroundColor: '#0f172a',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '20px',
    padding: '2px 8px',
    zIndex: 10,
    boxShadow: '0 4px 10px rgba(0, 0, 0, 0.3)',
  },
  // O hover no bubbleContainer revela hoverActions
  // Adicionaremos estilo direto via :hover em classes globais ou lidamos com JS.
  // Vamos configurar o hoverActions para aparecer na classe container correspondente
  actionBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    padding: '4px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background-color 0.2s',
  },
  reactionsPickerPopup: {
    position: 'absolute',
    bottom: '26px',
    left: '0',
    backgroundColor: '#1e293b',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '8px',
    padding: '4px',
    display: 'flex',
    gap: '4px',
    zIndex: 20,
    boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
  },
  reactionPickerEmoji: {
    background: 'none',
    border: 'none',
    fontSize: '16px',
    cursor: 'pointer',
    padding: '4px',
    borderRadius: '4px',
    transition: 'background-color 0.2s',
  },
  editForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    width: '100%',
  },
  editInput: {
    backgroundColor: '#020617',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '6px',
    color: '#ffffff',
    padding: '6px 10px',
    fontSize: '13px',
    outline: 'none',
    width: '100%',
  },
  editActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '6px',
  },
  editCancelBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    fontSize: '11px',
    cursor: 'pointer',
  },
  editSaveBtn: {
    backgroundColor: '#3b82f6',
    border: 'none',
    color: 'white',
    padding: '4px 10px',
    borderRadius: '4px',
    fontSize: '11px',
    cursor: 'pointer',
    fontWeight: 650,
  },
  editHistoryBox: {
    backgroundColor: '#020617',
    border: '1px solid rgba(168, 85, 247, 0.2)',
    borderRadius: '8px',
    padding: '8px',
    marginTop: '6px',
    fontSize: '11px',
    color: '#cbd5e1',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  editHistoryHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    fontWeight: 700,
    color: '#a855f7',
  },
  editHistoryClose: {
    background: 'none',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
  },
  editHistoryList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  editHistoryItem: {
    borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
    paddingBottom: '4px',
  },
  editHistoryMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    color: '#64748b',
    fontSize: '10px',
    marginBottom: '2px',
  },
  editHistoryDiff: {
    fontFamily: 'monospace',
    lineHeight: '1.3',
  },
  diffPrev: {
    color: '#f87171',
  },
  diffNew: {
    color: '#34d399',
  },
};
