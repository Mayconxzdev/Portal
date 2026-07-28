from sqlalchemy import or_, desc
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app.models.approval import Approval
from app.models.approval_comment import ApprovalComment
from app.models.approval_decision import ApprovalDecision
from app.models.user import User
from app.models.module import Module
from app.models.user_module_access import UserModuleAccess
from app.modules.approvals.schemas import ApprovalCreate
from app.core.audit import log_action
from app.core.permissions import PermissionLevel, LEVEL_VALUES

# Callback para enviar notificações websocket se registrado
ws_notification_callback = None

def register_ws_callback(callback):
    global ws_notification_callback
    ws_notification_callback = callback

def trigger_notification(event_type: str, approval: Approval, db: Session):
    if ws_notification_callback:
        try:
            ws_notification_callback(event_type, approval, db)
        except Exception as e:
            print(f"Erro ao disparar notificacao WS: {e}")

class ApprovalService:
    @staticmethod
    def log_access_denied(db: Session, current_user: User, approval: Optional[Approval], reason: str) -> None:
        log_action(
            db=db,
            user_id=current_user.id,
            action="approval.access.denied",
            module="approvals",
            details={
                "approval_id": approval.id if approval else None,
                "module_slug": approval.module_slug if approval else None,
                "reason": reason
            },
            commit=True
        )

    @staticmethod
    def validate_purchase_option_result(approval: Approval, result_payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not result_payload:
            return None

        decision_type = result_payload.get("decision_type")
        if decision_type != "selected_purchase_option":
            return result_payload

        action_payload = approval.action_payload or {}
        if action_payload.get("request_type") != "purchase_options":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A selecao de opcao de compra so pode ser usada em solicitacoes com opcoes de compra."
            )

        options = action_payload.get("options")
        selected_index = result_payload.get("selected_option_index")
        if not isinstance(options, list) or not options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta solicitacao nao possui opcoes de compra validas."
            )

        if not isinstance(selected_index, int) or selected_index < 0 or selected_index >= len(options):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A opcao de compra selecionada nao existe nesta solicitacao."
            )

        selected_option = options[selected_index] or {}
        normalized_payload = dict(result_payload)
        normalized_payload["selected_option_title"] = normalized_payload.get("selected_option_title") or selected_option.get("title")
        normalized_payload["selected_option_url"] = normalized_payload.get("selected_option_url") or selected_option.get("url")
        normalized_payload["approved_price"] = normalized_payload.get("approved_price", selected_option.get("price"))
        return normalized_payload

    @staticmethod
    def get_user_module_level(db: Session, user: User, module_slug: str) -> PermissionLevel:
        """
        Retorna o nivel de permissao do usuario em um modulo especifico.
        Se for ADMIN global, retorna PermissionLevel.ADMIN.
        """
        if user.role and user.role.name == "ADMIN":
            return PermissionLevel.ADMIN

        module = db.query(Module).filter(Module.code == module_slug, Module.is_active == True).first()
        if not module:
            return PermissionLevel.NO_ACCESS

        access = db.query(UserModuleAccess).filter(
            UserModuleAccess.user_id == user.id,
            UserModuleAccess.module_id == module.id
        ).first()

        if not access:
            return PermissionLevel.NO_ACCESS

        try:
            return PermissionLevel(access.permission_level)
        except ValueError:
            return PermissionLevel.NO_ACCESS

    @staticmethod
    def create_approval(db: Session, payload: ApprovalCreate, current_user: User) -> Approval:
        """
        Cria uma nova solicitacao de aprovacao.
        Exige permissao de nivel NORMAL ou superior no modulo de origem.
        """
        # 1. Valida se o usuario tem acesso ao modulo de origem
        user_level = ApprovalService.get_user_module_level(db, current_user, payload.module_slug)
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.NORMAL]:
            ApprovalService.log_access_denied(
                db,
                current_user,
                None,
                f"Permissao insuficiente para criar aprovacao no modulo {payload.module_slug}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissao insuficiente no modulo '{payload.module_slug}' para solicitar aprovacao (requer NORMAL)."
            )

        # 2. Cria a solicitacao
        new_approval = Approval(
            title=payload.title,
            description=payload.description,
            module_slug=payload.module_slug,
            requester_user_id=current_user.id,
            status="PENDING",
            risk_level=payload.risk_level,
            action_type=payload.action_type,
            action_payload=payload.action_payload,
            expires_at=payload.expires_at,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        db.add(new_approval)
        db.commit()
        db.refresh(new_approval)

        # Emite evento de aprovacao criada (Outbox pattern)
        from app.core.events import emit_event
        emit_event(
            db=db,
            event_type="approval.created",
            aggregate_type="approval",
            aggregate_id=str(new_approval.id),
            module="approvals",
            payload={
                "approval_id": new_approval.id,
                "title": new_approval.title,
                "module_slug": new_approval.module_slug,
                "risk_level": new_approval.risk_level,
                "action_type": new_approval.action_type
            },
            actor_user_id=current_user.id
        )
        db.commit()

        # 3. Log de Auditoria Global
        log_action(
            db=db,
            user_id=current_user.id,
            action="approval.created",
            module="approvals",
            details={
                "approval_id": new_approval.id,
                "title": new_approval.title,
                "module_slug": new_approval.module_slug,
                "risk_level": new_approval.risk_level
            }
        )

        # 4. Envia notificacao WebSocket em tempo real
        trigger_notification("approval.created", new_approval, db)

        return new_approval

    @staticmethod
    def list_approvals(db: Session, current_user: User) -> List[Approval]:
        """
        Lista aprovacoes de acordo com o escopo/RBAC:
        - ADMIN ve todas.
        - MANAGER ve todas do modulo correspondente que gerencia.
        - USER ve apenas as solicitadas por si mesmo.
        """
        query = db.query(Approval).options(
            joinedload(Approval.requester),
            joinedload(Approval.approver),
            joinedload(Approval.comments).joinedload(ApprovalComment.user),
            joinedload(Approval.decisions).joinedload(ApprovalDecision.decided_by)
        )

        # Se for admin, nao filtra por escopo
        if current_user.role and current_user.role.name == "ADMIN":
            return query.order_by(desc(Approval.created_at)).all()

        # Busca todos os modulos que o usuario tem nivel MANAGER ou superior
        managed_modules = []
        accesses = db.query(UserModuleAccess).filter(UserModuleAccess.user_id == current_user.id).all()
        for access in accesses:
            try:
                level = PermissionLevel(access.permission_level)
            except ValueError:
                level = PermissionLevel.NO_ACCESS

            if LEVEL_VALUES[level] >= LEVEL_VALUES[PermissionLevel.MANAGER]:
                module = db.query(Module).filter(Module.id == access.module_id).first()
                if module:
                    managed_modules.append(module.code)

        # Constrói filtros
        filters = []
        # O usuario comum sempre ve as que solicitou
        filters.append(Approval.requester_user_id == current_user.id)
        # Se for manager de algum modulo, ve as pendentes ou gerais daquele modulo
        if managed_modules:
            filters.append(Approval.module_slug.in_(managed_modules))

        query = query.filter(or_(*filters))
        return query.order_by(desc(Approval.created_at)).all()

    @staticmethod
    def get_approval_by_id(db: Session, approval_id: int, current_user: User) -> Approval:
        """
        Busca os detalhes de uma aprovacao validando as permissoes de visualizacao.
        """
        approval = db.query(Approval).filter(Approval.id == approval_id).options(
            joinedload(Approval.requester),
            joinedload(Approval.approver),
            joinedload(Approval.comments).joinedload(ApprovalComment.user),
            joinedload(Approval.decisions).joinedload(ApprovalDecision.decided_by)
        ).first()

        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Solicitacao de aprovacao nao encontrada."
            )

        # Valida visibilidade
        if current_user.role and current_user.role.name == "ADMIN":
            return approval

        if approval.requester_user_id == current_user.id:
            return approval

        # Verifica se o usuario e manager do modulo
        user_level = ApprovalService.get_user_module_level(db, current_user, approval.module_slug)
        if LEVEL_VALUES[user_level] >= LEVEL_VALUES[PermissionLevel.MANAGER]:
            return approval

        ApprovalService.log_access_denied(
            db,
            current_user,
            approval,
            "Usuario tentou acessar aprovacao fora do seu escopo"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta solicitacao de aprovacao."
        )

    @staticmethod
    def approve_approval(
        db: Session,
        approval_id: int,
        current_user: User,
        reason: Optional[str] = None,
        result_payload: Optional[Dict[str, Any]] = None
    ) -> Approval:
        """
        Aprova uma solicitacao PENDING.
        """
        approval = ApprovalService.get_approval_by_id(db, approval_id, current_user)

        # 1. Valida se esta pendente e nao expirada
        if approval.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Esta aprovacao ja foi finalizada com status: {approval.status}"
            )

        if approval.expires_at and approval.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            approval.status = "EXPIRED"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta solicitacao expirou e nao pode ser aprovada."
            )

        # 2. Valida autorizacao de decisao (ADMIN ou MANAGER do modulo)
        user_level = ApprovalService.get_user_module_level(db, current_user, approval.module_slug)
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            ApprovalService.log_access_denied(
                db,
                current_user,
                approval,
                "Permissao insuficiente para aprovar solicitacao"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissao insuficiente no modulo '{approval.module_slug}' para aprovar (requer MANAGER)."
            )

        # 3. Regra de Auto-Aprovacao
        if approval.requester_user_id == current_user.id and not is_admin:
            ApprovalService.log_access_denied(
                db,
                current_user,
                approval,
                "Tentativa de auto-aprovacao bloqueada"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao e permitido aprovar sua propria solicitacao."
            )

        # 4. Registra a decisao e atualiza status
        validated_result_payload = ApprovalService.validate_purchase_option_result(approval, result_payload)
        approval.status = "APPROVED"
        approval.approver_user_id = current_user.id
        approval.decided_at = datetime.now(timezone.utc)
        approval.result_payload = validated_result_payload

        decision = ApprovalDecision(
            approval_id=approval.id,
            decided_by_user_id=current_user.id,
            decision="APPROVED",
            reason=reason,
            created_at=datetime.now(timezone.utc)
        )
        db.add(decision)
        
        from app.core.events import emit_event
        emit_event(
            db=db,
            event_type="approval.approved",
            aggregate_type="approval",
            aggregate_id=str(approval.id),
            module="approvals",
            payload={
                "approval_id": approval.id,
                "title": approval.title,
                "requester_user_id": approval.requester_user_id,
                "approver_user_id": current_user.id
            },
            actor_user_id=current_user.id
        )
        
        db.commit()

        # Sincroniza status do modulo de compras
        if approval.module_slug == "purchases":
            try:
                from app.models.purchase import PurchaseRequest, PurchaseActivity
                purchase_req = db.query(PurchaseRequest).filter(PurchaseRequest.approval_id == approval.id).first()
                if purchase_req:
                    items_payload = None
                    if validated_result_payload and "items" in validated_result_payload:
                        items_payload = validated_result_payload["items"]
                    elif result_payload and "items" in result_payload:
                        items_payload = result_payload["items"]

                    if items_payload and isinstance(items_payload, list):
                        approved_count = 0
                        rejected_count = 0
                        revision_requested_count = 0
                        approved_total = 0.0
                        decision_map = {item_dec.get("item_id"): item_dec for item_dec in items_payload if item_dec.get("item_id")}

                        for req_item in purchase_req.items:
                            item_id_str = str(req_item.id)
                            if item_id_str in decision_map:
                                dec_info = decision_map[item_id_str]
                                dec_status = dec_info.get("decision", "APPROVED").upper()
                                dec_notes = dec_info.get("notes")

                                # Se houver alteração de quantidade
                                if "quantity" in dec_info:
                                    req_item.quantity = float(dec_info["quantity"])

                                # Se houver opção de compra selecionada
                                selected_opt_id_str = dec_info.get("selected_option_id")
                                if selected_opt_id_str:
                                    from app.models.purchase import PurchaseItemOption
                                    import uuid
                                    selected_opt_id = uuid.UUID(selected_opt_id_str)
                                    # Desmarca outras
                                    db.query(PurchaseItemOption).filter(PurchaseItemOption.purchase_item_id == req_item.id).update({"selected": False})
                                    # Marca a selecionada
                                    opt = db.query(PurchaseItemOption).filter(PurchaseItemOption.id == selected_opt_id).first()
                                    if opt:
                                        opt.selected = True
                                        req_item.selected_option_id = selected_opt_id
                                        req_item.estimated_unit_price = opt.total_price

                                if dec_notes:
                                    req_item.specifications = f"[Decisão Chefia: {dec_notes}] " + (req_item.specifications or "")

                                if dec_status == "APPROVED":
                                    req_item.approval_status = "APPROVED"
                                    approved_count += 1
                                    price = float(req_item.estimated_unit_price or 0.0)
                                    qty = float(req_item.quantity or 1.0)
                                    approved_total += price * qty
                                elif dec_status in ["CHEAPER_OPTION_REQUESTED", "MORE_OPTIONS_REQUESTED", "OTHER_BRAND_REQUESTED", "QUANTITY_CHANGE_REQUESTED", "REVISION_REQUESTED"]:
                                    req_item.approval_status = "REVISION_REQUESTED"
                                    revision_requested_count += 1
                                    req_item.specifications = f"[Revisao solicitada pela chefia: {dec_notes or 'outra opcao necessaria'}] " + (req_item.specifications or "")
                                else:
                                    req_item.approval_status = "REJECTED"
                                    rejected_count += 1
                                    req_item.specifications = "[REJEITADO PELO CHEFE] " + (req_item.specifications or "")

                        if revision_requested_count > 0:
                            # Se pediu revisão de algum item, a requisição inteira volta para atenção / revisão
                            purchase_req.status = "RFQ_PREPARING"
                            purchase_req.estimated_total = sum(float(it.estimated_unit_price or 0.0) * float(it.quantity) for it in purchase_req.items)
                        elif approved_count > 0:
                            purchase_req.status = "APPROVED"
                            purchase_req.approved_total = approved_total
                        else:
                            purchase_req.status = "REJECTED"
                            purchase_req.approved_total = 0.0
                    else:
                        purchase_req.status = "APPROVED"
                        purchase_req.approved_total = purchase_req.estimated_total
                        for req_item in purchase_req.items:
                            req_item.approval_status = "APPROVED"

                    purchase_req.updated_at = datetime.now(timezone.utc)
                    activity = PurchaseActivity(
                        purchase_request_id=purchase_req.id,
                        user_id=current_user.id,
                        action="request.approved",
                        details={"approval_id": approval.id, "reason": reason, "result_payload": validated_result_payload or result_payload},
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(activity)
                    db.commit()
            except Exception as e:
                print(f"Erro ao sincronizar status de compras na aprovacao: {e}")

        db.refresh(approval)

        # 5. Log de Auditoria Global
        audit_details = {
            "approval_id": approval.id,
            "title": approval.title,
            "auto_approved_admin": is_admin and approval.requester_user_id == current_user.id
        }
        if validated_result_payload:
            audit_details["result_payload_summary"] = {
                "decision_type": validated_result_payload.get("decision_type"),
                "selected_option_index": validated_result_payload.get("selected_option_index"),
                "selected_option_title": validated_result_payload.get("selected_option_title"),
                "approved_price": validated_result_payload.get("approved_price")
            }

        log_action(
            db=db,
            user_id=current_user.id,
            action="approval.approved",
            module="approvals",
            details=audit_details
        )

        # 6. Envia notificacao WebSocket em tempo real
        trigger_notification("approval.approved", approval, db)

        return approval

    @staticmethod
    def reject_approval(
        db: Session,
        approval_id: int,
        reason: Optional[str],
        current_user: User,
        result_payload: Optional[Dict[str, Any]] = None
    ) -> Approval:
        """
        Rejeita uma solicitacao PENDING.
        """
        approval = ApprovalService.get_approval_by_id(db, approval_id, current_user)

        # 1. Valida se esta pendente e nao expirada
        if approval.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Esta aprovacao ja foi finalizada com status: {approval.status}"
            )

        # 2. Valida autorizacao de decisao
        user_level = ApprovalService.get_user_module_level(db, current_user, approval.module_slug)
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        
        if LEVEL_VALUES[user_level] < LEVEL_VALUES[PermissionLevel.MANAGER] and not is_admin:
            ApprovalService.log_access_denied(
                db,
                current_user,
                approval,
                "Permissao insuficiente para rejeitar solicitacao"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissao insuficiente no modulo '{approval.module_slug}' para rejeitar (requer MANAGER)."
            )

        # 3. Registra a decisao e atualiza status
        approval.status = "REJECTED"
        approval.approver_user_id = current_user.id
        approval.decided_at = datetime.now(timezone.utc)
        approval.result_payload = result_payload

        decision = ApprovalDecision(
            approval_id=approval.id,
            decided_by_user_id=current_user.id,
            decision="REJECTED",
            reason=reason,
            created_at=datetime.now(timezone.utc)
        )
        db.add(decision)
        
        from app.core.events import emit_event
        emit_event(
            db=db,
            event_type="approval.rejected",
            aggregate_type="approval",
            aggregate_id=str(approval.id),
            module="approvals",
            payload={
                "approval_id": approval.id,
                "title": approval.title,
                "requester_user_id": approval.requester_user_id,
                "approver_user_id": current_user.id,
                "reason": reason
            },
            actor_user_id=current_user.id
        )
        
        db.commit()

        # Sincroniza status do modulo de compras
        if approval.module_slug == "purchases":
            try:
                from app.models.purchase import PurchaseRequest, PurchaseActivity
                purchase_req = db.query(PurchaseRequest).filter(PurchaseRequest.approval_id == approval.id).first()
                if purchase_req:
                    purchase_req.status = "CANCELLED"
                    purchase_req.updated_at = datetime.now(timezone.utc)
                    # Cria log de atividade
                    activity = PurchaseActivity(
                        purchase_request_id=purchase_req.id,
                        user_id=current_user.id,
                        action="request.rejected",
                        details={"approval_id": approval.id, "reason": reason},
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(activity)
                    db.commit()
            except Exception as e:
                print(f"Erro ao sincronizar status de compras na rejeicao: {e}")

        db.refresh(approval)

        # 4. Log de Auditoria Global
        log_action(
            db=db,
            user_id=current_user.id,
            action="approval.rejected",
            module="approvals",
            details={
                "approval_id": approval.id,
                "title": approval.title,
                "reason": reason
            }
        )

        # 5. Envia notificacao WebSocket em tempo real
        trigger_notification("approval.rejected", approval, db)

        return approval

    @staticmethod
    def cancel_approval(db: Session, approval_id: int, current_user: User) -> Approval:
        """
        Cancela uma solicitacao PENDING.
        Pode ser feito pelo solicitante ou por um ADMIN.
        """
        approval = ApprovalService.get_approval_by_id(db, approval_id, current_user)

        # 1. Valida se esta pendente
        if approval.status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Esta aprovacao nao pode ser cancelada pois esta com status: {approval.status}"
            )

        # 2. Valida se o cancelador e o solicitante ou admin
        is_admin = current_user.role and current_user.role.name == "ADMIN"
        if approval.requester_user_id != current_user.id and not is_admin:
            ApprovalService.log_access_denied(
                db,
                current_user,
                approval,
                "Permissao insuficiente para cancelar solicitacao"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas o solicitante original ou um administrador podem cancelar esta requisicao."
            )

        # 3. Registra a decisao e atualiza status
        approval.status = "CANCELLED"
        approval.decided_at = datetime.now(timezone.utc)

        decision = ApprovalDecision(
            approval_id=approval.id,
            decided_by_user_id=current_user.id,
            decision="CANCELLED",
            reason="Cancelado pelo solicitante ou administrador.",
            created_at=datetime.now(timezone.utc)
        )
        db.add(decision)
        db.commit()
        db.refresh(approval)

        # 4. Log de Auditoria Global
        log_action(
            db=db,
            user_id=current_user.id,
            action="approval.cancelled",
            module="approvals",
            details={
                "approval_id": approval.id,
                "title": approval.title
            }
        )

        # 5. Envia notificacao WebSocket em tempo real
        trigger_notification("approval.cancelled", approval, db)

        return approval

    @staticmethod
    def add_comment(db: Session, approval_id: int, comment_text: str, current_user: User) -> ApprovalComment:
        """
        Adiciona um comentario a uma solicitacao de aprovacao.
        Exige acesso de visualizacao na aprovacao.
        """
        # Valida se o usuario pode ler a aprovacao (se nao puder, levanta 403)
        approval = ApprovalService.get_approval_by_id(db, approval_id, current_user)

        new_comment = ApprovalComment(
            approval_id=approval.id,
            user_id=current_user.id,
            comment=comment_text,
            created_at=datetime.now(timezone.utc)
        )

        db.add(new_comment)
        
        from app.core.events import emit_event
        emit_event(
            db=db,
            event_type="approval.comment.created",
            aggregate_type="approval",
            aggregate_id=str(approval.id),
            module="approvals",
            payload={
                "approval_id": approval.id,
                "title": approval.title,
                "comment_id": new_comment.id,
                "comment_text": new_comment.comment,
                "author_user_id": current_user.id,
                "requester_user_id": approval.requester_user_id
            },
            actor_user_id=current_user.id
        )
        
        db.commit()
        db.refresh(new_comment)

        # Log de Auditoria Global
        log_action(
            db=db,
            user_id=current_user.id,
            action="approval.comment.created",
            module="approvals",
            details={
                "approval_id": approval.id,
                "comment_id": new_comment.id
            }
        )

        # Notificacao WebSocket de atualizacao
        trigger_notification("approval.updated", approval, db)

        return new_comment

    @staticmethod
    def get_summary(db: Session, current_user: User) -> Dict[str, Any]:
        """
        Retorna o sumario das metricas de aprovacoes visiveis ao usuario logado.
        """
        approvals = ApprovalService.list_approvals(db, current_user)

        total_pending = 0
        my_requests_pending = 0
        waiting_my_decision = 0
        approved_recent = 0
        rejected_recent = 0
        by_risk = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        by_module = {}

        is_admin = current_user.role and current_user.role.name == "ADMIN"

        for app in approvals:
            # Conta por risco e por modulo
            by_risk[app.risk_level] = by_risk.get(app.risk_level, 0) + 1
            by_module[app.module_slug] = by_module.get(app.module_slug, 0) + 1

            if app.status == "PENDING":
                total_pending += 1
                if app.requester_user_id == current_user.id:
                    my_requests_pending += 1

                # Aguardando minha decisao
                # Usuario e admin ou manager do modulo, e nao e o proprio solicitante (regra de auto-aprovacao)
                user_level = ApprovalService.get_user_module_level(db, current_user, app.module_slug)
                is_manager = LEVEL_VALUES[user_level] >= LEVEL_VALUES[PermissionLevel.MANAGER]
                
                if (is_admin or is_manager) and app.requester_user_id != current_user.id:
                    waiting_my_decision += 1
                elif is_admin and app.requester_user_id == current_user.id:
                    # Admin pode auto-aprovar, entao aparece nas pendentes dele
                    waiting_my_decision += 1

            elif app.status == "APPROVED":
                approved_recent += 1
            elif app.status == "REJECTED":
                rejected_recent += 1

        return {
            "total_pending": total_pending,
            "my_requests_pending": my_requests_pending,
            "waiting_my_decision": waiting_my_decision,
            "approved_recent": approved_recent,
            "rejected_recent": rejected_recent,
            "by_risk": by_risk,
            "by_module": by_module
        }
