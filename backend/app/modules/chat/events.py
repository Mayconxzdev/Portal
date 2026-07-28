from fastapi import WebSocket
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session

from app.models.chat import ChatConversationMember
from app.models.user import User


class ChatConnectionManager:
    def __init__(self):
        # user_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # conversation_id -> Set[user_id] que estão digitando
        self.typing_users: Dict[int, Set[int]] = {}
        self.loop = None

    async def connect(self, user_id: int, websocket: WebSocket, db: Session):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Envia evento de presença: online
        await self.broadcast_presence_change(user_id, "online", db)

    async def disconnect(self, user_id: int, websocket: WebSocket, db: Session):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                # Envia evento de presença: offline
                await self.broadcast_presence_change(user_id, "offline", db)

    def is_user_online(self, user_id: int) -> bool:
        return user_id in self.active_connections

    async def send_to_user(self, user_id: int, payload: dict):
        if user_id in self.active_connections:
            for ws in list(self.active_connections[user_id]):
                try:
                    await ws.send_json(payload)
                except Exception:
                    # Conexão quebrada, limpa depois no disconnect
                    pass

    async def broadcast_to_conversation(
        self,
        db: Session,
        conversation_id: int,
        event_type: str,
        data: dict,
        exclude_user_id: Optional[int] = None
    ):
        """
        Envia a mensagem/evento para todos os membros da conversa que possuem conexões WebSocket ativas.
        """
        members = db.query(ChatConversationMember).filter(
            ChatConversationMember.conversation_id == conversation_id,
            ChatConversationMember.archived_at == None
        ).all()
        
        payload = {
            "type": event_type,
            "data": data
        }
        
        for member in members:
            if exclude_user_id and member.user_id == exclude_user_id:
                continue
            if member.user_id in self.active_connections:
                await self.send_to_user(member.user_id, payload)
                
        # Adicionalmente, se o evento for uma auditoria MESSIAS, envia para os auditores MESSIAS ativos
        if event_type.startswith("chat.messias."):
            await self.send_to_messias_users(db, payload)

    async def send_to_messias_users(self, db: Session, payload: dict):
        """
        Envia eventos especiais de auditoria apenas para usuários conectados que possuem papel MESSIAS.
        """
        for user_id in list(self.active_connections.keys()):
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.role and user.role.name == "MESSIAS":
                await self.send_to_user(user_id, payload)

    async def broadcast_presence_change(self, user_id: int, status: str, db: Session):
        """
        Notifica todas as conversas das quais o usuário é membro sobre a alteração de seu status de presença.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
            
        payload = {
            "type": "chat.presence.changed",
            "data": {
                "user_id": user_id,
                "username": user.username,
                "status": status
            }
        }
        
        # Encontra todas as conversas do usuário
        conversations = db.query(ChatConversationMember.conversation_id).filter(
            ChatConversationMember.user_id == user_id,
            ChatConversationMember.archived_at == None
        ).all()
        
        conversation_ids = [c[0] for c in conversations]
        
        # Coleta membros dessas conversas para notificar
        notified_users: Set[int] = set()
        for cid in conversation_ids:
            members = db.query(ChatConversationMember.user_id).filter(
                ChatConversationMember.conversation_id == cid,
                ChatConversationMember.archived_at == None
            ).all()
            for m in members:
                notified_users.add(m[0])
                
        # Envia para cada usuário conectado nas mesmas conversas
        for n_uid in notified_users:
            if n_uid != user_id and n_uid in self.active_connections:
                await self.send_to_user(n_uid, payload)

    async def set_user_typing(self, user_id: int, conversation_id: int, is_typing: bool, db: Session):
        """
        Registra e distribui o status de digitação de um usuário.
        """
        if conversation_id not in self.typing_users:
            self.typing_users[conversation_id] = set()
            
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
            
        if is_typing:
            self.typing_users[conversation_id].add(user_id)
        else:
            self.typing_users[conversation_id].discard(user_id)
            
        # Distribui evento aos membros da conversa
        event_type = "chat.typing.started" if is_typing else "chat.typing.stopped"
        await self.broadcast_to_conversation(
            db=db,
            conversation_id=conversation_id,
            event_type=event_type,
            data={
                "conversation_id": conversation_id,
                "user_id": user_id,
                "username": user.username
            },
            exclude_user_id=user_id
        )


chat_ws_manager = ChatConnectionManager()
