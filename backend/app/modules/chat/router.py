from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastApiFile
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.models.chat import (
    ChatConversationMember,
    ChatMessage,
    ChatMessageAttachment,
    ChatMessiasAudit,
    ChatConversationLink,
    ChatMention
)
from app.modules.chat.schemas import (
    ChatConversationResponse,
    ChatConversationCreateRequest,
    ChatConversationUpdateRequest,
    ChatMessageResponse,
    ChatMessageCreateRequest,
    ChatMessageUpdateRequest,
    ChatReactionRequest,
    ChatMessiasAuditResponse,
    MentionSearchItemResponse,
    ChatSearchResponse
)
from app.modules.chat.service import ChatService
from app.modules.chat.repository import ChatRepository
from app.modules.chat.permissions import ChatPermissions
from app.modules.chat.mentions import ChatMentionsManager
from app.modules.chat.attachments import ChatAttachmentsManager
from app.modules.chat.messias import ChatMessiasManager


router = APIRouter()


def _serialize_chat_message(
    db: Session,
    msg: ChatMessage,
    current_user: User,
    effective_user: Optional[User] = None,
    include_messias_history: Optional[bool] = None,
) -> Dict[str, Any]:
    """Retorna uma mensagem no contrato público usado pelo frontend."""
    viewer = effective_user or ChatMessiasManager.get_effective_user(db, current_user)
    is_messias = ChatPermissions.is_messias(current_user) if include_messias_history is None else include_messias_history

    attachments_data = []
    for att in msg.attachments:
        if not att.file:
            continue
        attachments_data.append({
            "id": att.id,
            "file_id": att.file_id,
            "original_filename": att.file.original_filename,
            "size_bytes": att.file.size_bytes,
            "content_type": att.file.content_type,
            "attachment_type": att.attachment_type,
            "created_at": att.created_at,
        })

    reactions_data = []
    for reaction in msg.reactions:
        reactions_data.append({
            "id": reaction.id,
            "user_id": reaction.user_id,
            "username": reaction.user.username if reaction.user else "Usuario removido",
            "emoji": reaction.emoji,
            "created_at": reaction.created_at,
        })

    mentions_data = []
    for mention in msg.mentions:
        has_access = ChatMentionsManager.validate_mention_access(
            db,
            mention.mention_type,
            mention.target_id,
            mention.target_slug,
            viewer,
        )
        mentions_data.append({
            "id": mention.id,
            "mention_type": mention.mention_type,
            "target_id": mention.target_id,
            "target_slug": mention.target_slug,
            "display_label": mention.display_label if has_access else "Conteudo restrito",
            "created_at": mention.created_at,
        })

    edit_history = None
    if is_messias and msg.is_edited:
        edit_history = []
        for version in msg.versions:
            edit_history.append({
                "id": version.id,
                "message_id": version.message_id,
                "previous_body": version.previous_body,
                "new_body": version.new_body,
                "edited_by_user_id": version.edited_by_user_id,
                "edited_by_username": version.editor.username if version.editor else "Usuario removido",
                "edited_at": version.edited_at,
            })

    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_user_id": msg.sender_user_id,
        "sender_username": msg.sender.username if msg.sender else "Usuario removido",
        "parent_message_id": msg.parent_message_id,
        "message_type": msg.message_type,
        "body": msg.body,
        "is_edited": msg.is_edited,
        "is_deleted": msg.is_deleted,
        "is_pinned": msg.is_pinned,
        "is_ephemeral": msg.is_ephemeral,
        "expires_at": msg.expires_at,
        "reply_count": msg.reply_count,
        "created_at": msg.created_at,
        "updated_at": msg.updated_at,
        "deleted_at": msg.deleted_at,
        "deleted_by_user_id": msg.deleted_by_user_id,
        "reactions": reactions_data,
        "mentions": mentions_data,
        "attachments": attachments_data,
        "edit_history": edit_history,
    }


# ==========================================
# 1. ROTAS DE CONVERSAS (CHANNELS, DMs, GROUPS)
# ==========================================

@router.get("/conversations", response_model=List[ChatConversationResponse])
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna todas as conversas nas quais o usuário logado tem acesso.
    """
    effective_user = ChatMessiasManager.get_effective_user(db, current_user)
    conversations = ChatRepository.list_user_conversations(db, effective_user.id)
    
    response = []
    for conv in conversations:
        try:
            detail = ChatService.get_conversation_detail(db, conv.id, current_user)
            response.append(detail)
        except Exception:
            pass
            
    return response


@router.post("/conversations", response_model=ChatConversationResponse)
def create_conversation(
    payload: ChatConversationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cria uma nova conversa do tipo CHANNEL, GROUP ou DM.
    """
    conv = ChatService.create_conversation(
        db=db,
        creator=current_user,
        conv_type=payload.type,
        name=payload.name,
        description=payload.description,
        is_private=payload.is_private,
        member_ids=payload.member_ids
    )
    return ChatService.get_conversation_detail(db, conv.id, current_user)


@router.get("/conversations/{conversation_id}", response_model=ChatConversationResponse)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna os detalhes de uma conversa específica.
    """
    return ChatService.get_conversation_detail(db, conversation_id, current_user)


@router.patch("/conversations/{conversation_id}", response_model=ChatConversationResponse)
def update_conversation(
    conversation_id: int,
    payload: ChatConversationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atualiza as informações de uma conversa (canal ou grupo). Exige ser moderador.
    """
    ChatMessiasManager.verify_write_block(current_user)
    
    conversation = ChatPermissions.check_view_conversation(db, conversation_id, current_user)
    if not ChatPermissions.can_moderate_conversation(db, conversation, current_user):
        raise HTTPException(status_code=403, detail="Você não tem permissão para alterar as configurações desta conversa.")
        
    if payload.name is not None:
        conversation.name = payload.name
    if payload.description is not None:
        conversation.description = payload.description
    if payload.is_private is not None:
        conversation.is_private = payload.is_private
        
    db.commit()
    return ChatService.get_conversation_detail(db, conversation_id, current_user)


@router.post("/conversations/{conversation_id}/archive")
def archive_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Arquiva uma conversa ativa.
    """
    ChatMessiasManager.verify_write_block(current_user)
    conversation = ChatPermissions.check_view_conversation(db, conversation_id, current_user)
    if not ChatPermissions.can_moderate_conversation(db, conversation, current_user):
        raise HTTPException(status_code=403, detail="Você não tem permissão para arquivar esta conversa.")
        
    conversation.is_archived = True
    conversation.archived_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "message": "Conversa arquivada com sucesso."}


@router.post("/conversations/{conversation_id}/restore")
def restore_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Restaura uma conversa arquivada.
    """
    ChatMessiasManager.verify_write_block(current_user)
    conversation = ChatPermissions.check_view_conversation(db, conversation_id, current_user)
    if not ChatPermissions.can_moderate_conversation(db, conversation, current_user):
        raise HTTPException(status_code=403, detail="Você não tem permissão para restaurar esta conversa.")
        
    conversation.is_archived = False
    conversation.archived_at = None
    db.commit()
    return {"status": "success", "message": "Conversa restaurada com sucesso."}


# ==========================================
# 2. ROTAS DE MEMBROS
# ==========================================

@router.get("/conversations/{conversation_id}/members")
def get_conversation_members(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista todos os membros de uma conversa específica.
    """
    effective_user = ChatMessiasManager.get_effective_user(db, current_user)
    ChatPermissions.check_view_conversation(db, conversation_id, effective_user)
    
    members = db.query(ChatConversationMember).filter(
        ChatConversationMember.conversation_id == conversation_id,
        ChatConversationMember.archived_at == None
    ).all()
    
    response = []
    for m in members:
        # Mascara a role MESSIAS
        role_name = "ADMIN" if m.user.role and m.user.role.name == "MESSIAS" else (m.user.role.name if m.user.role else "USER")
        response.append({
            "user_id": m.user_id,
            "username": m.user.username,
            "role": m.role,
            "system_role": role_name,
            "joined_at": m.joined_at
        })
    return response


@router.post("/conversations/{conversation_id}/members")
def add_conversation_member(
    conversation_id: int,
    user_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Adiciona novos membros a um canal ou grupo. Exige privilégios de moderação.
    """
    ChatMessiasManager.verify_write_block(current_user)
    conversation = ChatPermissions.check_view_conversation(db, conversation_id, current_user)
    if not ChatPermissions.can_moderate_conversation(db, conversation, current_user):
        raise HTTPException(status_code=403, detail="Você não tem permissão para gerenciar membros desta conversa.")
        
    for uid in user_ids:
        # Verifica se já é membro
        existing = ChatRepository.get_conversation_member(db, conversation_id, uid)
        if not existing:
            u = db.query(User).filter(User.id == uid, User.is_active == True).first()
            if u:
                db.add(ChatConversationMember(
                    conversation_id=conversation_id,
                    user_id=uid,
                    role="MEMBER"
                ))
    db.commit()
    return {"status": "success", "message": "Membros adicionados com sucesso."}


@router.delete("/conversations/{conversation_id}/members/{user_id}")
def remove_conversation_member(
    conversation_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove um membro de um canal ou grupo. Exige moderação.
    """
    ChatMessiasManager.verify_write_block(current_user)
    conversation = ChatPermissions.check_view_conversation(db, conversation_id, current_user)
    if not ChatPermissions.can_moderate_conversation(db, conversation, current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para remover este membro.")
        
    member = ChatRepository.get_conversation_member(db, conversation_id, user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Membro não encontrado nesta conversa.")
        
    member.archived_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "message": "Membro removido com sucesso."}


# ==========================================
# 3. ROTAS DE MENSAGENS E THREADS
# ==========================================

@router.get("/conversations/{conversation_id}/messages", response_model=List[ChatMessageResponse])
def get_messages(
    conversation_id: int,
    limit: int = 50,
    before_message_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista as mensagens paginadas da conversa.
    Se o usuário for MESSIAS, inclui mensagens apagadas e o histórico de edições.
    """
    effective_user = ChatMessiasManager.get_effective_user(db, current_user)
    ChatPermissions.check_view_conversation(db, conversation_id, effective_user)
    
    is_messias = ChatPermissions.is_messias(current_user)
    
    messages = ChatRepository.list_messages(
        db=db,
        conversation_id=conversation_id,
        limit=limit,
        before_message_id=before_message_id,
        is_messias=is_messias
    )

    return [
        _serialize_chat_message(
            db,
            msg,
            current_user=current_user,
            effective_user=effective_user,
            include_messias_history=is_messias,
        )
        for msg in messages
    ]
    
    response = []
    for msg in messages:
        # Prepara anexos
        attachments_data = []
        for att in msg.attachments:
            attachments_data.append({
                "id": att.id,
                "file_id": att.file_id,
                "original_filename": att.file.original_filename,
                "size_bytes": att.file.size_bytes,
                "content_type": att.file.content_type,
                "attachment_type": att.attachment_type,
                "created_at": att.created_at
            })
            
        # Prepara reações
        reactions_data = []
        for r in msg.reactions:
            reactions_data.append({
                "id": r.id,
                "user_id": r.user_id,
                "username": r.user.username,
                "emoji": r.emoji,
                "created_at": r.created_at
            })
            
        # Prepara menções
        mentions_data = []
        for men in msg.mentions:
            # Valida se o usuário logado tem permissão para ler o objeto mencionado
            has_access = ChatMentionsManager.validate_mention_access(db, men.mention_type, men.target_id, men.target_slug, effective_user)
            display_label = men.display_label if has_access else "Conteúdo restrito (sem acesso)"
            
            mentions_data.append({
                "id": men.id,
                "mention_type": men.mention_type,
                "target_id": men.target_id,
                "target_slug": men.target_slug,
                "display_label": display_label,
                "created_at": men.created_at
            })
            
        # Prepara versões de edição para o MESSIAS
        edit_history = None
        if is_messias and msg.is_edited:
            edit_history = []
            for ver in msg.versions:
                edit_history.append({
                    "id": ver.id,
                    "message_id": ver.message_id,
                    "previous_body": ver.previous_body,
                    "new_body": ver.new_body,
                    "edited_by_user_id": ver.edited_by_user_id,
                    "edited_by_username": ver.editor.username,
                    "edited_at": ver.edited_at
                })
                
        response.append({
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_user_id": msg.sender_user_id,
            "sender_username": msg.sender.username,
            "parent_message_id": msg.parent_message_id,
            "message_type": msg.message_type,
            "body": msg.body,
            "is_edited": msg.is_edited,
            "is_deleted": msg.is_deleted,
            "is_pinned": msg.is_pinned,
            "is_ephemeral": msg.is_ephemeral,
            "expires_at": msg.expires_at,
            "reply_count": msg.reply_count,
            "created_at": msg.created_at,
            "updated_at": msg.updated_at,
            "deleted_at": msg.deleted_at,
            "deleted_by_user_id": msg.deleted_by_user_id,
            "reactions": reactions_data,
            "mentions": mentions_data,
            "attachments": attachments_data,
            "edit_history": edit_history
        })
        
    return response


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageResponse)
def send_message(
    conversation_id: int,
    payload: ChatMessageCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Envia uma nova mensagem no chat.
    """
    mentions_dict = [m.model_dump() for m in payload.mentions]
    msg = ChatService.send_message(
        db=db,
        conversation_id=conversation_id,
        sender=current_user,
        body=payload.body,
        parent_message_id=payload.parent_message_id,
        message_type=payload.message_type,
        file_ids=payload.file_ids,
        mentions=mentions_dict,
        is_ephemeral=payload.is_ephemeral,
        expires_in_seconds=payload.expires_in_seconds,
        visibility_mode=payload.visibility_mode
    )
    
    # Auto marca como lido para quem enviou
    ChatService.mark_as_read(db, conversation_id, current_user)
    
    # Carrega relações
    refreshed = db.query(ChatMessage).filter(ChatMessage.id == msg.id).first()
    return _serialize_chat_message(db, refreshed, current_user=current_user)


@router.patch("/messages/{message_id}", response_model=ChatMessageResponse)
def edit_message(
    message_id: int,
    payload: ChatMessageUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Edita o texto de uma mensagem que o próprio usuário enviou.
    """
    msg = ChatService.edit_message(db, message_id, current_user, payload.body)
    return _serialize_chat_message(db, msg, current_user=current_user)


@router.delete("/messages/{message_id}")
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exclui uma mensagem (soft delete).
    """
    ChatService.delete_message(db, message_id, current_user)
    return {"status": "success", "message": "Mensagem excluida com sucesso."}


@router.get("/messages/{message_id}/thread", response_model=List[ChatMessageResponse])
def get_thread_replies(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista todas as respostas (réplicas) em uma determinada thread de mensagem.
    """
    msg = ChatRepository.get_message(db, message_id)
    if not msg:
        raise HTTPException(status_code=404, detail="Mensagem raiz nao encontrada.")
        
    effective_user = ChatMessiasManager.get_effective_user(db, current_user)
    ChatPermissions.check_view_conversation(db, msg.conversation_id, effective_user)
    
    replies = db.query(ChatMessage).filter(
        ChatMessage.parent_message_id == message_id,
        ChatMessage.is_deleted == False
    ).order_by(ChatMessage.id.asc()).all()
    
    return [
        _serialize_chat_message(db, reply, current_user=current_user, effective_user=effective_user)
        for reply in replies
    ]


# ==========================================
# 4. REAÇÕES DE EMOJI
# ==========================================

@router.post("/messages/{message_id}/reactions")
def add_reaction(
    message_id: int,
    payload: ChatReactionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reage a uma mensagem de chat com um emoji.
    """
    ChatService.add_reaction(db, message_id, current_user, payload.emoji)
    return {"status": "success", "message": "Reação adicionada com sucesso."}


@router.delete("/messages/{message_id}/reactions")
def remove_reaction(
    message_id: int,
    emoji: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove uma reação emoji enviada anteriormente.
    """
    ChatService.remove_reaction(db, message_id, current_user, emoji)
    return {"status": "success", "message": "Reação removida com sucesso."}


# ==========================================
# 5. UPLOADS E ANEXOS SEGUROS
# ==========================================

@router.post("/conversations/{conversation_id}/attachments")
def upload_attachment(
    conversation_id: int,
    file: UploadFile = FastApiFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Realiza o upload seguro de um arquivo de mídia/documento para a conversa do chat.
    Garante o bloqueio de executáveis corporativos perigosos (.exe, .bat, .js, etc.).
    """
    ChatMessiasManager.verify_write_block(current_user)
    ChatPermissions.check_write_conversation(db, conversation_id, current_user)
    
    file_row = ChatAttachmentsManager.upload_attachment(db, conversation_id, file, current_user)
    
    return {
        "status": "success",
        "file_id": file_row.id,
        "original_filename": file_row.original_filename,
        "size_bytes": file_row.size_bytes,
        "content_type": file_row.content_type
    }


@router.get("/attachments/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint seguro para download de anexos do chat.
    Verifica se o usuário atual possui permissão de acesso à conversa do anexo.
    """
    att = db.query(ChatMessageAttachment).filter(ChatMessageAttachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")
        
    effective_user = ChatMessiasManager.get_effective_user(db, current_user)
    ChatPermissions.check_view_conversation(db, att.message.conversation_id, effective_user)
    
    from fastapi.responses import FileResponse
    path = ChatAttachmentsManager.UPLOAD_DIR / att.file.storage_key
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo físico indisponível no servidor local.")
        
    return FileResponse(
        path=str(path),
        filename=att.file.original_filename,
        media_type=att.file.content_type
    )


# ==========================================
# 6. BUSCA E AUTOCOMPLETE
# ==========================================

@router.get("/search", response_model=ChatSearchResponse)
def search_chat(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Realiza busca geral em conversas e corpo de mensagens nas quais o usuário possui permissão.
    """
    if not q.strip():
        return ChatSearchResponse(messages=[], conversations=[])
        
    effective_user = ChatMessiasManager.get_effective_user(db, current_user)
    term = f"%{q.strip().lower()}%"
    
    # 1. Filtra as conversas que ele pode visualizar
    conversations = ChatRepository.list_user_conversations(db, effective_user.id)
    conversation_ids = [c.id for c in conversations]
    
    # 2. Busca mensagens
    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id.in_(conversation_ids),
        ChatMessage.body_search.ilike(term),
        ChatMessage.is_deleted == False
    ).order_by(ChatMessage.created_at.desc()).limit(30).all()
    
    # 3. Busca conversas correspondentes por nome
    matched_convs = [c for c in conversations if q.lower() in (c.name or "").lower()]
    
    return {
        "messages": messages,
        "conversations": matched_convs
    }


@router.get("/mentions/search", response_model=List[MentionSearchItemResponse])
def search_mentions(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Busca autocomplete para menções inteligentes (@usuário, @módulo, @objeto TI, @objeto Kanban).
    Garante a filtragem rigorosa de permissão de visualização do usuário.
    """
    effective_user = ChatMessiasManager.get_effective_user(db, current_user)
    return ChatMentionsManager.search_mentions(db, q, effective_user)


@router.get("/users/search")
def search_chat_users(
    q: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Busca usuários ativos para iniciar novas DMs ou criar grupos.
    """
    term = f"%{q.strip()}%"
    query = db.query(User).filter(
        User.is_active == True,
        User.id != current_user.id
    )
    if not (current_user.role and current_user.role.name == "MESSIAS"):
        from app.models.role import Role
        query = query.outerjoin(Role).filter((Role.name != "MESSIAS") | (Role.id == None))

    users = query.filter(or_(User.username.ilike(term), User.email.ilike(term))).limit(15).all()
    
    response = []
    for u in users:
        # Mascara a role MESSIAS
        role_name = "ADMIN" if u.role and u.role.name == "MESSIAS" else (u.role.name if u.role else "USER")
        response.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role_name": role_name
        })
    return response


# ==========================================
# 7. LEITURA, NOTIFICAÇÕES E NÃO PERTURBE
# ==========================================

@router.post("/conversations/{conversation_id}/read")
def mark_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marca uma conversa como lida e propaga o status.
    """
    ChatService.mark_as_read(db, conversation_id, current_user)
    return {"status": "success", "message": "Conversa marcada como lida."}


@router.get("/unread-summary")
def get_unread_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna resumo quantitativo de mensagens não lidas e menções direcionadas.
    """
    effective_user = ChatMessiasManager.get_effective_user(db, current_user)
    conversations = ChatRepository.list_user_conversations(db, effective_user.id)
    
    total_unread = 0
    total_mentions = 0
    
    for conv in conversations:
        unread = ChatRepository.count_unread_messages(db, conv.id, effective_user.id)
        total_unread += unread
        
        # Somas menções específicas do usuário não lidas
        member = ChatRepository.get_conversation_member(db, conv.id, effective_user.id)
        if member and unread > 0:
            last_id = member.last_read_message_id or 0
            mentions_count = db.query(ChatMention).join(ChatMessage).filter(
                ChatMessage.conversation_id == conv.id,
                ChatMessage.id > last_id,
                ChatMention.mention_type == "USER",
                ChatMention.target_id == effective_user.id
            ).count()
            total_mentions += mentions_count
            
    return {
        "unread_count": total_unread,
        "mentions_count": total_mentions
    }


# ==========================================
# 8. INTEGRAÇÕES ENTRE MÓDULOS (TI / KANBAN)
# ==========================================

@router.post("/messages/{message_id}/create-it-ticket")
def create_it_ticket_from_message(
    message_id: int,
    priority: str = "MEDIA",
    category: str = "OUTRO",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Integração de TI: cria um Chamado de TI técnico a partir de uma mensagem de chat.
    A mensagem vira a descrição base e o solicitante vira o criador do chamado.
    """
    ChatMessiasManager.verify_write_block(current_user)
    
    message = ChatRepository.get_message(db, message_id)
    if not message or message.is_deleted:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")
        
    ChatPermissions.check_view_conversation(db, message.conversation_id, current_user)
    
    from app.modules.it.service import ITService
    from app.modules.it.schemas import TicketCreate
    
    # Cria o ticket
    payload = TicketCreate(
        title=f"Chamado aberto via Chat - Msg #{message.id}",
        description=message.body or "Sem conteúdo de texto.",
        priority=priority,
        category=category
    )
    
    ticket = ITService.create_ticket(db, payload, current_user)
    
    # Vincula na tabela de conexões do chat
    db.add(ChatConversationLink(
        conversation_id=message.conversation_id,
        message_id=message.id,
        module_slug="it",
        entity_type="it_ticket",
        entity_id=ticket.id,
        created_by_user_id=current_user.id
    ))
    db.commit()
    
    # Cria uma resposta informativa automática no chat da conversa
    ChatService.send_message(
        db=db,
        conversation_id=message.conversation_id,
        sender=current_user,
        message_type="SYSTEM",
        body=f"🎫 Chamado técnico **{ticket.ticket_number}** criado com sucesso a partir da mensagem anterior!"
    )
    
    return {
        "status": "success",
        "ticket_id": ticket.id,
        "ticket_number": ticket.ticket_number,
        "title": ticket.title
    }


@router.post("/messages/{message_id}/create-kanban-card")
def create_kanban_card_from_message(
    message_id: int,
    board_id: int,
    column_id: Optional[int] = None,
    priority: str = "MEDIUM",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Integração de Kanban: cria um card de operação no board Kanban a partir de uma mensagem de chat.
    """
    ChatMessiasManager.verify_write_block(current_user)
    
    message = ChatRepository.get_message(db, message_id)
    if not message or message.is_deleted:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada.")
        
    ChatPermissions.check_view_conversation(db, message.conversation_id, current_user)
    
    from app.modules.kanban.service import KanbanService
    from app.modules.kanban.schemas import CardCreate
    
    # Cria o card
    payload = CardCreate(
        title=f"Ação via Chat - Msg #{message.id}",
        description=message.body or "Mensagem do chat",
        column_id=column_id,
        priority=priority
    )
    
    card = KanbanService.create_card(db, board_id, payload, current_user)
    
    # Vincula no chat
    db.add(ChatConversationLink(
        conversation_id=message.conversation_id,
        message_id=message.id,
        module_slug="kanban",
        entity_type="kanban_card",
        entity_id=card.id,
        created_by_user_id=current_user.id
    ))
    db.commit()
    
    # Notifica na conversa
    ChatService.send_message(
        db=db,
        conversation_id=message.conversation_id,
        sender=current_user,
        message_type="SYSTEM",
        body=f"📋 Card Kanban **{card.title}** criado no quadro operacional!"
    )
    
    return {
        "status": "success",
        "card_id": card.id,
        "title": card.title
    }


# ==========================================
# 9. RECURSOS EXCLUSIVOS DO PAPEL MESSIAS
# ==========================================

@router.get("/messias/audit", response_model=List[ChatMessiasAuditResponse])
def get_messias_audits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna logs especiais de auditoria gerados por ações dos MESSIAS.
    Apenas acessível para usuários com a role real MESSIAS.
    """
    if not ChatPermissions.is_messias(current_user):
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas o MESSIAS possui permissão de auditoria.")
        
    logs = db.query(ChatMessiasAudit).order_by(ChatMessiasAudit.created_at.desc()).limit(100).all()
    
    # Prepara resposta populando os usernames dos envolvidos
    response = []
    for log in logs:
        m_user = db.query(User).filter(User.id == log.messias_user_id).first()
        t_user = db.query(User).filter(User.id == log.target_user_id).first() if log.target_user_id else None
        
        response.append({
            "id": log.id,
            "messias_user_id": log.messias_user_id,
            "messias_username": m_user.username if m_user else "Desconhecido",
            "action": log.action,
            "target_user_id": log.target_user_id,
            "target_username": t_user.username if t_user else None,
            "conversation_id": log.conversation_id,
            "message_id": log.message_id,
            "metadata": log.metadata_json,
            "created_at": log.created_at
        })
        
    # Loga que o próprio MESSIAS abriu a auditoria
    ChatRepository.create_messias_audit_log(
        db=db,
        messias_user_id=current_user.id,
        action="chat.messias.audit.opened"
    )
    db.commit()
    
    return response


@router.post("/messias/view-as-user/start")
def start_simulation(
    target_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Inicia sessão de simulação como outro usuário. Apenas leitura.
    """
    target = ChatMessiasManager.start_simulation(db, current_user, target_user_id)
    return {
        "status": "success",
        "message": f"Simulando acesso como '{target.username}' (Somente Leitura)."
    }


@router.post("/messias/view-as-user/stop")
def stop_simulation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Finaliza sessão de simulação.
    """
    ChatMessiasManager.stop_simulation(db, current_user)
    return {"status": "success", "message": "Simulação finalizada."}


# === NOVAS ROTAS CHAT FASE 5.2 ===

@router.post("/messages/{message_id}/open-once")
def open_once_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marca uma mensagem do tipo ONCE como visualizada pelo usuário atual.
    """
    return ChatService.open_once_message(db, message_id, current_user)


@router.post("/messages/{message_id}/forward")
def forward_message(
    message_id: int,
    target_conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Encaminha uma mensagem para outra conversa.
    """
    return ChatService.forward_message(db, message_id, target_conversation_id, current_user)


@router.post("/messages/delete-selected")
def delete_selected_messages(
    message_ids: List[int],
    delete_type: str = "ME", # ME ou EVERYONE
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exclui múltiplas mensagens selecionadas (em lote).
    """
    return ChatService.delete_selected(db, message_ids, current_user, delete_type)


@router.post("/messages/{message_id}/delete-for-me")
def delete_for_me(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exclui a mensagem apenas para o usuário logado (oculta na visualização).
    """
    ChatService.delete_for_me(db, message_id, current_user)
    return {"status": "success", "message": "Mensagem excluída para você."}


@router.post("/messages/{message_id}/delete-for-everyone")
def delete_for_everyone(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exclui a mensagem para todos os participantes da conversa (soft delete).
    """
    return ChatService.delete_for_everyone(db, message_id, current_user)


@router.get("/conversations/{conversation_id}/export")
def export_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exporta o histórico da conversa em formato de texto para download.
    """
    from fastapi.responses import StreamingResponse
    from io import StringIO
    
    log_content = ChatService.export_conversation(db, conversation_id, current_user)
    
    output = StringIO()
    output.write(log_content)
    output.seek(0)
    
    filename = f"chat-export-{conversation_id}.txt"
    return StreamingResponse(
        output, 
        media_type="text/plain", 
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/conversations/{conversation_id}/media")
def get_conversation_media(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna todos os arquivos de mídia (imagens, vídeos e GIFs) da conversa.
    """
    return ChatService.get_conversation_media(db, conversation_id, current_user)


@router.get("/messias/special-messages")
def get_messias_special_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna mensagens especiais de auditoria para o painel MESSIAS.
    """
    return ChatService.get_messias_special_messages(db, current_user)
