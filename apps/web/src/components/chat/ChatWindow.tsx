import React, { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';
import { MessageComposer } from './MessageComposer';
import { Info, HelpCircle, MessageSquare } from 'lucide-react';

interface ChatWindowProps {
  conversation: any;
  messages: any[];
  currentUser: any;
  isMessias: boolean;
  onSendMessage: (payload: { body: string; message_type: string; file_ids: number[]; mentions: any[] }) => void;
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
  onToggleDetails: () => void;
  typingText: string | null;
  isReadOnly: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  conversation,
  messages,
  currentUser,
  isMessias,
  onSendMessage,
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
  onToggleDetails,
  typingText,
  isReadOnly,
}) => {
  const historyRef = useRef<HTMLDivElement>(null);

  // Faz scroll para o final do chat ao carregar mensagens
  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [messages, typingText]);

  if (!conversation) {
    return (
      <div style={styles.emptyContainer}>
        <div style={styles.emptyContent}>
          <div style={styles.iconCircle}>
            <MessageSquare size={36} style={{ color: '#06b6d4' }} />
          </div>
          <h3 style={styles.emptyTitle}>Portal Vesper Chat</h3>
          <p style={styles.emptyDesc}>
            Selecione um canal, grupo ou inicie uma conversa direta para enviar mensagens internas.
          </p>
        </div>
      </div>
    );
  }

  // Filtra as mensagens ativas (se o usuário for comum, oculta as apagadas)
  const visibleMessages = messages.filter((msg) => isMessias || !msg.is_deleted);

  // Calcula mensagens fixadas ativas
  const pinnedMessages = visibleMessages.filter((msg) => msg.is_pinned);

  return (
    <div style={styles.window}>
      {/* Cabeçalho */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.headerName}>
            {conversation.type === 'CHANNEL' ? '#' : conversation.type === 'GROUP' ? '👥' : '💬'}{' '}
            {conversation.name || 'Conversa'}
          </span>
          <div style={styles.headerStatus}>
            {typingText ? (
              <span style={styles.typingText}>{typingText}</span>
            ) : conversation.type === 'DM' ? (
              <span style={styles.presenceOnline}>Disponível</span>
            ) : (
              <span style={styles.channelMeta}>
                {conversation.members?.length || 0} membros
              </span>
            )}
          </div>
        </div>
        <div style={styles.headerRight}>
          <button onClick={onToggleDetails} style={styles.headerActionBtn} title="Detalhes da Conversa">
            <Info size={18} />
          </button>
        </div>
      </div>

      {/* Banner de Mensagem Fixada no Topo (se houver) */}
      {pinnedMessages.length > 0 && (
        <div style={styles.pinnedBanner}>
          <div style={styles.pinnedBannerContent}>
            <strong>Fixada: </strong>
            <span>{pinnedMessages[pinnedMessages.length - 1].body || '[Mídia]'}</span>
          </div>
        </div>
      )}

      {/* Histórico de Mensagens */}
      <div ref={historyRef} className="chat-messages-history" style={styles.history}>
        {visibleMessages.length === 0 ? (
          <div style={styles.emptyMessages}>Sem mensagens nesta conversa. Comece enviando algo!</div>
        ) : (
          visibleMessages.map((msg) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              currentUser={currentUser}
              isMessias={isMessias}
              onReact={onReact}
              onRemoveReact={onRemoveReact}
              onEdit={onEdit}
              onDelete={onDelete}
              onPin={onPin}
              onUnpin={onUnpin}
              onOpenThread={onOpenThread}
              onCreateTicket={onCreateTicket}
              onCreateCard={onCreateCard}
              onNavigateModule={onNavigateModule}
            />
          ))
        )}
      </div>

      {/* Composer de Entrada */}
      <MessageComposer
        conversationId={conversation.id}
        onSendMessage={onSendMessage}
        isReadOnly={isReadOnly}
        currentUser={currentUser}
      />
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  emptyContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    backgroundColor: '#0a0f1d',
    borderRadius: '12px',
    border: '1px solid rgba(255, 255, 255, 0.04)',
  },
  emptyContent: {
    textAlign: 'center',
    maxWidth: '320px',
    padding: '24px',
  },
  iconCircle: {
    width: '72px',
    height: '72px',
    borderRadius: '50%',
    backgroundColor: 'rgba(6, 182, 212, 0.1)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px auto',
    border: '1px solid rgba(6, 182, 212, 0.15)',
  },
  emptyTitle: {
    fontSize: '16px',
    fontWeight: 700,
    color: '#ffffff',
    margin: '0 0 8px 0',
  },
  emptyDesc: {
    fontSize: '13px',
    color: '#64748b',
    lineHeight: '1.5',
    margin: 0,
  },
  window: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    backgroundColor: 'rgba(15, 23, 42, 0.4)',
    border: '1px solid rgba(255, 255, 255, 0.04)',
    borderRadius: '12px',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    padding: '12px 20px',
    backgroundColor: '#090d16',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
    justifyContent: 'space-between',
  },
  headerLeft: {
    display: 'flex',
    flexDirection: 'column',
  },
  headerName: {
    fontSize: '14.5px',
    fontWeight: 700,
    color: '#ffffff',
  },
  headerStatus: {
    fontSize: '11px',
    marginTop: '2px',
  },
  typingText: {
    color: '#a78bfa',
    fontStyle: 'italic',
    fontWeight: 500,
  },
  presenceOnline: {
    color: '#10b981', // green-500
    fontWeight: 500,
  },
  channelMeta: {
    color: '#64748b',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
  },
  headerActionBtn: {
    background: 'none',
    border: 'none',
    color: '#cbd5e1',
    cursor: 'pointer',
    padding: '6px',
    borderRadius: '50%',
    transition: 'background-color 0.2s',
  },
  pinnedBanner: {
    backgroundColor: 'rgba(251, 191, 36, 0.08)',
    borderBottom: '1px solid rgba(251, 191, 36, 0.15)',
    padding: '8px 20px',
    fontSize: '12px',
    color: '#fbbf24',
  },
  pinnedBannerContent: {
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  history: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  emptyMessages: {
    textAlign: 'center',
    color: '#475569',
    fontSize: '13px',
    padding: '40px 0',
  },
};
