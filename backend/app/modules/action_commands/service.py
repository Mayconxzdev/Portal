import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.models.action_command import ActionCommandDraft
from app.models.action_intent import ActionIntent
from app.models.user import User
from app.models.master_data import ProductItem, Supplier
from app.modules.action_commands.intent_registry import INTENT_REGISTRY
from app.modules.action_commands.parser import parse_text_command
from app.modules.action_commands.handlers import execute_action_handler
from app.modules.approvals.service import ApprovalService
from app.core.permissions import PermissionLevel, LEVEL_VALUES
from app.core.events import emit_event

class ActionCommandsService:

    @staticmethod
    def parse_command(db: Session, text: str, source: str, context: Dict[str, Any], current_user: User) -> ActionCommandDraft:
        """
        Interpreta um comando por texto livre, enriquecendo o contexto e salvando o draft inicial.
        """
        action_key, extracted_data = parse_text_command(db, text)
        
        # Enriquece com contexto extra enviado da tela
        initial_data = {}
        if context:
            if "product_item_id" in context:
                initial_data["product_item_id"] = context["product_item_id"]
            if "supplier_id" in context:
                initial_data["supplier_id"] = context["supplier_id"]
            if "notes" in context:
                initial_data["notes"] = context["notes"]

        # Une dados extraídos do texto e do contexto
        for k, v in initial_data.items():
            if v and not extracted_data.get(k):
                extracted_data[k] = v

        return ActionCommandsService.prepare_action(
            db=db,
            action_key=action_key,
            source=source,
            source_module=context.get("module") if context else None,
            source_entity_type=context.get("entity_type") if context else None,
            source_entity_id=context.get("entity_id") if context else None,
            raw_text=text,
            initial_data=extracted_data,
            current_user=current_user
        )

    @staticmethod
    def prepare_action(
        db: Session,
        action_key: str,
        source: str,
        source_module: Optional[str],
        source_entity_type: Optional[str],
        source_entity_id: Optional[str],
        raw_text: Optional[str],
        initial_data: Dict[str, Any],
        current_user: User
    ) -> ActionCommandDraft:
        """
        Prepara a ação baseada no registry (contextual ou texto livre), verificando permissões e riscos.
        """
        if action_key not in INTENT_REGISTRY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ação {action_key} não registrada no sistema."
            )

        intent = INTENT_REGISTRY[action_key]
        
        # 1. Validação de Acesso ao Módulo
        module_name = intent["module"]
        # Se for master_data ou files, pode exigir leitura geral
        check_module = module_name
        if module_name == "master_data":
            check_module = "purchases" # Permissões de Compras servem de proxy para Master Data

        user_level = ApprovalService.get_user_module_level(db, current_user, check_module)
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        
        # Permissão mínima: leitura
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.READ_ONLY] and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Você não possui permissão para acessar o módulo {intent['module']}."
            )

        # 2. Classificação de Risco
        risk_level = intent["risk_level"]
        requires_approval = risk_level in ["HIGH", "CRITICAL"]

        # 3. Processamento de Dados (Fuzzy match e Enriquecimento)
        enriched_data = dict(initial_data)
        
        # Busca detalhes humanos para o preview
        preview_data = {}
        if "product_item_id" in enriched_data and enriched_data["product_item_id"]:
            prod_id = enriched_data["product_item_id"]
            if isinstance(prod_id, str):
                try:
                    prod_id = uuid.UUID(prod_id)
                except ValueError:
                    prod_id = None
            if prod_id:
                prod = db.query(ProductItem).filter(ProductItem.id == prod_id).first()
                if prod:
                    preview_data["Produto"] = f"{prod.name} (SKU: {prod.sku})"
                    preview_data["Unidade"] = prod.unit_of_measure or "un"
        if "supplier_id" in enriched_data and enriched_data["supplier_id"]:
            sup_id = enriched_data["supplier_id"]
            if isinstance(sup_id, str):
                try:
                    sup_id = uuid.UUID(sup_id)
                except ValueError:
                    sup_id = None
            if sup_id:
                sup = db.query(Supplier).filter(Supplier.id == sup_id).first()
                if sup:
                    preview_data["Fornecedor"] = sup.person.name if sup.person else sup.company_name
        if "unit_price" in enriched_data and enriched_data["unit_price"]:
            preview_data["Valor Unitário"] = f"R$ {float(enriched_data['unit_price']):.2f}"
        if "quantity" in enriched_data and enriched_data["quantity"]:
            preview_data["Quantidade"] = float(enriched_data["quantity"])
        if "description" in enriched_data and enriched_data["description"]:
            preview_data["Descrição"] = enriched_data["description"]
        if "category" in enriched_data and enriched_data["category"]:
            preview_data["Categoria"] = enriched_data["category"]
        if "notes" in enriched_data and enriched_data["notes"]:
            preview_data["Observações"] = enriched_data["notes"]

        # 4. Detecção de Campos Faltantes
        missing_fields = []
        for field in intent["required_fields"]:
            if field["name"] not in enriched_data or enriched_data[field["name"]] is None:
                missing_fields.append(field)

        # Consulta staging legado em busca de correspondencias para auxiliar o preenchimento (UAL)
        try:
            from app.modules.legacy_imports.service import LegacyImportService
            # Se falta produto e temos um termo de busca
            if any(f["name"] == "product_item_id" for f in missing_fields):
                term = initial_data.get("product_name") or initial_data.get("description") or raw_text
                if term and len(str(term).strip()) > 2:
                    legacy_items = LegacyImportService.legacy_context_search(db, str(term), "PRODUCT_ITEM")
                    if legacy_items:
                        preview_data["Nota de Staging"] = f"Encontrei {len(legacy_items)} itens parecidos no staging legado. Cadastre de forma oficial para prosseguir."
            
            # Se falta fornecedor
            if any(f["name"] == "supplier_id" for f in missing_fields):
                term = initial_data.get("supplier_name") or raw_text
                if term and len(str(term).strip()) > 2:
                    legacy_sups = LegacyImportService.legacy_context_search(db, str(term), "SUPPLIER")
                    if legacy_sups:
                        preview_data["Nota de Staging"] = f"Encontrei {len(legacy_sups)} fornecedores parecidos no staging legado. Cadastre de forma oficial para prosseguir."
        except Exception:
            # Importacao circular ou outro erro nao deve travar a UAL
            pass

        # 5. Determinação de Status
        if missing_fields:
            draft_status = "NEEDS_MORE_INFO"
        elif requires_approval:
            draft_status = "APPROVAL_REQUIRED"
        else:
            draft_status = "READY_TO_CONFIRM"

        # 6. Salva Rascunho no Banco de Dados
        draft = ActionCommandDraft(
            user_id=current_user.id,
            source=source,
            source_module=source_module,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            raw_text=raw_text,
            action_key=action_key,
            intent_type=action_key,
            module=intent["module"],
            status=draft_status,
            extracted_data=initial_data,
            enriched_data=enriched_data,
            missing_fields={ "fields": missing_fields },
            preview=preview_data,
            risk_level=risk_level,
            requires_confirmation=True,
            requires_approval=requires_approval,
            target_action_type=intent["target_action_type"]
        )

        db.add(draft)
        db.flush() # Gera o ID UUID

        # Emite Evento do Outbox
        emit_event(
            db=db,
            event_type="action_command.parsed" if raw_text else "action_command.prepared",
            aggregate_type="action_command_draft",
            aggregate_id=str(draft.id),
            module="action_commands",
            payload={
                "id": str(draft.id),
                "action_key": draft.action_key,
                "status": draft.status,
                "risk_level": draft.risk_level
            },
            actor_user_id=current_user.id
        )

        if missing_fields:
            emit_event(
                db=db,
                event_type="action_command.missing_fields",
                aggregate_type="action_command_draft",
                aggregate_id=str(draft.id),
                module="action_commands",
                payload={
                    "id": str(draft.id),
                    "missing_count": len(missing_fields)
                },
                actor_user_id=current_user.id
            )

        db.commit()
        return draft

    @staticmethod
    def confirm_action(db: Session, draft_id: uuid.UUID, override_data: Dict[str, Any], current_user: User) -> ActionCommandDraft:
        """
        Confirma o rascunho de comando. Executa direto se for LOW seguro, ou gera Action Intent se for sensível.
        """
        draft = db.query(ActionCommandDraft).filter(ActionCommandDraft.id == draft_id).first()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rascunho de comando não encontrado."
            )

        if draft.status in ["CONFIRMED", "EXECUTED", "FAILED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Este comando já foi processado e está com status {draft.status}."
            )

        # Atualiza dados com o override de campos faltantes preenchidos pelo usuário
        if override_data:
            for k, v in override_data.items():
                draft.enriched_data[k] = v

        # Re-verifica se ainda há campos faltantes
        intent = INTENT_REGISTRY[draft.action_key]
        missing_fields = []
        for field in intent["required_fields"]:
            if field["name"] not in draft.enriched_data or draft.enriched_data[field["name"]] is None:
                missing_fields.append(field)

        if missing_fields:
            draft.status = "NEEDS_MORE_INFO"
            draft.missing_fields = { "fields": missing_fields }
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não foi possível confirmar: faltam informações de {[f['label'] for f in missing_fields]}."
            )

        draft.status = "CONFIRMED"
        draft.confirmed_at = datetime.now(timezone.utc)
        db.flush()

        # Emite evento de confirmação
        emit_event(
            db=db,
            event_type="action_command.confirmed",
            aggregate_type="action_command_draft",
            aggregate_id=str(draft.id),
            module="action_commands",
            payload={
                "id": str(draft.id),
                "action_key": draft.action_key
            },
            actor_user_id=current_user.id
        )

        # Regras de Risco e Moderação por Alçadas
        if draft.risk_level == "CRITICAL":
            # Comando crítico é bloqueado por questões de conformidade tributária/fiscal/segurança nesta PR
            draft.status = "FAILED"
            draft.error_message = "Ação bloqueada de forma estrita pelo portão de segurança de Risco CRITICAL."
            db.commit()
            emit_event(
                db=db,
                event_type="action_command.failed",
                aggregate_type="action_command_draft",
                aggregate_id=str(draft.id),
                module="action_commands",
                payload={
                    "id": str(draft.id),
                    "error": draft.error_message
                },
                actor_user_id=current_user.id
            )
            return draft

        # Se for HIGH ou exigir aprovação gerencial
        if draft.risk_level == "HIGH" or draft.requires_approval:
            # Cria uma Action Intent pendente no banco
            action_intent = ActionIntent(
                source="user",
                proposed_action=draft.target_action_type,
                target_module=draft.module,
                title=f"Aprovação: {intent['title']}",
                summary=f"Ação solicitada via Universal Action Layer por {current_user.username}.",
                risk_level=draft.risk_level,
                status="APPROVAL_REQUIRED",
                action_payload=draft.enriched_data,
                created_by_user_id=current_user.id,
                created_at=datetime.now(timezone.utc)
            )
            db.add(action_intent)
            db.flush()

            draft.action_intent_id = action_intent.id
            draft.status = "APPROVAL_REQUIRED"
            db.commit()

            emit_event(
                db=db,
                event_type="action_command.approval_required",
                aggregate_type="action_command_draft",
                aggregate_id=str(draft.id),
                module="action_commands",
                payload={
                    "id": str(draft.id),
                    "action_intent_id": str(action_intent.id)
                },
                actor_user_id=current_user.id
            )
            return draft

        # Ações LOW (Seguras) ou MEDIUM que o usuário tem alçada para rodar direto
        try:
            # Verifica se o usuário tem permissão de escrita/execução
            user_level = ApprovalService.get_user_module_level(db, current_user, draft.module)
            is_admin = current_user.role and current_user.role.name == "ADMIN"
            
            # MEDIUM exige privilégios de NORMAL ou superior
            required_level = PermissionLevel.NORMAL if draft.risk_level == "MEDIUM" else PermissionLevel.READ_ONLY
            if LEVEL_VALUES[user_level] < LEVEL_VALUES[required_level] and not is_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não possui permissão de escrita para executar esta ação."
                )

            # Executa de fato no módulo de destino
            res = execute_action_handler(db, draft.action_key, draft.enriched_data, current_user)
            
            draft.status = "EXECUTED"
            draft.created_entity_type = res.get("created_entity_type")
            draft.created_entity_id = res.get("created_entity_id")
            
            # Atualiza o preview final com o resumo real da criação
            draft.preview["Resultado"] = res.get("summary")
            
            db.commit()

            emit_event(
                db=db,
                event_type="action_command.executed",
                aggregate_type="action_command_draft",
                aggregate_id=str(draft.id),
                module="action_commands",
                payload={
                    "id": str(draft.id),
                    "created_entity_type": draft.created_entity_type,
                    "created_entity_id": draft.created_entity_id
                },
                actor_user_id=current_user.id
            )
            
        except Exception as e:
            draft.status = "FAILED"
            draft.error_message = str(e)
            db.commit()
            emit_event(
                db=db,
                event_type="action_command.failed",
                aggregate_type="action_command_draft",
                aggregate_id=str(draft.id),
                module="action_commands",
                payload={
                    "id": str(draft.id),
                    "error": str(e)
                },
                actor_user_id=current_user.id
            )
            raise e

        return draft

    @staticmethod
    def cancel_action(db: Session, draft_id: uuid.UUID, current_user: User) -> ActionCommandDraft:
        """
        Cancela a execução de um rascunho de comando.
        """
        draft = db.query(ActionCommandDraft).filter(ActionCommandDraft.id == draft_id).first()
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rascunho de comando não encontrado."
            )

        if draft.status in ["CONFIRMED", "EXECUTED", "FAILED", "CANCELLED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Este comando já foi finalizado com status {draft.status}."
            )

        draft.status = "CANCELLED"
        db.commit()

        emit_event(
            db=db,
            event_type="action_command.cancelled",
            aggregate_type="action_command_draft",
            aggregate_id=str(draft.id),
            module="action_commands",
            payload={
                "id": str(draft.id)
            },
            actor_user_id=current_user.id
        )

        return draft

    @staticmethod
    def get_recent_commands(db: Session, current_user: User, limit: int = 10) -> List[ActionCommandDraft]:
        """
        Retorna comandos de ação recentes criados pelo usuário logado.
        """
        return db.query(ActionCommandDraft).filter(
            ActionCommandDraft.user_id == current_user.id
        ).order_by(ActionCommandDraft.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_available_actions(module: Optional[str], entity_type: Optional[str]) -> List[Dict[str, Any]]:
        """
        Retorna a lista de ações disponíveis filtradas por módulo e tipo de entidade para preenchimento de botões rápidos.
        """
        actions = []
        for key, val in INTENT_REGISTRY.items():
            # Filtro por módulo
            if module and val["module"] != module:
                continue
            
            # Filtro por entidade de destino
            # Procura nos required fields se o target_entity coincide
            has_entity = False
            if entity_type:
                for f in val["required_fields"]:
                    if f.get("source_entity") == entity_type:
                        has_entity = True
                        break
                if not has_entity:
                    continue

            actions.append({
                "action_key": val["action_key"],
                "title": val["title"],
                "description": val["description"],
                "module": val["module"],
                "risk_level": val["risk_level"]
            })
        return actions
