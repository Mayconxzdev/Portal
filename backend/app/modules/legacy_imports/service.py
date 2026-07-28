import re
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.legacy_import import (
    LegacyImportBatch,
    LegacyImportRow,
    LegacyDuplicateCandidate,
    LegacyImportDecision
)
from app.models.master_data import Person, ProductItem
from app.modules.legacy_imports.schemas import (
    LegacyImportBatchCreate,
    LegacyImportRowCreate,
    LegacyImportDecisionCreate
)
from app.core.events import emit_event

logger = logging.getLogger("vesper.legacy_imports")

class LegacyImportService:
    @staticmethod
    def sanitize_data(data: Any) -> Any:
        """
        Sanitiza recursivamente dicionarios e listas para substituir chaves sensiveis
        (contendo password, key, secret, token, hash, pwd, credential, etc) por '******'
        e mascarar caminhos locais ou de rede do Windows.
        """
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                lower_k = k.lower()
                # Verifica se a chave e sensivel
                if any(sub in lower_k for sub in ["password", "key", "secret", "token", "hash", "pwd", "credential"]):
                    sanitized[k] = "******"
                else:
                    sanitized[k] = LegacyImportService.sanitize_data(v)
            return sanitized
        elif isinstance(data, list):
            return [LegacyImportService.sanitize_data(item) for item in data]
        elif isinstance(data, str):
            # Mascara caminhos de arquivos de rede ou drive local
            if data.startswith("\\\\") or re.match(r'^[a-zA-Z]:\\', data):
                parts = data.split("\\")
                if len(parts) > 2:
                    return f"{parts[0]}\\...\\{parts[-1]}"
            return data
        else:
            return data

    @staticmethod
    def normalize_row_data(entity_target: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aplica regras de normalizacao com base na entidade de destino (SUPPLIER, PRODUCT_ITEM, etc).
        Garante padronizacao para deteccao de duplicados e importacoes futuras.
        """
        normalized = {}
        
        # Copia dados basicos para manter estrutura geral
        for k, v in raw_data.items():
            normalized[k] = v
            
        # Normalizacoes por tipo
        # 1. Documentos (CPF/CNPJ)
        for doc_key in ["cnpj", "cpf", "document_number", "documento", "cgc"]:
            if doc_key in raw_data and raw_data[doc_key]:
                normalized[doc_key] = re.sub(r'\D', '', str(raw_data[doc_key]))
                
        # 2. E-mails
        for email_key in ["email", "e-mail", "preferred_contact_email", "contato_email"]:
            if email_key in raw_data and raw_data[email_key]:
                normalized[email_key] = str(raw_data[email_key]).strip().lower()
                
        # 3. SKUs e codigos
        for sku_key in ["sku", "code", "codigo", "codigo_item", "supplier_code", "customer_code"]:
            if sku_key in raw_data and raw_data[sku_key]:
                # Remove espacos extras e coloca em maiusculas
                normalized[sku_key] = re.sub(r'\s+', '', str(raw_data[sku_key])).upper()
                
        # 4. Precos
        for price_key in ["price", "unit_price", "preco", "valor", "valor_unitario", "total_amount"]:
            if price_key in raw_data and raw_data[price_key] is not None:
                val = raw_data[price_key]
                if isinstance(val, (int, float)):
                    normalized[price_key] = float(val)
                else:
                    try:
                        # Trata formato BR (ex: "1.250,50") ou US (ex: "1,250.50")
                        val_str = str(val).replace("R$", "").strip()
                        if "," in val_str and "." in val_str:
                            if val_str.find(".") < val_str.find(","): # BR
                                val_str = val_str.replace(".", "").replace(",", ".")
                            else: # US
                                val_str = val_str.replace(",", "")
                        elif "," in val_str:
                            val_str = val_str.replace(",", ".")
                        normalized[price_key] = float(val_str)
                    except ValueError:
                        normalized[price_key] = None

        return normalized

    @staticmethod
    def create_batch(
        db: Session,
        batch_in: LegacyImportBatchCreate,
        current_user_id: Optional[int] = None
    ) -> LegacyImportBatch:
        """
        Cria um novo batch de importacao.
        """
        # Limpa e sanitiza o path se houver segredo
        masked_path = LegacyImportService.sanitize_data(batch_in.source_path_masked)
        
        batch = LegacyImportBatch(
            source_app=batch_in.source_app,
            source_name=batch_in.source_name,
            source_path_masked=masked_path,
            module_target=batch_in.module_target,
            status="DISCOVERED",
            notes=batch_in.notes,
            tenant_id=batch_in.tenant_id,
            created_by_user_id=current_user_id
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        # Emite evento de criacao de batch
        emit_event(
            db=db,
            event_type="legacy.import.batch.created",
            aggregate_type="LegacyImportBatch",
            aggregate_id=str(batch.id),
            module="legacy_imports",
            payload={
                "batch_id": str(batch.id),
                "source_app": batch.source_app,
                "source_name": batch.source_name,
                "module_target": batch.module_target,
                "actor_user_id": current_user_id,
                "summary": f"Lote de importacao {batch.source_name} criado para o modulo {batch.module_target}."
            },
            actor_user_id=current_user_id,
            tenant_id=batch.tenant_id
        )
        db.commit()

        return batch

    @staticmethod
    def add_rows_to_batch(
        db: Session,
        batch_id: uuid.UUID,
        rows_in: List[LegacyImportRowCreate]
    ) -> List[LegacyImportRow]:
        """
        Insere as linhas de staging no lote. Faz sanitizacao recursiva dos dados brutos,
        normaliza os campos essenciais, detecta duplicidades contra a base oficial do Master Data
        e emite os alertas necessários.
        """
        batch = db.query(LegacyImportBatch).filter(LegacyImportBatch.id == batch_id).first()
        if not batch:
            raise ValueError(f"Batch com ID {batch_id} nao encontrado.")

        batch.status = "EXTRACTED"
        
        inserted_rows = []
        total_in = len(rows_in)
        valid_in = 0
        duplicate_in = 0
        error_in = 0

        for r_create in rows_in:
            try:
                # 1. Sanitizacao de dados brutos contra segredos e paths
                sanitized_raw = LegacyImportService.sanitize_data(r_create.raw_data_json)
                
                # 2. Normalizacao basica
                normalized = LegacyImportService.normalize_row_data(r_create.entity_target, sanitized_raw)
                
                # 3. Cria a linha de staging
                row = LegacyImportRow(
                    batch_id=batch_id,
                    source_app=batch.source_app,
                    source_table_or_sheet=r_create.source_table_or_sheet,
                    source_row_id=r_create.source_row_id,
                    module_target=batch.module_target,
                    entity_target=r_create.entity_target,
                    raw_data_json=sanitized_raw,
                    normalized_data_json=normalized,
                    confidence_score=r_create.confidence_score or 1.0,
                    status="PENDING_REVIEW",
                    tenant_id=batch.tenant_id
                )
                db.add(row)
                db.flush() # Gera o ID do Row
                
                # 4. Detecção de Duplicidades contra o Master Data
                duplicates = LegacyImportService.detect_duplicates_for_row(db, row)
                if duplicates:
                    row.status = "DUPLICATE_CANDIDATE"
                    row.detected_duplicates_json = {
                        "candidates": [
                            {
                                "target_id": str(c.target_entity_id),
                                "match_type": c.match_type,
                                "score": c.score
                            }
                            for c in duplicates
                        ]
                    }
                    duplicate_in += 1
                    
                    # Emite evento de duplicado detectado
                    emit_event(
                        db=db,
                        event_type="legacy.import.duplicate.detected",
                        aggregate_type="LegacyImportRow",
                        aggregate_id=str(row.id),
                        module="legacy_imports",
                        payload={
                            "row_id": str(row.id),
                            "batch_id": str(batch.id),
                            "entity_target": row.entity_target,
                            "match_type": duplicates[0].match_type,
                            "score": duplicates[0].score,
                            "summary": f"Duplicidade em staging detectada para {row.entity_target}."
                        },
                        tenant_id=batch.tenant_id
                    )
                else:
                    valid_in += 1
                
                inserted_rows.append(row)
                
            except Exception as e:
                logger.error(f"Erro ao processar linha de importacao: {e}")
                error_in += 1
                
        # Atualiza contadores no batch
        batch.total_rows += total_in
        batch.valid_rows += valid_in
        batch.duplicate_rows += duplicate_in
        batch.error_rows += error_in
        
        if batch.error_rows > 0 and batch.valid_rows == 0:
            batch.status = "FAILED"
        else:
            batch.status = "NEEDS_REVIEW"
            
        batch.finished_at = datetime.now(timezone.utc)
        db.commit()

        # Emite evento de lote pronto para revisao
        if batch.status == "NEEDS_REVIEW":
            emit_event(
                db=db,
                event_type="legacy.import.ready_for_review",
                aggregate_type="LegacyImportBatch",
                aggregate_id=str(batch.id),
                module="legacy_imports",
                payload={
                    "batch_id": str(batch.id),
                    "source_app": batch.source_app,
                    "source_name": batch.source_name,
                    "module_target": batch.module_target,
                    "total_rows": batch.total_rows,
                    "summary": f"Lote {batch.source_name} concluido e pronto para revisao administrativa."
                },
                tenant_id=batch.tenant_id
            )
        elif batch.status == "FAILED":
            emit_event(
                db=db,
                event_type="legacy.import.failed",
                aggregate_type="LegacyImportBatch",
                aggregate_id=str(batch.id),
                module="legacy_imports",
                payload={
                    "batch_id": str(batch.id),
                    "source_app": batch.source_app,
                    "error_message": "Todas as linhas falharam no processamento de staging.",
                    "summary": f"Falha ao processar lote {batch.source_name}."
                },
                tenant_id=batch.tenant_id
            )
            
        db.commit()
        return inserted_rows

    @staticmethod
    def detect_duplicates_for_row(db: Session, row: LegacyImportRow) -> List[LegacyDuplicateCandidate]:
        """
        Compara os dados normalizados da linha contra registros oficiais do Master Data
        (e futuramente outros modulos) por CNPJ/CPF, e-mail ou SKU.
        Salva candidatos encontrados em legacy_duplicate_candidates.
        """
        candidates = []
        norm = row.normalized_data_json
        
        if row.entity_target in ["SUPPLIER", "CUSTOMER"]:
            # 1. Busca por Documento (CNPJ / CPF)
            doc_num = None
            for key in ["cnpj", "cpf", "document_number", "documento", "cgc"]:
                if norm.get(key):
                    doc_num = norm.get(key)
                    break
                    
            if doc_num:
                # Busca exata no Master Data (people)
                person = db.query(Person).filter(Person.document_number == doc_num).first()
                if person:
                    cand = LegacyDuplicateCandidate(
                        row_id=row.id,
                        target_entity_type="PERSON",
                        target_entity_id=str(person.id),
                        match_type="DOCUMENT",
                        score=1.0,
                        status="PENDING"
                    )
                    db.add(cand)
                    candidates.append(cand)
                    
            # 2. Busca por E-mail
            email_val = None
            for key in ["email", "e-mail", "preferred_contact_email", "contato_email"]:
                if norm.get(key):
                    email_val = norm.get(key)
                    break
                    
            if email_val:
                person = db.query(Person).filter(func.lower(Person.email) == email_val.lower()).first()
                if person and not any(c.target_entity_id == str(person.id) for c in candidates):
                    cand = LegacyDuplicateCandidate(
                        row_id=row.id,
                        target_entity_type="PERSON",
                        target_entity_id=str(person.id),
                        match_type="EMAIL",
                        score=0.9,
                        status="PENDING"
                    )
                    db.add(cand)
                    candidates.append(cand)

            # 3. Busca por Nome Exato
            name_val = norm.get("name") or norm.get("razao_social") or norm.get("nome")
            if name_val:
                person = db.query(Person).filter(func.lower(Person.name) == name_val.lower()).first()
                if person and not any(c.target_entity_id == str(person.id) for c in candidates):
                    cand = LegacyDuplicateCandidate(
                        row_id=row.id,
                        target_entity_type="PERSON",
                        target_entity_id=str(person.id),
                        match_type="NAME",
                        score=0.8,
                        status="PENDING"
                    )
                    db.add(cand)
                    candidates.append(cand)

        elif row.entity_target == "PRODUCT_ITEM":
            # Busca por SKU
            sku_val = norm.get("sku") or norm.get("code") or norm.get("codigo")
            if sku_val:
                item = db.query(ProductItem).filter(func.upper(ProductItem.sku) == sku_val.upper()).first()
                if item:
                    cand = LegacyDuplicateCandidate(
                        row_id=row.id,
                        target_entity_type="PRODUCT_ITEM",
                        target_entity_id=str(item.id),
                        match_type="SKU",
                        score=1.0,
                        status="PENDING"
                    )
                    db.add(cand)
                    candidates.append(cand)

        if candidates:
            db.flush()
        return candidates

    @staticmethod
    def record_row_decision(
        db: Session,
        row_id: uuid.UUID,
        decision_in: LegacyImportDecisionCreate,
        current_user_id: int
    ) -> LegacyImportDecision:
        """
        Registra a decisao de um administrador/gerente sobre a linha de staging.
        Muda o status da linha de acordo com a decisao, mas NAO insere o dado nas tabelas ativas.
        """
        row = db.query(LegacyImportRow).filter(LegacyImportRow.id == row_id).first()
        if not row:
            raise ValueError(f"Linha de importacao com ID {row_id} nao encontrada.")

        decision = LegacyImportDecision(
            row_id=row_id,
            decision=decision_in.decision,
            reason=decision_in.reason,
            decided_by_user_id=current_user_id
        )
        db.add(decision)

        # Atualiza status da linha
        if decision_in.decision == "ACCEPT":
            row.status = "READY"
        elif decision_in.decision == "REJECT":
            row.status = "REJECTED"
        elif decision_in.decision == "MERGE":
            row.status = "READY" # Sera promovido mesclado futuramente
        elif decision_in.decision == "CREATE_NEW":
            row.status = "READY"
        elif decision_in.decision == "NEEDS_MORE_INFO":
            row.status = "PENDING_REVIEW"
            
        row.reviewed_by_user_id = current_user_id
        row.reviewed_at = datetime.now(timezone.utc)
        
        # Se houver candidatos a duplicados vinculados, atualiza o status deles
        for cand in row.duplicate_candidates:
            if decision_in.decision == "MERGE":
                cand.status = "CONFIRMED_DUPLICATE"
            elif decision_in.decision == "CREATE_NEW":
                cand.status = "NOT_DUPLICATE"
            elif decision_in.decision == "REJECT":
                cand.status = "PENDING"
        
        db.commit()

        # Emite evento de linha revisada
        emit_event(
            db=db,
            event_type="legacy.import.row.reviewed",
            aggregate_type="LegacyImportRow",
            aggregate_id=str(row.id),
            module="legacy_imports",
            payload={
                "row_id": str(row.id),
                "batch_id": str(row.batch_id),
                "entity_target": row.entity_target,
                "decision": decision.decision,
                "actor_user_id": current_user_id,
                "summary": f"Decisao '{decision.decision}' registrada para {row.entity_target}."
            },
            actor_user_id=current_user_id,
            tenant_id=row.tenant_id
        )
        db.commit()
        db.refresh(decision)
        return decision

    @staticmethod
    def get_batches(db: Session, skip: int = 0, limit: int = 100) -> List[LegacyImportBatch]:
        return db.query(LegacyImportBatch).order_by(LegacyImportBatch.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_batch_by_id(db: Session, batch_id: uuid.UUID) -> Optional[LegacyImportBatch]:
        return db.query(LegacyImportBatch).filter(LegacyImportBatch.id == batch_id).first()

    @staticmethod
    def get_rows_by_batch(db: Session, batch_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[LegacyImportRow]:
        return db.query(LegacyImportRow).filter(LegacyImportRow.batch_id == batch_id).order_by(LegacyImportRow.created_at.asc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_row_by_id(db: Session, row_id: uuid.UUID) -> Optional[LegacyImportRow]:
        return db.query(LegacyImportRow).filter(LegacyImportRow.id == row_id).first()

    @staticmethod
    def get_duplicates(db: Session, skip: int = 0, limit: int = 100) -> List[LegacyDuplicateCandidate]:
        return db.query(LegacyDuplicateCandidate).filter(LegacyDuplicateCandidate.status == "PENDING").order_by(LegacyDuplicateCandidate.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_summary(db: Session) -> Dict[str, Any]:
        """
        Retorna estatisticas consolidadas sobre os lotes de staging.
        """
        total_batches = db.query(LegacyImportBatch).count()
        total_rows = db.query(LegacyImportRow).count()
        
        status_counts = {}
        statuses = db.query(LegacyImportRow.status, func.count(LegacyImportRow.id)).group_by(LegacyImportRow.status).all()
        for s, count in statuses:
            status_counts[s] = count
            
        module_counts = {}
        modules = db.query(LegacyImportRow.module_target, func.count(LegacyImportRow.id)).group_by(LegacyImportRow.module_target).all()
        for m, count in modules:
            module_counts[m] = count

        return {
            "total_batches": total_batches,
            "total_rows": total_rows,
            "status_counts": status_counts,
            "module_counts": module_counts
        }

    @staticmethod
    def legacy_context_search(db: Session, query: str, entity_target: str) -> List[Dict[str, Any]]:
        """
        Permite que a UAL pesquise os dados em staging de forma segura.
        Retorna apenas registros que foram marcados com status READY (ou pendentes de revisao),
        mas NUNCA exibe dados mascarados como senhas, mesmo em raw_data_json.
        """
        # Faz uma busca por similaridade de nome ou SKU nos dados normalizados salvos
        # e filtra por entity_target.
        rows = db.query(LegacyImportRow).filter(
            LegacyImportRow.entity_target == entity_target,
            LegacyImportRow.status.in_(["PENDING_REVIEW", "READY"])
        ).all()
        
        results = []
        query_clean = query.strip().lower()
        
        for r in rows:
            norm = r.normalized_data_json
            # Verifica se algum campo de texto bate com a query
            match = False
            for field in ["name", "razao_social", "nome", "sku", "description", "title", "subject"]:
                if field in norm and norm[field] and query_clean in str(norm[field]).lower():
                    match = True
                    break
            
            if match:
                results.append({
                    "id": str(r.id),
                    "batch_id": str(r.batch_id),
                    "entity_target": r.entity_target,
                    "normalized_data": r.normalized_data_json,
                    "confidence_score": r.confidence_score,
                    "status": r.status
                })
                
        # Limita a 10 resultados para nao sobrecarregar
        return results[:10]
