import asyncio
from fastapi import WebSocket
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.models.approval import Approval

class ConnectionManager:
    def __init__(self):
        # user_id -> List[WebSocket]
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        print(f"[WS] WebSocket conectado para usuario {user_id}")

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        print(f"[WS] WebSocket desconectado para usuario {user_id}")

    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

    async def broadcast(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for ws in connections:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()


class KanbanConnectionManager:
    def __init__(self):
        self.board_connections: Dict[int, Dict[int, List[WebSocket]]] = {}

    async def connect(self, board_id: int, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.board_connections.setdefault(board_id, {}).setdefault(user_id, []).append(websocket)

    def disconnect(self, board_id: int, user_id: int, websocket: WebSocket):
        users = self.board_connections.get(board_id)
        if not users:
            return
        sockets = users.get(user_id)
        if sockets and websocket in sockets:
            sockets.remove(websocket)
        if sockets == []:
            users.pop(user_id, None)
        if not users:
            self.board_connections.pop(board_id, None)

    async def broadcast_board(self, board_id: int, message: dict):
        users = self.board_connections.get(board_id, {})
        for user_id, sockets in list(users.items()):
            for websocket in list(sockets):
                try:
                    await websocket.send_json(message)
                except Exception:
                    self.disconnect(board_id, user_id, websocket)


kanban_manager = KanbanConnectionManager()

def authenticate_ws_token(token: str, db: Session) -> Optional[any]:
    """
    Decodifica o token JWT para autenticar a conexao WebSocket.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        from app.models.user import User
        user = db.query(User).filter(User.username == username).first()
        if user and user.is_active:
            return user
    except JWTError:
        return None
    return None

def ws_approval_callback(event_type: str, approval: Approval, db: Session):
    """
    Callback disparado quando ocorre algum evento de aprovações.
    Decide quais usuários devem receber a notificação e cria a task assíncrona.
    """
    try:
        # Pega a thread/loop de eventos para rodar o send de forma assíncrona
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Se não houver loop na thread atual (caso rode em background thread), cria um temporário
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Constrói o payload da notificação
    payload = {
        "event_type": event_type,
        "approval_id": approval.id,
        "title": approval.title,
        "module_slug": approval.module_slug,
        "status": approval.status,
        "risk_level": approval.risk_level,
        "requester_user_id": approval.requester_user_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Agenda a tarefa assíncrona de distribuição de mensagens
    if loop.is_running():
        loop.create_task(distribute_notification(event_type, approval, payload, db))
    else:
        loop.run_until_complete(distribute_notification(event_type, approval, payload, db))

async def distribute_notification(event_type: str, approval: Approval, payload: dict, db: Session):
    """
    Distribui as notificações para os usuários relevantes:
    - O solicitante original (requester_user_id) sempre recebe atualizações de suas solicitações.
    - Todos os ADMINs recebem todas as notificações.
    - Managers de um módulo recebem notificações referentes àquele módulo.
    """
    from app.models.user import User
    from app.modules.approvals.service import ApprovalService
    from app.core.permissions import PermissionLevel, LEVEL_VALUES

    # 1. Identifica destinatários
    recipients = set()
    
    # Solicitante recebe
    recipients.add(approval.requester_user_id)

    # Busca todos os usuários ativos do sistema
    users = db.query(User).filter(User.is_active == True).all()
    for user in users:
        # Admin recebe tudo
        if user.role and user.role.name == "ADMIN":
            recipients.add(user.id)
            continue

        # Verifica se o usuário é manager ou superior no módulo correspondente
        user_level = ApprovalService.get_user_module_level(db, user, approval.module_slug)
        if LEVEL_VALUES[user_level] >= LEVEL_VALUES[PermissionLevel.MANAGER]:
            recipients.add(user.id)

    # 2. Envia para cada destinatário conectado
    for r_id in recipients:
        await manager.send_to_user(r_id, {
            "type": "approval_notification",
            "data": payload
        })
