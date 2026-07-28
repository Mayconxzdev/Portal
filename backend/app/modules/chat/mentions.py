from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Any, Optional

from app.models.user import User
from app.models.user_module_access import UserModuleAccess
from app.models.module import Module
from app.models.chat import ChatConversation
from app.models.it import ITTicket, ITAsset, ITCertificate
from app.models.kanban import KanbanCard, KanbanBoard, KanbanBoardPermission, File
from app.models.approval import Approval
from app.core.permissions import PermissionLevel, LEVEL_VALUES
from app.modules.chat.permissions import ChatPermissions
from app.modules.chat.repository import ChatRepository


class ChatMentionsManager:
    @staticmethod
    def search_mentions(db: Session, query: str, user: User) -> List[Dict[str, Any]]:
        """
        Busca objetos mencionáveis aos quais o usuário logado possui acesso.
        Retorna itens formatados com segurança.
        """
        results = []
        term = f"%{query}%"
        limit = 10
        
        # 1. Busca por Usuários (@usuário)
        users = db.query(User).filter(
            User.is_active == True,
            or_(User.username.ilike(term), User.email.ilike(term))
        ).limit(limit).all()
        
        for u in users:
            # Não vazar o papel especial MESSIAS
            role_name = "ADMIN" if u.role and u.role.name == "MESSIAS" else (u.role.name if u.role else "USER")
            results.append({
                "type": "USER",
                "id": u.id,
                "slug": u.username,
                "label": u.username,
                "details": f"{u.email} ({role_name})",
                "has_access": True
            })

        # 2. Busca por Canais/Grupos (@canal)
        conversations = db.query(ChatConversation).filter(
            ChatConversation.is_archived == False,
            ChatConversation.type.in_(["CHANNEL", "GROUP"]),
            ChatConversation.name.ilike(term)
        ).all()
        
        for conv in conversations:
            if ChatPermissions.can_view_conversation(db, conv, user):
                results.append({
                    "type": "CHANNEL" if conv.type == "CHANNEL" else "GROUP",
                    "id": conv.id,
                    "slug": conv.name.lower().replace(" ", "-"),
                    "label": conv.name,
                    "details": conv.description or ("Grupo de Chat" if conv.type == "GROUP" else "Canal público"),
                    "has_access": True
                })

        # 3. Busca por Módulos (@módulo)
        # Primeiro, pega os módulos que ele possui permissão
        modules = db.query(Module).filter(
            Module.is_active == True,
            Module.name.ilike(term)
        ).all()
        
        # Constrói o mapa de permissões do usuário
        user_perms = {}
        if user.role and user.role.name in ["ADMIN", "MESSIAS"]:
            for m in modules:
                user_perms[m.code] = "ADMIN"
        else:
            for acc in user.module_accesses:
                user_perms[acc.module.code] = acc.permission_level
                
        for m in modules:
            perm = user_perms.get(m.code, "NO_ACCESS")
            if perm != "NO_ACCESS":
                results.append({
                    "type": "MODULE",
                    "id": m.id,
                    "slug": m.code,
                    "label": m.name,
                    "details": f"Módulo do Portal - Permissão: {perm}",
                    "has_access": True
                })

        # 4. Chamados de TI (@TI-000123)
        # Se o usuário for ADMIN/MESSIAS ou membro técnico de TI, pode ver todos. 
        # Usuário comum só vê chamados criados por ele mesmo.
        is_it_admin = user.role and user.role.name in ["ADMIN", "MESSIAS"]
        if not is_it_admin:
            it_access = db.query(Module).filter(Module.code == "it").first()
            it_access_level = "NO_ACCESS"
            if it_access:
                for acc in user.module_accesses:
                    if acc.module_id == it_access.id:
                        it_access_level = acc.permission_level
            is_it_admin = LEVEL_VALUES.get(PermissionLevel(it_access_level), 0) >= LEVEL_VALUES[PermissionLevel.MANAGER]
            
        tickets_query = db.query(ITTicket).filter(
            or_(ITTicket.ticket_number.ilike(term), ITTicket.title.ilike(term))
        )
        if not is_it_admin:
            tickets_query = tickets_query.filter(ITTicket.requester_user_id == user.id)
            
        tickets = tickets_query.limit(limit).all()
        for t in tickets:
            results.append({
                "type": "IT_TICKET",
                "id": t.id,
                "slug": t.ticket_number,
                "label": f"{t.ticket_number}: {t.title}",
                "details": f"Chamado de TI - Status: {t.status} | Prioridade: {t.priority}",
                "has_access": True
            })

        # 5. Ativos de TI (Equipamentos e Certificados)
        # Visível apenas para gestores de TI / ADMIN / MESSIAS
        if is_it_admin:
            assets = db.query(ITAsset).filter(
                or_(ITAsset.asset_tag.ilike(term), ITAsset.name.ilike(term))
            ).limit(5).all()
            for asset in assets:
                results.append({
                    "type": "ASSET",
                    "id": asset.id,
                    "slug": asset.asset_tag or str(asset.id),
                    "label": f"Equipamento {asset.asset_tag or ''}: {asset.name}",
                    "details": f"Ativo de TI - Status: {asset.status} | Tipo: {asset.asset_type}",
                    "has_access": True
                })
                
            certs = db.query(ITCertificate).filter(
                or_(ITCertificate.name.ilike(term), ITCertificate.domain_or_system.ilike(term))
            ).limit(5).all()
            for cert in certs:
                results.append({
                    "type": "CERTIFICATE",
                    "id": cert.id,
                    "slug": cert.domain_or_system,
                    "label": f"Certificado: {cert.name}",
                    "details": f"Domínio: {cert.domain_or_system} | Expira em: {cert.expires_at.strftime('%d/%m/%Y')}",
                    "has_access": True
                })

        # 6. Cards de Kanban (@Card)
        # Só vê se ele for ADMIN/MESSIAS ou se ele tiver acesso ao quadro do card
        kanban_boards = db.query(KanbanBoard).all()
        allowed_board_ids = set()
        if user.role and user.role.name in ["ADMIN", "MESSIAS"]:
            allowed_board_ids = {b.id for b in kanban_boards}
        else:
            board_perms = db.query(KanbanBoardPermission).filter(
                KanbanBoardPermission.user_id == user.id
            ).all()
            allowed_board_ids = {p.board_id for p in board_perms}
            
        if allowed_board_ids:
            cards = db.query(KanbanCard).filter(
                KanbanCard.board_id.in_(allowed_board_ids),
                or_(KanbanCard.title.ilike(term), KanbanCard.description.ilike(term))
            ).limit(limit).all()
            
            for c in cards:
                results.append({
                    "type": "KANBAN_CARD",
                    "id": c.id,
                    "slug": f"card-{c.id}",
                    "label": f"Card: {c.title}",
                    "details": f"Kanban - Quadro: {c.board.name} | Coluna: {c.column.name}",
                    "has_access": True
                })

        # 7. Aprovações (@Aprovação)
        # ADMIN/MESSIAS vê tudo. Colaborador vê se for solicitante ou aprovador.
        approval_query = db.query(Approval).filter(Approval.title.ilike(term))
        if not (user.role and user.role.name in ["ADMIN", "MESSIAS"]):
            approval_query = approval_query.filter(
                or_(Approval.requester_user_id == user.id, Approval.approver_user_id == user.id)
            )
        approvals = approval_query.limit(limit).all()
        for app in approvals:
            results.append({
                "type": "APPROVAL",
                "id": app.id,
                "slug": f"approval-{app.id}",
                "label": f"Aprovação: {app.title}",
                "details": f"Status: {app.status} | Módulo: {app.module_slug}",
                "has_access": True
            })

        # 8. Arquivos (@Arquivo)
        # Lista arquivos do usuário ou carregados no portal que ele tem permissão de ler
        files = db.query(File).filter(
            File.deleted_at == None,
            File.original_filename.ilike(term)
        ).limit(limit).all()
        for f in files:
            # ADMIN/MESSIAS ou dono do arquivo
            if (user.role and user.role.name in ["ADMIN", "MESSIAS"]) or f.uploaded_by_user_id == user.id:
                results.append({
                    "type": "FILE",
                    "id": f.id,
                    "slug": f.stored_filename,
                    "label": f"Arquivo: {f.original_filename}",
                    "details": f"Tamanho: {round(f.size_bytes / 1024, 1)} KB | Tipo: {f.content_type}",
                    "has_access": True
                })

        return results

    @staticmethod
    def validate_mention_access(db: Session, mention_type: str, target_id: Optional[int], target_slug: Optional[str], user: User) -> bool:
        """
        Valida se o usuário tem permissão para visualizar o objeto mencionado no chat.
        Utilizado no carregamento do chip visual para decidir se mostra o título do card/ticket real ou 'Você não tem acesso a este item'.
        """
        if user.role and user.role.name in ["ADMIN", "MESSIAS"]:
            return True
            
        if mention_type == "USER":
            return True
            
        if mention_type == "CHANNEL" or mention_type == "GROUP":
            conv = ChatRepository.get_conversation(db, target_id)
            if not conv:
                return False
            return ChatPermissions.can_view_conversation(db, conv, user)
            
        if mention_type == "MODULE":
            # slug contém o code do módulo
            module_code = target_slug
            if not module_code:
                return False
            module = db.query(Module).filter(Module.code == module_code).first()
            if not module or not module.is_active:
                return False
            access = db.query(UserModuleAccess).filter(
                UserModuleAccess.user_id == user.id,
                UserModuleAccess.module_id == module.id
            ).first()
            return access is not None and access.permission_level != "NO_ACCESS"

        if mention_type == "IT_TICKET":
            ticket = db.query(ITTicket).filter(ITTicket.id == target_id).first()
            if not ticket:
                return False
            if ticket.requester_user_id == user.id:
                return True
            # Se for gerente de TI ou superior
            it_access = db.query(Module).filter(Module.code == "it").first()
            if it_access:
                access = db.query(UserModuleAccess).filter(
                    UserModuleAccess.user_id == user.id,
                    UserModuleAccess.module_id == it_access.id
                ).first()
                if access and LEVEL_VALUES.get(PermissionLevel(access.permission_level), 0) >= LEVEL_VALUES[PermissionLevel.MANAGER]:
                    return True
            return False

        if mention_type == "KANBAN_CARD":
            card = db.query(KanbanCard).filter(KanbanCard.id == target_id).first()
            if not card:
                return False
            # Verifica se ele tem permissão de leitura no board
            perm = db.query(KanbanBoardPermission).filter(
                KanbanBoardPermission.board_id == card.board_id,
                KanbanBoardPermission.user_id == user.id
            ).first()
            return perm is not None

        if mention_type == "APPROVAL":
            app = db.query(Approval).filter(Approval.id == target_id).first()
            if not app:
                return False
            return app.requester_user_id == user.id or app.approver_user_id == user.id

        if mention_type == "FILE":
            f = db.query(File).filter(File.id == target_id, File.deleted_at == None).first()
            if not f:
                return False
            return f.uploaded_by_user_id == user.id

        return False
