import React, { useState, useEffect, useRef } from 'react';
import { X, Send, CornerDownRight } from 'lucide-react';

interface ThreadDrawerProps {
  parentMessage: any;
  currentUser: any;
  onClose: () => void;
  onSendReply: (body: string) => void;
  isReadOnly: boolean;
}

export const ThreadDrawer: React.FC<ThreadDrawerProps> = ({
  parentMessage,
  currentUser,
  onClose,
  onSendReply,
  isReadOnly,
}) => {
  const [replies, setReplies] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [replyText, setReplyText] = useState('');
  const historyRef = useRef<HTMLDivElement>(null);

  const fetchReplies = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/chat/messages/${parentMessage.id}/thread`);
      if (res.ok) {
        const data = await res.json();
        setReplies(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReplies();
  }, [parentMessage.id]);

  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [replies]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim() || isReadOnly) return;
    onSendReply(replyText.trim());
    
    // Otimista: insere localmente e limpa
    const newReply = {
      id: Date.now(), // ID temporário
      sender_username: currentUser.username,
      sender_user_id: currentUser.id,
      body: replyText,
      created_at: new Date().toISOString(),
      message_type: 'TEXT',
      reactions: [],
      attachments: [],
      mentions: [],
    };
    setReplies([...replies, newReply]);
    setReplyText('');
  };

  return (
    <div style={styles.drawer}>
      <div style={styles.header}>
        <div style={styles.headerTitle}>
          <CornerDownRight size={16} style={{ color: '#8b5cf6' }} />
          <span>Thread</span>
        </div>
        <button onClick={onClose} style={styles.closeBtn}>
          <X size={18} />
        </button>
      </div>

      {/* Conteúdo Principal */}
      <div style={styles.main}>
        {/* Mensagem Raiz */}
        <div style={styles.rootMessage}>
          <div style={styles.msgMeta}>
            <span style={styles.msgAuthor}>{parentMessage.sender_username}</span>
            <span style={styles.msgTime}>
              {new Date(parentMessage.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <div style={styles.msgBody}>
            {parentMessage.is_deleted ? (
              <span style={styles.deletedText}>Mensagem apagada</span>
            ) : (
              parentMessage.body
            )}
          </div>
        </div>

        <div style={styles.divider}>Respostas</div>

        {/* Lista de Respostas */}
        <div ref={historyRef} style={styles.repliesHistory}>
          {loading ? (
            <div style={styles.loading}>Carregando respostas...</div>
          ) : replies.length === 0 ? (
            <div style={styles.empty}>Nenhuma resposta ainda nesta thread.</div>
          ) : (
            replies.map((rep) => (
              <div key={rep.id} style={styles.replyItem}>
                <div style={styles.msgMeta}>
                  <span style={styles.replyAuthor}>{rep.sender_username}</span>
                  <span style={styles.msgTime}>
                    {new Date(rep.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div style={styles.replyBody}>{rep.body}</div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Composer no rodapé */}
      {!isReadOnly ? (
        <form onSubmit={handleSubmit} style={styles.composerForm}>
          <input
            type="text"
            placeholder="Responder na thread..."
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            style={styles.replyInput}
          />
          <button type="submit" disabled={!replyText.trim()} style={styles.sendBtn}>
            <Send size={15} />
          </button>
        </form>
      ) : (
        <div style={styles.readOnlyBanner}>Modo visualização — escrita desativada</div>
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
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
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
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
    padding: '16px',
  },
  rootMessage: {
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.04)',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '16px',
  },
  msgMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '11px',
    marginBottom: '4px',
  },
  msgAuthor: {
    fontWeight: 600,
    color: '#60a5fa',
  },
  replyAuthor: {
    fontWeight: 600,
    color: '#cbd5e1',
  },
  msgTime: {
    color: '#64748b',
  },
  msgBody: {
    fontSize: '13px',
    color: '#e2e8f0',
    lineHeight: '1.4',
  },
  deletedText: {
    fontStyle: 'italic',
    color: '#64748b',
  },
  divider: {
    fontSize: '11px',
    fontWeight: 700,
    textTransform: 'uppercase',
    color: '#64748b',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
    paddingBottom: '6px',
    marginBottom: '12px',
    letterSpacing: '0.5px',
  },
  repliesHistory: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  loading: {
    textAlign: 'center',
    color: '#64748b',
    fontSize: '12.5px',
    padding: '20px 0',
  },
  empty: {
    textAlign: 'center',
    color: '#64748b',
    fontSize: '12px',
    padding: '20px 0',
  },
  replyItem: {
    backgroundColor: 'rgba(255, 255, 255, 0.01)',
    border: '1px solid rgba(255, 255, 255, 0.02)',
    borderRadius: '6px',
    padding: '8px 10px',
  },
  replyBody: {
    fontSize: '12.5px',
    color: '#e2e8f0',
    lineHeight: '1.4',
  },
  composerForm: {
    display: 'flex',
    padding: '12px 16px',
    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
    gap: '8px',
    backgroundColor: '#090d16',
  },
  replyInput: {
    flex: 1,
    backgroundColor: '#020617',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '6px',
    color: '#ffffff',
    padding: '8px 12px',
    fontSize: '12.5px',
    outline: 'none',
  },
  sendBtn: {
    backgroundColor: '#8b5cf6',
    border: 'none',
    borderRadius: '6px',
    color: '#ffffff',
    width: '32px',
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  readOnlyBanner: {
    padding: '12px 16px',
    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
    textAlign: 'center',
    fontSize: '12px',
    color: '#fbbf24',
    backgroundColor: 'rgba(245, 158, 11, 0.05)',
    fontWeight: 500,
  },
};
