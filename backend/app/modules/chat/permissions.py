from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage
from app.modules.chat.repository import ChatRepository


class ChatPermissions:
    @staticmethod
    def is_messias(user: User) -> bool:
        return user.role is not None and user.role.name == "MESSIAS"

    @staticmethod
    def is_admin(user: User) -> bool:
        return user.role is not None and user.role.name in ["ADMIN", "MESSIAS"]

    @staticmethod
    def can_view_conversation(db: Session, conversation: ChatConversation, user: User) -> bool:
        # MESSIAS e ADMIN gerais podem ver todas as conversas do sistema corporativo
        if ChatPermissions.is_admin(user):
            return True
            
        # Canais públicos são visíveis para qualquer usuário com acesso ao módulo chat
        if conversation.type == "CHANNEL" and not conversation.is_private:
            return True
            
        # Canais privados, DMs e grupos exigem ser membro ativo
        member = ChatRepository.get_conversation_member(db, conversation.id, user.id)
        return member is not None

    @staticmethod
    def can_write_in_conversation(db: Session, conversation: ChatConversation, user: User) -> bool:
        # Se for canal público e o usuário tem acesso ao chat, ele pode enviar mensagens
        if conversation.type == "CHANNEL" and not conversation.is_private:
            # Verifica se ele é membro com restrição read_only
            member = ChatRepository.get_conversation_member(db, conversation.id, user.id)
            if member and member.role == "READ_ONLY":
                return False
            return True
            
        # Para canais privados, grupos e DMs, precisa ser membro ativo com permissão de escrita
        member = ChatRepository.get_conversation_member(db, conversation.id, user.id)
        if not member:
            return False
        return member.role != "READ_ONLY"

    @staticmethod
    def can_moderate_conversation(db: Session, conversation: ChatConversation, user: User) -> bool:
        # ADMINs globais ou MESSIAS podem moderar qualquer conversa
        if ChatPermissions.is_admin(user):
            return True
            
        # Apenas OWNER ou MODERATOR do canal/grupo podem moderar
        member = ChatRepository.get_conversation_member(db, conversation.id, user.id)
        if not member:
            return False
        return member.role in ["OWNER", "MODERATOR"]

    @staticmethod
    def check_view_conversation(db: Session, conversation_id: int, user: User) -> ChatConversation:
        conversation = ChatRepository.get_conversation(db, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversa nao encontrada.")
            
        if not ChatPermissions.can_view_conversation(db, conversation, user):
            raise HTTPException(status_code=403, detail="Acesso negado a esta conversa.")
            
        return conversation

    @staticmethod
    def check_write_conversation(db: Session, conversation_id: int, user: User) -> ChatConversation:
        conversation = ChatRepository.get_conversation(db, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversa nao encontrada.")
            
        if not ChatPermissions.can_write_in_conversation(db, conversation, user):
            raise HTTPException(status_code=403, detail="Você nao tem permissão para enviar mensagens nesta conversa.")
            
        return conversation

    @staticmethod
    def check_message_owner_or_moderator(db: Session, message: ChatMessage, user: User):
        # O autor da mensagem sempre pode gerenciar/deletar/editar (conforme regras do app)
        if message.sender_user_id == user.id:
            return
            
        # Administradores globais podem gerenciar
        if ChatPermissions.is_admin(user):
            return
            
        # Moderadores da conversa podem gerenciar
        conversation = ChatRepository.get_conversation(db, message.conversation_id)
        if conversation and ChatPermissions.can_moderate_conversation(db, conversation, user):
            return
            
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas o autor ou moderador do canal pode alterar esta mensagem.")
