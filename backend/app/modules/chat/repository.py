from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional

from app.models.chat import (
    ChatConversation,
    ChatConversationMember,
    ChatMessage,
    ChatMessiasAudit
)


class ChatRepository:
    @staticmethod
    def get_conversation(db: Session, conversation_id: int) -> Optional[ChatConversation]:
        return db.query(ChatConversation).filter(
            ChatConversation.id == conversation_id
        ).first()

    @staticmethod
    def get_conversation_member(db: Session, conversation_id: int, user_id: int) -> Optional[ChatConversationMember]:
        return db.query(ChatConversationMember).filter(
            ChatConversationMember.conversation_id == conversation_id,
            ChatConversationMember.user_id == user_id,
            ChatConversationMember.archived_at == None
        ).first()

    @staticmethod
    def list_user_conversations(db: Session, user_id: int) -> List[ChatConversation]:
        """
        Retorna todas as conversas das quais o usuário é membro ativo ou canais públicos.
        """
        # Pega as IDs das conversas onde ele é membro
        member_subquery = db.query(ChatConversationMember.conversation_id).filter(
            ChatConversationMember.user_id == user_id,
            ChatConversationMember.archived_at == None
        ).subquery()

        # Retorna conversas onde ele é membro OR canais públicos (is_private=False)
        return db.query(ChatConversation).filter(
            or_(
                ChatConversation.id.in_(member_subquery),
                and_(ChatConversation.type == "CHANNEL", ChatConversation.is_private == False)
            ),
            ChatConversation.is_archived == False
        ).order_by(ChatConversation.updated_at.desc()).all()

    @staticmethod
    def get_last_message(db: Session, conversation_id: int, is_messias: bool = False) -> Optional[ChatMessage]:
        query = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        )
        if not is_messias:
            query = query.filter(
                ChatMessage.is_deleted == False
            )
        return query.order_by(ChatMessage.created_at.desc()).first()

    @staticmethod
    def count_unread_messages(db: Session, conversation_id: int, user_id: int) -> int:
        member = ChatRepository.get_conversation_member(db, conversation_id, user_id)
        if not member:
            return 0
            
        query = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.sender_user_id != user_id,
            ChatMessage.is_deleted == False
        )
        
        if member.last_read_message_id:
            query = query.filter(ChatMessage.id > member.last_read_message_id)
        elif member.last_read_at:
            query = query.filter(ChatMessage.created_at > member.last_read_at)
            
        return query.count()

    @staticmethod
    def list_messages(
        db: Session,
        conversation_id: int,
        limit: int = 50,
        before_message_id: Optional[int] = None,
        is_messias: bool = False
    ) -> List[ChatMessage]:
        query = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        )
        
        if not is_messias:
            # Usuário comum não vê mensagens marcadas como deletadas
            query = query.filter(ChatMessage.is_deleted == False)
            
        if before_message_id:
            query = query.filter(ChatMessage.id < before_message_id)
            
        return query.order_by(ChatMessage.id.desc()).limit(limit).all()

    @staticmethod
    def get_message(db: Session, message_id: int) -> Optional[ChatMessage]:
        return db.query(ChatMessage).filter(ChatMessage.id == message_id).first()

    @staticmethod
    def create_messias_audit_log(
        db: Session,
        messias_user_id: int,
        action: str,
        target_user_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> ChatMessiasAudit:
        log = ChatMessiasAudit(
            messias_user_id=messias_user_id,
            action=action,
            target_user_id=target_user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            metadata_json=metadata
        )
        db.add(log)
        db.flush()
        return log
