import openpyxl
import hashlib
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.stock import (
    StockCatalogImportRun,
    StockCatalogCybersulProduct,
    StockCatalogItem,
    StockCatalogLink,
    StockCatalogSearchIndex
)
from app.modules.stock.parser import _text, _norm, _money

class CybersulImporter:
    @staticmethod
    def import_products(filepath: str, db: Session, user_id: Optional[int] = None) -> StockCatalogImportRun:
        """
        Importa produtos do Cybersul a partir do arquivo excel cybersul-codigo.xlsx.
        """
        # Calcular hash do arquivo
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        file_hash = hasher.hexdigest()
        filename = filepath.split("\\")[-1].split("/")[-1]

        # Criar import run no banco
        run = StockCatalogImportRun(
            source_type="CYBERSUL",
            source_path=filepath,
            source_filename=filename,
            source_hash=file_hash,
            status="RUNNING",
            total_rows=0,
            total_items=0,
            total_offers=0,
            total_errors=0,
            total_review=0,
            triggered_by_user_id=user_id
        )
        db.add(run)
        db.commit()

        try:
            wb = openpyxl.load_workbook(filepath, data_only=True)
            ws = wb.active
            
            total_rows = 0
            total_items = 0
            total_links_created = 0

            # Mapeamento estrito de colunas
            # Col 0 (A) - Código
            # Col 1 (B) - Descrição
            # Col 2 (C) - un
            # Col 3 (D) - Complemento
            # Col 4 (E) - QT. Vesper
            # Col 8 (I) - QT. Ventrio
            # Col 12 (M) - Total
            
            rows = list(ws.iter_rows(values_only=True))
            header = [str(x).strip().lower() if x is not None else "" for x in rows[0]]
            
            # Mapeamento posicional baseado no cabeçalho detectado
            col_code = 0
            col_desc = 1
            col_unit = 2
            col_comp = 3
            col_vesp = 4
            col_vent = 8
            col_tot = 12

            # --- Carregar e pre-tokenizar itens que ainda não têm cybersul_product_id ---
            matching_items = db.query(StockCatalogItem).filter(
                StockCatalogItem.cybersul_product_id.is_(None)
            ).all()
            item_tokens = []
            for item in matching_items:
                tokens = set([t for t in (item.normalized_name or "").split() if len(t) > 2])
                item_tokens.append((item, tokens))

            # Tratar linhas de dados
            for row_idx in range(1, len(rows)):
                row = rows[row_idx]
                if not row or len(row) < 3:
                    continue
                    
                code_raw = _text(row[col_code])
                desc_raw = _text(row[col_desc])
                
                if not code_raw or not desc_raw:
                    continue

                total_rows += 1
                
                unit_raw = _text(row[col_unit]) or "UN"
                comp_raw = _text(row[col_comp]) if col_comp < len(row) else None
                
                vesp_raw = _money(row[col_vesp]) if col_vesp < len(row) else 0.0
                vent_raw = _money(row[col_vent]) if col_vent < len(row) else 0.0
                tot_raw = _money(row[col_tot]) if col_tot < len(row) else 0.0

                normalized_desc = _norm(desc_raw)

                # Verificar se o produto já existe no cybersul (para atualizar ou inserir)
                prod = db.query(StockCatalogCybersulProduct).filter(
                    StockCatalogCybersulProduct.cybersul_code == code_raw
                ).first()

                if not prod:
                    total_items += 1
                    prod = StockCatalogCybersulProduct(
                        cybersul_code=code_raw,
                        description=desc_raw,
                        normalized_description=normalized_desc,
                        complement=comp_raw,
                        unit=unit_raw,
                        balance_vesper=vesp_raw or 0.0,
                        balance_ventrio=vent_raw or 0.0,
                        balance_total=tot_raw or 0.0,
                        cost_price=None,
                        supplier_name=None,
                        ncm=None,
                        group_name=None,
                        active=True,
                        source_row=row_idx + 1,
                        import_run_id=run.id
                    )
                    db.add(prod)
                else:
                    # Atualiza saldos e descrição
                    prod.description = desc_raw
                    prod.normalized_description = normalized_desc
                    prod.complement = comp_raw
                    prod.unit = unit_raw
                    prod.balance_vesper = vesp_raw or 0.0
                    prod.balance_ventrio = vent_raw or 0.0
                    prod.balance_total = tot_raw or 0.0
                    prod.import_run_id = run.id
                
                db.flush()

                # --- Algoritmo de Vínculo Inteligente com Compras Nova ---
                tokens_cyber = set([t for t in normalized_desc.split() if len(t) > 2])
                if tokens_cyber:
                    for item, tokens_item in item_tokens:
                        if not tokens_item:
                            continue
                        if item.cybersul_product_id is not None:
                            continue

                        # Interseção de palavras
                        common = tokens_item.intersection(tokens_cyber)
                        overlap = len(common) / max(len(tokens_item), len(tokens_cyber))

                        # Se houver alto pareamento, vincular
                        if overlap >= 0.70:
                            confidence = float(overlap)
                            match_type = "EXACT" if overlap >= 0.90 else "FUZZY"
                            
                            # Inativar links anteriores deste item
                            db.query(StockCatalogLink).filter(
                                StockCatalogLink.stock_catalog_item_id == item.id
                            ).update({"needs_review": False})

                            link = StockCatalogLink(
                                stock_catalog_item_id=item.id,
                                cybersul_product_id=prod.id,
                                match_type=match_type,
                                confidence=confidence,
                                match_reason=f"Pareamento automático de palavras comuns (coeficiente: {overlap:.2f}).",
                                needs_review=overlap < 0.85 # Manda para revisão se confiança < 85%
                            )
                            db.add(link)
                            total_links_created += 1

                            # Se confiança alta, atualiza chave estrangeira direta no item
                            if overlap >= 0.85:
                                item.cybersul_product_id = prod.id
                                
                                # Atualiza também o índice de busca com o código cybersul
                                search_idx = db.query(StockCatalogSearchIndex).filter(
                                    StockCatalogSearchIndex.item_id == item.id
                                ).first()
                                if search_idx:
                                    search_idx.cybersul_code = prod.cybersul_code
                                    
                            db.flush()

            # Finalizar run
            run.status = "SUCCESS"
            run.finished_at = datetime.now(timezone.utc)
            run.total_rows = total_rows
            run.total_items = total_items
            run.total_offers = total_links_created # Registramos os links gerados como ofertas ou no metadata
            
            db.commit()

        except Exception as e:
            db.rollback()
            run.status = "FAILED"
            run.finished_at = datetime.now(timezone.utc)
            run.error_message = str(e)
            db.commit()
            raise e

        return run
