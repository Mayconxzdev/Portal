from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.module import Module
from app.api.health import router as health_router
from app.core.permissions import get_current_user, check_module_access, PermissionLevel
from app.models.user import User
from app.api.auth import router as auth_router
from app.api.search import router as search_router
from app.api.events import router as events_router
from app.api.integrations import router as integrations_router

# Importa os roteadores de cada um dos 10 módulos (knowledge unificado em files)
from app.modules.dashboard.router import router as dashboard_router
from app.modules.kanban.router import router as kanban_router
from app.modules.proposals.router import router as proposals_router
from app.modules.purchases.router import router as purchases_router, public_router as purchases_public_router
from app.modules.it.router import router as it_router
from app.modules.chat.router import router as chat_router
from app.modules.files.router import router as files_router
from app.modules.stock.router import router as stock_router
from app.modules.approvals.router import router as approvals_router
from app.modules.automations.router import router as automations_router
from app.modules.admin.router import router as admin_router
from app.modules.action_intents.router import router as action_intents_router
from app.modules.notifications.router import router as notifications_router
from app.modules.reactions.router import router as reactions_router
from app.modules.master_data.router import router as master_data_router
from app.modules.action_commands.router import router as action_commands_router
from app.modules.legacy_imports.router import router as legacy_import_router
from app.modules.legacy_promotion.router import router as legacy_promotion_router
from app.modules.vault.router import router as vault_router

api_router = APIRouter()

# Acopla a rota de healthcheck avançada
api_router.include_router(health_router, tags=["Health"])

# Acopla o roteador de autenticação real
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(events_router, prefix="/events", tags=["Events"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["Integrations"])
api_router.include_router(action_intents_router, prefix="/action-intents", tags=["Action Intents"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(reactions_router, prefix="/reactions", tags=["Reactions"])
api_router.include_router(master_data_router, prefix="/master-data", tags=["Master Data"])
api_router.include_router(action_commands_router, prefix="/action-commands", tags=["Action Commands"])
api_router.include_router(legacy_import_router, prefix="/legacy-import", tags=["Legacy Import"])
api_router.include_router(legacy_promotion_router, prefix="/legacy-promotion", tags=["Legacy Promotion"])
api_router.include_router(vault_router, prefix="/vault", tags=["Vault"])


# Rotas Globais do Portal Vesper (v1)

@api_router.get("/modules")
def list_available_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna a lista oficial e o status de ativação dos módulos registrados no banco PostgreSQL.
    Retorna também o nível de acesso real do usuário logado para cada módulo.
    """
    try:
        modules = db.query(Module).order_by(Module.id).all()
        if not modules:
            raise Exception("Sem modulos cadastrados")
        
        # Constrói o mapeamento de permissões do usuário
        permissions_map = {}
        if current_user.role and current_user.role.name == "ADMIN":
            for m in modules:
                permissions_map[m.code] = "ADMIN"
        else:
            for acc in current_user.module_accesses:
                permissions_map[acc.module.code] = acc.permission_level
        
        # Garante que todo módulo tem pelo menos NO_ACCESS mapeado se não houver registro específico
        for m in modules:
            if m.code not in permissions_map:
                permissions_map[m.code] = "NO_ACCESS"

        return {
            "status": "success",
            "modules": [
                {
                    "id": m.id,
                    "name": m.name,
                    "code": m.code,
                    "is_active": m.is_active,
                    "is_restricted": m.is_restricted,
                    "permission_level": permissions_map[m.code]
                }
                for m in modules
            ]
        }
    except Exception:
        # Fallback local seguro caso ocorra erro inesperado no DB
        fallback_modules = [
            {"id": 1, "name": "Dashboard", "code": "dashboard", "is_active": True, "is_restricted": False},
            {"id": 2, "name": "Kanban", "code": "kanban", "is_active": True, "is_restricted": False},
            {"id": 3, "name": "Propostas", "code": "proposals", "is_active": True, "is_restricted": False},
            {"id": 4, "name": "Compras", "code": "purchases", "is_active": True, "is_restricted": False},
            {"id": 5, "name": "TI", "code": "it", "is_active": True, "is_restricted": False},
            {"id": 6, "name": "Chat Interno", "code": "chat", "is_active": True, "is_restricted": False},
            {"id": 7, "name": "Arquivos / Knowledge", "code": "files", "is_active": True, "is_restricted": False},
            {"id": 8, "name": "Estoque Básico", "code": "stock", "is_active": True, "is_restricted": False},
            {"id": 9, "name": "Aprovações", "code": "approvals", "is_active": True, "is_restricted": False},
            {"id": 10, "name": "Automações IA", "code": "automations", "is_active": True, "is_restricted": False},
            {"id": 11, "name": "Administração", "code": "admin", "is_active": True, "is_restricted": True}
        ]
        
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        return {
            "status": "fallback",
            "modules": [
                {
                    **m,
                    "permission_level": "ADMIN" if is_admin else ("NO_ACCESS" if m["is_restricted"] else "NORMAL")
                } for m in fallback_modules
            ]
        }

# Montagem das sub-rotas estruturadas dos 10 módulos
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(kanban_router, prefix="/kanban", tags=["Kanban"], dependencies=[Depends(check_module_access("kanban", PermissionLevel.READ_ONLY))])
api_router.include_router(proposals_router, prefix="/proposals", tags=["Proposals"], dependencies=[Depends(check_module_access("proposals", PermissionLevel.READ_ONLY))])
api_router.include_router(purchases_public_router, prefix="/purchases", tags=["Purchases"])
api_router.include_router(purchases_router, prefix="/purchases", tags=["Purchases"], dependencies=[Depends(check_module_access("purchases", PermissionLevel.READ_ONLY))])
api_router.include_router(it_router, prefix="/it", tags=["IT"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"], dependencies=[Depends(check_module_access("chat", PermissionLevel.READ_ONLY))])
api_router.include_router(files_router, prefix="/files", tags=["Files"], dependencies=[Depends(check_module_access("files", PermissionLevel.READ_ONLY))])
api_router.include_router(stock_router, prefix="/stock-catalog", tags=["Stock"], dependencies=[Depends(check_module_access("stock", PermissionLevel.READ_ONLY))])
api_router.include_router(approvals_router, prefix="/approvals", tags=["Approvals"], dependencies=[Depends(check_module_access("approvals", PermissionLevel.READ_ONLY))])
api_router.include_router(automations_router, prefix="/automations", tags=["Automations"], dependencies=[Depends(check_module_access("automations", PermissionLevel.READ_ONLY))])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])

# Rota WebSocket de Notificações em Tempo Real (Aprovações e atualizações)
from fastapi import WebSocket, WebSocketDisconnect, status
from app.core.ws import manager, authenticate_ws_token, kanban_manager
from app.modules.kanban.service import KanbanService
from typing import Optional

@api_router.websocket("/ws/events")
@api_router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Endpoint WebSocket para recebimento de eventos e notificações ao vivo do Portal Vesper.
    Autenticação aceita via query parameter 'token' ou via cookie 'access_token'.
    """
    if not token:
        # Se não enviado por query param, tenta extrair dos cookies
        token = websocket.cookies.get("access_token")
        if token and token.startswith("Bearer "):
            token = token[7:]

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = authenticate_ws_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(user.id, websocket)
    try:
        while True:
            # Mantém a conexão ativa escutando pings periódicos
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
    except Exception:
        manager.disconnect(user.id, websocket)


@api_router.websocket("/ws/kanban")
async def websocket_kanban(
    websocket: WebSocket,
    board_id: int,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    WebSocket autenticado por board do Kanban. A conexao so e aceita quando o
    usuario tem acesso de leitura ao board informado.
    """
    if not token:
        token = websocket.cookies.get("access_token")
        if token and token.startswith("Bearer "):
            token = token[7:]

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = authenticate_ws_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        KanbanService.get_board_detail(db, board_id, user)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await kanban_manager.connect(board_id, user.id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        kanban_manager.disconnect(board_id, user.id, websocket)
    except Exception:
        kanban_manager.disconnect(board_id, user.id, websocket)


@api_router.websocket("/ws/it")
async def websocket_it(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    WebSocket autenticado do modulo TI. Nesta fase ele mantém canal por usuário
    para eventos de chamados próprios ou fila técnica; o frontend mantém polling
    como fallback.
    """
    if not token:
        token = websocket.cookies.get("access_token")
        if token and token.startswith("Bearer "):
            token = token[7:]
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    user = authenticate_ws_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.connect(user.id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
    except Exception:
        manager.disconnect(user.id, websocket)


@api_router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    WebSocket autenticado para o modulo de Chat.
    Permite comunicação bidirecional de eventos como digitação, status de presença e entrega instantânea de mensagens.
    """
    if not token:
        token = websocket.cookies.get("access_token")
        if token and token.startswith("Bearer "):
            token = token[7:]

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = authenticate_ws_token(token, db)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    from app.modules.chat.events import chat_ws_manager
    import json

    await chat_ws_manager.connect(user.id, websocket, db)
    try:
        while True:
            raw_data = await websocket.receive_text()
            if raw_data == "ping":
                await websocket.send_text("pong")
                continue
            try:
                data = json.loads(raw_data)
                if isinstance(data, dict):
                    if data.get("type") == "typing":
                        conversation_id = data.get("conversation_id")
                        is_typing = data.get("is_typing", False)
                        if conversation_id:
                            await chat_ws_manager.set_user_typing(user.id, int(conversation_id), is_typing, db)
            except Exception:
                pass
    except WebSocketDisconnect:
        await chat_ws_manager.disconnect(user.id, websocket, db)
    except Exception:
        await chat_ws_manager.disconnect(user.id, websocket, db)
