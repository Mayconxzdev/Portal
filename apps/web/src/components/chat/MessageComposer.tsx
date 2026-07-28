import React, { useState, useEffect, useRef } from 'react';
import { Paperclip, Smile, Mic, MicOff, Send, EyeOff, Video } from 'lucide-react';

interface MentionItem {
  type: string;
  id: number | null;
  slug: string | null;
  label: string;
  details: string | null;
  has_access: boolean;
}

interface MessageComposerProps {
  conversationId: number;
  onSendMessage: (payload: {
    body: string;
    message_type: string;
    file_ids: number[];
    mentions: any[];
  }) => void;
  isReadOnly: boolean;
  currentUser: any;
}

const COMMON_EMOJIS = ['😀', '😂', '👍', '❤️', '🔥', '👏', '🎉', '💡', '😮', '😢', '🙏', '👀'];

interface PendingAttachment {
  file: File;
  fileId: number;
  localUrl: string;
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  conversationId,
  onSendMessage,
  isReadOnly,
  currentUser,
}) => {
  const [text, setText] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([]);

  useEffect(() => {
    if (errorMessage) {
      const timer = setTimeout(() => setErrorMessage(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [errorMessage]);
  
  // Estados para Gravação de Áudio
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<any>(null);

  // Estados para Autocomplete de Menções
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionIndex, setMentionIndex] = useState(-1);
  const [mentionSuggestions, setMentionSuggestions] = useState<MentionItem[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Foco no campo ao trocar de conversa
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
    setText('');
    setShowEmojiPicker(false);
    cancelRecording();
    setShowSuggestions(false);
  }, [conversationId]);

  // Cronômetro da gravação
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      setRecordingSeconds(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  // Hook para monitorar digitação e abrir busca de menções
  useEffect(() => {
    if (mentionQuery !== null) {
      const fetchSuggestions = async () => {
        try {
          const res = await fetch(`/api/v1/chat/mentions/search?q=${encodeURIComponent(mentionQuery)}`);
          if (res.ok) {
            const data = await res.json();
            setMentionSuggestions(data);
            setShowSuggestions(data.length > 0);
          }
        } catch (err) {
          console.error(err);
        }
      };
      
      const debounce = setTimeout(fetchSuggestions, 150);
      return () => clearTimeout(debounce);
    } else {
      setShowSuggestions(false);
      setMentionSuggestions([]);
    }
  }, [mentionQuery]);

  // Função para tratar digitação de `@`
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setText(val);

    const selectionStart = e.target.selectionStart;
    const textBeforeCursor = val.substring(0, selectionStart);
    
    // Procura por `@` digitado sem espaço antes dele ou no início do texto
    const mentionMatch = textBeforeCursor.match(/@(\w*)$/);
    
    if (mentionMatch) {
      setMentionQuery(mentionMatch[1]);
      setMentionIndex(-1);
    } else {
      setMentionQuery(null);
    }
  };

  // Trata teclas de atalho e envio
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showSuggestions && mentionSuggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setMentionIndex((prev) => (prev + 1) % mentionSuggestions.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setMentionIndex((prev) => (prev - 1 + mentionSuggestions.length) % mentionSuggestions.length);
        return;
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        const selected = mentionSuggestions[mentionIndex >= 0 ? mentionIndex : 0];
        if (selected) {
          insertMention(selected);
        }
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setMentionQuery(null);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const insertMention = (item: MentionItem) => {
    if (!textareaRef.current) return;
    
    const cursor = textareaRef.current.selectionStart;
    const before = text.substring(0, cursor);
    const after = text.substring(cursor);
    
    // Substitui o `@termo` pela menção formatada
    const lastIndex = before.lastIndexOf('@');
    const newBefore = before.substring(0, lastIndex) + `@${item.label} `;
    
    setText(newBefore + after);
    setMentionQuery(null);
    
    // Foca de volta
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        const newCursorPos = newBefore.length;
        textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
      }
    }, 50);
  };

  // Faz upload do anexo
  const uploadFile = async (file: File): Promise<number | null> => {
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`/api/v1/chat/conversations/${conversationId}/attachments`, {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        return data.file_id;
      } else {
        const err = await res.json();
        setErrorMessage(err.detail || 'Falha no upload do arquivo.');
      }
    } catch (e) {
      console.error(e);
    }
    return null;
  };

  // Remove um anexo pendente da lista
  const removePendingAttachment = (fileId: number) => {
    setPendingAttachments((prev) => {
      const target = prev.find(att => att.fileId === fileId);
      if (target) {
        URL.revokeObjectURL(target.localUrl);
      }
      return prev.filter(att => att.fileId !== fileId);
    });
  };

  // Lida com mudança no file-input
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || isReadOnly) return;
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileId = await uploadFile(file);
      if (fileId) {
        const localUrl = URL.createObjectURL(file);
        setPendingAttachments((prev) => [
          ...prev,
          {
            file,
            fileId,
            localUrl
          }
        ]);
      }
    }
    // Reseta input
    e.target.value = '';
  };

  // Ctrl+V para colar imagens/prints
  const handlePaste = async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    if (isReadOnly) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const blob = items[i].getAsFile();
        if (blob) {
          const file = new File([blob], `print-${Date.now()}.png`, { type: 'image/png' });
          const fileId = await uploadFile(file);
          if (fileId) {
            const localUrl = URL.createObjectURL(file);
            setPendingAttachments((prev) => [
              ...prev,
              {
                file,
                fileId,
                localUrl
              }
            ]);
          }
        }
      }
    }
  };

  // Gravação de Áudio Real
  const startRecording = async () => {
    if (isReadOnly) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const file = new File([audioBlob], `audio-${Date.now()}.webm`, { type: 'audio/webm' });
        
        const fileId = await uploadFile(file);
        if (fileId) {
          onSendMessage({
            body: 'Mensagem de áudio gravada',
            message_type: 'AUDIO',
            file_ids: [fileId],
            mentions: [],
          });
        }
        
        // Libera a webcam/microfone
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      setErrorMessage('Não foi possível acessar o microfone.');
      console.error(err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const cancelRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.onstop = null; // evita enviar ao cancelar
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  // Envia Mensagem de Texto com anexos
  const handleSend = () => {
    if ((!text.trim() && pendingAttachments.length === 0) || isReadOnly) return;

    const file_ids = pendingAttachments.map((a) => a.fileId);

    // Analisa as menções presentes no texto para mapear os objetos correspondentes
    const mentionsList: any[] = [];
    
    // Identifica chips de menção a módulos (ex: @TI, @Kanban)
    const modulesMap: Record<string, string> = {
      'TI': 'it', 'Kanban': 'kanban', 'Aprovações': 'approvals',
      'Compras': 'purchases', 'Propostas': 'proposals', 'Arquivos': 'files',
      'Estoque': 'stock', 'Chat': 'chat'
    };

    // Regex simples para capturar palavras precedidas de @ no texto
    const words = text.split(/\s+/);
    words.forEach(w => {
      if (w.startsWith('@')) {
        const label = w.substring(1);
        if (modulesMap[label]) {
          mentionsList.push({
            mention_type: 'MODULE',
            target_slug: modulesMap[label],
            display_label: label
          });
        }
      }
    });

    // Determina o tipo de mensagem e o corpo
    let body = text;
    let message_type = 'TEXT';

    if (text.trim() === '' && pendingAttachments.length > 0) {
      if (pendingAttachments.length === 1) {
        const first = pendingAttachments[0];
        body = `Compartilhou o arquivo: ${first.file.name}`;
        if (first.file.type.startsWith('image/')) message_type = 'IMAGE';
        else if (first.file.type.startsWith('video/')) message_type = 'VIDEO';
        else if (first.file.type.startsWith('audio/')) message_type = 'AUDIO';
        else message_type = 'FILE';
      } else {
        body = `Compartilhou ${pendingAttachments.length} arquivos: ${pendingAttachments.map(a => a.file.name).join(', ')}`;
        message_type = 'FILE';
      }
    }

    onSendMessage({
      body: body,
      message_type,
      file_ids,
      mentions: mentionsList,
    });

    // Limpa estado local e revoga URLs
    pendingAttachments.forEach(att => URL.revokeObjectURL(att.localUrl));
    setPendingAttachments([]);
    setText('');
    setMentionQuery(null);
  };

  const insertEmoji = (emoji: string) => {
    setText((prev) => prev + emoji);
    setShowEmojiPicker(false);
    if (textareaRef.current) textareaRef.current.focus();
  };

  if (isReadOnly) {
    return (
      <div style={styles.readOnlyContainer}>
        <EyeOff size={18} style={{ color: '#fbbf24' }} />
        <span>Modo visualização ativo — Você não tem permissão para enviar mensagens nesta simulação.</span>
      </div>
    );
  }

  return (
    <div style={styles.composerWrapper}>
      {errorMessage && (
        <div style={{
          backgroundColor: 'rgba(239, 68, 68, 0.12)',
          borderBottom: '1px solid rgba(239, 68, 68, 0.25)',
          color: '#fca5a5',
          padding: '8px 16px',
          fontSize: '12px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontWeight: '600'
        }}>
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '14px' }}>×</button>
        </div>
      )}
      {/* Autocomplete de sugestões */}
      {showSuggestions && (
        <div style={styles.suggestionsBox}>
          {mentionSuggestions.map((item, idx) => (
            <div
              key={idx}
              onClick={() => insertMention(item)}
              style={{
                ...styles.suggestionItem,
                ...(idx === mentionIndex ? styles.suggestionItemActive : {}),
              }}
            >
              <div style={styles.suggestionLabel}>
                <span style={styles.typeBadge}>{item.type}</span>
                <span>{item.label}</span>
              </div>
              {item.details && <span style={styles.suggestionDetails}>{item.details}</span>}
              {!item.has_access && <span style={styles.restrictedText}>(Sem acesso)</span>}
            </div>
          ))}
        </div>
      )}

      {/* Emoji Picker Popover */}
      {showEmojiPicker && (
        <div style={styles.emojiPicker}>
          <div style={styles.emojiGrid}>
            {COMMON_EMOJIS.map((emoji) => (
              <button
                key={emoji}
                onClick={() => insertEmoji(emoji)}
                style={styles.emojiBtn}
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Visualização Prévia dos Anexos Fila */}
      {pendingAttachments.length > 0 && (
        <div style={styles.attachmentsPreviewContainer}>
          {pendingAttachments.map((att) => {
            const isImage = att.file.type.startsWith('image/');
            return (
              <div key={att.fileId} style={styles.attachmentPreviewCard}>
                {isImage ? (
                  <div style={styles.previewImageWrapper}>
                    <img 
                      src={att.localUrl} 
                      alt={att.file.name} 
                      style={styles.previewImage}
                    />
                  </div>
                ) : (
                  <div style={styles.previewFileIcon}>
                    <Paperclip size={18} style={{ color: '#38bdf8' }} />
                  </div>
                )}
                <span style={styles.previewFilename} title={att.file.name}>{att.file.name}</span>
                <button 
                  type="button" 
                  onClick={() => removePendingAttachment(att.fileId)} 
                  style={styles.removeAttachmentBtn}
                  title="Remover anexo"
                >
                  ×
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Composer Input Bar */}
      <div style={styles.composerBar}>
        {isRecording ? (
          <div style={styles.recordingState}>
            <div style={styles.recordingPulse}></div>
            <span style={styles.recordingTimer}>
              Gravando Áudio... {Math.floor(recordingSeconds / 60)}:
              {String(recordingSeconds % 60).padStart(2, '0')}
            </span>
            <button onClick={cancelRecording} style={styles.cancelRecBtn}>
              Cancelar
            </button>
            <button onClick={stopRecording} style={styles.sendRecBtn}>
              Enviar Áudio
            </button>
          </div>
        ) : (
          <>
            {/* Seletor de Arquivo Oculto */}
            <label style={styles.iconButton} title="Anexar arquivo">
              <Paperclip size={18} />
              <input
                type="file"
                multiple
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
            </label>

            {/* Emoji Trigger */}
            <button
              onClick={() => setShowEmojiPicker(!showEmojiPicker)}
              style={styles.iconButton}
              title="Inserir emoji"
            >
              <Smile size={18} />
            </button>

            {/* Microfone Trigger */}
            <button
              onClick={startRecording}
              style={styles.iconButton}
              title="Gravar áudio"
            >
              <Mic size={18} />
            </button>

            {/* Input de Texto */}
            <textarea
              ref={textareaRef}
              rows={1}
              value={text}
              onChange={handleTextChange}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder="Envie uma mensagem ou use @ para mencionar..."
              style={styles.textarea}
            />

            {/* Botão de Enviar */}
            <button
              onClick={handleSend}
              disabled={!text.trim() && pendingAttachments.length === 0}
              style={{
                ...styles.sendBtn,
                ...((!text.trim() && pendingAttachments.length === 0) ? styles.sendBtnDisabled : {}),
              }}
            >
              <Send size={16} />
            </button>
          </>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  composerWrapper: {
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#090d16',
    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
  },
  readOnlyContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    backgroundColor: 'rgba(245, 158, 11, 0.05)',
    borderTop: '1px solid rgba(245, 158, 11, 0.1)',
    color: '#fbbf24',
    padding: '16px',
    fontSize: '13px',
    fontWeight: 500,
    textAlign: 'center',
  },
  composerBar: {
    display: 'flex',
    alignItems: 'end',
    padding: '12px 16px',
    gap: '12px',
  },
  iconButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '36px',
    height: '36px',
    borderRadius: '50%',
    color: '#94a3b8',
    cursor: 'pointer',
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.04)',
    transition: 'all 0.2s',
  },
  textarea: {
    flex: 1,
    backgroundColor: '#020617',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: '12px',
    color: '#ffffff',
    padding: '10px 14px',
    fontSize: '13px',
    outline: 'none',
    resize: 'none',
    maxHeight: '120px',
    fontFamily: 'Inter, system-ui, sans-serif',
    lineHeight: '1.4',
  },
  sendBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '38px',
    height: '38px',
    borderRadius: '50%',
    backgroundColor: '#3b82f6',
    border: 'none',
    color: '#ffffff',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  sendBtnDisabled: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    color: '#475569',
    cursor: 'default',
  },
  recordingState: {
    display: 'flex',
    alignItems: 'center',
    width: '100%',
    gap: '12px',
    backgroundColor: '#1e1b4b', // indigo-950
    padding: '8px 16px',
    borderRadius: '12px',
    border: '1px solid rgba(99, 102, 241, 0.2)',
  },
  recordingPulse: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    backgroundColor: '#ef4444',
    animation: 'pulse 1.2s infinite',
  },
  recordingTimer: {
    fontSize: '13px',
    color: '#e0d7ff',
    fontWeight: 600,
    flex: 1,
  },
  cancelRecBtn: {
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    fontSize: '12.5px',
    fontWeight: 500,
  },
  sendRecBtn: {
    backgroundColor: '#ef4444',
    border: 'none',
    color: 'white',
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '12.5px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  emojiPicker: {
    position: 'absolute',
    bottom: '60px',
    left: '16px',
    backgroundColor: '#0f172a',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '8px',
    padding: '10px',
    boxShadow: '0 10px 25px rgba(0, 0, 0, 0.5)',
    zIndex: 100,
  },
  emojiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(6, 1fr)',
    gap: '6px',
  },
  emojiBtn: {
    fontSize: '18px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '4px',
    borderRadius: '4px',
    transition: 'background-color 0.2s',
  },
  suggestionsBox: {
    position: 'absolute',
    bottom: '60px',
    left: '80px',
    right: '16px',
    backgroundColor: '#0f172a',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '8px',
    maxHeight: '220px',
    overflowY: 'auto',
    boxShadow: '0 10px 25px rgba(0, 0, 0, 0.5)',
    zIndex: 200,
    display: 'flex',
    flexDirection: 'column',
  },
  suggestionItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 12px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  suggestionItemActive: {
    backgroundColor: 'rgba(59, 130, 246, 0.1)',
  },
  suggestionLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '13px',
    color: '#cbd5e1',
    fontWeight: 500,
  },
  typeBadge: {
    fontSize: '9px',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    color: '#94a3b8',
    padding: '2px 6px',
    borderRadius: '4px',
    fontWeight: 700,
  },
  suggestionDetails: {
    fontSize: '11px',
    color: '#64748b',
  },
  restrictedText: {
    fontSize: '11px',
    color: '#ef4444',
    fontWeight: 500,
  },
  attachmentsPreviewContainer: {
    display: 'flex',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: '10px',
    padding: '12px 16px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
    backgroundColor: 'rgba(255, 255, 255, 0.01)',
  },
  attachmentPreviewCard: {
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    width: '80px',
    padding: '8px',
    borderRadius: '8px',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
  },
  previewImageWrapper: {
    width: '48px',
    height: '48px',
    borderRadius: '4px',
    overflow: 'hidden',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#000',
  },
  previewImage: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
  },
  previewFileIcon: {
    width: '48px',
    height: '48px',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1e293b',
  },
  previewFilename: {
    width: '100%',
    fontSize: '9px',
    color: '#94a3b8',
    marginTop: '4px',
    textAlign: 'center',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  removeAttachmentBtn: {
    position: 'absolute',
    top: '-6px',
    right: '-6px',
    width: '16px',
    height: '16px',
    borderRadius: '50%',
    backgroundColor: '#ef4444',
    color: '#fff',
    border: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '11px',
    fontWeight: 'black',
    cursor: 'pointer',
    boxShadow: '0 2px 5px rgba(0,0,0,0.3)',
  },
};
