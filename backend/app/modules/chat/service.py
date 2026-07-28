import asyncio
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from app.models.chat import (
    ChatConversation,
    ChatConversationMember,
    ChatMessage,
    ChatMessageVersion,
    ChatMessageAttachment,
    ChatReaction,
    ChatMention
)
from app.models.user import User
from app.models.kanban import File
from app.modules.chat.repository import ChatRepository
from app.modules.chat.permissions import ChatPermissions
from app.modules.chat.sanitize import sanitize_message_body
from app.modules.chat.events import chat_ws_manager
from app.modules.chat.messias import ChatMessiasManager


def _safe_run_coroutine(coro):
    """
    Executa uma corotina de forma segura a partir de contexto síncrono.
    Evita erros de loop ausente ou fechado na threadpool.
    """
    try:
        from app.modules.chat.events import chat_ws_manager
        loop = chat_ws_manager.loop
        
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
            return

        # Fallback caso não esteja no lifecycle/lifespan do FastAPI
        try:
            current_loop = asyncio.get_running_loop()
            if current_loop.is_running():
                asyncio.run_coroutine_threadsafe(coro, current_loop)
                return
        except RuntimeError:
            pass

        # Fallback de último caso: cria novo loop temporário
        new_loop = asyncio.new_event_loop()
        try:
            new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    except Exception as e:
        import logging
        logging.getLogger("chat.ws").warning(f"Falha ao rodar corotina WS em background: {e}")


class ChatService:
    @staticmethod
    def create_conversation(
        db: Session,
        creator: User,
        conv_type: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_private: bool = False,
        member_ids: List[int] = []
    ) -> ChatConversation:
        ChatMessiasManager.verify_write_block(creator)
        
        if conv_type not in ["CHANNEL", "DM", "GROUP"]:
            raise HTTPException(status_code=400, detail="Tipo de conversa inválido.")
            
        if conv_type == "CHANNEL" and not ChatPermissions.is_admin(creator) and creator.role.name != "MANAGER":
            raise HTTPException(
                status_code=403, 
                detail="Apenas administradores ou gerentes podem criar canais."
            )
            
        # Se for DM, garante que é estritamente entre 2 participantes
        if conv_type == "DM":
            if not member_ids or len(member_ids) != 1:
                raise HTTPException(status_code=400, detail="DM deve ser criada com exatamente um outro participante.")
                
            other_user_id = member_ids[0]
            if other_user_id == creator.id:
                raise HTTPException(status_code=400, detail="Você não pode criar uma DM com você mesmo.")
                
            # Verifica se já existe DM entre os dois
            existing_dm = db.query(ChatConversation).join(ChatConversationMember).filter(
                ChatConversation.type == "DM",
                ChatConversationMember.user_id.in_([creator.id, other_user_id])
            ).all()
            
            for dm in existing_dm:
                # Confirma se ela tem exatamente os dois membros
                member_count = db.query(ChatConversationMember).filter(
                    ChatConversationMember.conversation_id == dm.id
                ).count()
                if member_count == 2:
                    return dm
                    
            name = None
            description = None
            is_private = True
            
        # Cria a conversa
        conversation = ChatConversation(
            type=conv_type,
            name=name,
            description=description,
            is_private=is_private,
            created_by_user_id=creator.id,
            owner_user_id=creator.id
        )
        db.add(conversation)
        db.flush()
        
        # Adiciona o criador como OWNER
        db.add(ChatConversationMember(
            conversation_id=conversation.id,
            user_id=creator.id,
            role="OWNER",
            is_muted=False,
            notification_level="ALL"
        ))
        
        # Adiciona os outros membros se houver
        if conv_type == "DM":
            db.add(ChatConversationMember(
                conversation_id=conversation.id,
                user_id=member_ids[0],
                role="MEMBER",
                is_muted=False,
                notification_level="ALL"
            ))
        elif conv_type == "GROUP" or conv_type == "CHANNEL":
            for m_id in set(member_ids):
                if m_id == creator.id:
                    continue
                # Verifica se o usuário existe
                u = db.query(User).filter(User.id == m_id, User.is_active == True).first()
                if u:
                    db.add(ChatConversationMember(
                        conversation_id=conversation.id,
                        user_id=m_id,
                        role="MEMBER",
                        is_muted=False,
                        notification_level="ALL"
                    ))
                    
        db.commit()
        db.refresh(conversation)
        
        # Propaga a criação da conversa via WS
        for m in conversation.members:
            chat_ws_manager.active_connections.get(m.user_id)
            # Envia notificação de nova conversa
            _safe_run_coroutine(
                chat_ws_manager.send_to_user(m.user_id, {
                    "type": "chat.conversation.created",
                    "data": {
                        "id": conversation.id,
                        "type": conversation.type,
                        "name": conversation.name
                    }
                })
            )
            
        return conversation

    @staticmethod
    def get_conversation_detail(db: Session, conversation_id: int, user: User) -> Dict[str, Any]:
        # Resolve se estamos simulando permissões
        effective_user = ChatMessiasManager.get_effective_user(db, user)
        conversation = ChatPermissions.check_view_conversation(db, conversation_id, effective_user)
        
        # Serializa membros
        members_data = []
        for m in conversation.members:
            members_data.append({
                "id": m.id,
                "user_id": m.user_id,
                "username": m.user.username,
                "role": m.role,
                "is_muted": m.is_muted,
                "joined_at": m.joined_at,
                "last_read_message_id": m.last_read_message_id,
                "last_read_at": m.last_read_at,
                "notification_level": m.notification_level
            })
            
        # Pega a última mensagem
        last_msg = ChatRepository.get_last_message(db, conversation.id, ChatPermissions.is_messias(user))
        last_msg_data = None
        if last_msg:
            last_msg_data = {
                "id": last_msg.id,
                "conversation_id": last_msg.conversation_id,
                "sender_user_id": last_msg.sender_user_id,
                "sender_username": last_msg.sender.username,
                "parent_message_id": last_msg.parent_message_id,
                "message_type": last_msg.message_type,
                "body": last_msg.body,
                "is_edited": last_msg.is_edited,
                "is_deleted": last_msg.is_deleted,
                "is_pinned": last_msg.is_pinned,
                "is_ephemeral": last_msg.is_ephemeral,
                "expires_at": last_msg.expires_at,
                "reply_count": last_msg.reply_count,
                "created_at": last_msg.created_at,
                "updated_at": last_msg.updated_at,
                "deleted_at": last_msg.deleted_at,
                "deleted_by_user_id": last_msg.deleted_by_user_id,
                "reactions": [],
                "mentions": [],
                "attachments": [],
                "edit_history": None,
            }
            
        # Unread count
        unread = ChatRepository.count_unread_messages(db, conversation.id, effective_user.id)
        
        # Nome da conversa em DM deve ser o nome do outro participante
        conv_name = conversation.name
        if conversation.type == "DM":
            other_member = next((m for m in conversation.members if m.user_id != effective_user.id), None)
            if other_member:
                conv_name = other_member.user.username
            else:
                conv_name = "Conversa Arquivada"
                
        return {
            "id": conversation.id,
            "type": conversation.type,
            "name": conv_name,
            "description": conversation.description,
            "is_private": conversation.is_private,
            "is_archived": conversation.is_archived,
            "created_by_user_id": conversation.created_by_user_id,
            "owner_user_id": conversation.owner_user_id,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "archived_at": conversation.archived_at,
            "members": members_data,
            "unread_count": unread,
            "last_message": last_msg_data
        }

    @staticmethod
    def send_message(
        db: Session,
        conversation_id: int,
        sender: User,
        body: Optional[str] = None,
        parent_message_id: Optional[int] = None,
        message_type: str = "TEXT",
        file_ids: List[int] = [],
        mentions: List[Dict[str, Any]] = [],
        is_ephemeral: bool = False,
        expires_in_seconds: Optional[int] = None,
        visibility_mode: str = "NORMAL"
    ) -> ChatMessage:
        ChatMessiasManager.verify_write_block(sender)
        
        conversation = ChatPermissions.check_write_conversation(db, conversation_id, sender)
        
        # Sanitiza a mensagem para evitar XSS
        sanitized_body = sanitize_message_body(body) if body else None
        
        # Limpa o texto para busca (remove tags e caracteres desnecessários)
        body_search = body.lower() if body else None
        
        expires_at = None
        if is_ephemeral and expires_in_seconds:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
            
        message = ChatMessage(
            conversation_id=conversation.id,
            sender_user_id=sender.id,
            parent_message_id=parent_message_id,
            message_type=message_type,
            body=sanitized_body,
            body_search=body_search,
            is_ephemeral=is_ephemeral,
            expires_at=expires_at,
            visibility_mode=visibility_mode
        )
        db.add(message)
        db.flush()
        
        # Seta parent reply count
        if parent_message_id:
            parent = ChatRepository.get_message(db, parent_message_id)
            if parent:
                parent.reply_count += 1
                
        # Associa arquivos anexados
        for f_id in file_ids:
            f = db.query(File).filter(File.id == f_id).first()
            if f:
                # Determina tipo de anexo com base na extensão
                ext = Path(f.original_filename).suffix.lower()
                from app.modules.chat.attachments import ChatAttachmentsManager
                attachment_type = ChatAttachmentsManager.get_attachment_type(ext)
                
                db.add(ChatMessageAttachment(
                    message_id=message.id,
                    file_id=f.id,
                    attachment_type=attachment_type,
                    uploaded_by_user_id=sender.id
                ))
                
        # Insere menções no banco
        for men in mentions:
            db.add(ChatMention(
                message_id=message.id,
                mention_type=men["mention_type"],
                target_id=men.get("target_id"),
                target_slug=men.get("target_slug"),
                display_label=men["display_label"]
            ))
            
        # Atualiza a data de modificação da conversa
        conversation.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(message)
        
        # Emissao de eventos no Event Engine
        from app.core.events import emit_event
        
        # chat.message.created
        try:
            emit_event(
                db=db,
                event_type="chat.message.created",
                aggregate_type="chat_message",
                aggregate_id=str(message.id),
                module="chat",
                payload={
                    "message_id": message.id,
                    "conversation_id": message.conversation_id,
                    "sender_user_id": message.sender_user_id,
                    "body_preview": message.body[:100] if message.body else "",
                    "message_type": message.message_type
                },
                actor_user_id=sender.id
            )
        except Exception as e:
            import logging
            logging.getLogger("vesper.events").warning(f"Erro ao emitir evento chat.message.created: {e}")
            
        # chat.message.mentioned
        for men in mentions:
            if men.get("mention_type") == "USER" and men.get("target_id"):
                try:
                    emit_event(
                        db=db,
                        event_type="chat.message.mentioned",
                        aggregate_type="chat_message",
                        aggregate_id=str(message.id),
                        module="chat",
                        payload={
                            "message_id": message.id,
                            "conversation_id": message.conversation_id,
                            "sender_user_id": message.sender_user_id,
                            "mentioned_user_id": int(men["target_id"]),
                            "body_preview": message.body[:100] if message.body else ""
                        },
                        actor_user_id=sender.id
                    )
                except Exception as e:
                    import logging
                    logging.getLogger("vesper.events").warning(f"Erro ao emitir evento chat.message.mentioned: {e}")
                    
        # chat.file.uploaded
        if file_ids:
            for f_id in file_ids:
                try:
                    emit_event(
                        db=db,
                        event_type="chat.file.uploaded",
                        aggregate_type="chat_message",
                        aggregate_id=str(message.id),
                        module="chat",
                        payload={
                            "message_id": message.id,
                            "conversation_id": message.conversation_id,
                            "sender_user_id": message.sender_user_id,
                            "file_id": f_id
                        },
                        actor_user_id=sender.id
                    )
                except Exception as e:
                    import logging
                    logging.getLogger("vesper.events").warning(f"Erro ao emitir evento chat.file.uploaded: {e}")
        
        # Dispara evento WS em tempo real para os membros da conversa
        # (Executa na thread assíncrona do fastapi para não bloquear o banco)
        
        # Prepara payload formatado do WS
        ws_data = {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "sender_user_id": message.sender_user_id,
            "sender_username": sender.username,
            "message_type": message.message_type,
            "body": message.body,
            "is_edited": message.is_edited,
            "is_deleted": message.is_deleted,
            "is_pinned": message.is_pinned,
            "is_ephemeral": message.is_ephemeral,
            "visibility_mode": message.visibility_mode,
            "reply_count": message.reply_count,
            "created_at": message.created_at.isoformat(),
            "updated_at": message.updated_at.isoformat()
        }
        
        _safe_run_coroutine(
            chat_ws_manager.broadcast_to_conversation(
                db=db,
                conversation_id=conversation_id,
                event_type="chat.message.created",
                data=ws_data
            )
        )
        
        return message

    @staticmethod
    def edit_message(db: Session, message_id: int, user: User, new_body: str) -> ChatMessage:
        ChatMessiasManager.verify_write_block(user)
        
        message = ChatRepository.get_message(db, message_id)
        if not message or message.is_deleted:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada.")
            
        # Somente o autor pode editar sua mensagem
        if message.sender_user_id != user.id:
            raise HTTPException(status_code=403, detail="Você só pode editar suas próprias mensagens.")
            
        previous_body = message.body
        sanitized_body = sanitize_message_body(new_body)
        
        # Salva histórico
        db.add(ChatMessageVersion(
            message_id=message.id,
            previous_body=previous_body or "",
            new_body=sanitized_body,
            edited_by_user_id=user.id
        ))
        
        message.body = sanitized_body
        message.body_search = new_body.lower()
        message.is_edited = True
        message.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(message)
        
        # Notifica via WS
        ws_data = {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "body": message.body,
            "is_edited": True,
            "updated_at": message.updated_at.isoformat()
        }
        _safe_run_coroutine(
            chat_ws_manager.broadcast_to_conversation(
                db=db,
                conversation_id=message.conversation_id,
                event_type="chat.message.updated",
                data=ws_data
            )
        )
        
        return message

    @staticmethod
    def delete_message(db: Session, message_id: int, user: User) -> ChatMessage:
        ChatMessiasManager.verify_write_block(user)
        
        message = ChatRepository.get_message(db, message_id)
        if not message or message.is_deleted:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada.")
            
        # Valida se é autor ou moderador
        ChatPermissions.check_message_owner_or_moderator(db, message, user)
        
        message.is_deleted = True
        message.deleted_at = datetime.now(timezone.utc)
        message.deleted_by_user_id = user.id
        
        # Se for resposta, decresce contagem da mensagem pai
        if message.parent_message_id:
            parent = ChatRepository.get_message(db, message.parent_message_id)
            if parent and parent.reply_count > 0:
                parent.reply_count -= 1
                
        db.commit()
        db.refresh(message)
        
        # Notifica via WS
        ws_data = {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "is_deleted": True,
            "deleted_at": message.deleted_at.isoformat()
        }
        _safe_run_coroutine(
            chat_ws_manager.broadcast_to_conversation(
                db=db,
                conversation_id=message.conversation_id,
                event_type="chat.message.deleted",
                data=ws_data
            )
        )
        
        return message

    @staticmethod
    def add_reaction(db: Session, message_id: int, user: User, emoji: str) -> ChatReaction:
        ChatMessiasManager.verify_write_block(user)
        
        message = ChatRepository.get_message(db, message_id)
        if not message or message.is_deleted:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada.")
            
        # Valida acesso à conversa
        ChatPermissions.check_view_conversation(db, message.conversation_id, user)
        
        # Verifica se já reagiu
        existing = db.query(ChatReaction).filter(
            ChatReaction.message_id == message_id,
            ChatReaction.user_id == user.id,
            ChatReaction.emoji == emoji
        ).first()
        
        if existing:
            return existing
            
        reaction = ChatReaction(
            message_id=message_id,
            user_id=user.id,
            emoji=emoji
        )
        db.add(reaction)
        db.commit()
        db.refresh(reaction)
        
        # WS
        _safe_run_coroutine(
            chat_ws_manager.broadcast_to_conversation(
                db=db,
                conversation_id=message.conversation_id,
                event_type="chat.message.reaction.created",
                data={
                    "message_id": message_id,
                    "conversation_id": message.conversation_id,
                    "reaction_id": reaction.id,
                    "user_id": user.id,
                    "username": user.username,
                    "emoji": emoji
                }
            )
        )
        
        return reaction

    @staticmethod
    def remove_reaction(db: Session, message_id: int, user: User, emoji: str):
        ChatMessiasManager.verify_write_block(user)
        
        message = ChatRepository.get_message(db, message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada.")
            
        reaction = db.query(ChatReaction).filter(
            ChatReaction.message_id == message_id,
            ChatReaction.user_id == user.id,
            ChatReaction.emoji == emoji
        ).first()
        
        if not reaction:
            raise HTTPException(status_code=404, detail="Reação não encontrada.")
            
        db.delete(reaction)
        db.commit()
        
        # WS
        _safe_run_coroutine(
            chat_ws_manager.broadcast_to_conversation(
                db=db,
                conversation_id=message.conversation_id,
                event_type="chat.message.reaction.deleted",
                data={
                    "message_id": message_id,
                    "conversation_id": message.conversation_id,
                    "user_id": user.id,
                    "emoji": emoji
                }
            )
        )

    @staticmethod
    def mark_as_read(db: Session, conversation_id: int, user: User):
        member = ChatRepository.get_conversation_member(db, conversation_id, user.id)
        if not member:
            return
            
        # Pega última mensagem
        last_msg = ChatRepository.get_last_message(db, conversation_id)
        if last_msg:
            member.last_read_message_id = last_msg.id
            member.last_read_at = datetime.now(timezone.utc)
            db.commit()
            
            # Se for DM, avisa o outro membro sobre o "visto"
            conversation = ChatRepository.get_conversation(db, conversation_id)
            if conversation and conversation.type == "DM":
                _safe_run_coroutine(
                    chat_ws_manager.broadcast_to_conversation(
                        db=db,
                        conversation_id=conversation_id,
                        event_type="chat.read.updated",
                        data={
                            "conversation_id": conversation_id,
                            "user_id": user.id,
                            "last_read_message_id": last_msg.id,
                            "last_read_at": member.last_read_at.isoformat()
                        },
                        exclude_user_id=user.id
                    )
                )

    # === NOVOS MÉTODOS FASE 5.2 ===

    @staticmethod
    def delete_for_me(db: Session, message_id: int, user: User) -> None:
        from app.models.chat import ChatMessageDelete
        # Verifica se já não foi apagada para mim
        existing = db.query(ChatMessageDelete).filter(
            ChatMessageDelete.message_id == message_id,
            ChatMessageDelete.user_id == user.id
        ).first()
        if not existing:
            delete_record = ChatMessageDelete(
                message_id=message_id,
                user_id=user.id,
                deleted_at=datetime.now(timezone.utc)
            )
            db.add(delete_record)
            db.commit()

    @staticmethod
    def delete_for_everyone(db: Session, message_id: int, user: User) -> ChatMessage:
        return ChatService.delete_message(db, message_id, user)

    @staticmethod
    def delete_selected(db: Session, message_ids: List[int], user: User, delete_type: str) -> Dict[str, str]:
        for msg_id in message_ids:
            if delete_type == "ME":
                ChatService.delete_for_me(db, msg_id, user)
            elif delete_type == "EVERYONE":
                # Verifica se é autor ou moderador
                msg = ChatRepository.get_message(db, msg_id)
                if msg:
                    try:
                        ChatPermissions.check_message_owner_or_moderator(db, msg, user)
                        ChatService.delete_for_everyone(db, msg_id, user)
                    except Exception:
                        # Ignora se não tiver permissão para alguma mensagem específica do lote
                        pass
        return {"status": "success", "message": f"Mensagens processadas para exclusão do tipo {delete_type}."}

    @staticmethod
    def open_once_message(db: Session, message_id: int, user: User) -> Dict[str, Any]:
        msg = ChatRepository.get_message(db, message_id)
        if not msg:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada.")
            
        # Registra visualização na lista JSON
        viewed = msg.viewed_by_users or []
        if user.id not in viewed:
            viewed.append(user.id)
            msg.viewed_by_users = viewed
            db.commit()
            
            # Notifica WS para atualização
            ws_data = {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "viewed_by_users": viewed
            }
            _safe_run_coroutine(
                chat_ws_manager.broadcast_to_conversation(
                    db=db,
                    conversation_id=msg.conversation_id,
                    event_type="chat.message.once_viewed",
                    data=ws_data
                )
            )
            
        return {"status": "success", "viewed_by_users": viewed}

    @staticmethod
    def forward_message(db: Session, message_id: int, target_conversation_id: int, user: User) -> ChatMessage:
        ChatMessiasManager.verify_write_block(user)
        msg = ChatRepository.get_message(db, message_id)
        if not msg or msg.is_deleted:
            raise HTTPException(status_code=404, detail="Mensagem para encaminhamento não encontrada.")
            
        # Verifica se tem acesso à conversa origem e destino
        ChatPermissions.check_view_conversation(db, msg.conversation_id, user)
        ChatPermissions.check_write_conversation(db, target_conversation_id, user)
        
        # Clona a mensagem
        forwarded_body = f"[Encaminhado]: {msg.body}" if msg.body else "[Encaminhado]"
        
        # Coleta os arquivos anexos
        file_ids = [att.file_id for att in msg.attachments]
        
        # Envia
        new_msg = ChatService.send_message(
            db=db,
            conversation_id=target_conversation_id,
            sender=user,
            body=forwarded_body,
            message_type=msg.message_type,
            file_ids=file_ids
        )
        
        # Registra auditoria/vínculo se necessário
        return new_msg

    @staticmethod
    def export_conversation(db: Session, conversation_id: int, user: User) -> str:
        effective_user = ChatMessiasManager.get_effective_user(db, user)
        conversation = ChatPermissions.check_view_conversation(db, conversation_id, effective_user)
        
        is_messias = ChatPermissions.is_messias(user)
        messages = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        ).order_by(ChatMessage.created_at.asc()).all()
        
        # Geração de log estruturado simples
        log_lines = []
        log_lines.append("=== Portal Vesper - Exportacao de Chat ===")
        log_lines.append(f"Conversa: {conversation.name or 'DM'}")
        log_lines.append(f"Exportado por: {user.username} em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        log_lines.append("===========================================\n")
        
        for msg in messages:
            # Oculta mensagens deletadas para usuário comum
            if msg.is_deleted and not is_messias:
                log_lines.append(f"[{msg.created_at.strftime('%d/%m/%Y %H:%M')}] {msg.sender.username}: [Mensagem Apagada]")
                continue
                
            body_text = msg.body or ""
            if msg.visibility_mode == "ONCE" and user.id in (msg.viewed_by_users or []) and not is_messias:
                body_text = "[Visualização única - já visualizada]"
                
            log_lines.append(f"[{msg.created_at.strftime('%d/%m/%Y %H:%M')}] {msg.sender.username}: {body_text}")
            
        return "\n".join(log_lines)

    @staticmethod
    def get_conversation_media(db: Session, conversation_id: int, user: User) -> List[Dict[str, Any]]:
        effective_user = ChatMessiasManager.get_effective_user(db, user)
        ChatPermissions.check_view_conversation(db, conversation_id, effective_user)
        
        # Filtra mensagens que contêm anexos do tipo imagem/vídeo/GIF
        messages = db.query(ChatMessage).join(ChatMessageAttachment).filter(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.is_deleted == False
        ).order_by(ChatMessage.created_at.desc()).all()
        
        media_list = []
        for msg in messages:
            for att in msg.attachments:
                if att.attachment_type in ["IMAGE", "VIDEO", "GIF"]:
                    media_list.append({
                        "message_id": msg.id,
                        "attachment_id": att.id,
                        "file_id": att.file_id,
                        "filename": att.file.original_filename,
                        "content_type": att.file.content_type,
                        "size_bytes": att.file.size_bytes,
                        "created_at": att.created_at
                    })
        return media_list

    @staticmethod
    def get_messias_special_messages(db: Session, user: User) -> List[Dict[str, Any]]:
        if not ChatPermissions.is_messias(user):
            raise HTTPException(status_code=403, detail="Acesso negado. Apenas o MESSIAS possui permissão.")
            
        # Retorna mensagens marcadas como apagadas, editadas, de visualização única ou temporárias
        messages = db.query(ChatMessage).filter(
            (ChatMessage.is_deleted == True) | 
            (ChatMessage.is_edited == True) | 
            (ChatMessage.visibility_mode.in_(["ONCE", "TEMPORARY", "AUDIT"]))
        ).order_by(ChatMessage.created_at.desc()).limit(100).all()
        
        result = []
        for msg in messages:
            versions = []
            for v in msg.versions:
                versions.append({
                    "previous": v.previous_body,
                    "new": v.new_body,
                    "edited_at": v.edited_at
                })
            result.append({
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "conversation_name": msg.conversation.name if msg.conversation else "DM",
                "sender_username": msg.sender.username,
                "body": msg.body,
                "is_deleted": msg.is_deleted,
                "is_edited": msg.is_edited,
                "visibility_mode": msg.visibility_mode,
                "created_at": msg.created_at,
                "viewed_by_users": msg.viewed_by_users,
                "edit_history": versions
            })
        return result
