import React, { useState, useEffect, useRef } from 'react';
import {
  Search as IconSearch,
  ShieldAlert as IconShieldExclamation,
  Users as IconUsers,
  Hash as IconHash,
  ChevronRight as IconChevronRight,
  Pin as IconPin,
  Paperclip as IconPaperclip,
  Send as IconSend,
  X as IconX,
  MoreVertical as IconDotsVertical,
  FileText as IconFileText,
  MessageSquareText as IconMessageDots,
  Settings as IconSettings,
} from 'lucide-react';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { Textarea } from '../components/ui/Textarea';
import { Button } from '../components/ui/Button';
import { CompactModuleHeader } from '../components/layout/CompactModuleHeader';
import { KodaMascot } from '../components/ui/KodaMascot';
import { ConversationDetailsDrawer } from '../components/chat/ConversationDetailsDrawer';
import { MessageActionToolbar } from '../components/chat/MessageActionToolbar';
import { ReplyPreview } from '../components/chat/ReplyPreview';
import { useActionCommands, ActionCommandDraft } from '../hooks/useActionCommands';
import { ActionCommandCard } from '../components/actions/ActionCommandCard';

interface ChatPageProps {
  currentUser: any;
  onBack?: () => void;
}

const quickReactionDefaults = ['👍', '❤️', '😂', '🔥', '👏', '💡'];
const quickReactionPalette = [
  '👍', '❤️', '😂', '🔥', '👏', '💡',
  '😮', '😢', '🙏', '🎉', '🤔', '👀',
  '🚀', '✨', '💯', '✅', '❌', '🎵',
  '🎬', '📄', '💻', '👑', '☀️', '🌈',
  '🌟', '🎈', '🎁', '🍕', '☕', '💼',
];

export const ChatPage: React.FC<ChatPageProps> = ({ currentUser, onBack }) => {
  const { parseCommand, confirmCommand, cancelCommand } = useActionCommands();
  const [activeActionDraft, setActiveActionDraft] = useState<any | null>(null);

  // Lista de conversas e conversa selecionada
  const [conversations, setConversations] = useState<any[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [typingUsers, setTypingUsers] = useState<Record<number, string[]>>({});
  const [unreadCounts, setUnreadCounts] = useState<Record<number, number>>({});

  const sendSystemMessage = async (body: string) => {
    if (!selectedConversationId) return;
    try {
      await fetch(`/api/v1/chat/conversations/${selectedConversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          body,
          message_type: 'TEXT',
          file_ids: [],
          mentions: [],
          is_ephemeral: false,
          visibility_mode: 'NORMAL'
        }),
      });
      loadMessages(selectedConversationId);
    } catch (err) {
      console.error('Erro ao enviar mensagem de sistema:', err);
    }
  };

  const handleConfirmAction = async (draftId: string, overrideData?: any): Promise<ActionCommandDraft> => {
    try {
      const result = await confirmCommand(draftId, overrideData);
      setActiveActionDraft(result);
      if (result.status === 'EXECUTED') {
        sendSystemMessage(`[Ação Executada] ${result.preview?.Resultado || 'Ação executada com sucesso.'}`);
        setActiveActionDraft(null);
      } else if (result.status === 'FAILED') {
        sendSystemMessage(`[Ação Falhou] ${result.error_message || 'Falhou'}`);
        setActiveActionDraft(null);
      } else if (result.status === 'APPROVAL_REQUIRED') {
        sendSystemMessage(`[Aprovação Solicitada] Solicitação de aprovação criada para: ${result.preview?.Produto || 'Ação'}`);
        setActiveActionDraft(null);
      }
      return result;
    } catch (err: any) {
      showChatToast(err.message || 'Erro ao confirmar ação.');
      throw err;
    }
  };

  const handleCancelAction = async (draftId: string): Promise<ActionCommandDraft> => {
    try {
      const result = await cancelCommand(draftId);
      setActiveActionDraft(null);
      showChatToast('Ação cancelada.');
      return result;
    } catch (err: any) {
      showChatToast(err.message || 'Erro ao cancelar ação.');
      throw err;
    }
  };

  // Modais de Criação
  const [showChannelModal, setShowChannelModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showDMModal, setShowDMModal] = useState(false);
  const [channelForm, setChannelForm] = useState({ name: '', description: '', is_private: false });
  const [groupForm, setGroupForm] = useState({ name: '', member_ids: [] as number[] });
  const [dmSearch, setDmSearch] = useState('');
  const [dmUsers, setDmUsers] = useState<any[]>([]);

  // Modos de Envio e composer
  const [messageText, setMessageText] = useState('');
  const [messageVisibilityMode, setMessageVisibilityMode] = useState<string>('NORMAL'); // NORMAL, ONCE, TEMP_1H, TEMP_24H, TEMP_7D, AUDIT
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFileIds, setUploadedFileIds] = useState<number[]>([]);
  const [uploadedFilesPreview, setUploadedFilesPreview] = useState<any[]>([]);

  // Seleção Múltipla (Exclusão / Encaminhamento em lote)
  const [selectedMessageIds, setSelectedMessageIds] = useState<number[]>([]);
  const [isSelectionMode, setIsSelectionMode] = useState(false);

  // Modal de Encaminhamento
  const [forwardModalOpen, setForwardModalOpen] = useState(false);
  const [messageToForward, setMessageToForward] = useState<number | null>(null);

  // Lightbox e Galeria
  const [mediaGallery, setMediaGallery] = useState<any[]>([]);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const [galleryOpen, setGalleryOpen] = useState(false);

  // Perfil Flutuante
  const [activeProfileUser, setActiveProfileUser] = useState<any | null>(null);

  // Pesquisa local e global
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchFilters, setSearchFilters] = useState({
    userId: '',
    hasAttachments: false,
    messageType: ''
  });

  // Painel do MESSIAS
  const [messiasPanelOpen, setMessiasPanelOpen] = useState(false);
  const [messiasSpecialMessages, setMessiasSpecialMessages] = useState<any[]>([]);
  const [simulationUser, setSimulationUser] = useState<any | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [systemUsers, setSystemUsers] = useState<any[]>([]);
  const [replyToMessage, setReplyToMessage] = useState<any | null>(null);
  const [editingMessage, setEditingMessage] = useState<any | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: number; mode: 'ME' | 'EVERYONE' } | null>(null);
  const [messageTypeMenuOpen, setMessageTypeMenuOpen] = useState(false);
  const [chatToast, setChatToast] = useState<string | null>(null);

  // Customização de Emojis de Reação e Scroll Inteligente
  const [preferredEmojis, setPreferredEmojis] = useState<string[]>(quickReactionDefaults);
  const [showEmojiConfigModal, setShowEmojiConfigModal] = useState(false);
  const [emojiInputs, setEmojiInputs] = useState<string[]>(quickReactionDefaults);
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState(false);
  const chatMessagesRef = useRef<HTMLDivElement>(null);
  const prevConvIdRef = useRef<number | null>(null);

  // Estados adicionais de personalização e scroll aprimorado
  const [selectedSlotIndex, setSelectedSlotIndex] = useState<number>(0);
  const [chatTheme, setChatTheme] = useState<string>('purple'); // purple, blue, green, rose, dark
  const [chatWallpaper, setChatWallpaper] = useState<string>('gradient'); // gradient, grid, dark-pure, warm
  const [sendShortcut, setSendShortcut] = useState<string>('enter'); // enter, ctrl-enter
  const [newMessagesCount, setNewMessagesCount] = useState<number>(0);
  const lastMessageIdRef = useRef<number | null>(null);

  // Inicializa preferências do localStorage baseadas no usuário logado
  useEffect(() => {
    if (!currentUser) return;
    const userId = currentUser.id || 'guest';
    
    // Emojis preferidos
    const savedEmojis = localStorage.getItem(`vesper_chat_preferred_reactions_${userId}`);
    if (savedEmojis) {
      try {
        const parsed = JSON.parse(savedEmojis);
        if (Array.isArray(parsed) && parsed.length === 6) {
          setPreferredEmojis(parsed);
          setEmojiInputs(parsed);
        }
      } catch (e) {
        console.error(e);
      }
    } else {
      // Compatibilidade retroativa ou valores padrão
      const savedLegacy = localStorage.getItem('vesper_chat_preferred_reactions');
      if (savedLegacy) {
        try {
          const parsed = JSON.parse(savedLegacy);
          if (Array.isArray(parsed) && parsed.length === 6) {
            setPreferredEmojis(parsed);
            setEmojiInputs(parsed);
          }
        } catch (e) {
          console.error(e);
        }
      }
    }

    // Tema
    const savedTheme = localStorage.getItem(`vesper_chat_theme_${userId}`);
    if (savedTheme) {
      setChatTheme(savedTheme);
    }

    // Wallpaper
    const savedWallpaper = localStorage.getItem(`vesper_chat_wallpaper_${userId}`);
    if (savedWallpaper) {
      setChatWallpaper(savedWallpaper);
    }

    // Atalho de envio
    const savedShortcut = localStorage.getItem(`vesper_chat_send_shortcut_${userId}`);
    if (savedShortcut) {
      setSendShortcut(savedShortcut);
    }
  }, [currentUser]);

  const handleScroll = () => {
    const container = chatMessagesRef.current;
    if (!container) return;
    const isFar = container.scrollHeight - container.scrollTop - container.clientHeight > 300;
    setShowScrollBottomBtn(isFar);
    
    // Se o usuário rolou manualmente até perto do fim, zera o contador de novas mensagens não vistas
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 120;
    if (isNearBottom) {
      setNewMessagesCount(0);
    }
  };

  const handleScrollToBottom = () => {
    const container = chatMessagesRef.current;
    if (container) {
      container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
      setShowScrollBottomBtn(false);
      setNewMessagesCount(0);
    }
  };

  const handleSavePreferences = (
    newEmojis: string[],
    newTheme: string,
    newWallpaper: string,
    newShortcut: string
  ) => {
    if (!currentUser) return;
    const userId = currentUser.id || 'guest';
    const clean = newEmojis.map(e => e.trim()).filter(e => e !== '');
    
    if (clean.length === 6) {
      setPreferredEmojis(clean);
      localStorage.setItem(`vesper_chat_preferred_reactions_${userId}`, JSON.stringify(clean));
    }
    
    setChatTheme(newTheme);
    localStorage.setItem(`vesper_chat_theme_${userId}`, newTheme);
    
    setChatWallpaper(newWallpaper);
    localStorage.setItem(`vesper_chat_wallpaper_${userId}`, newWallpaper);
    
    setSendShortcut(newShortcut);
    localStorage.setItem(`vesper_chat_send_shortcut_${userId}`, newShortcut);
    
    setShowEmojiConfigModal(false);
    showChatToast('Personalização salva com sucesso!');
  };

  const handleOpenGeneralConfig = () => {
    setEmojiInputs([...preferredEmojis]);
    setSelectedSlotIndex(0);
    setShowEmojiConfigModal(true);
  };

  const loadSystemUsers = async () => {
    try {
      const res = await fetch('/api/v1/chat/users/search');
      if (res.ok) {
        const data = await res.json();
        const isCurrentUserMessias = currentUser?.role === 'MESSIAS' || currentUser?.username === 'MESSIAS';
        setSystemUsers(data.filter((u: any) => u.id !== currentUser?.id && u.username !== 'MESSIAS' && (isCurrentUserMessias || (u.role_name !== 'MESSIAS' && u.role !== 'MESSIAS'))));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const isMessias = currentUser?.role === 'MESSIAS';
  const isStaff = currentUser?.role === 'ADMIN' || currentUser?.role === 'MESSIAS';
  const isReadOnly = currentUser?.role === 'READ_ONLY' || simulationUser !== null;

  const messageModeLabels: Record<string, string> = {
    NORMAL: 'Mensagem normal',
    ONCE: 'Mensagem única',
    TEMP_1H: 'Expira em 1h',
    TEMP_24H: 'Expira em 24h',
    AUDIT: 'Comunicado',
  };

  const showChatToast = (message: string) => {
    setChatToast(message);
    window.setTimeout(() => setChatToast(null), 2600);
  };

  // Carrega conversas
  const loadConversations = async () => {
    try {
      const res = await fetch('/api/v1/chat/conversations');
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Carrega mensagens da conversa ativa
  const loadMessages = async (convId: number) => {
    try {
      const res = await fetch(`/api/v1/chat/conversations/${convId}/messages?limit=100`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.slice().reverse());
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Marca conversa como lida
  const markAsRead = async (convId: number) => {
    try {
      await fetch(`/api/v1/chat/conversations/${convId}/read`, { method: 'POST' });
      setUnreadCounts(prev => ({ ...prev, [convId]: 0 }));
      loadConversations();
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadConversations();
    loadSystemUsers();
  }, [simulationUser]);

  useEffect(() => {
    if (selectedConversationId) {
      loadMessages(selectedConversationId);
      markAsRead(selectedConversationId);
      setSelectedMessageIds([]);
      setIsSelectionMode(false);
      setReplyToMessage(null);
      setEditingMessage(null);
    } else {
      setMessages([]);
      setReplyToMessage(null);
      setEditingMessage(null);
    }
  }, [selectedConversationId, simulationUser]);

  // Rolar inteligente para o final do feed
  useEffect(() => {
    const container = chatMessagesRef.current;
    if (!container) return;

    const isDifferentConv = selectedConversationId !== prevConvIdRef.current;
    prevConvIdRef.current = selectedConversationId;

    const lastMsg = messages[messages.length - 1];
    const lastMsgId = lastMsg ? lastMsg.id : null;
    const isNewMessage = lastMsgId !== lastMessageIdRef.current;
    lastMessageIdRef.current = lastMsgId;

    if (isDifferentConv) {
      container.scrollTop = container.scrollHeight;
      setShowScrollBottomBtn(false);
      setNewMessagesCount(0);
      return;
    }

    if (isNewMessage && lastMsg) {
      const isOwnLastMsg = lastMsg.sender_user_id === currentUser.id;
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 250;

      if (isOwnLastMsg) {
        // Se eu enviei a mensagem, rola para o fim com suavidade
        setTimeout(() => {
          container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
        }, 50);
        setNewMessagesCount(0);
      } else if (isNearBottom) {
        // Se outra pessoa enviou e eu já estava perto do fim, rola para o fim
        setTimeout(() => {
          container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
        }, 50);
        setNewMessagesCount(0);
      } else {
        // Se outra pessoa enviou e eu estava rolando para cima, não rola, mas ativa a indicação
        setShowScrollBottomBtn(true);
        setNewMessagesCount(prev => prev + 1);
      }
    }
  }, [messages, selectedConversationId, currentUser.id]);

  // WebSocket Integration
  const connectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProto}//${window.location.host}/api/v1/ws/chat`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (event.data === 'pong') return;
      try {
        const payload = JSON.parse(event.data);
        const { type, data } = payload;

        switch (type) {
          case 'chat.message.created':
            if (data.conversation_id === selectedConversationId) {
              setMessages((prev) => {
                if (prev.some((m) => m.id === data.id)) return prev;
                return [...prev, data];
              });
              markAsRead(data.conversation_id);
            } else {
              setUnreadCounts(prev => ({ ...prev, [data.conversation_id]: (prev[data.conversation_id] || 0) + 1 }));
            }
            loadConversations();
            break;

          case 'chat.message.updated':
            if (data.conversation_id === selectedConversationId) {
              setMessages((prev) => prev.map((m) => (m.id === data.id ? { ...m, body: data.body, is_edited: true, edit_history: data.edit_history } : m)));
            }
            break;

          case 'chat.message.deleted':
            if (data.conversation_id === selectedConversationId) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === data.id
                    ? { ...m, is_deleted: true, body: '[Mensagem Apagada]', deleted_at: data.deleted_at }
                    : m
                )
              );
            }
            break;

          case 'chat.message.reaction.created':
          case 'chat.message.reaction.deleted':
            if (data.conversation_id === selectedConversationId) {
              setMessages((prev) =>
                prev.map((m) => (m.id === data.message_id ? { ...m, reactions: data.reactions } : m))
              );
            }
            break;

          case 'chat.message.once_viewed':
            if (data.conversation_id === selectedConversationId) {
              setMessages((prev) =>
                prev.map((m) => (m.id === data.id ? { ...m, viewed_by_users: data.viewed_by_users } : m))
              );
            }
            break;

          case 'chat.typing.started':
            setTypingUsers((prev) => {
              const current = prev[data.conversation_id] || [];
              if (current.includes(data.username)) return prev;
              return { ...prev, [data.conversation_id]: [...current, data.username] };
            });
            break;

          case 'chat.typing.stopped':
            setTypingUsers((prev) => {
              const current = prev[data.conversation_id] || [];
              return {
                ...prev,
                [data.conversation_id]: current.filter((u) => u !== data.username),
              };
            });
            break;

          default:
            break;
        }
      } catch (err) {
        console.error(err);
      }
    };

    ws.onclose = () => {
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 4000);
    };
  };

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [selectedConversationId]);

  // Enviar Mensagem
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!messageText.trim() && uploadedFileIds.length === 0) || !selectedConversationId || isReadOnly) return;

    // Intercepta comandos de ação do Portal
    const textLower = messageText.toLowerCase();
    const commandVerbs = ["cotar", "atualizar", "preço", "preco", "respondeu", "chamado", "abrir", "solicitar", "move", "mover", "cria", "criar", "procura", "buscar", "remover", "apagar", "desconto", "pdf", "senha", "skymail", "travando", "pc", "computador", "impressora", "op"];
    const hasCommandKeyword = commandVerbs.some(word => textLower.includes(word)) || messageText.startsWith("/");
    
    if (hasCommandKeyword && !uploadedFileIds.length && !editingMessage) {
      try {
        const draft = await parseCommand(messageText, 'chat', { module: 'chat' });
        if (draft && draft.action_key && (draft.action_key !== 'master_data.item.search' || textLower.includes('buscar') || textLower.includes('procura') || textLower.includes('item'))) {
          setActiveActionDraft(draft);
          setMessageText('');
          return;
        }
      } catch (err) {
        console.error('Erro ao analisar comando no chat:', err);
      }
    }

    if (editingMessage) {
      try {
        const res = await fetch(`/api/v1/chat/messages/${editingMessage.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ body: messageText }),
        });
        if (res.ok) {
          setMessageText('');
          setEditingMessage(null);
          loadMessages(selectedConversationId);
        }
      } catch (err) {
        console.error(err);
      }
      return;
    }

    let expiresSeconds = undefined;
    if (messageVisibilityMode === 'TEMP_1H') expiresSeconds = 3600;
    if (messageVisibilityMode === 'TEMP_24H') expiresSeconds = 86400;
    if (messageVisibilityMode === 'TEMP_7D') expiresSeconds = 604800;

    const payload = {
      body: messageText,
      message_type: uploadedFileIds.length > 0 ? 'IMAGE' : 'TEXT',
      file_ids: uploadedFileIds,
      mentions: [],
      parent_message_id: replyToMessage?.id,
      is_ephemeral: messageVisibilityMode.startsWith('TEMP_'),
      expires_in_seconds: expiresSeconds,
      visibility_mode: messageVisibilityMode === 'ONCE' ? 'ONCE' : messageVisibilityMode === 'AUDIT' ? 'AUDIT' : 'NORMAL'
    };

    try {
      const res = await fetch(`/api/v1/chat/conversations/${selectedConversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setMessageText('');
        setMessageVisibilityMode('NORMAL');
        setUploadedFileIds([]);
        setUploadedFilesPreview([]);
        setReplyToMessage(null);
        loadMessages(selectedConversationId);
        loadConversations();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Upload de arquivos
  const handleUploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !selectedConversationId) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', files[0]);

    try {
      const res = await fetch(`/api/v1/chat/conversations/${selectedConversationId}/attachments`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        setUploadedFileIds([...uploadedFileIds, data.file_id]);
        setUploadedFilesPreview([...uploadedFilesPreview, { name: files[0].name, id: data.file_id }]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveAttachment = (idToRemove: number) => {
    setUploadedFileIds(prev => prev.filter(id => id !== idToRemove));
    setUploadedFilesPreview(prev => prev.filter(item => item.id !== idToRemove));
  };

  const handleReact = async (messageId: number, emoji: string) => {
    try {
      await fetch(`/api/v1/chat/messages/${messageId}/reactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emoji })
      });
      loadMessages(selectedConversationId!);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemoveReact = async (messageId: number, emoji: string) => {
    try {
      await fetch(`/api/v1/chat/messages/${messageId}/reactions?emoji=${encodeURIComponent(emoji)}`, {
        method: 'DELETE'
      });
      loadMessages(selectedConversationId!);
    } catch (err) {
      console.error(err);
    }
  };

  // Abrir mensagem de visualização única
  const handleOpenOnce = async (id: number) => {
    try {
      await fetch(`/api/v1/chat/messages/${id}/open-once`, { method: 'POST' });
      loadMessages(selectedConversationId!);
    } catch (err) {
      console.error(err);
    }
  };

  // Excluir mensagem (para mim ou para todos)
  const handleDeleteMessage = async (id: number, type: 'ME' | 'EVERYONE') => {
    const endpoint = type === 'ME' ? `/api/v1/chat/messages/${id}/delete-for-me` : `/api/v1/chat/messages/${id}/delete-for-everyone`;
    try {
      await fetch(endpoint, { method: 'POST' });
      loadMessages(selectedConversationId!);
      showChatToast('Mensagem apagada.');
    } catch (err) {
      console.error(err);
    }
  };

  const handleCopyMessage = async (body?: string) => {
    if (!body) return;
    try {
      await navigator.clipboard.writeText(body);
      showChatToast('Mensagem copiada.');
    } catch {
      showChatToast('Não foi possível copiar a mensagem.');
    }
  };

  // Excluir em Lote
  const handleBulkDelete = async (type: 'ME' | 'EVERYONE') => {
    if (selectedMessageIds.length === 0) return;
    try {
      await fetch(`/api/v1/chat/messages/delete-selected?delete_type=${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selectedMessageIds)
      });
      setSelectedMessageIds([]);
      setIsSelectionMode(false);
      loadMessages(selectedConversationId!);
    } catch (err) {
      console.error(err);
    }
  };

  // Encaminhar mensagem
  const handleForwardMessage = async (convId: number) => {
    if (!messageToForward) return;
    try {
      await fetch(`/api/v1/chat/messages/${messageToForward}/forward?target_conversation_id=${convId}`, {
        method: 'POST'
      });
      setForwardModalOpen(false);
      setMessageToForward(null);
      showChatToast('Mensagem encaminhada.');
    } catch (err) {
      console.error(err);
    }
  };

  // Exportar conversa
  const handleExportChat = (id: number) => {
    window.open(`/api/v1/chat/conversations/${id}/export`, '_blank');
  };

  // Buscar Galeria de Mídias
  const handleOpenGallery = async () => {
    if (!selectedConversationId) return;
    try {
      const res = await fetch(`/api/v1/chat/conversations/${selectedConversationId}/media`);
      if (res.ok) {
        const data = await res.json();
        setMediaGallery(data);
        setGalleryOpen(true);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Pesquisar mensagens
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    let url = `/api/v1/chat/search?q=${encodeURIComponent(searchQuery)}`;
    if (selectedConversationId) {
      url += `&conversation_id=${selectedConversationId}`;
    }
    try {
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.messages || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Carrega Usuários para DM/Grupo
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

  const handleCreateChannelSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/v1/chat/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'CHANNEL',
          name: channelForm.name,
          description: channelForm.description,
          is_private: channelForm.is_private
        })
      });
      if (res.ok) {
        setShowChannelModal(false);
        setChannelForm({ name: '', description: '', is_private: false });
        loadConversations();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateGroupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/v1/chat/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'GROUP',
          name: groupForm.name,
          member_ids: groupForm.member_ids
        })
      });
      if (res.ok) {
        setShowGroupModal(false);
        setGroupForm({ name: '', member_ids: [] });
        loadConversations();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleStartDM = async (userId: number) => {
    try {
      const res = await fetch('/api/v1/chat/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'DM',
          member_ids: [userId]
        })
      });
      if (res.ok) {
        const newConv = await res.json();
        setSelectedConversationId(newConv.id);
        setShowDMModal(false);
        loadConversations();
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Simulação do MESSIAS
  const handleStartSimulation = async (userId: number, username: string) => {
    try {
      await fetch(`/api/v1/chat/messias/view-as-user/start?target_user_id=${userId}`, { method: 'POST' });
      setSimulationUser({ id: userId, username });
      setMessiasPanelOpen(false);
      loadConversations();
    } catch (err) {
      console.error(err);
    }
  };

  const handleStopSimulation = async () => {
    try {
      await fetch('/api/v1/chat/messias/view-as-user/stop', { method: 'POST' });
      setSimulationUser(null);
      loadConversations();
    } catch (err) {
      console.error(err);
    }
  };

  // Carregar mensagens especiais do MESSIAS
  const handleOpenMessiasPanel = async () => {
    setMessiasPanelOpen(true);
    try {
      const res = await fetch('/api/v1/chat/messias/special-messages');
      if (res.ok) {
        const data = await res.json();
        setMessiasSpecialMessages(data);
      }
      const uRes = await fetch('/api/v1/chat/users/search');
      if (uRes.ok) {
        const data = await uRes.json();
        setDmUsers(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Abrir Perfil Flutuante
  const handleOpenProfile = async (username: string) => {
    try {
      // Mock de informações adicionais do perfil (setor, ramal, email)
      setActiveProfileUser({
        username,
        email: `${username.toLowerCase()}@portal.local`,
        sector: 'Tecnologia da Informação',
        ramal: '4002',
        status: 'Online'
      });
    } catch (err) {
      console.error(err);
    }
  };

  const selectedConv = conversations.find(c => c.id === selectedConversationId);

  return (
    <div className="chat-module module-page">
      <CompactModuleHeader
        icon={<IconMessageDots size={20} />}
        title="Chat Interno"
        description="Comunicação em tempo real, canais de equipe, mensagens diretas e compartilhamento de mídias."
      />

      {simulationUser && (
        <div className="chat-simulation-banner">
          <span>Visualizando como {simulationUser.username} (somente leitura)</span>
          <Button size="sm" variant="secondary" onClick={handleStopSimulation}>Parar simulação</Button>
        </div>
      )}

      <div className={`chat-module-grid ${(selectedConv && showDetails) ? '' : 'chat-module-grid--no-details'}`}>
        <div className="chat-sidebar-panel">
          <div className="chat-sidebar-header">
            <h2>Conversas</h2>
            <div className="chat-sidebar-actions">
              {isMessias && (
                <button type="button" className="chat-icon-btn" onClick={handleOpenMessiasPanel} title="Auditoria MESSIAS">
                  <IconShieldExclamation size={16} />
                </button>
              )}
              {!isReadOnly && (
                <>
                  <button type="button" className="chat-icon-btn" onClick={() => setShowChannelModal(true)} title="Novo canal">
                    <IconHash size={16} />
                  </button>
                  <button type="button" className="chat-icon-btn" onClick={handleOpenGroup} title="Novo grupo">
                    <IconUsers size={16} />
                  </button>
                </>
              )}
              <button type="button" className="chat-icon-btn" onClick={handleOpenGeneralConfig} title="Personalização do Chat">
                <IconSettings size={16} />
              </button>
            </div>
          </div>

          <div className="chat-search-row">
            <input
              type="text"
              placeholder="Buscar nas mensagens..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button type="button" className="chat-icon-btn" onClick={handleSearch}>
              <IconSearch size={14} />
            </button>
          </div>

          <div className="chat-conv-list">
            {/* Seção de Canais e Grupos */}
            <div className="chat-section-header" style={{ padding: '8px 12px 4px', fontSize: 10, fontWeight: 900, textTransform: 'uppercase', color: '#64748b', letterSpacing: 0.5 }}>
              Canais e Grupos
            </div>
            {conversations.filter(c => c.type === 'CHANNEL' || c.type === 'GROUP').map((c) => {
              const isActive = c.id === selectedConversationId;
              const count = unreadCounts[c.id] || c.unread_count || 0;
              return (
                <div
                  key={c.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => setSelectedConversationId(c.id)}
                  onKeyDown={(e) => e.key === 'Enter' && setSelectedConversationId(c.id)}
                  className={`chat-conv-item ${isActive ? 'active' : ''}`}
                >
                  <div style={{ minWidth: 0 }}>
                    <strong>{c.type === 'CHANNEL' ? `# ${c.name}` : c.name || 'Conversa'}</strong>
                    {c.last_message && (
                      <span className="preview">
                        {c.last_message.is_deleted ? 'Mensagem apagada' : c.last_message.body}
                      </span>
                    )}
                  </div>
                  {count > 0 && <span className="chat-unread-badge">{count}</span>}
                </div>
              );
            })}
            {conversations.filter(c => c.type === 'CHANNEL' || c.type === 'GROUP').length === 0 && (
              <div style={{ padding: '6px 12px', fontSize: 11, color: '#475569', fontStyle: 'italic' }}>Nenhum canal/grupo</div>
            )}

            {/* Seção de Mensagens Diretas (Todos os usuários do sistema) */}
            <div className="chat-section-header" style={{ padding: '16px 12px 4px', fontSize: 10, fontWeight: 900, textTransform: 'uppercase', color: '#64748b', letterSpacing: 0.5 }}>
              Mensagens Diretas
            </div>
            {systemUsers.filter(u => u.username.toLowerCase().includes(searchQuery.toLowerCase())).map((u) => {
              const activeConv = conversations.find(c => c.type === 'DM' && c.members?.some((m: any) => m.id === u.id));
              const isActive = activeConv ? activeConv.id === selectedConversationId : false;
              const count = activeConv ? (unreadCounts[activeConv.id] || activeConv.unread_count || 0) : 0;
              const lastMsg = activeConv?.last_message;

              const handleClick = () => {
                if (activeConv) {
                  setSelectedConversationId(activeConv.id);
                } else {
                  handleStartDM(u.id);
                }
              };

              return (
                <div
                  key={u.id}
                  role="button"
                  tabIndex={0}
                  onClick={handleClick}
                  onKeyDown={(e) => e.key === 'Enter' && handleClick()}
                  className={`chat-conv-item ${isActive ? 'active' : ''}`}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ color: '#10b981', fontSize: 10 }} title="Online">●</span>
                      <strong>{u.username}</strong>
                      <span style={{ fontSize: 10, color: '#64748b' }}>({u.sector || 'Geral'})</span>
                    </div>
                    {lastMsg ? (
                      <span className="preview">
                        {lastMsg.is_deleted ? 'Mensagem apagada' : lastMsg.body}
                      </span>
                    ) : (
                      <span className="preview" style={{ color: '#475569', fontStyle: 'italic' }}>Clique para iniciar conversa</span>
                    )}
                  </div>
                  {count > 0 && <span className="chat-unread-badge">{count}</span>}
                </div>
              );
            })}
            {systemUsers.filter(u => u.username.toLowerCase().includes(searchQuery.toLowerCase())).length === 0 && (
              <div style={{ padding: '6px 12px', fontSize: 11, color: '#475569', fontStyle: 'italic' }}>Nenhum usuário encontrado</div>
            )}
          </div>
        </div>

        <div className="chat-main-panel">
        {selectedConv ? (
          <>
            <div className="chat-thread-header">
              <div>
                <h3>{selectedConv.type === 'CHANNEL' ? `# ${selectedConv.name}` : selectedConv.name || 'Conversa'}</h3>
                <span className="text-muted" style={{ fontSize: 12 }}>
                  {selectedConv.members?.length || 0} participantes
                </span>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <Button size="sm" variant="secondary" onClick={handleOpenGallery}>Mídias</Button>
                <Button size="sm" variant="ghost" onClick={() => handleExportChat(selectedConv.id)}>Exportar</Button>
                <Button size="sm" variant="ghost" onClick={() => setShowDetails((v) => !v)}>
                  {showDetails ? 'Ocultar detalhes' : 'Detalhes'}
                </Button>
              </div>
            </div>

            {/* Painel de Mensagens Fixadas */}
            {messages.filter(m => m.is_pinned).length > 0 && (
              <div className="glass-card p-3 border-b border-yellow-500/20 bg-yellow-500/5 flex justify-between items-center" style={{ borderRadius: 0 }}>
                <div className="flex items-center gap-2 text-xs font-bold text-yellow-300">
                  <IconPin size={14} />
                  <span>Fixado: <span className="underline">{messages.filter(m => m.is_pinned)[0].body}</span></span>
                </div>
              </div>
            )}

            <div className={`chat-messages chat-wallpaper-${chatWallpaper}`} ref={chatMessagesRef} onScroll={handleScroll}>
              {messages.map((msg) => {
                const isOwn = msg.sender_user_id === currentUser.id;
                const isDeleted = msg.is_deleted;
                const hasOnceOpened = msg.visibility_mode === 'ONCE' && (msg.viewed_by_users || []).includes(currentUser.id);

                return (
                  <div key={msg.id} className={`chat-message-row ${isOwn ? 'own' : ''}`}>
                    <div className={`chat-bubble ${isOwn ? 'own' : ''} chat-theme-${chatTheme}`} style={{ maxWidth: 'min(520px, 85%)' }}>
                      <span className="sender" onClick={() => handleOpenProfile(msg.sender_username)} role="button" tabIndex={0}>
                        {msg.sender_username}
                      </span>
                      <div className="relative group">
                        {/* Mensagem Especial Badge */}
                        {msg.visibility_mode === 'ONCE' && (
                          <span className="text-[9px] bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 px-1.5 py-0.5 rounded font-extrabold block mb-2 w-fit">
                            👁️ VISUALIZAÇÃO ÚNICA
                          </span>
                        )}
                        {msg.is_ephemeral && (
                          <span className="text-[9px] bg-orange-500/10 border border-orange-500/30 text-orange-300 px-1.5 py-0.5 rounded font-extrabold block mb-2 w-fit">
                            ⏱️ MENSAGEM TEMPORÁRIA
                          </span>
                        )}

                        {/* Corpo da Mensagem */}
                        {isDeleted ? (
                          <span className="text-xs font-bold text-red-500 line-through">[Mensagem Apagada]</span>
                        ) : msg.visibility_mode === 'ONCE' && !hasOnceOpened && !isOwn ? (
                          <div className="space-y-2">
                            <span className="text-xs font-bold block text-slate-200">Conteúdo oculto por segurança.</span>
                            <Button size="sm" variant="primary" onClick={() => handleOpenOnce(msg.id)}>
                              Revelar Mensagem
                            </Button>
                          </div>
                        ) : msg.visibility_mode === 'ONCE' && hasOnceOpened && !isOwn ? (
                          <span className="text-xs font-bold text-slate-400 italic">[Mensagem de visualização única aberta e destruída]</span>
                        ) : (
                          <p>{msg.body}</p>
                        )}

                        {/* Render de Anexos */}
                        {msg.attachments && msg.attachments.map((att: any) => {
                          const url = `/api/v1/chat/attachments/${att.id}/download`;
                          const ext = att.original_filename.split('.').pop()?.toLowerCase() || '';
                          const isImage = att.attachment_type === 'IMAGE' || ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext);
                          const isVideo = att.attachment_type === 'VIDEO' || ['mp4', 'webm', 'mov', 'avi'].includes(ext);
                          const isAudio = att.attachment_type === 'AUDIO' || ['mp3', 'wav', 'ogg', 'm4a'].includes(ext);
                          
                          if (isImage) {
                            return (
                              <div key={att.id} className="chat-message-image-container mt-2">
                                <a href={url} target="_blank" rel="noreferrer" title="Visualizar imagem">
                                  <img src={url} alt={att.original_filename} className="chat-message-image" />
                                </a>
                              </div>
                            );
                          }

                          if (isVideo) {
                            return (
                              <div key={att.id} className="chat-message-video-container mt-2">
                                <video src={url} controls className="chat-message-video" />
                              </div>
                            );
                          }

                          if (isAudio) {
                            return (
                              <div key={att.id} className="chat-message-audio-container mt-2">
                                <audio src={url} controls className="chat-message-audio" />
                              </div>
                            );
                          }

                          // Helper local para ícones semânticos de documentos
                          const getDocumentSymbol = (filename: string) => {
                            const extension = filename.split('.').pop()?.toLowerCase();
                            if (extension === 'pdf') return <span title="PDF" style={{ marginRight: 4 }}>📕</span>;
                            if (['xlsx', 'xls', 'csv'].includes(extension || '')) return <span title="Planilha" style={{ marginRight: 4 }}>📗</span>;
                            if (['zip', 'rar', '7z'].includes(extension || '')) return <span title="Compactado" style={{ marginRight: 4 }}>📙</span>;
                            return <IconFileText size={16} className="text-slate-400" />;
                          };

                          return (
                            <div key={att.id} className="mt-2 border-t border-white/5 pt-2 flex items-center gap-2">
                              {getDocumentSymbol(att.original_filename)}
                              <a href={url} target="_blank" rel="noreferrer" className="text-xs font-bold text-sky-400 hover:underline">
                                {att.original_filename}
                              </a>
                            </div>
                          );
                        })}

                        {/* Exibição de reações na bolha */}
                        {msg.reactions && msg.reactions.length > 0 && (
                          <div className="chat-message-reactions-list">
                            {Array.from(new Set(msg.reactions.map((r: any) => r.emoji))).map((emoji: any) => {
                              const count = msg.reactions.filter((r: any) => r.emoji === emoji).length;
                              const userReacted = msg.reactions.some((r: any) => r.emoji === emoji && r.user_id === currentUser.id);
                              
                              return (
                                <button
                                  key={emoji}
                                  type="button"
                                  className={`chat-message-reaction-badge ${userReacted ? 'active' : ''}`}
                                  onClick={() => {
                                    if (userReacted) {
                                      handleRemoveReact(msg.id, emoji);
                                    } else {
                                      handleReact(msg.id, emoji);
                                    }
                                  }}
                                  title={`${msg.reactions
                                    .filter((r: any) => r.emoji === emoji)
                                    .map((r: any) => r.username)
                                    .join(', ')} reagiu(aram) com ${emoji}`}
                                >
                                  <span>{emoji}</span>
                                  <span className="count">{count}</span>
                                </button>
                              );
                            })}
                          </div>
                        )}

                        {/* Opções Hover da Mensagem */}
                        {!isReadOnly && !isDeleted && (
                          <MessageActionToolbar
                            canEdit={isOwn}
                            canDelete={isOwn || isStaff}
                            onReply={() => { setReplyToMessage(msg); setEditingMessage(null); }}
                            onForward={() => { setMessageToForward(msg.id); setForwardModalOpen(true); }}
                            onCopy={() => handleCopyMessage(msg.body)}
                            onDelete={() => setDeleteConfirm({ id: msg.id, mode: isOwn || isStaff ? 'EVERYONE' : 'ME' })}
                            onEdit={() => { setEditingMessage(msg); setMessageText(msg.body); setReplyToMessage(null); }}
                          />
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {replyToMessage && <ReplyPreview message={replyToMessage} onCancel={() => setReplyToMessage(null)} />}
            {editingMessage && (
              <div className="reply-preview">
                <div>
                  <strong>Editando mensagem</strong>
                  <p>{editingMessage.body}</p>
                </div>
                <button type="button" className="chat-icon-btn" onClick={() => { setEditingMessage(null); setMessageText(''); }}>
                  <IconX size={14} />
                </button>
              </div>
            )}

            {/* Visualização de Anexos na fila de Upload */}
            {(uploadedFilesPreview.length > 0 || isUploading) && (
              <div className="chat-composer-attachments-preview">
                {uploadedFilesPreview.map((file) => {
                  const ext = file.name.split('.').pop()?.toLowerCase() || '';
                  const isImg = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext);
                  const isVid = ['mp4', 'webm', 'mov', 'avi'].includes(ext);
                  const isAud = ['mp3', 'wav', 'ogg', 'm4a'].includes(ext);
                  const tempUrl = `/api/v1/chat/attachments/file/${file.id}/download`;
                  
                  return (
                    <div key={file.id} className="attachment-preview-item group/preview">
                      <a href={tempUrl} target="_blank" rel="noreferrer" className="attachment-preview-link" title="Clique para pré-visualizar">
                        {isImg ? (
                          <img src={tempUrl} alt={file.name} className="attachment-preview-thumb" />
                        ) : isVid ? (
                          <div className="attachment-preview-doc" style={{ background: 'rgba(168, 85, 247, 0.08)' }}>
                            <span style={{ fontSize: 20 }} title="Vídeo">🎬</span>
                            <span className="attachment-preview-name" title={file.name}>{file.name}</span>
                          </div>
                        ) : isAud ? (
                          <div className="attachment-preview-doc" style={{ background: 'rgba(16, 185, 129, 0.08)' }}>
                            <span style={{ fontSize: 20 }} title="Áudio">🎵</span>
                            <span className="attachment-preview-name" title={file.name}>{file.name}</span>
                          </div>
                        ) : (
                          <div className="attachment-preview-doc">
                            <span style={{ fontSize: 20 }} title="Documento">📄</span>
                            <span className="attachment-preview-name" title={file.name}>{file.name}</span>
                          </div>
                        )}
                        <div className="attachment-preview-overlay">
                          <span>Ver</span>
                        </div>
                      </a>
                      <button
                        type="button"
                        className="attachment-preview-remove"
                        onClick={() => handleRemoveAttachment(file.id)}
                        title="Remover anexo"
                      >
                        <IconX size={10} />
                      </button>
                    </div>
                  );
                })}
                {isUploading && (
                  <div className="attachment-preview-item loading-item">
                    <div className="chat-upload-spinner" />
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Enviando...</span>
                  </div>
                )}
              </div>
            )}

            {activeActionDraft && (
              <div className="px-5 py-3 border-t border-gray-900 bg-gray-950/40 flex justify-center w-full">
                <ActionCommandCard
                  draft={activeActionDraft}
                  onConfirm={handleConfirmAction}
                  onCancel={handleCancelAction}
                  onSuccess={(res) => {
                    if (res.status === 'EXECUTED') {
                      sendSystemMessage(`[Ação Executada] ${res.preview?.Resultado || 'Ação executada com sucesso.'}`);
                      setActiveActionDraft(null);
                    } else if (res.status === 'FAILED') {
                      sendSystemMessage(`[Ação Falhou] ${res.error_message || 'Falhou'}`);
                      setActiveActionDraft(null);
                    } else if (res.status === 'APPROVAL_REQUIRED') {
                      sendSystemMessage(`[Aprovação Solicitada] Solicitação de aprovação criada para: ${res.preview?.Produto || 'Ação'}`);
                      setActiveActionDraft(null);
                    }
                  }}
                  isAdmin={currentUser?.role === 'ADMIN'}
                />
              </div>
            )}

            <form onSubmit={handleSendMessage} className="chat-composer">
              <div className="chat-composer-tools" style={{ display: 'none' }}>
                {[
                  { key: 'NORMAL', label: 'Normal' },
                  { key: 'ONCE', label: 'Única' },
                  { key: 'TEMP_1H', label: '1h' },
                  { key: 'TEMP_24H', label: '24h' },
                  { key: 'AUDIT', label: 'Comunicado' },
                ].map((mode) => (
                  <button
                    key={mode.key}
                    type="button"
                    className={`product-chip ${messageVisibilityMode === mode.key ? 'active' : ''}`}
                    style={{ padding: '6px 10px', fontSize: 11 }}
                    onClick={() => setMessageVisibilityMode(mode.key)}
                  >
                    {mode.label}
                  </button>
                ))}
              </div>
              <div className="message-type-menu">
                <button
                  type="button"
                  className="chat-icon-btn"
                  aria-label="Tipo de mensagem"
                  title={`Tipo atual: ${messageModeLabels[messageVisibilityMode]}`}
                  onClick={() => setMessageTypeMenuOpen((value) => !value)}
                >
                  <IconDotsVertical size={18} />
                </button>
                {messageTypeMenuOpen && (
                  <div className="message-type-menu__panel">
                    {Object.entries(messageModeLabels).map(([key, label]) => (
                      <button
                        key={key}
                        type="button"
                        className={messageVisibilityMode === key ? 'active' : ''}
                        onClick={() => {
                          setMessageVisibilityMode(key);
                          setMessageTypeMenuOpen(false);
                        }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <label className="chat-icon-btn" style={{ cursor: 'pointer' }} title="Anexar arquivo" aria-label="Anexar arquivo">
                <IconPaperclip size={18} />
                <input type="file" style={{ display: 'none' }} onChange={handleUploadFile} />
              </label>
              <textarea
                placeholder={`${messageModeLabels[messageVisibilityMode]} - digite sua mensagem...`}
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                onKeyDown={(e) => {
                  if (sendShortcut === 'enter') {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage(e);
                    }
                  } else if (sendShortcut === 'ctrl-enter') {
                    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                      e.preventDefault();
                      handleSendMessage(e);
                    }
                  }
                }}
              />
              <Button type="submit" variant="primary" className="chat-composer-send" disabled={(!messageText.trim() && uploadedFileIds.length === 0) || isReadOnly} rightIcon={<IconSend size={16} />}>
                Enviar
              </Button>
            </form>
          </>
        ) : (
          <div className="chat-empty-center flex flex-col items-center justify-center text-center p-8 space-y-6 h-full bg-slate-900/10 backdrop-blur-md rounded-2xl border border-white/5">
            <KodaMascot size="lg" mood="chat" className="mb-2" />
            <div className="max-w-md space-y-2">
              <h3 className="text-xl font-bold text-white">Central de Mensagens do Portal</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Olá! Sou o Koda. Selecione um canal de equipe ou inicie uma nova conversa direta para compartilhar ideias, arquivos e acompanhar chamados de TI.
              </p>
            </div>
            {!isReadOnly && (
              <div className="flex flex-wrap justify-center gap-3 pt-2">
                <Button variant="primary" size="sm" onClick={() => setShowChannelModal(true)} leftIcon={<IconHash size={15} />}>
                  Criar Canal
                </Button>
              </div>
            )}
          </div>
        )}
        </div>

        {selectedConv && showDetails && (
          <div className="chat-details-panel">
            <ConversationDetailsDrawer
              conversation={selectedConv}
              currentUser={currentUser}
              onClose={() => setShowDetails(false)}
              onArchive={() => loadConversations()}
              onRemoveMember={async () => loadConversations()}
              onAddMembers={async () => loadConversations()}
              pinnedMessages={messages.filter((m) => m.is_pinned)}
              onUnpin={() => selectedConversationId && loadMessages(selectedConversationId)}
            />
          </div>
        )}
      </div>



      {/* Modais */}

      {chatToast && <div className="chat-toast">{chatToast}</div>}

      {deleteConfirm && (
        <Modal
          isOpen={true}
          onClose={() => setDeleteConfirm(null)}
          title="Apagar mensagem?"
          size="sm"
          footer={
            <>
              <Button variant="ghost" onClick={() => setDeleteConfirm(null)}>
                Cancelar
              </Button>
              <Button
                variant="danger"
                onClick={() => {
                  handleDeleteMessage(deleteConfirm.id, deleteConfirm.mode);
                  setDeleteConfirm(null);
                }}
              >
                Apagar
              </Button>
            </>
          }
        >
          <p style={{ color: '#cbd5e1', margin: 0, fontSize: 14 }}>
            Essa ação não pode ser desfeita. A conversa será atualizada para todos que têm permissão de ver a mensagem.
          </p>
        </Modal>
      )}

      {/* 1. Modal de Encaminhamento de Mensagem */}
      {forwardModalOpen && (
        <Modal isOpen={true} onClose={() => setForwardModalOpen(false)} title="Encaminhar Mensagem" size="md">
          <div className="space-y-4">
            <p className="text-sm font-semibold text-slate-300">Selecione o canal ou DM para onde deseja encaminhar a mensagem:</p>
            <div className="space-y-2 max-h-60 overflow-y-auto pr-1 custom-scroll">
              {conversations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => handleForwardMessage(c.id)}
                  className="w-full p-3 border border-slate-700/30 rounded-xl bg-slate-900/30 hover:bg-slate-800/30 text-left text-white text-sm flex justify-between items-center transition-colors"
                >
                  <span>{c.name || 'Conversa'}</span>
                  <IconChevronRight size={16} className="text-slate-400" />
                </button>
              ))}
            </div>
          </div>
        </Modal>
      )}

      {/* 2. Lightbox / Galeria de Mídias */}
      {galleryOpen && (
        <Modal isOpen={true} onClose={() => setGalleryOpen(false)} title="Galeria de Arquivos e Mídias" size="lg">
          <div className="grid grid-cols-3 gap-2 max-h-96 overflow-y-auto p-1 custom-scroll">
            {mediaGallery.map((m, index) => (
              <div key={index} className="border border-slate-700/30 rounded-lg overflow-hidden cursor-pointer hover:opacity-90 transition-opacity" onClick={() => setLightboxIndex(index)}>
                <img src={`/api/v1/chat/attachments/${m.attachment_id}/download`} alt={m.filename} className="w-full h-24 object-cover" />
              </div>
            ))}
            {mediaGallery.length === 0 && (
              <p className="text-center font-semibold col-span-3 text-slate-400 py-12">Nenhuma imagem ou mídia enviada nesta conversa.</p>
            )}
          </div>
        </Modal>
      )}

      {/* 3. Perfil Flutuante */}
      {activeProfileUser && (
        <Modal isOpen={true} onClose={() => setActiveProfileUser(null)} title="Ficha do Usuário" size="sm">
          <div className="space-y-4 text-center">
            <div className="w-20 h-20 rounded-full border border-slate-700/30 bg-slate-800/40 flex items-center justify-center text-4xl mx-auto">
              👤
            </div>
            <div>
              <h4 className="text-xl font-bold text-white">{activeProfileUser.username}</h4>
              <span className="text-xs font-semibold text-slate-400 uppercase">{activeProfileUser.sector}</span>
            </div>
            <div className="glass-panel p-4 border border-slate-700/30 rounded-xl text-left text-xs space-y-2 text-slate-300">
              <div>E-mail: <span className="text-white">{activeProfileUser.email}</span></div>
              <div>Ramal: <span className="text-white">{activeProfileUser.ramal}</span></div>
              <div>Status: <span className="text-emerald-400">● {activeProfileUser.status}</span></div>
            </div>
            <div className="flex gap-2 justify-center pt-2">
              <Button size="sm" variant="primary" onClick={() => setActiveProfileUser(null)}>
                Iniciar DM
              </Button>
              <Button size="sm" variant="ghost" disabled title="Chamadas ao vivo em fase futura.">
                📞 Ligar
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* 4. Painel do MESSIAS */}
      {messiasPanelOpen && (
        <Modal isOpen={true} onClose={() => setMessiasPanelOpen(false)} title="Painel de Auditoria MESSIAS" size="lg">
          <div className="space-y-6">
            {/* Visualizar como usuário */}
            <div className="glass-card p-4 border border-yellow-500/20 bg-yellow-500/5">
              <h4 className="font-semibold text-md mb-2 text-yellow-300">🎭 Visualizar como outro usuário (Simulação)</h4>
              <div className="flex flex-wrap gap-2">
                {dmUsers.map(u => (
                  <Button
                    key={u.id}
                    onClick={() => handleStartSimulation(u.id, u.username)}
                    size="sm"
                    variant="primary"
                  >
                    Simular {u.username}
                  </Button>
                ))}
              </div>
            </div>

            {/* Listagem de Mensagens Especiais */}
            <div className="space-y-3">
              <h4 className="font-semibold text-md text-white">📑 Auditoria de Mensagens Especiais (Apagadas/Editadas/Temporárias)</h4>
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1 custom-scroll">
                {messiasSpecialMessages.map((m) => (
                  <div key={m.id} className="glass-card p-3 border border-slate-700/30 text-xs space-y-1 text-slate-300">
                    <div className="flex justify-between font-semibold text-slate-400">
                      <span>Remetente: {m.sender_username} | Chat: {m.conversation_name}</span>
                      <span>Modo: {m.visibility_mode}</span>
                    </div>
                    <p className="text-sm font-semibold text-white">{m.body}</p>
                    {m.is_deleted && <span className="text-[10px] text-red-400 font-bold block">❌ MENSAGEM APAGADA</span>}
                    {m.is_edited && <span className="text-[10px] text-purple-400 font-bold block">✏️ MENSAGEM EDITADA</span>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* MODAL CRIAR CANAL */}
      {showChannelModal && (
        <Modal isOpen={true} onClose={() => setShowChannelModal(false)} title="Criar Novo Canal" size="sm">
          <form onSubmit={handleCreateChannelSubmit} className="space-y-3">
            <Input label="Nome do Canal" value={channelForm.name} onChange={(e: any) => setChannelForm({ ...channelForm, name: e.target.value })} required />
            <Textarea label="Descrição" value={channelForm.description} onChange={(e: any) => setChannelForm({ ...channelForm, description: e.target.value })} rows={2} />
            <label className="flex items-center gap-2 font-bold text-xs cursor-pointer">
              <input type="checkbox" checked={channelForm.is_private} onChange={(e: any) => setChannelForm({ ...channelForm, is_private: e.target.checked })} />
              Canal Privado (Apenas membros selecionados)
            </label>
            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="ghost" onClick={() => setShowChannelModal(false)}>Cancelar</Button>
              <Button type="submit" variant="success">Criar Canal</Button>
            </div>
          </form>
        </Modal>
      )}

      {/* MODAL CRIAR GRUPO */}
      {showGroupModal && (
        <Modal isOpen={true} onClose={() => setShowGroupModal(false)} title="Criar Novo Grupo" size="sm">
          <form onSubmit={handleCreateGroupSubmit} className="space-y-3">
            <Input label="Nome do Grupo" value={groupForm.name} onChange={(e: any) => setGroupForm({ ...groupForm, name: e.target.value })} required />
            <div className="space-y-2">
              <label className="font-bold text-xs">Selecionar Membros</label>
              <div className="border border-slate-700/30 rounded-lg bg-slate-900/30 p-2 max-h-40 overflow-y-auto space-y-1 custom-scroll">
                {dmUsers.map(u => {
                  const selected = groupForm.member_ids.includes(u.id);
                  return (
                    <div
                      key={u.id}
                      onClick={() => {
                        if (selected) {
                          setGroupForm({ ...groupForm, member_ids: groupForm.member_ids.filter(id => id !== u.id) });
                        } else {
                          setGroupForm({ ...groupForm, member_ids: [...groupForm.member_ids, u.id] });
                        }
                      }}
                      className={`p-2 rounded border border-slate-700/30 cursor-pointer text-xs transition-colors ${
                        selected ? 'bg-sky-500/20 text-white font-bold' : 'text-slate-300 hover:bg-slate-800/20'
                      }`}
                    >
                      {u.username}
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="ghost" onClick={() => setShowGroupModal(false)}>Cancelar</Button>
              <Button type="submit" variant="success">Criar Grupo</Button>
            </div>
          </form>
        </Modal>
      )}

      {/* MODAL INICIAR DM */}
      {showDMModal && (
        <Modal isOpen={true} onClose={() => setShowDMModal(false)} title="Iniciar Nova Conversa Direta" size="sm">
          <div className="space-y-3">
            <Input label="Buscar Usuário" value={dmSearch} onChange={(e: any) => {
              setDmSearch(e.target.value);
              fetch(`/api/v1/chat/users/search?q=${encodeURIComponent(e.target.value)}`).then(res => res.json()).then(setDmUsers);
            }} />
            <div className="space-y-2 max-h-48 overflow-y-auto custom-scroll">
              {dmUsers.map(u => (
                <div
                  key={u.id}
                  onClick={() => handleStartDM(u.id)}
                  className="p-3 rounded-lg border border-slate-700/30 bg-slate-900/30 hover:bg-slate-800/30 cursor-pointer text-sm text-white flex justify-between items-center transition-colors"
                >
                  <span>{u.username}</span>
                  <IconChevronRight size={14} className="text-slate-400" />
                </div>
              ))}
            </div>
          </div>
        </Modal>
      )}

      {/* Botão flutuante para descer (Scroll to Bottom) */}
      {showScrollBottomBtn && (
        <button 
          type="button" 
          className="chat-scroll-bottom-btn" 
          onClick={handleScrollToBottom} 
          title="Rolar para baixo"
          aria-label="Rolar para baixo"
        >
          <IconChevronRight size={18} style={{ transform: 'rotate(90deg)' }} />
          {newMessagesCount > 0 && (
            <span className="chat-scroll-bottom-badge">{newMessagesCount}</span>
          )}
        </button>
      )}

      {/* Modal de Personalização do Chat */}
      {showEmojiConfigModal && (
        <Modal
          isOpen={true}
          onClose={() => setShowEmojiConfigModal(false)}
          title="Configuracoes e Personalizacao do Chat"
          size="md"
          footer={
            <>
              <Button variant="ghost" onClick={() => setShowEmojiConfigModal(false)}>
                Cancelar
              </Button>
              <Button variant="success" onClick={() => handleSavePreferences(emojiInputs, chatTheme, chatWallpaper, sendShortcut)}>
                Salvar configuracoes
              </Button>
            </>
          }
        >
          <div className="chat-config-panel">
            
            {/* Emojis Rápidos */}
            <div className="chat-config-section">
              <strong className="chat-config-title">Emojis de reacao rapida</strong>
              <span className="chat-config-help">
                Selecione um slot abaixo e clique em qualquer emoji da paleta para personaliza-lo:
              </span>
              
              <div className="chat-config-slots">
                {emojiInputs.map((val, idx) => {
                  const isSelected = selectedSlotIndex === idx;
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setSelectedSlotIndex(idx)}
                      className={`chat-config-emoji-slot ${isSelected ? 'is-selected' : ''}`}
                    >
                      {val || ' '}
                    </button>
                  );
                })}
              </div>

              <div className="chat-config-emoji-palette">
                <div className="chat-config-emoji-grid">
                  {quickReactionPalette.map((emoji) => (
                    <button
                      key={emoji}
                      type="button"
                      onClick={() => {
                        const newInputs = [...emojiInputs];
                        newInputs[selectedSlotIndex] = emoji;
                        setEmojiInputs(newInputs);
                        // Avança automaticamente para o próximo slot
                        setSelectedSlotIndex((selectedSlotIndex + 1) % 6);
                      }}
                      className="chat-config-emoji-btn"
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Tema Visual */}
            <div className="chat-config-section">
              <strong className="chat-config-title">Tema das bolhas enviadas</strong>
              <div className="chat-config-choice-grid chat-config-choice-grid--five">
                {[
                  { key: 'purple', name: 'Roxo Vesper', color: '#8b5cf6' },
                  { key: 'blue', name: 'Azul Celeste', color: '#0ea5e9' },
                  { key: 'green', name: 'Verde Esmeralda', color: '#10b981' },
                  { key: 'rose', name: 'Rosa Sunset', color: '#f43f5e' },
                  { key: 'dark', name: 'Grafite Minimal', color: '#64748b' }
                ].map((themeOpt) => {
                  const isActive = chatTheme === themeOpt.key;
                  return (
                    <button
                      key={themeOpt.key}
                      type="button"
                      onClick={() => setChatTheme(themeOpt.key)}
                      className={`chat-config-choice ${isActive ? 'is-selected' : ''}`}
                    >
                      <span 
                        className="chat-config-color-dot" 
                        style={{ background: themeOpt.color }} 
                      />
                      <span>{themeOpt.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Papel de Parede */}
            <div className="chat-config-section">
              <strong className="chat-config-title">Plano de fundo do Chat</strong>
              <div className="chat-config-choice-grid">
                {[
                  { key: 'gradient', name: 'Clássico adaptável' },
                  { key: 'grid', name: 'Grade Fina' },
                  { key: 'dark-pure', name: 'Liso neutro' },
                  { key: 'warm', name: 'Gradiente Quente' }
                ].map((wallOpt) => {
                  const isActive = chatWallpaper === wallOpt.key;
                  return (
                    <button
                      key={wallOpt.key}
                      type="button"
                      onClick={() => setChatWallpaper(wallOpt.key)}
                      className={`chat-config-choice chat-config-choice--compact ${isActive ? 'is-selected' : ''}`}
                    >
                      {wallOpt.name}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Comportamento de Envio */}
            <div className="chat-config-section chat-config-section--last">
              <strong className="chat-config-title">Atalho para envio</strong>
              <div className="chat-config-radio-grid">
                <label className="chat-config-radio">
                  <input
                    type="radio"
                    name="shortcut"
                    value="enter"
                    checked={sendShortcut === 'enter'}
                    onChange={() => setSendShortcut('enter')}
                    className="accent-purple-500"
                  />
                  <div>
                    <strong>Apenas Enter</strong>
                    <span>Enter envia, Shift+Enter pula linha</span>
                  </div>
                </label>
                
                <label className="chat-config-radio">
                  <input
                    type="radio"
                    name="shortcut"
                    value="ctrl-enter"
                    checked={sendShortcut === 'ctrl-enter'}
                    onChange={() => setSendShortcut('ctrl-enter')}
                    className="accent-purple-500"
                  />
                  <div>
                    <strong>Ctrl + Enter</strong>
                    <span>Ctrl+Enter envia, Enter pula linha</span>
                  </div>
                </label>
              </div>
            </div>

          </div>
        </Modal>
      )}
    </div>
  );
};

export default ChatPage;
