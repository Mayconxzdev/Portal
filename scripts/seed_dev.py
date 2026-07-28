import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Adiciona o diretório backend ao PATH para importar os modelos do app
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.models.role import Role
from app.models.module import Module
from app.models.user_module_access import UserModuleAccess
from app.models.kanban import (
    KanbanBoard,
    KanbanBoardPermission,
    KanbanCard,
    KanbanCardAssignee,
    KanbanCardChecklist,
    KanbanCardChecklistItem,
    KanbanCardComment,
    KanbanColumn,
    KanbanCustomField,
    KanbanLabel,
    KanbanTVView,
    KanbanBoardView,
)
from app.models.it import (
    ITAccessCatalog,
    ITAccessRequest,
    ITAsset,
    ITCertificate,
    ITChecklistTemplate,
    ITCredential,
    ITMaintenanceRecord,
    ITNetworkItem,
    ITSlaPolicy,
    ITTicket,
    ITAssetCustomField,
    ITCorporateEmail,
    ITNASFolder,
    ITNote,
    ITChangeLog,
)
from app.models.chat import (
    ChatConversation,
    ChatConversationMember,
    ChatMessage,
    ChatMessageVersion,
    ChatMessageAttachment,
    ChatReaction,
    ChatMention,
    ChatPin,
    ChatReadReceipt,
    ChatNotificationSetting,
    ChatActivity,
    ChatMessiasAudit,
    ChatConversationLink,
)
from app.modules.it.credentials import encrypt_secret
from app.core.security import get_password_hash

def parse_env_file(env_path: Path) -> dict:
    """
    Realiza o parse manual do arquivo .env para evitar erros de dependência da biblioteca python-dotenv.
    """
    config = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    config[key.strip()] = val.strip().strip('"').strip("'")
    return config

def main():
    print("🌱 Iniciando o seed de banco de dados do Portal Vesper...")
    
    # 1. Carrega variáveis de ambiente locais
    root_path = Path(__file__).parent.parent
    env_config = parse_env_file(root_path / ".env")
    
    db_url = env_config.get("DATABASE_URL")
    if not db_url:
        # Fallback de montagem rápida de credenciais
        db_user = env_config.get("POSTGRES_USER", "vesper_admin")
        db_pass = env_config.get("POSTGRES_PASSWORD", "local-dev-postgres-password")
        db_host = env_config.get("POSTGRES_SERVER", "localhost")
        db_port = env_config.get("POSTGRES_PORT", "55432")
        db_name = env_config.get("POSTGRES_DB", "portal_vesper")
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    print(f"🔌 Conectando ao PostgreSQL em: {db_url.split('@')[1] if '@' in db_url else 'localhost'}")
    
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        db = Session()
    except Exception as e:
        print(f"❌ Falha ao estabelecer conexão com o PostgreSQL: {str(e)}")
        print("💡 Certifique-se de que os containers do docker estejam ativos (docker compose up -d)")
        sys.exit(1)

    try:
        # 2. Semeia os 11 Módulos Oficiais
        print("📦 Semeando módulos oficiais...")
        official_modules = [
            {"name": "Dashboard", "code": "dashboard", "is_restricted": False},
            {"name": "Kanban", "code": "kanban", "is_restricted": False},
            {"name": "Propostas", "code": "proposals", "is_restricted": False},
            {"name": "Compras", "code": "purchases", "is_restricted": False},
            {"name": "TI", "code": "it", "is_restricted": False},
            {"name": "Chat Interno", "code": "chat", "is_restricted": False},
            {"name": "Arquivos / Knowledge", "code": "files", "is_restricted": False},
            {"name": "Estoque Básico", "code": "stock", "is_restricted": False},
            {"name": "Aprovações", "code": "approvals", "is_restricted": False},
            {"name": "Automações IA", "code": "automations", "is_restricted": False},
            {"name": "Administração", "code": "admin", "is_restricted": True}
        ]

        inserted_modules = []
        for mod_data in official_modules:
            existing = db.query(Module).filter(Module.code == mod_data["code"]).first()
            if not existing:
                mod = Module(
                    name=mod_data["name"],
                    code=mod_data["code"],
                    is_active=True,
                    is_restricted=mod_data["is_restricted"]
                )
                db.add(mod)
                inserted_modules.append(mod)
                print(f"   [+] Módulo criado: {mod_data['name']}")
            else:
                inserted_modules.append(existing)
        db.commit()

        # 3. Semeia Perfis / Cargos (Roles)
        print("👤 Semeando roles de sistema...")
        roles = [
            {"name": "ADMIN", "description": "Administrador Geral do Portal"},
            {"name": "APPROVER", "description": "Gestor e Aprovador de Operações"},
            {"name": "USER", "description": "Colaborador Normal do Portal"},
            {"name": "MESSIAS", "description": "Papel especial de auditoria e supervisão do Chat"}
        ]
        
        for role_data in roles:
            existing = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not existing:
                role = Role(name=role_data["name"], description=role_data["description"])
                db.add(role)
                print(f"   [+] Role criada: {role_data['name']}")
        db.commit()

        # 4. Semeia usuário administrador de desenvolvimento.
        # As credenciais vêm do .env e nunca devem ser reutilizadas em ambiente compartilhado.
        admin_username = env_config.get("PORTAL_DEV_ADMIN_USER", "vesper_admin")
        admin_password = env_config.get("PORTAL_DEV_ADMIN_PASSWORD", "portal-dev-only")
        admin_email = env_config.get("PORTAL_DEV_ADMIN_EMAIL", "admin@vesper.local")
        admin_pass_hash = get_password_hash(admin_password)
        
        # Recupera o ID da role ADMIN
        admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
        admin_role_id = admin_role.id if admin_role else None
        
        print("👤 Semeando usuário admin local de desenvolvimento...")
        admin_user = db.query(User).filter(User.username == admin_username).first()
        if not admin_user:
            admin_user = User(
                username=admin_username,
                email=admin_email,
                hashed_password=admin_pass_hash,
                is_active=True,
                role_id=admin_role_id
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"   [+] Usuário local '{admin_username}' criado. Credencial lida do .env.")
        else:
            # Garante que a role esteja correta caso o usuário já exista
            if admin_user.role_id != admin_role_id:
                admin_user.role_id = admin_role_id
                db.commit()
                print(f"   [~] Role do usuário '{admin_username}' atualizada para ADMIN.")
            print(f"   [~] Usuário '{admin_username}' já existente.")

        # 5. Concede Permissão ADMIN para todos os módulos ao usuário admin
        print("🛡️ Concedendo níveis de acessos aos módulos...")
        for mod in inserted_modules:
            existing_access = db.query(UserModuleAccess).filter(
                UserModuleAccess.user_id == admin_user.id,
                UserModuleAccess.module_id == mod.id
            ).first()
            
            if not existing_access:
                access = UserModuleAccess(
                    user_id=admin_user.id,
                    module_id=mod.id,
                    permission_level="ADMIN"
                )
                db.add(access)
                print(f"   [+] Acesso ADMIN liberado para o módulo: {mod.code}")
            else:
                # Garante que a permissão é ADMIN mesmo se já existir
                if existing_access.permission_level != "ADMIN":
                    existing_access.permission_level = "ADMIN"
                    print(f"   [~] Acesso atualizado para ADMIN no módulo: {mod.code}")
        db.commit()

        # 6. Semeia Usuário Comum de Desenvolvimento (vesper_user)
        user_role = db.query(Role).filter(Role.name == "USER").first()
        user_role_id = user_role.id if user_role else None

        print("Semeando usuario comum local de desenvolvimento...")
        common_user = db.query(User).filter(User.username == "vesper_user").first()
        if not common_user:
            common_user = User(
                username="vesper_user",
                email="user@vesper.local",
                hashed_password=get_password_hash("userpass"),
                is_active=True,
                role_id=user_role_id
            )
            db.add(common_user)
            db.commit()
            db.refresh(common_user)
            print("   [+] Usuario 'vesper_user' criado (senha: userpass)")
        else:
            print("   [~] Usuario 'vesper_user' ja existente.")

        # Concede acesso READ_ONLY ao dashboard e NORMAL ao modulo approvals e purchases para vesper_user
        dashboard_mod = db.query(Module).filter(Module.code == "dashboard").first()
        if dashboard_mod and common_user:
            existing = db.query(UserModuleAccess).filter(
                UserModuleAccess.user_id == common_user.id,
                UserModuleAccess.module_id == dashboard_mod.id
            ).first()
            if not existing:
                db.add(UserModuleAccess(
                    user_id=common_user.id,
                    module_id=dashboard_mod.id,
                    permission_level="READ_ONLY"
                ))
                db.commit()
                print("   [+] Acesso READ_ONLY ao Dashboard para vesper_user")

        approvals_mod = db.query(Module).filter(Module.code == "approvals").first()
        if approvals_mod and common_user:
            existing = db.query(UserModuleAccess).filter(
                UserModuleAccess.user_id == common_user.id,
                UserModuleAccess.module_id == approvals_mod.id
            ).first()
            if not existing:
                db.add(UserModuleAccess(
                    user_id=common_user.id,
                    module_id=approvals_mod.id,
                    permission_level="NORMAL"
                ))
                db.commit()
                print("   [+] Acesso NORMAL ao modulo approvals para vesper_user")

        purchases_mod = db.query(Module).filter(Module.code == "purchases").first()
        if purchases_mod and common_user:
            existing = db.query(UserModuleAccess).filter(
                UserModuleAccess.user_id == common_user.id,
                UserModuleAccess.module_id == purchases_mod.id
            ).first()
            if not existing:
                db.add(UserModuleAccess(
                    user_id=common_user.id,
                    module_id=purchases_mod.id,
                    permission_level="NORMAL"
                ))
                db.commit()
                print("   [+] Acesso NORMAL ao modulo purchases para vesper_user")

        # 7. Dados opcionais do Kanban apenas em desenvolvimento local.
        environment = env_config.get("ENVIRONMENT", "development")
        if environment == "development" and admin_user:
            print("Semeando boards de desenvolvimento do Kanban...")
            dev_boards = [
                {"name": "Produção", "slug": "producao", "description": "Fluxo operacional de produção."},
                {"name": "TI", "slug": "ti", "description": "Demandas internas de tecnologia."},
                {"name": "Projetos", "slug": "projetos", "description": "Acompanhamento simples de projetos."},
            ]

            for board_data in dev_boards:
                board = db.query(KanbanBoard).filter(KanbanBoard.slug == board_data["slug"]).first()
                if not board:
                    board = KanbanBoard(
                        name=board_data["name"],
                        slug=board_data["slug"],
                        description=board_data["description"],
                        created_by_user_id=admin_user.id,
                    )
                    db.add(board)
                    db.flush()
                    print(f"   [+] Board Kanban criado: {board.name}")

                permission = db.query(KanbanBoardPermission).filter(
                    KanbanBoardPermission.board_id == board.id,
                    KanbanBoardPermission.user_id == admin_user.id,
                ).first()
                if not permission:
                    db.add(KanbanBoardPermission(board_id=board.id, user_id=admin_user.id, access_level="ADMIN"))

                default_columns = [("A Fazer", 0, False), ("Em andamento", 1, False), ("Concluído", 2, True)]
                for column_name, position, is_done in default_columns:
                    column = db.query(KanbanColumn).filter(
                        KanbanColumn.board_id == board.id,
                        KanbanColumn.name == column_name,
                    ).first()
                    if not column:
                        db.add(KanbanColumn(
                            board_id=board.id,
                            name=column_name,
                            position=position,
                            is_done_column=is_done,
                        ))
                db.flush()

                first_column = db.query(KanbanColumn).filter(
                    KanbanColumn.board_id == board.id,
                    KanbanColumn.position == 0,
                ).first()
                if first_column:
                    existing_card = db.query(KanbanCard).filter(
                        KanbanCard.board_id == board.id,
                        KanbanCard.title == f"Revisar fluxo de {board.name}",
                    ).first()
                    if not existing_card:
                        db.add(KanbanCard(
                            board_id=board.id,
                            column_id=first_column.id,
                            title=f"Revisar fluxo de {board.name}",
                            description="Card de exemplo criado apenas no ambiente de desenvolvimento.",
                            position=0,
                            priority="MEDIUM",
                            created_by_user_id=admin_user.id,
                        ))
                        db.flush()
                        existing_card = db.query(KanbanCard).filter(
                            KanbanCard.board_id == board.id,
                            KanbanCard.title == f"Revisar fluxo de {board.name}",
                        ).first()

                    default_views = [
                        ("Quadro", "BOARD", True, ["title", "priority", "due_date", "assignees", "labels"]),
                        ("Lista", "LIST", False, ["title", "status", "priority", "due_date", "assignees", "labels", "updated_at"]),
                        ("TV Lista", "TV_LIST", False, ["title", "status", "priority", "due_date", "assignees"]),
                    ]
                    if board.slug == "producao":
                        default_views = [
                            ("Quadro de Producao", "PRODUCTION_BOARD", True, ["title", "op", "cliente", "modelo", "entrega", "responsaveis"]),
                            ("Lista de Producao", "PRODUCTION_LIST", False, ["op", "title", "status", "cliente", "modelo", "tensao", "qtd", "inicio", "entrega", "setor", "pendencia", "prioridade", "responsaveis"]),
                            ("TV Producao Lista", "TV_LIST", False, ["op", "cliente", "modelo", "qtd", "entrega", "setor", "pendencia"]),
                            ("TV Producao Cards", "TV_BOARD", False, ["op", "cliente", "modelo", "entrega", "etapa"]),
                        ]
                        for position, (name, key) in enumerate([
                            ("OP", "op"),
                            ("Cliente", "cliente"),
                            ("Modelo", "modelo"),
                            ("Tensao", "tensao"),
                            ("Qtd", "qtd"),
                            ("Inicio", "inicio"),
                            ("Entrega", "entrega"),
                            ("Setor", "setor"),
                            ("Pendencia", "pendencia"),
                            ("Material", "material"),
                            ("Etapa", "etapa"),
                        ]):
                            field = db.query(KanbanCustomField).filter(KanbanCustomField.board_id == board.id, KanbanCustomField.key == key).first()
                            if not field:
                                db.add(KanbanCustomField(board_id=board.id, name=name, key=key, field_type="TEXT", position=position))

                        tv_view = db.query(KanbanTVView).filter(KanbanTVView.board_id == board.id, KanbanTVView.is_default == True).first()
                        if not tv_view:
                            db.add(KanbanTVView(
                                board_id=board.id,
                                name="Monitor Producao",
                                is_default=True,
                                layout_type="PRODUCTION",
                                refresh_interval_seconds=30,
                                sort_by="urgency_score",
                                group_by="urgency",
                                visible_custom_fields=["op", "cliente", "modelo", "qtd", "entrega", "setor", "pendencia"],
                                filters={},
                                created_by_user_id=admin_user.id,
                            ))

                        examples = [
                            ("OP 1001 - Pedido atrasado", "URGENT", -2, None, {"op": "1001", "cliente": "Cliente A", "modelo": "Painel", "tensao": "220V", "qtd": "2", "inicio": "2026-05-20", "entrega": "2026-05-20", "setor": "Corte", "pendencia": "Material", "material": "Aco", "etapa": "Corte"}),
                            ("OP 1002 - Vence hoje", "HIGH", 0, admin_user.id, {"op": "1002", "cliente": "Cliente B", "modelo": "Suporte", "tensao": "110V", "qtd": "5", "inicio": "2026-05-22", "entrega": "2026-05-22", "setor": "Montagem", "pendencia": "Conferencia", "material": "Aluminio", "etapa": "Montagem"}),
                            ("OP 1003 - Proxima entrega", "MEDIUM", 3, admin_user.id, {"op": "1003", "cliente": "Cliente C", "modelo": "Base", "tensao": "380V", "qtd": "1", "inicio": "2026-05-22", "entrega": "2026-05-25", "setor": "Pintura", "pendencia": "Secagem", "material": "Inox", "etapa": "Pintura"}),
                        ]
                        for idx, (title, priority, days, assignee_id, custom_fields) in enumerate(examples, start=1):
                            card = db.query(KanbanCard).filter(KanbanCard.board_id == board.id, KanbanCard.title == title).first()
                            if not card:
                                card = KanbanCard(
                                    board_id=board.id,
                                    column_id=first_column.id,
                                    title=title,
                                    description="Exemplo real de desenvolvimento para Modo TV.",
                                    position=idx,
                                    priority=priority,
                                    due_date=datetime.now() + timedelta(days=days),
                                    assigned_to_user_id=assignee_id,
                                    custom_fields=custom_fields,
                                    created_by_user_id=admin_user.id,
                                )
                                db.add(card)
                                db.flush()
                            if assignee_id and not db.query(KanbanCardAssignee).filter(KanbanCardAssignee.card_id == card.id, KanbanCardAssignee.user_id == assignee_id).first():
                                db.add(KanbanCardAssignee(card_id=card.id, user_id=assignee_id, assigned_by_user_id=admin_user.id))

                    for view_name, view_type, is_default, visible_columns in default_views:
                        view = db.query(KanbanBoardView).filter(KanbanBoardView.board_id == board.id, KanbanBoardView.name == view_name).first()
                        if not view:
                            db.add(KanbanBoardView(
                                board_id=board.id,
                                name=view_name,
                                view_type=view_type,
                                is_default=is_default,
                                density="COMPACT" if "Lista" in view_name else "COMFORTABLE",
                                visible_columns=visible_columns,
                                sort_by="entrega" if view_type == "PRODUCTION_LIST" else "position",
                                group_by="column",
                                created_by_user_id=admin_user.id,
                                created_at=datetime.now(),
                                updated_at=datetime.now(),
                            ))

                    for label_name, color in [
                        ("Urgente", "#ef4444"),
                        ("Cliente", "#3b82f6"),
                        ("Interno", "#22c55e"),
                        ("Aguardando", "#f59e0b"),
                    ]:
                        label = db.query(KanbanLabel).filter(
                            KanbanLabel.board_id == board.id,
                            KanbanLabel.name == label_name,
                        ).first()
                        if not label:
                            db.add(KanbanLabel(board_id=board.id, name=label_name, color=color))

                    if existing_card:
                        checklist = db.query(KanbanCardChecklist).filter(
                            KanbanCardChecklist.card_id == existing_card.id,
                            KanbanCardChecklist.title == "Preparacao",
                        ).first()
                        if not checklist:
                            checklist = KanbanCardChecklist(
                                card_id=existing_card.id,
                                title="Preparacao",
                                position=0,
                                created_by_user_id=admin_user.id,
                            )
                            db.add(checklist)
                            db.flush()
                            db.add(KanbanCardChecklistItem(
                                checklist_id=checklist.id,
                                text="Confirmar responsavel",
                                position=0,
                                created_by_user_id=admin_user.id,
                            ))
                            db.add(KanbanCardChecklistItem(
                                checklist_id=checklist.id,
                                text="Definir proximo passo",
                                position=1,
                                created_by_user_id=admin_user.id,
                            ))

                        comment = db.query(KanbanCardComment).filter(
                            KanbanCardComment.card_id == existing_card.id,
                            KanbanCardComment.comment == "Comentario de desenvolvimento para validar historico do card.",
                        ).first()
                        if not comment:
                            db.add(KanbanCardComment(
                                card_id=existing_card.id,
                                user_id=admin_user.id,
                                comment="Comentario de desenvolvimento para validar historico do card.",
                            ))

                        assignee = db.query(KanbanCardAssignee).filter(
                            KanbanCardAssignee.card_id == existing_card.id,
                            KanbanCardAssignee.user_id == admin_user.id,
                        ).first()
                        if not assignee:
                            db.add(KanbanCardAssignee(
                                card_id=existing_card.id,
                                user_id=admin_user.id,
                                assigned_by_user_id=admin_user.id,
                            ))
                            existing_card.assigned_to_user_id = admin_user.id
            db.commit()

            print("Semeando dados de desenvolvimento do TI real...")
            sla_defaults = [
                ("SLA Baixa", None, "BAIXA", 480, 2880),
                ("SLA Media", None, "MEDIA", 240, 1440),
                ("SLA Alta", None, "ALTA", 60, 480),
                ("SLA Critica", None, "CRITICA", 30, 240),
            ]
            for name, category, priority, response_minutes, resolution_minutes in sla_defaults:
                if not db.query(ITSlaPolicy).filter(ITSlaPolicy.name == name).first():
                    db.add(ITSlaPolicy(name=name, category=category, priority=priority, response_minutes=response_minutes, resolution_minutes=resolution_minutes))

            template_defaults = {
                "INTERNET_REDE": ["Verificar conexao local", "Validar equipamento de rede", "Testar navegacao com usuario"],
                "COMPUTADOR": ["Identificar maquina", "Verificar disco/memoria", "Confirmar solucao com usuario"],
                "ACESSO": ["Validar solicitante", "Confirmar sistema", "Registrar conclusao"],
                "CERTIFICADO": ["Conferir dominio/sistema", "Planejar renovacao", "Registrar certificado novo"],
            }
            for category, items in template_defaults.items():
                if not db.query(ITChecklistTemplate).filter(ITChecklistTemplate.category == category, ITChecklistTemplate.title == "Atendimento padrao").first():
                    db.add(ITChecklistTemplate(category=category, title="Atendimento padrao", items=items))

            if not db.query(ITTicket).filter(ITTicket.ticket_number == "TI-000001").first():
                db.add(ITTicket(
                    ticket_number="TI-000001",
                    title="Internet instavel na producao",
                    description="Chamado exemplo para validar fila de atendimento.",
                    requester_user_id=common_user.id,
                    assigned_to_user_id=admin_user.id,
                    status="EM_ATENDIMENTO",
                    priority="ALTA",
                    category="INTERNET_REDE",
                    due_at=datetime.now() + timedelta(hours=8),
                ))

            if not db.query(ITAsset).filter(ITAsset.asset_tag == "TI-NB-001").first():
                db.add(ITAsset(asset_tag="TI-NB-001", name="Notebook Administrativo", asset_type="NOTEBOOK", status="EM_USO", assigned_to_user_id=common_user.id, location="Administrativo", serial_number="DEV-NB-001"))

            if not db.query(ITAccessCatalog).filter(ITAccessCatalog.system_name == "Portal Vesper").first():
                db.add(ITAccessCatalog(system_name="Portal Vesper", access_type="Usuario interno", responsible_team="TI", description="Acesso ao Portal Vesper local."))

            if not db.query(ITAccessRequest).filter(ITAccessRequest.system_name == "Portal Vesper", ITAccessRequest.requester_user_id == common_user.id).first():
                db.add(ITAccessRequest(requester_user_id=common_user.id, target_user_id=common_user.id, system_name="Portal Vesper", access_type="Modulo Kanban", reason="Exemplo de solicitacao de acesso."))

            if not db.query(ITCredential).filter(ITCredential.title == "Credencial fake de laboratorio").first():
                db.add(ITCredential(
                    title="Credencial fake de laboratorio",
                    system_name="Ambiente local",
                    username="usuario_fake",
                    secret_encrypted=encrypt_secret("senha_fake_de_desenvolvimento"),
                    secret_hint="Somente desenvolvimento",
                    visibility_level="IT_MANAGER",
                    created_by_user_id=admin_user.id,
                ))

            if not db.query(ITCertificate).filter(ITCertificate.name == "Certificado portal local").first():
                db.add(ITCertificate(name="Certificado portal local", domain_or_system="portal.local", issuer="Dev CA", provider="Local", expires_at=datetime.now() + timedelta(days=25), responsible_user_id=admin_user.id, status="VENCENDO"))
            if not db.query(ITCertificate).filter(ITCertificate.name == "Certificado legado vencido").first():
                db.add(ITCertificate(name="Certificado legado vencido", domain_or_system="legado.local", issuer="Dev CA", provider="Local", expires_at=datetime.now() - timedelta(days=2), responsible_user_id=admin_user.id, status="VENCIDO"))

            if not db.query(ITNetworkItem).filter(ITNetworkItem.name == "Switch laboratorio").first():
                db.add(ITNetworkItem(name="Switch laboratorio", item_type="SWITCH", ip_address="192.168.0.10", location="Rack local", status="ATIVO"))

            if not db.query(ITMaintenanceRecord).filter(ITMaintenanceRecord.title == "Limpeza preventiva notebook").first():
                db.add(ITMaintenanceRecord(title="Limpeza preventiva notebook", description="Registro exemplo de manutencao.", status="AGENDADA", scheduled_at=datetime.now() + timedelta(days=7), performed_by_user_id=admin_user.id))

            # Semeia novos recursos avançados de TI (Fase 5.2)
            print("🌱 Semeando recursos avançados de TI (Fase 5.2)...")
            
            # 1. Campos personalizados de ativos
            if not db.query(ITAssetCustomField).filter(ITAssetCustomField.name == "Local Fisico").first():
                db.add(ITAssetCustomField(name="Local Fisico", field_type="TEXT", options=[], is_active=True))
            if not db.query(ITAssetCustomField).filter(ITAssetCustomField.name == "Tomada de Rede").first():
                db.add(ITAssetCustomField(name="Tomada de Rede", field_type="TEXT", options=[], is_active=True))
            if not db.query(ITAssetCustomField).filter(ITAssetCustomField.name == "Rack").first():
                db.add(ITAssetCustomField(name="Rack", field_type="SELECT", options=["Rack Principal", "Rack Producao", "Rack Lab"], is_active=True))
            db.flush()

            # 2. E-mails corporativos
            if not db.query(ITCorporateEmail).filter(ITCorporateEmail.email_address == "usuario@portal.example").first():
                # Busca credencial vinculada
                cred = db.query(ITCredential).filter(ITCredential.title == "Credencial fake de laboratorio").first()
                db.add(ITCorporateEmail(
                    email_address="usuario@portal.example",
                    login="usuario_portal",
                    user_id=common_user.id,
                    server_config="imap.portal.example:993 (SSL), smtp.portal.example:465 (SSL)",
                    recommended_client="Thunderbird",
                    status="ATIVO",
                    credential_id=cred.id if cred else None
                ))
            if not db.query(ITCorporateEmail).filter(ITCorporateEmail.email_address == "admin@portal.example").first():
                db.add(ITCorporateEmail(
                    email_address="admin@portal.example",
                    login="admin_portal",
                    user_id=admin_user.id,
                    server_config="imap.portal.example:993 (SSL), smtp.portal.example:465 (SSL)",
                    recommended_client="Outlook",
                    status="ATIVO"
                ))
            db.flush()

            # 3. Pastas do NAS QNAP
            if not db.query(ITNASFolder).filter(ITNASFolder.name == "Compartilhamento Público").first():
                db.add(ITNASFolder(
                    name="Compartilhamento Público",
                    network_path="\\\\fileserver.local\\publico",
                    drive_letter="P:",
                    permission_level="ESCRITA",
                    notes="Pasta de uso comum de todos os colaboradores."
                ))
            if not db.query(ITNASFolder).filter(ITNASFolder.name == "Financeiro Restrito").first():
                db.add(ITNASFolder(
                    name="Financeiro Restrito",
                    network_path="\\\\fileserver.local\\financeiro",
                    drive_letter="F:",
                    user_id=admin_user.id,
                    permission_level="ADMIN",
                    notes="Acesso restrito ao time administrativo/financeiro."
                ))
            db.flush()

            # 4. Sticky Notes (Notas)
            if not db.query(ITNote).filter(ITNote.content == "Lembrar de renovar o certificado portal.local antes do dia 15!").first():
                db.add(ITNote(
                    title="Alerta de Certificado",
                    content="Lembrar de renovar o certificado portal.local antes do dia 15!",
                    color="red",
                    tags=["importante", "certificados"],
                    is_pinned=True,
                    created_by_user_id=admin_user.id
                ))
            if not db.query(ITNote).filter(ITNote.content == "Fazer o backup semanal do NAS toda sexta-feira às 18h.").first():
                db.add(ITNote(
                    title="Rotina de Backup",
                    content="Fazer o backup semanal do NAS toda sexta-feira às 18h.",
                    color="blue",
                    tags=["rotina", "backup"],
                    is_pinned=False,
                    created_by_user_id=admin_user.id
                ))
            db.flush()

            # 5. Logs de alteração ISO 9001
            if not db.query(ITChangeLog).filter(ITChangeLog.entity_type == "ITAsset").first():
                db.add(ITChangeLog(
                    entity_type="ITAsset",
                    entity_id=1,
                    action="CREATE",
                    field_name="name",
                    old_value=None,
                    new_value="Notebook Administrativo",
                    reason="Cadastro inicial do ativo",
                    origin="MANUAL",
                    user_id=admin_user.id
                ))
            db.flush()

            # 8. Semeia usuários MESSIAS de desenvolvimento
            print("👤 Semeando usuários MESSIAS local de desenvolvimento...")
            messias_role = db.query(Role).filter(Role.name == "MESSIAS").first()
            messias_role_id = messias_role.id if messias_role else None
            
            audit_demo_password = env_config.get("PORTAL_DEV_AUDITOR_PASSWORD", "portal-dev-only")
            for username in ["auditor.demo", "gestor.demo"]:
                user_row = db.query(User).filter(User.username == username).first()
                if not user_row:
                    user_row = User(
                        username=username,
                        email=f"{username.lower()}@vesper.local",
                        hashed_password=get_password_hash(audit_demo_password),
                        is_active=True,
                        role_id=messias_role_id
                    )
                    db.add(user_row)
                    db.commit()
                    db.refresh(user_row)
                    print(f"   [+] Usuário de auditoria '{username}' criado. Credencial lida do .env.")
                else:
                    if user_row.role_id != messias_role_id:
                        user_row.role_id = messias_role_id
                        db.commit()
                        print(f"   [~] Role do usuário '{username}' atualizada para MESSIAS.")
                    print(f"   [~] Usuário MESSIAS '{username}' já existente.")
                
                # Seta acesso ADMIN para todos os módulos
                for mod in inserted_modules:
                    existing_access = db.query(UserModuleAccess).filter(
                        UserModuleAccess.user_id == user_row.id,
                        UserModuleAccess.module_id == mod.id
                    ).first()
                    if not existing_access:
                        db.add(UserModuleAccess(
                            user_id=user_row.id,
                            module_id=mod.id,
                            permission_level="ADMIN"
                        ))
                db.commit()

            # 9. Semeia dados de desenvolvimento do Chat
            print("💬 Semeando dados de desenvolvimento do Chat...")
            chat_channels = [
                {"name": "Geral", "description": "Canal geral da equipe de demonstração."},
                {"name": "TI & Suporte", "description": "Discussões e suporte interno de TI."},
                {"name": "Produção", "description": "Comunicações sobre o fluxo operacional de produção."},
                {"name": "Aprovações", "description": "Notificações e alinhamento de aprovações pendentes."},
                {"name": "Projetos", "description": "Ideias e planejamento de novos projetos."}
            ]
            
            all_users = db.query(User).all()
            user_admin_row = db.query(User).filter(User.username == admin_username).first()
            user_auditor_row = db.query(User).filter(User.username == "auditor.demo").first()
            user_manager_row = db.query(User).filter(User.username == "gestor.demo").first()
            user_common_row = db.query(User).filter(User.username == "vesper_user").first()
            
            creator_id = user_admin_row.id if user_admin_row else all_users[0].id
            
            channels_map = {}
            for chan_data in chat_channels:
                chan = db.query(ChatConversation).filter(
                    ChatConversation.type == "CHANNEL",
                    ChatConversation.name == chan_data["name"]
                ).first()
                if not chan:
                    chan = ChatConversation(
                        type="CHANNEL",
                        name=chan_data["name"],
                        description=chan_data["description"],
                        is_private=False,
                        is_archived=False,
                        created_by_user_id=creator_id,
                        owner_user_id=creator_id
                    )
                    db.add(chan)
                    db.flush()
                    print(f"   [+] Canal criado: {chan.name}")
                channels_map[chan_data["name"]] = chan
                
                # Adiciona todos os usuários como membros
                for u in all_users:
                    member = db.query(ChatConversationMember).filter(
                        ChatConversationMember.conversation_id == chan.id,
                        ChatConversationMember.user_id == u.id
                    ).first()
                    if not member:
                        role = "OWNER" if u.id == creator_id else ("MODERATOR" if u.role and u.role.name in ["ADMIN", "MESSIAS"] else "MEMBER")
                        db.add(ChatConversationMember(
                            conversation_id=chan.id,
                            user_id=u.id,
                            role=role,
                            is_muted=False,
                            notification_level="ALL"
                        ))
            db.commit()
            
            # Cria mensagens de exemplo no canal Geral
            geral_chan = channels_map.get("Geral")
            if geral_chan and user_common_row and user_auditor_row and user_manager_row:
                # 1. Mensagem de boas vindas
                msg1 = db.query(ChatMessage).filter(ChatMessage.conversation_id == geral_chan.id, ChatMessage.body == "Sejam bem-vindos ao novo Chat do Portal Vesper!").first()
                if not msg1:
                    msg1 = ChatMessage(
                        conversation_id=geral_chan.id,
                        sender_user_id=creator_id,
                        message_type="TEXT",
                        body="Sejam bem-vindos ao novo Chat do Portal Vesper!",
                        body_search="Sejam bem-vindos ao novo Chat do Portal Vesper!"
                    )
                    db.add(msg1)
                    db.flush()
                    
                # 2. Mensagem editada para testar o MESSIAS
                msg2 = db.query(ChatMessage).filter(ChatMessage.conversation_id == geral_chan.id, ChatMessage.body == "Vamos alinhar a entrega da OP 1002 hoje a tarde.").first()
                if not msg2:
                    msg2 = ChatMessage(
                        conversation_id=geral_chan.id,
                        sender_user_id=user_common_row.id,
                        message_type="TEXT",
                        body="Vamos alinhar a entrega da OP 1002 hoje a tarde.",
                        body_search="Vamos alinhar a entrega da OP 1002 hoje a tarde.",
                        is_edited=True
                    )
                    db.add(msg2)
                    db.flush()
                    db.add(ChatMessageVersion(
                        message_id=msg2.id,
                        previous_body="Vamos alinhar a entrega da OP 1002 amanhã de manhã.",
                        new_body="Vamos alinhar a entrega da OP 1002 hoje a tarde.",
                        edited_by_user_id=user_common_row.id
                    ))
                    
                # 3. Mensagem apagada para testar o MESSIAS
                msg3 = db.query(ChatMessage).filter(ChatMessage.conversation_id == geral_chan.id, ChatMessage.body == "Mensagem inadequada que foi removida.").first()
                if not msg3:
                    msg3 = ChatMessage(
                        conversation_id=geral_chan.id,
                        sender_user_id=user_common_row.id,
                        message_type="TEXT",
                        body="Mensagem inadequada que foi removida.",
                        body_search="Mensagem inadequada que foi removida.",
                        is_deleted=True,
                        deleted_at=datetime.now(timezone.utc),
                        deleted_by_user_id=creator_id
                    )
                    db.add(msg3)
                    db.flush()
                
                # 4. Mensagem com reação
                msg4 = db.query(ChatMessage).filter(ChatMessage.conversation_id == geral_chan.id, ChatMessage.body == "Excelente trabalho com as correções no Kanban!").first()
                if not msg4:
                    msg4 = ChatMessage(
                        conversation_id=geral_chan.id,
                        sender_user_id=user_auditor_row.id,
                        message_type="TEXT",
                        body="Excelente trabalho com as correções no Kanban!",
                        body_search="Excelente trabalho com as correções no Kanban!"
                    )
                    db.add(msg4)
                    db.flush()
                    
                    # Reação do usuário gestor de demonstração
                    db.add(ChatReaction(
                        message_id=msg4.id,
                        user_id=user_manager_row.id,
                        emoji="👍"
                    ))
                    
                # 5. Resposta em thread
                if msg4:
                    reply1 = db.query(ChatMessage).filter(ChatMessage.conversation_id == geral_chan.id, ChatMessage.parent_message_id == msg4.id).first()
                    if not reply1:
                        reply1 = ChatMessage(
                            conversation_id=geral_chan.id,
                            sender_user_id=user_manager_row.id,
                            parent_message_id=msg4.id,
                            message_type="TEXT",
                            body="Com certeza! A sincronização em tempo real ficou ótima.",
                            body_search="Com certeza! A sincronização em tempo real ficou ótima."
                        )
                        db.add(reply1)
                        msg4.reply_count += 1
            db.commit()

            print("Banco de dados semeado com sucesso! Fundacao pronta para uso local.")

    except Exception as e:
        print(f"❌ Erro ao semear o banco de dados: {str(e)}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()

