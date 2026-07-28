import uuid
import logging
import csv
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.legacy_import import (
    LegacyImportBatch,
    LegacyImportRow,
    LegacyDuplicateCandidate,
    LegacyImportDecision,
    LegacyEntityLink,
    LegacyOperationalRecord,
    LegacyFileIndex
)
from app.models.master_data import (
    Person,
    Supplier,
    Customer,
    ProductItem,
    Service
)
from app.models.purchase import (
    PurchasePriceHistory,
    PurchasePriceReference,
    PurchasePriceEvidence,
    PurchasePriceUpdateSuggestion
)
from app.models.it import ITSystem, ITAccessRecord
from app.models.user import User
from app.models.user_module_access import UserModuleAccess
from app.core.events import emit_event

logger = logging.getLogger("vesper.legacy_promotion")

class LegacyPromotionService:
    @staticmethod
    def get_dashboard_stats(db: Session) -> Dict[str, int]:
        """
        Retorna contagens gerais para o dashboard de Dados Reais Ativados.
        """
        return {
            "suppliers_count": db.query(Supplier).count(),
            "customers_count": db.query(Customer).count(),
            "products_count": db.query(ProductItem).count(),
            "services_count": db.query(Service).count(),
            "price_history_count": db.query(PurchasePriceHistory).count(),
            "it_access_count": db.query(ITAccessRecord).count(),
            "legacy_ops_count": db.query(LegacyOperationalRecord).filter(LegacyOperationalRecord.entity_target == "PRODUCTION_OP").count(),
            "legacy_projects_count": db.query(LegacyOperationalRecord).filter(LegacyOperationalRecord.entity_target == "PROJECT_TASK").count(),
            "legacy_proposals_count": db.query(LegacyOperationalRecord).filter(LegacyOperationalRecord.entity_target == "PROPOSAL_DOCUMENT").count(),
            "legacy_files_count": db.query(LegacyFileIndex).count(),
            "pending_review_count": db.query(LegacyImportRow).filter(LegacyImportRow.status == "PENDING_REVIEW").count(),
            "blocked_duplicates_count": db.query(LegacyImportRow).filter(LegacyImportRow.status == "DUPLICATE_CANDIDATE").count(),
        }

    @staticmethod
    def preview_batch_promotion(db: Session, batch_id: uuid.UUID) -> Dict[str, Any]:
        """
        Gera uma prévia da promoção de um lote.
        """
        batch = db.query(LegacyImportBatch).filter(LegacyImportBatch.id == batch_id).first()
        if not batch:
            raise ValueError("Lote não encontrado")

        rows = db.query(LegacyImportRow).filter(LegacyImportRow.batch_id == batch_id).all()
        
        # Agrupar contagens
        summary_map = {}
        for r in rows:
            target = r.entity_target
            if target not in summary_map:
                summary_map[target] = {
                    "entity_target": target,
                    "to_create": 0,
                    "to_link_existing": 0,
                    "to_skip_duplicate": 0,
                    "total": 0
                }
            
            summary_map[target]["total"] += 1
            
            # Checar duplicados e decisão
            has_decision = db.query(LegacyImportDecision).filter(LegacyImportDecision.row_id == r.id).first()
            has_duplicates = db.query(LegacyDuplicateCandidate).filter(LegacyDuplicateCandidate.row_id == r.id).first()
            
            if has_decision:
                dec = has_decision.decision
                if dec == "ACCEPT" or dec == "CREATE_NEW":
                    summary_map[target]["to_create"] += 1
                elif dec == "MERGE" or dec == "UPDATE_EXISTING":
                    summary_map[target]["to_link_existing"] += 1
                else:
                    summary_map[target]["to_skip_duplicate"] += 1
            else:
                if has_duplicates:
                    summary_map[target]["to_skip_duplicate"] += 1
                else:
                    summary_map[target]["to_create"] += 1

        return {
            "source_app": batch.source_app,
            "module_target": batch.module_target,
            "summary": list(summary_map.values()),
            "can_promote": batch.status in ["NEEDS_REVIEW", "READY_TO_IMPORT", "DISCOVERED", "EXTRACTED"]
        }

    @staticmethod
    def promote_row(db: Session, row_id: uuid.UUID, user_id: int, reason: str) -> Dict[str, Any]:
        """
        Promove uma única linha de staging para a base de dados oficial de forma atômica.
        """
        row = db.query(LegacyImportRow).filter(LegacyImportRow.id == row_id).first()
        if not row:
            raise ValueError("Linha de importação não encontrada")

        if row.status == "IMPORTED":
            return {"status": "skipped", "message": "Linha já importada", "link_id": None}

        # Criar a transação segura
        try:
            link = LegacyPromotionService._execute_promotion(db, row, user_id, reason)
            
            # Registrar decisão humana no histórico de staging
            decision = db.query(LegacyImportDecision).filter(LegacyImportDecision.row_id == row_id).first()
            if not decision:
                decision = LegacyImportDecision(
                    row_id=row_id,
                    decision="ACCEPT",
                    reason=reason,
                    decided_by_user_id=user_id,
                    decided_at=datetime.now(timezone.utc)
                )
                db.add(decision)

            row.status = "IMPORTED"
            row.reviewed_by_user_id = user_id
            row.reviewed_at = datetime.now(timezone.utc)
            db.commit()
            
            # Emitir evento
            emit_event(
                db=db,
                event_type="legacy.promotion.row.promoted",
                aggregate_type="LegacyImportRow",
                aggregate_id=str(row_id),
                module="legacy_promotion",
                payload={
                    "row_id": str(row_id),
                    "entity_target": row.entity_target,
                    "action": link.action if link else "PROMOTED",
                    "actor_user_id": user_id,
                    "reason": reason
                },
                actor_user_id=user_id
            )
            db.commit()
            
            return {
                "status": "success",
                "message": f"Promovido com sucesso: {row.entity_target}",
                "link_id": str(link.id) if link else None
            }
        except Exception as e:
            db.rollback()
            logger.exception(f"Falha ao promover linha {row_id}: {e}")
            
            emit_event(
                db=db,
                event_type="legacy.promotion.failed",
                aggregate_type="LegacyImportRow",
                aggregate_id=str(row_id),
                module="legacy_promotion",
                payload={
                    "row_id": str(row_id),
                    "error": str(e),
                    "actor_user_id": user_id
                },
                actor_user_id=user_id
            )
            db.commit()
            
            raise

    @staticmethod
    def promote_batch_accepted(db: Session, batch_id: uuid.UUID, user_id: int, reason: str) -> Dict[str, Any]:
        """
        Promove todas as linhas com decisão ACCEPT/CREATE_NEW ou sem duplicidade de um lote específico.
        """
        batch = db.query(LegacyImportBatch).filter(LegacyImportBatch.id == batch_id).first()
        if not batch:
            raise ValueError("Lote não encontrado")

        rows = db.query(LegacyImportRow).filter(
            LegacyImportRow.batch_id == batch_id,
            LegacyImportRow.status.in_(["PENDING_REVIEW", "READY", "DUPLICATE_CANDIDATE"])
        ).all()

        promoted_count = 0
        skipped_count = 0
        failed_count = 0

        for r in rows:
            # Verifica se há decisão de rejeição ou duplicidade bloqueada
            has_decision = db.query(LegacyImportDecision).filter(LegacyImportDecision.row_id == r.id).first()
            has_duplicates = db.query(LegacyDuplicateCandidate).filter(LegacyDuplicateCandidate.row_id == r.id).first()
            
            should_promote = False
            if has_decision:
                if has_decision.decision in ["ACCEPT", "CREATE_NEW", "MERGE", "UPDATE_EXISTING"]:
                    should_promote = True
            else:
                if not has_duplicates:
                    should_promote = True
                else:
                    skipped_count += 1
                    r.status = "DUPLICATE_CANDIDATE"
            
            if should_promote:
                try:
                    LegacyPromotionService.promote_row(db, r.id, user_id, reason)
                    promoted_count += 1
                except Exception:
                    failed_count += 1
                    r.status = "ERROR"

        batch.status = "IMPORTED"
        batch.finished_at = datetime.now(timezone.utc)
        db.commit()

        # Emitir evento do lote
        emit_event(
            db=db,
            event_type="legacy.promotion.batch.completed",
            aggregate_type="LegacyImportBatch",
            aggregate_id=str(batch_id),
            module="legacy_promotion",
            payload={
                "batch_id": str(batch_id),
                "promoted_count": promoted_count,
                "skipped_count": skipped_count,
                "failed_count": failed_count,
                "actor_user_id": user_id
            },
            actor_user_id=user_id
        )
        db.commit()

        return {
            "status": "completed",
            "promoted": promoted_count,
            "skipped": skipped_count,
            "failed": failed_count
        }

    @staticmethod
    def promote_all_ready_by_module(db: Session, module: str, user_id: int, reason: str) -> Dict[str, Any]:
        """
        Promove todos os registros LegacyImportRow com status=READY cujo entity_target corresponde ao módulo solicitado.
        Módulo MASTER_DATA: promove SUPPLIER, CUSTOMER, PRODUCT_ITEM, SERVICE.
        """
        MODULE_ENTITY_MAP: Dict[str, List[str]] = {
            "MASTER_DATA": ["SUPPLIER", "CUSTOMER", "PRODUCT_ITEM", "PRODUCT", "SERVICE", "PERSON"],
            "PURCHASES": ["PURCHASE_ITEM", "PURCHASE_ORDER"],
        }

        if module not in MODULE_ENTITY_MAP:
            raise ValueError(f"Módulo '{module}' não suportado para promoção em lote.")

        entity_targets = MODULE_ENTITY_MAP[module]

        rows = db.query(LegacyImportRow).filter(
            LegacyImportRow.status == "READY",
            LegacyImportRow.entity_target.in_(entity_targets)
        ).all()

        promoted_count = 0
        skipped_count = 0

        for r in rows:
            try:
                LegacyPromotionService.promote_row(db, r.id, user_id, reason)
                promoted_count += 1
            except Exception as exc:
                logger.warning(f"Pulado row {r.id}: {exc}")
                skipped_count += 1

        return {
            "promoted_count": promoted_count,
            "skipped_count": skipped_count,
            "module": module
        }

    @staticmethod
    def sync_portal_access(db: Session, actor_user_id: int) -> Dict[str, Any]:

        """
        Sincroniza os acessos reais e permissões dos usuários internos do Portal Vesper na tabela `it_access_records`.
        """
        # Garante a existência do sistema Portal Vesper
        portal_sys = db.query(ITSystem).filter(ITSystem.name == "Portal Vesper").first()
        if not portal_sys:
            portal_sys = ITSystem(
                name="Portal Vesper",
                description="Sistema Operacional Interno Corporativo da Vesper/Ventrio",
                is_active=True
            )
            db.add(portal_sys)
            db.commit()
            db.refresh(portal_sys)

        # Mapear outros sistemas padrão
        sistemas_padrao = [
            "Kanban", "Help Desk", "Abacus", "Cybersul", "Skymail/E-mail", "NAS",
            "AnyDesk", "Impacta/VOIP", "Office", "ESET", "Fusion", "Compras",
            "Produção", "Projetos", "Estoque",
            "TI", "Aprovações", "Automação IA", "Administração", "Chat", "Knowledge", "Propostas"
        ]
        
        sys_map = {"Portal Vesper": portal_sys}
        for sys_name in sistemas_padrao:
            s = db.query(ITSystem).filter(ITSystem.name == sys_name).first()
            if not s:
                s = ITSystem(name=sys_name, description=f"Módulo ou ferramenta de TI: {sys_name}", is_active=True)
                db.add(s)
            sys_map[sys_name] = s
        db.commit()

        # Ler usuários ativos
        users = db.query(User).filter(User.is_active == True).all()
        
        accesses_created = 0
        
        for u in users:
            # Checar acesso geral ao Portal Vesper
            profile = u.role.name if u.role else "USER"
            
            existing = db.query(ITAccessRecord).filter(
                ITAccessRecord.user_id == u.id,
                ITAccessRecord.system_name == "Portal Vesper"
            ).first()
            
            if not existing:
                access = ITAccessRecord(
                    user_id=u.id,
                    system_id=portal_sys.id,
                    system_name="Portal Vesper",
                    access_profile=profile,
                    status="ACTIVE",
                    origin="PORTAL",
                    has_secret=False,
                    last_updated_at=datetime.now(timezone.utc)
                )
                db.add(access)
                accesses_created += 1
            else:
                existing.access_profile = profile
                existing.last_updated_at = datetime.now(timezone.utc)
                
            # Sincronizar acessos de módulos específicos via user_module_access
            module_accesses = db.query(UserModuleAccess).filter(UserModuleAccess.user_id == u.id).all()
            for ma in module_accesses:
                mod_name = ma.module.name
                if mod_name in sys_map:
                    existing_mod = db.query(ITAccessRecord).filter(
                        ITAccessRecord.user_id == u.id,
                        ITAccessRecord.system_name == mod_name
                    ).first()
                    
                    if not existing_mod:
                        access_mod = ITAccessRecord(
                            user_id=u.id,
                            system_id=sys_map[mod_name].id,
                            system_name=mod_name,
                            access_profile=ma.permission_level,
                            status="ACTIVE",
                            origin="PORTAL",
                            has_secret=False,
                            last_updated_at=datetime.now(timezone.utc)
                        )
                        db.add(access_mod)
                        accesses_created += 1
                    else:
                        existing_mod.access_profile = ma.permission_level
                        existing_mod.last_updated_at = datetime.now(timezone.utc)

        db.commit()

        # Emitir evento de sync
        emit_event(
            db=db,
            event_type="portal.access.sync.completed",
            aggregate_type="ITAccessRecord",
            aggregate_id=str(portal_sys.id),
            module="legacy_promotion",
            payload={
                "users_count": len(users),
                "accesses_created": accesses_created,
                "actor_user_id": actor_user_id
            },
            actor_user_id=actor_user_id
        )
        db.commit()

        return {
            "status": "success",
            "users_synced": len(users),
            "accesses_created": accesses_created,
            "timestamp": datetime.now(timezone.utc)
        }

    @staticmethod
    def export_access_matrix_csv(db: Session, actor_user_id: Optional[int] = None) -> str:
        """
        Gera uma representação CSV limpa e sanitizada da Matriz de Acessos para o chefe.
        Protege segredos substituindo-os por marcas de proteção.
        """
        records = db.query(ITAccessRecord).order_by(ITAccessRecord.system_name, ITAccessRecord.legacy_user_name).all()
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        
        # Header do CSV
        writer.writerow([
            "Colaborador / Usuário", 
            "E-mail",
            "Sistema / Ferramenta", 
            "Perfil de Acesso", 
            "Status", 
            "Origem dos Dados", 
            "Credencial Protegida (Sem Senha Exposta)", 
            "Ultima Atualizacao",
            "Observacao"
        ])
        
        for r in records:
            # Identificar nome do usuário
            user_name = r.legacy_user_name
            user_email = ""
            if r.user:
                user_name = (
                    getattr(r.user, "full_name", None)
                    or getattr(r.user, "username", None)
                    or getattr(r.user, "email", None)
                )
                user_email = r.user.email
            elif r.person:
                user_name = r.person.name
                user_email = r.person.email
                
            has_secret_str = "Sim (Protegida)" if r.has_secret else "Não"
            last_up = r.last_updated_at.strftime("%d/%m/%Y %H:%M") if r.last_updated_at else ""
            note = "Credencial armazenada somente no Cofre; senha nao exportada." if r.has_secret else ""
            
            writer.writerow([
                user_name or "Desconhecido",
                user_email or "",
                r.system_name,
                r.access_profile or "USER",
                r.status,
                r.origin,
                has_secret_str,
                last_up,
                note
            ])
            
        csv_data = output.getvalue()
        if actor_user_id is not None:
            emit_event(
                db=db,
                event_type="it.access.matrix.exported",
                aggregate_type="ITAccessRecord",
                aggregate_id="access-matrix",
                module="it",
                payload={
                    "records_count": len(records),
                    "actor_user_id": actor_user_id,
                    "contains_secrets": False
                },
                actor_user_id=actor_user_id
            )
            db.commit()

        return csv_data

    @staticmethod
    def export_access_matrix_to_network(db: Session, actor_user_id: int) -> Dict[str, Any]:
        """
        Exporta a matriz de acessos sanitizada para um diretório configurável.
        """
        import os
        import tempfile
        csv_data = LegacyPromotionService.export_access_matrix_csv(db, actor_user_id=actor_user_id)
        target_dir = os.getenv("PORTAL_EXPORT_DIR") or os.path.join(tempfile.gettempdir(), "Portal-Vesper-Dados")
        target_path = os.path.join(target_dir, "matriz_de_acessos_ti.csv")
        try:
            os.makedirs(target_dir, exist_ok=True)
            with open(target_path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(csv_data)
            return {
                "status": "success",
                "message": f"Matriz de acessos exportada com sucesso em: {target_path}",
                "path": target_path
            }
        except Exception as e:
            raise ValueError(f"Falha ao gravar arquivo de exportação: {str(e)}")

    # ---------------------------------------------------------------------------
    # Lógica Privada de Promoção das Entidades
    # ---------------------------------------------------------------------------
    @staticmethod
    def _execute_promotion(db: Session, row: LegacyImportRow, user_id: int, reason: str) -> LegacyEntityLink:
        normalized = row.normalized_data_json
        target = row.entity_target
        
        official_type = ""
        official_id = ""
        action = "CREATED"
        
        if target == "SUPPLIER":
            # Normalizar documento
            doc = normalized.get("cnpj") or normalized.get("document_number")
            name = normalized.get("name") or normalized.get("company_name") or "Fornecedor Importado"
            
            # Deduplicação por CNPJ
            supplier = None
            if doc:
                person = db.query(Person).filter(Person.document_number == doc).first()
                if person:
                    supplier = db.query(Supplier).filter(Supplier.person_id == person.id).first()
            
            if supplier:
                official_type = "Supplier"
                official_id = str(supplier.id)
                action = "LINKED_EXISTING"
            else:
                # Criar nova Person e Supplier
                new_person = Person(
                    type="COMPANY",
                    name=name,
                    legal_name=normalized.get("trade_name") or normalized.get("legal_name"),
                    document_type="CNPJ",
                    document_number=doc,
                    email=normalized.get("email"),
                    phone=normalized.get("phone"),
                    is_active=True
                )
                db.add(new_person)
                db.flush()
                
                new_supplier = Supplier(
                    person_id=new_person.id,
                    supplier_code=normalized.get("supplier_code") or f"FORN-{new_person.document_number[-4:]}" if doc else f"FORN-{uuid.uuid4().hex[:6].upper()}",
                    preferred_contact_email=new_person.email,
                    status="ACTIVE"
                )
                db.add(new_supplier)
                db.flush()
                
                official_type = "Supplier"
                official_id = str(new_supplier.id)
                
        elif target == "CUSTOMER":
            doc = normalized.get("cnpj") or normalized.get("cpf") or normalized.get("document_number")
            name = normalized.get("name") or normalized.get("company_name") or "Cliente Importado"
            
            customer = None
            if doc:
                person = db.query(Person).filter(Person.document_number == doc).first()
                if person:
                    customer = db.query(Customer).filter(Customer.person_id == person.id).first()
                    
            if customer:
                official_type = "Customer"
                official_id = str(customer.id)
                action = "LINKED_EXISTING"
            else:
                new_person = Person(
                    type="COMPANY" if (doc and len(doc) == 14) else "INDIVIDUAL",
                    name=name,
                    legal_name=normalized.get("legal_name"),
                    document_type="CNPJ" if (doc and len(doc) == 14) else ("CPF" if doc else None),
                    document_number=doc,
                    email=normalized.get("email"),
                    phone=normalized.get("phone"),
                    is_active=True
                )
                db.add(new_person)
                db.flush()
                
                new_customer = Customer(
                    person_id=new_person.id,
                    customer_code=normalized.get("customer_code") or f"CLI-{uuid.uuid4().hex[:6].upper()}",
                    status="ACTIVE"
                )
                db.add(new_customer)
                db.flush()
                
                official_type = "Customer"
                official_id = str(new_customer.id)
                
        elif target == "PRODUCT_ITEM":
            sku = normalized.get("sku") or normalized.get("code") or normalized.get("codigo_item")
            name = normalized.get("name") or "Item Importado"
            
            product = None
            if sku:
                product = db.query(ProductItem).filter(ProductItem.sku == sku).first()
                
            if product:
                official_type = "ProductItem"
                official_id = str(product.id)
                action = "LINKED_EXISTING"
            else:
                new_product = ProductItem(
                    sku=sku or f"SKU-{uuid.uuid4().hex[:8].upper()}",
                    name=name,
                    description=normalized.get("description"),
                    item_type="RAW_MATERIAL",
                    unit_of_measure=normalized.get("unit_of_measure") or normalized.get("unit") or "un",
                    is_active=True
                )
                db.add(new_product)
                db.flush()
                
                official_type = "ProductItem"
                official_id = str(new_product.id)
                
        elif target == "SERVICE":
            name = normalized.get("name") or "Serviço Importado"
            
            service = db.query(Service).filter(Service.name == name).first()
            if service:
                official_type = "Service"
                official_id = str(service.id)
                action = "LINKED_EXISTING"
            else:
                new_service = Service(
                    name=name,
                    description=normalized.get("description"),
                    is_active=True
                )
                db.add(new_service)
                db.flush()
                
                official_type = "Service"
                official_id = str(new_service.id)
                
        elif target == "TEMPLATE" or target == "PROPOSAL_DOCUMENT":
            # Como o modulo de Propostas final ainda não existe, nós gravamos no legacy_file_index
            file_name = normalized.get("file_name")
            file_path = normalized.get("file_path_masked")
            
            # Checar duplicado por caminho
            existing = db.query(LegacyFileIndex).filter(LegacyFileIndex.file_path_masked == file_path).first()
            if existing:
                official_type = "LegacyFileIndex"
                official_id = str(existing.id)
                action = "LINKED_EXISTING"
            else:
                new_file = LegacyFileIndex(
                    legacy_row_id=row.id,
                    file_name=file_name,
                    file_path_masked=file_path,
                    file_type=normalized.get("file_type") or "PDF",
                    file_size_bytes=normalized.get("file_size_bytes"),
                    category=normalized.get("category") or "PROPOSAL",
                    suggested_module="proposals",
                    tags=normalized.get("tags") or [],
                    metadata_json=row.raw_data_json
                )
                db.add(new_file)
                db.flush()
                
                official_type = "LegacyFileIndex"
                official_id = str(new_file.id)

        elif target == "PRODUCTION_OP" or target == "PROJECT_TASK" or target == "PROPOSAL":
            # Visões operacionais reais legadas
            title = normalized.get("title") or normalized.get("numero_op") or normalized.get("proposal_id") or "Registro Legado"
            
            new_rec = LegacyOperationalRecord(
                legacy_row_id=row.id,
                source_app=row.source_app,
                entity_target=target,
                title=title,
                status=normalized.get("status") or normalized.get("status_geral"),
                responsible=normalized.get("responsible"),
                record_date=datetime.now(timezone.utc),
                data_json=row.raw_data_json
            )
            db.add(new_rec)
            db.flush()
            
            official_type = "LegacyOperationalRecord"
            official_id = str(new_rec.id)
            
        elif target == "PRICE_HISTORY":
            # Requer mapeamento de SKU e CNPJ Fornecedor
            sku = normalized.get("sku") or normalized.get("codigo_item")
            doc = normalized.get("cnpj") or normalized.get("documento")
            
            product = db.query(ProductItem).filter(ProductItem.sku == sku).first() if sku else None
            supplier = None
            if doc:
                person = db.query(Person).filter(Person.document_number == doc).first()
                if person:
                    supplier = db.query(Supplier).filter(Supplier.person_id == person.id).first()
                    
            if not product:
                raise ValueError(f"Produto não cadastrado para o SKU: {sku}. Cadastre-o antes de promover o preço.")
                
            unit_price = normalized.get("unit_price") or normalized.get("price") or 0.0
            
            new_hist = PurchasePriceHistory(
                product_item_id=product.id,
                supplier_id=supplier.id if supplier else None,
                unit_price=unit_price,
                quantity=normalized.get("quantity"),
                total_amount=normalized.get("total_amount"),
                currency=normalized.get("currency") or "BRL",
                unit_of_measure=normalized.get("unit_of_measure") or product.unit_of_measure,
                source_type="IMPORTED_XLSX",
                source_id=row.source_row_id,
                created_by_user_id=user_id
            )
            db.add(new_hist)
            db.flush()
            
            # Tratar preço de referência
            ref = db.query(PurchasePriceReference).filter(
                PurchasePriceReference.product_item_id == product.id,
                PurchasePriceReference.supplier_id == (supplier.id if supplier else None),
                PurchasePriceReference.is_active == True
            ).first()
            
            if not ref:
                # Se não há preço de referência ativo, cria um
                new_ref = PurchasePriceReference(
                    product_item_id=product.id,
                    supplier_id=supplier.id if supplier else None,
                    current_unit_price=unit_price,
                    currency="BRL",
                    unit_of_measure=product.unit_of_measure,
                    source_history_id=new_hist.id,
                    approved_by_user_id=user_id,
                    notes="Preço de referência inicial promovido a partir do legado."
                )
                db.add(new_ref)
            else:
                # Se há preço de referência e ele diverge significativamente (ex: > 10% ou < 10%)
                diff = abs(ref.current_unit_price - unit_price)
                pct = (diff / ref.current_unit_price) if ref.current_unit_price > 0 else 0
                if pct > 0.10:
                    # Cria sugestão de atualização
                    direction = "INCREASE" if unit_price > ref.current_unit_price else "DECREASE"
                    
                    # Cria evidência provisória
                    evidence = PurchasePriceEvidence(
                        source_type="IMPORT_STAGING",
                        supplier_id=supplier.id if supplier else None,
                        product_item_id=product.id,
                        unit_price=unit_price,
                        quantity=normalized.get("quantity"),
                        total_amount=normalized.get("total_amount"),
                        created_by_user_id=user_id
                    )
                    db.add(evidence)
                    db.flush()
                    
                    new_sug = PurchasePriceUpdateSuggestion(
                        product_item_id=product.id,
                        supplier_id=supplier.id if supplier else None,
                        evidence_id=evidence.id,
                        history_id=new_hist.id,
                        reference_id=ref.id,
                        old_unit_price=ref.current_unit_price,
                        new_unit_price=unit_price,
                        pct_variation=pct,
                        variation_direction=direction,
                        status="PENDING",
                        reason="Preço promovido do legado diverge do preço de referência atual.",
                        created_by_user_id=user_id
                    )
                    db.add(new_sug)
            
            official_type = "PurchasePriceHistory"
            official_id = str(new_hist.id)
            
        elif target == "IT_ACCESS" or target == "EMAIL_ACCOUNT_ACCESS" or target == "NAS_ACCESS" or target == "VOIP_ACCOUNT" or target == "CREDENTIAL_METADATA":
            system_name = normalized.get("system_name") or normalized.get("domain") or "Sistema Legado"
            
            # Garante o sistema no catálogo
            system = db.query(ITSystem).filter(ITSystem.name == system_name).first()
            if not system:
                system = ITSystem(name=system_name, description=f"Importado de acessos legados ({row.source_app})", is_active=True)
                db.add(system)
                db.flush()
                
            # Procurar usuário real
            email = normalized.get("email") or normalized.get("login")
            user = None
            if email:
                user = db.query(User).filter(User.email == email).first()
                
            # Tratar segredos
            has_secret = False
            raw_data = row.raw_data_json
            for k in raw_data.keys():
                if any(sub in k.lower() for sub in ["password", "senha", "key", "secret", "token", "hash", "pwd", "credential"]):
                    has_secret = True
                    break
                    
            new_access = ITAccessRecord(
                user_id=user.id if user else None,
                system_id=system.id,
                system_name=system_name,
                legacy_user_name=normalized.get("usuario") or normalized.get("nome") or normalized.get("username"),
                access_profile=normalized.get("perfil") or normalized.get("access_profile"),
                status="ACTIVE",
                origin=row.source_app,
                has_secret=has_secret,
                last_updated_at=datetime.now(timezone.utc)
            )
            db.add(new_access)
            db.flush()
            
            official_type = "ITAccessRecord"
            official_id = str(new_access.id)
            
        else:
            raise NotImplementedError(f"Tipo de promoção não suportado: {target}")

        # Gravar link
        link = LegacyEntityLink(
            legacy_row_id=row.id,
            source_app=row.source_app,
            entity_target=target,
            official_entity_type=official_type,
            official_entity_id=official_id,
            action=action,
            created_by_user_id=user_id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(link)
        db.flush()
        
        return link

    @staticmethod
    def get_access_matrix(db: Session) -> List[Dict[str, Any]]:
        """
        Retorna a matriz de acessos de TI mapeada com informações do usuário.
        """
        records = db.query(ITAccessRecord).order_by(ITAccessRecord.system_name, ITAccessRecord.legacy_user_name).all()
        result = []
        for r in records:
            user_name = r.legacy_user_name
            user_email = ""
            if r.user:
                user_name = (
                    getattr(r.user, "full_name", None)
                    or getattr(r.user, "username", None)
                    or getattr(r.user, "email", None)
                )
                user_email = r.user.email
            elif r.person:
                user_name = r.person.name
                user_email = r.person.email

            result.append({
                "id": r.id,
                "user_id": r.user_id,
                "person_id": r.person_id,
                "legacy_user_name": r.legacy_user_name,
                "system_id": r.system_id,
                "system_name": r.system_name,
                "access_profile": r.access_profile,
                "status": r.status,
                "origin": r.origin,
                "has_secret": r.has_secret,
                "last_updated_at": r.last_updated_at,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "user_name": user_name or "Desconhecido",
                "user_email": user_email or ""
            })
        return result

    @staticmethod
    def get_operational_records(db: Session, entity_target: Optional[str] = None) -> List[LegacyOperationalRecord]:
        """
        Retorna os registros operacionais legados da tabela legacy_operational_records.
        """
        query = db.query(LegacyOperationalRecord)
        if entity_target:
            query = query.filter(LegacyOperationalRecord.entity_target == entity_target)
        return query.order_by(LegacyOperationalRecord.created_at.desc()).all()

    @staticmethod
    def get_file_index(
        db: Session, 
        suggested_module: Optional[str] = None, 
        category: Optional[str] = None
    ) -> List[LegacyFileIndex]:
        """
        Retorna os índices de arquivos legados pesquisáveis.
        """
        query = db.query(LegacyFileIndex)
        if suggested_module:
            query = query.filter(LegacyFileIndex.suggested_module == suggested_module)
        if category:
            query = query.filter(LegacyFileIndex.category == category)
        return query.order_by(LegacyFileIndex.created_at.desc()).all()
