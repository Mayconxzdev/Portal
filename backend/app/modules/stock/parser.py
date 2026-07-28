import re
import hashlib
import uuid
import openpyxl
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.stock import (
    StockCatalogImportRun,
    StockCatalogTreeNode,
    StockCatalogItem,
    StockCatalogItemSpec,
    StockCatalogSupplier,
    StockCatalogOffer,
    StockCatalogSearchIndex,
    StockCatalogReviewQueue
)

# Constantes de Cores (Hex ARGB)
COLOR_FAMILY_ORANGE_1 = "FFFFC000"
COLOR_FAMILY_ORANGE_2 = "FFFC6E04"
COLOR_PRODUCT_LIGHT_BLUE = "FFE6EDEE"
COLOR_PRODUCT_LIGHT_BLUE_ALT = "FFD9E1F2"
COLOR_SEPARATOR_WHITE = "FFFFFFFF"

def _text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\n", " ")).strip()

def _norm(value: Any) -> str:
    text = _text(value).lower()
    trans = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüç", "aaaaaeeeeiiiiooooouuuuc")
    return text.translate(trans)

def _money(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    text = _text(value).replace("R$", "").replace("%", "").strip()
    if not text or text in {"-", "."}:
        return None
    text = re.sub(r"[^0-9,.\-]", "", text)
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None

def _email(value: Any) -> Optional[str]:
    text = _text(value).lower()
    match = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", text)
    return match.group(0) if match else None

def _phone(value: Any) -> Optional[str]:
    text = _text(value)
    digits = re.sub(r"\D", "", text)
    if len(digits) < 8:
        return None
    return digits[:15]

def _clean_supplier(value: Any) -> Optional[str]:
    text = _text(value)
    if not text:
        return None
    # Remover e-mail e telefone se estiverem misturados no nome
    text = re.sub(r"[\w.\-+]+@[\w.\-]+\.\w+", "", text)
    text = re.sub(r"\d{2,}\s*\d{4,}-\d{4,}", "", text)
    text = re.sub(r"\(\d{2,}\)\s*\d{4,}-\d{4,}", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -:,")
    return text[:255] or None

def _is_redundant(s1: str, s2: str) -> bool:
    """
    Retorna True se s1 e s2 têm grande sobreposição de palavras (Jaccard-like),
    evitando repetição de prefixos ou nomes redundantes.
    """
    w1 = set(re.findall(r'\w+', _norm(s1)))
    w2 = set(re.findall(r'\w+', _norm(s2)))
    if not w1 or not w2:
        return False
    # Ignorar palavras curtas (1 caractere) a menos que sejam números
    w1 = {w for w in w1 if len(w) > 1 or w.isdigit()}
    w2 = {w for w in w2 if len(w) > 1 or w.isdigit()}
    if not w1 or not w2:
        return False
    intersection = w1.intersection(w2)
    overlap = len(intersection) / min(len(w1), len(w2))
    return overlap >= 0.6

def _get_cell_bg_color(cell: Any) -> Optional[str]:
    if not cell or not cell.fill or cell.fill.fill_type is None:
        return None
    try:
        color = cell.fill.start_color
        if color and color.type == "rgb" and isinstance(color.rgb, str):
            return color.rgb.upper()
    except Exception:
        pass
    return None

def _is_family_color(color: Optional[str]) -> bool:
    return color in (COLOR_FAMILY_ORANGE_1, COLOR_FAMILY_ORANGE_2)

def _is_product_color(color: Optional[str]) -> bool:
    return color in (COLOR_PRODUCT_LIGHT_BLUE, COLOR_PRODUCT_LIGHT_BLUE_ALT)


def _persist_quarantine_row(
    db: Session,
    run: StockCatalogImportRun,
    *,
    sheet_name: str,
    row_num: int,
    desc_val: str,
    reason: str,
    ctx_snapshot: dict,
    family_node_id=None,
) -> None:
    """Persiste linha inválida em quarentena (invisível ao usuário comum)."""
    identity_hash = hashlib.sha256(
        f"quarantine|{sheet_name}|{row_num}|{_norm(desc_val)}".encode("utf-8")
    ).hexdigest()
    existing = db.query(StockCatalogItem).filter(StockCatalogItem.identity_hash == identity_hash).first()
    if existing:
        return
    item = StockCatalogItem(
        import_run_id=run.id,
        source_sheet=sheet_name[:100],
        family_node_id=family_node_id,
        display_name=(desc_val or reason)[:255],
        base_name=(desc_val or "Linha em quarentena")[:255],
        normalized_name=_norm(desc_val or reason)[:255],
        identity_hash=identity_hash,
        active=True,
        quality_status="QUARANTINED",
        visibility_scope="HIDDEN",
        is_parser_junk=True,
        is_tree_visible_common=False,
        is_searchable_common=False,
        is_operational=False,
        review_type="quarantined_invalid_row",
        review_reason=reason[:500] if reason else None,
        needs_review=True,
        metadata_json={
            "source_row": row_num,
            "source_text": desc_val,
            "quarantine_reason": reason,
            "parser_context": ctx_snapshot,
        },
    )
    db.add(item)
    db.flush()
    review_entry = StockCatalogReviewQueue(
        item_id=item.id,
        import_run_id=run.id,
        review_type="quarantined_invalid_row",
        severity="LOW",
        title=f"Quarentena: {(desc_val or reason)[:200]}"[:255],
        description=reason,
        status="PENDING",
    )
    db.add(review_entry)


def _apply_row_classification_to_context(ctx, classification: str, desc_val: str) -> None:
    """Atualiza ParserContext conforme classificação da linha."""
    from app.modules.stock.measure_utils import StringClassification, humanize_product_name

    if classification == StringClassification.LENGTH_GROUP:
        ctx.reset_on_length_group(desc_val)
    elif classification == StringClassification.DIMENSION:
        ctx.apply_dimension(desc_val)
    elif classification == StringClassification.WEIGHT:
        ctx.apply_weight(desc_val)
    elif classification == StringClassification.THICKNESS:
        ctx.apply_thickness(desc_val)
    elif classification == StringClassification.TECHNICAL_CODE:
        ctx.apply_technical_code(desc_val)
    elif classification == StringClassification.APPLICATION_NOTE:
        ctx.apply_application(desc_val)
    elif classification == StringClassification.PRODUCT_NAME:
        thickness_match = re.search(
            r"\b(\d+(?:[.,]\d+)?\s*mm|\d+/\d+\s*mm|\d+/\d+\")", desc_val, re.IGNORECASE
        )
        if thickness_match:
            ctx.apply_thickness(thickness_match.group(1))


class ComprasNovaParser:
    @staticmethod
    def parse_sheet_header(ws: openpyxl.worksheet.worksheet.Worksheet) -> Tuple[int, Dict[str, int]]:
        """
        Localiza a linha do cabeçalho e mapeia as colunas de forma robusta,
        evitando falsos positivos de linhas de título ou comentários.
        """
        aliases = {
            "codigo": ["codigo", "código", "cod", "código cybersul"],
            "description": ["material", "descricao", "descrição", "produto", "item"],
            "raw_price": ["preco", "preço", "preco unit", "preço unit", "preco p", "preço p", "valor"],
            "final_value": ["valor final", "preco final", "preço final"],
            "unit": ["unidade", "unid", "un"],
            "weight": ["peso", "kg/m"],
            "supplier": ["fornecedor", "forn"],
            "updated_at": ["atualizado", "ultima atualizacao", "última atualização", "data"],
            "email": ["email", "e-mail"],
            "phone": ["telefone", "fone"],
        }
        
        # Carregar primeiras 30 linhas de valores
        rows_data = []
        for r in range(1, 31):
            row_vals = [ws.cell(row=r, column=c).value for c in range(1, 15)]
            rows_data.append((r, row_vals))
            
        best = None
        for pos, (row_num, values) in enumerate(rows_data):
            current = [_norm(v) for v in values]
            has_code = any("codigo" in cell or "código" in cell or "cod" in cell for cell in current)
            has_description = any(any(term in cell for term in ("material", "descricao", "descrição", "produto", "item")) for cell in current)
            has_price = any("preco" in cell or "preço" in cell or "valor final" in cell for cell in current)
            has_technical = any(any(term in cell for term in ("diametro", "diâmetro", "cv", "polo", "pólo", "pas", "pás", "vazao", "vazão", "pressao", "pressão")) for cell in current)
            
            # Condição robusta de cabeçalho: código + (descrição ou preço com característica técnica/fornecedor)
            has_supplier_in_header = any("fornecedor" in cell or "forn" in cell for cell in current)
            if not (has_code and (has_description or (has_price and (has_technical or has_supplier_in_header)))):
                continue
                
            next_values = rows_data[pos + 1][1] if pos + 1 < len(rows_data) else []
            max_len = max(len(values), len(next_values))
            
            # Combina a linha atual com a próxima para tratar cabeçalhos de duas linhas (ex: Preço / unit)
            header = [
                _norm(values[idx] if idx < len(values) else "") + " " + _norm(next_values[idx] if idx < len(next_values) else "")
                for idx in range(max_len)
            ]
            
            mapping = {}
            for key, terms in aliases.items():
                for idx, cell in enumerate(header):
                    if any(term in cell for term in terms):
                        mapping[key] = idx
                        break
                        
            score = (
                int("description" in mapping) + 
                int("raw_price" in mapping) + 
                int("final_value" in mapping) + 
                int("supplier" in mapping)
            )
            
            if score >= 2 and (best is None or score > best[2]):
                best = (row_num, mapping, score)
                
        if best:
            return best[0], best[1]
            
        # Fallback se não encontrar
        return 1, {"codigo": 0, "description": 1, "raw_price": 2, "final_value": 5, "supplier": 7, "updated_at": 8}


    @staticmethod
    def parse_workbook(filepath: str, db: Session, user_id: Optional[int] = None) -> StockCatalogImportRun:
        """
        Parser principal por árvore visual para a planilha Compras Nova.
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
            source_type="COMPRAS_NOVA",
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
            total_rows = 0
            total_items = 0
            total_offers = 0
            total_review = 0

            # Listar worksheets e ignorar as de controle
            ignored_sheets = {"indice", "índice", "planilha1", "config", "ajustes"}
            
            for sheet_name in wb.sheetnames:
                sheet_norm = _norm(sheet_name).replace(" ", "")
                if sheet_norm in ignored_sheets:
                    continue

                ws = wb[sheet_name]
                header_row, mapping = ComprasNovaParser.parse_sheet_header(ws)
                
                # Criar nó da aba na árvore
                sheet_node = StockCatalogTreeNode(
                    import_run_id=run.id,
                    source_type="COMPRAS_NOVA",
                    source_sheet=sheet_name[:100],
                    parent_id=None,
                    node_type="sheet",
                    title=sheet_name[:255],
                    normalized_title=_norm(sheet_name)[:255],
                    path=sheet_name[:1000],
                    depth=0,
                    position=0,
                    start_row=1,
                    end_row=ws.max_row,
                    confidence=1.0,
                    needs_review=False
                )
                db.add(sheet_node)
                db.flush()

                # Estados do Parser para reconstrução da Árvore Visual
                current_family_node: Optional[StockCatalogTreeNode] = None
                current_product_node: Optional[StockCatalogTreeNode] = None
                current_variation_node: Optional[StockCatalogTreeNode] = None
                
                # Variáveis de contexto para itens e especificações
                current_product_title = ""
                current_family_title_original = ""  # Case original (sem .upper()) para base_name dos itens
                current_variation_label = ""
                current_spec_text = ""
                current_measure = ""
                current_code = ""
                current_unit = "un"
                
                # Máquina de estados sequencial para saneamento global
                from app.modules.stock.measure_utils import (
                    classify_string,
                    humanize_product_name,
                    is_invalid_product_name,
                    StringClassification,
                )
                from app.modules.stock.parser_context import (
                    ParserContext,
                    QUARANTINE_TYPES,
                    is_attribute_only,
                    is_navigation_product,
                )

                ctx = ParserContext()
                ctx.last_valid_category = sheet_name

                last_item_created: Optional[StockCatalogItem] = None

                # Ler linhas de dados
                rows = list(ws.iter_rows())
                for idx in range(header_row, len(rows)):
                    row_cells = rows[idx]
                    total_rows += 1
                    row_num = idx + 1

                    # Células de interesse
                    col_desc_idx = mapping.get("description", 1)
                    cell_desc = row_cells[col_desc_idx] if col_desc_idx < len(row_cells) else None
                    desc_val = _text(cell_desc.value) if cell_desc else ""
                    row_class = classify_string(desc_val)

                    row_raw_content = " ".join([str(cell.value) for cell in row_cells if cell.value is not None]).lower()
                    is_quarantine_raw = row_class in QUARANTINE_TYPES or any(
                        k in row_raw_content for k in ["subtotal", "total", "média", "media", "fórmula", "formula", "#nome?"]
                    )
                    is_row_prod_invalid = is_invalid_product_name(desc_val)
                    
                    cell_code = row_cells[mapping["codigo"]] if "codigo" in mapping and mapping["codigo"] < len(row_cells) else None
                    code_val = _text(cell_code.value) if cell_code else ""
                    
                    price_val = _money(row_cells[mapping["raw_price"]].value) if "raw_price" in mapping and mapping["raw_price"] < len(row_cells) else None
                    final_val = _money(row_cells[mapping["final_value"]].value) if "final_value" in mapping and mapping["final_value"] < len(row_cells) else None
                    
                    supplier_raw = row_cells[mapping["supplier"]].value if "supplier" in mapping and mapping["supplier"] < len(row_cells) else None
                    supplier_clean = _clean_supplier(supplier_raw)

                    if is_quarantine_raw and not price_val and not supplier_clean and not code_val:
                        _persist_quarantine_row(
                            db,
                            run,
                            sheet_name=sheet_name,
                            row_num=row_num,
                            desc_val=desc_val,
                            reason=f"Linha classificada como {row_class}",
                            ctx_snapshot=ctx.snapshot(),
                            family_node_id=current_family_node.id if current_family_node else None,
                        )
                        continue

                    _is_spec_line = desc_val.startswith("(") and desc_val.endswith(")")
                    _is_measure_only = bool(
                        re.match(r'^[0-9.]+(?:[/][0-9.]+)?(?:"|\'|\s*mm|\s*cm|\s*m\b)?$', desc_val.strip())
                    )

                    if desc_val and row_class == StringClassification.PRODUCT_NAME and not _is_spec_line:
                        _apply_row_classification_to_context(ctx, row_class, desc_val)
                    elif desc_val and is_attribute_only(row_class):
                        _apply_row_classification_to_context(ctx, row_class, desc_val)
                    
                    email_val = _email(row_cells[mapping["email"]].value) if "email" in mapping and mapping["email"] < len(row_cells) else None
                    phone_val = _phone(row_cells[mapping["phone"]].value) if "phone" in mapping and mapping["phone"] < len(row_cells) else None
                    
                    unit_val = _text(row_cells[mapping["unit"]].value) if "unit" in mapping and mapping["unit"] < len(row_cells) else "un"

                    # Analisar cores
                    bg_color = _get_cell_bg_color(cell_desc) if cell_desc else None
                    is_bold = cell_desc.font.bold if cell_desc and cell_desc.font else False

                    # Regra de Separação de Atuador na aba Conexões Alta Pressão
                    is_forced_atuador_family = (
                        _norm(sheet_name) == "conexoes alta pressao" and 
                        _norm(desc_val) == "atuador" and
                        (bg_color == COLOR_FAMILY_ORANGE_1 or bg_color == COLOR_FAMILY_ORANGE_2 or is_bold)
                    )

                    # --- 1. Classificação de Família (Family Node) ---
                    if _is_family_color(bg_color) or is_forced_atuador_family:
                        if desc_val:
                            current_family_node = StockCatalogTreeNode(
                                import_run_id=run.id,
                                source_type="COMPRAS_NOVA",
                                source_sheet=sheet_name[:100],
                                parent_id=sheet_node.id,
                                node_type="family",
                                title=desc_val.upper()[:255],
                                normalized_title=_norm(desc_val)[:255],
                                path=f"{sheet_name} > {desc_val.upper()}"[:1000],
                                depth=1,
                                position=row_num,
                                start_row=row_num,
                                end_row=row_num,
                                style_signature=f"bg:{bg_color}"[:255] if bg_color else None,
                                confidence=1.0,
                                needs_review=False
                            )
                            db.add(current_family_node)
                            db.flush()
                            
                            # Limpar nós inferiores
                            current_product_node = None
                            current_variation_node = None
                            current_product_title = ""
                            current_family_title_original = desc_val  # Preservar o case original para base_name
                            current_variation_label = ""
                            last_item_created = None

                            ctx.reset_on_family(desc_val)
                        continue

                    # --- 2. Classificação de Produto (Product Node) ---
                    # Linhas entre parênteses (ex: "(9,53 mm)") são specs, não títulos de produto
                    # Linhas que são medidas simples (ex: '3/8"', '1"', '1.1/4"') também não são títulos
                    _is_spec_line = desc_val.startswith("(") and desc_val.endswith(")")
                    _is_measure_only = bool(re.match(r'^[0-9.]+(?:[/][0-9.]+)?(?:\"|\'|\s*mm|\s*cm|\s*m\b)?$', desc_val.strip()))
                    is_product_title_row = (
                        _is_product_color(bg_color) and is_bold and desc_val and
                        price_val is None and supplier_clean is None and
                        not _is_spec_line and not _is_measure_only and
                        len(desc_val) > 3 and
                        not current_product_title and
                        not current_variation_label and
                        not is_row_prod_invalid and
                        is_navigation_product(row_class)
                    )
                    
                    # Fallback para abas sem cores (ex: Mat. Elétrico Ex)
                    # Requer ao menos 2 palavras: variações únicas ('Bipolar', '3/8"') são variações, não produtos
                    _desc_word_count = len(desc_val.split())
                    is_no_color_product = (
                        not bg_color and is_bold and desc_val and
                        price_val is None and supplier_clean is None and
                        len(desc_val) > 5 and not _norm(desc_val).startswith("(") and
                        _desc_word_count >= 2 and
                        not current_product_title and
                        not current_variation_label and
                        not is_row_prod_invalid and
                        is_navigation_product(row_class)
                    )
                    
                    if is_product_title_row or is_no_color_product:
                        # Se for na aba Conexões Alta Pressão e o texto for BICO, criamos família
                        if _norm(desc_val) == "bico":
                            current_family_node = StockCatalogTreeNode(
                                import_run_id=run.id,
                                source_type="COMPRAS_NOVA",
                                source_sheet=sheet_name[:100],
                                parent_id=sheet_node.id,
                                node_type="family",
                                title="BICO",
                                normalized_title="bico",
                                path=f"{sheet_name} > BICO"[:1000],
                                depth=1,
                                position=row_num,
                                start_row=row_num,
                                end_row=row_num,
                                style_signature="forced_bico",
                                confidence=1.0,
                                needs_review=False
                            )
                            db.add(current_family_node)
                            db.flush()
                            current_product_node = None
                            current_variation_node = None
                            continue
                            
                        # Determinar nó pai (Family)
                        parent_id = current_family_node.id if current_family_node else sheet_node.id
                        
                        current_product_node = StockCatalogTreeNode(
                            import_run_id=run.id,
                            source_type="COMPRAS_NOVA",
                            source_sheet=sheet_name[:100],
                            parent_id=parent_id,
                            node_type="product",
                            title=desc_val[:255],
                            normalized_title=_norm(desc_val)[:255],
                            path=f"{current_family_node.path if current_family_node else sheet_name} > {desc_val}"[:1000],
                            depth=2,
                            position=row_num,
                            start_row=row_num,
                            end_row=row_num,
                            style_signature=f"bg:{bg_color}_bold:{is_bold}"[:255] if bg_color else f"bold:{is_bold}",
                            confidence=1.0,
                            needs_review=False
                        )
                        db.add(current_product_node)
                        db.flush()
                        
                        current_product_title = desc_val
                        current_variation_node = None
                        current_spec_text = ""
                        current_measure = ""
                        last_item_created = None
                        ctx.reset_on_product(desc_val, raw=desc_val)
                        continue

                    # --- 3. Classificação de Variações, Especificações e Ofertas ---
                    # Linhas vazias ou separadores são ignoradas
                    # Limpa o contexto de produto e variação do grupo anterior ao encontrar linha vazia
                    if not desc_val and price_val is None and supplier_clean is None:
                        current_product_node = None
                        current_product_title = ""
                        current_variation_node = None
                        current_variation_label = ""
                        current_spec_text = ""
                        last_item_created = None
                        continue

                    # Verificar se é uma linha contendo apenas a medida ou especificação (ex: '(9,53 mm)' ou '3/8"')
                    # sem preço na linha. Isso também abrange linhas com cor de produto que sejam specs (ex: "(9,53 mm)").
                    is_pure_spec_or_variation = (
                        desc_val and price_val is None and supplier_clean is None
                    )
                    
                    if is_pure_spec_or_variation:
                        if row_class in QUARANTINE_TYPES:
                            _persist_quarantine_row(
                                db,
                                run,
                                sheet_name=sheet_name,
                                row_num=row_num,
                                desc_val=desc_val,
                                reason=f"Linha classificada como {row_class}",
                                ctx_snapshot=ctx.snapshot(),
                                family_node_id=current_family_node.id if current_family_node else None,
                            )
                            continue

                        if is_attribute_only(row_class) or row_class == StringClassification.LENGTH_GROUP:
                            if row_class == StringClassification.DIMENSION:
                                current_spec_text = desc_val
                            continue

                        if desc_val.startswith("(") and desc_val.endswith(")"):
                            current_spec_text = desc_val.strip("()")
                            if last_item_created:
                                spec = StockCatalogItemSpec(
                                    item_id=last_item_created.id,
                                    spec_key="medida",
                                    spec_value=current_spec_text,
                                    normalized_value=_norm(current_spec_text),
                                )
                                db.add(spec)
                                last_item_created.display_name = f"{last_item_created.display_name} - ({current_spec_text})"
                                last_item_created.specification_text = current_spec_text
                                db.flush()
                            continue

                        # Variação tradicional (ex: 3/8", Bipolar) — não atributo isolado
                        if row_class in (StringClassification.VARIATION_GROUP, StringClassification.THICKNESS) or _is_measure_only:
                            current_variation_label = desc_val
                            if current_product_node:
                                parent_id = current_product_node.id
                                path_base = current_product_node.path
                            elif current_family_node:
                                parent_id = current_family_node.id
                                path_base = current_family_node.path
                            else:
                                parent_id = sheet_node.id
                                path_base = sheet_name

                            current_variation_node = StockCatalogTreeNode(
                                import_run_id=run.id,
                                source_type="COMPRAS_NOVA",
                                source_sheet=sheet_name[:100],
                                parent_id=parent_id,
                                node_type="variation",
                                title=desc_val[:255],
                                normalized_title=_norm(desc_val)[:255],
                                path=f"{path_base} > {desc_val}"[:1000],
                                depth=3,
                                position=row_num,
                                start_row=row_num,
                                end_row=row_num,
                                style_signature="pure_variation",
                                confidence=1.0,
                                needs_review=False,
                            )
                            db.add(current_variation_node)
                            db.flush()
                        elif row_class == StringClassification.PRODUCT_NAME and current_product_node:
                            current_variation_label = humanize_product_name(desc_val) or desc_val
                        continue

                    # Se a linha não tem descrição nem preço, ignorar para evitar duplicação de itens, apenas atualiza contatos do fornecedor se presentes
                    if not desc_val and price_val is None:
                        if supplier_clean:
                            supplier_norm = _norm(supplier_clean)
                            sup = db.query(StockCatalogSupplier).filter(
                                StockCatalogSupplier.normalized_name == supplier_norm
                            ).first()
                            if sup:
                                if email_val:
                                    sup.email = email_val
                                if phone_val:
                                    sup.phone = phone_val
                                db.flush()
                        continue

                    # Caso em que a linha tem dados de preço ou fornecedor (Oferta real)
                    # É hora de criar ou mapear o item comprável correspondente!
                    if price_val is not None or supplier_clean is not None:
                        # Ignorar linhas de consolidação (média, total, fórmulas de soma)
                        desc_norm = _norm(desc_val)
                        is_consolidated = any(t in desc_norm for t in ["media", "média", "total", "subtotal", "formula", "fórmula", "fechamento", "consolidado"])
                        
                        if is_consolidated or is_quarantine_raw:
                            if is_quarantine_raw:
                                _persist_quarantine_row(
                                    db,
                                    run,
                                    sheet_name=sheet_name,
                                    row_num=row_num,
                                    desc_val=desc_val,
                                    reason="Linha de consolidação ou erro de fórmula",
                                    ctx_snapshot=ctx.snapshot(),
                                    family_node_id=current_family_node.id if current_family_node else None,
                                )
                            continue

                        if supplier_clean:
                            ctx.apply_supplier(supplier_clean)
                        if price_val:
                            ctx.apply_price(price_val)

                        prod_clean = None
                        if desc_val and not is_row_prod_invalid:
                            prod_clean = humanize_product_name(desc_val)

                        # If the current description is actually an attribute (thickness/dimension/weight)
                        # prefer the last valid product title as the base name. This prevents creating
                        # items whose base_name is the raw measurement like '1"'.
                        from app.modules.stock.measure_utils import StringClassification as _SC
                        if current_product_title:
                            prod_clean = ctx.last_valid_product or humanize_product_name(current_product_title)
                        elif (not prod_clean or row_class in {_SC.THICKNESS, _SC.DIMENSION, _SC.WEIGHT, _SC.LENGTH_GROUP}) and ctx.last_valid_product:
                            prod_clean = ctx.last_valid_product

                        if not prod_clean:
                            if ctx.last_valid_product:
                                prod_clean = ctx.last_valid_product
                            else:
                                prod_clean = humanize_product_name(
                                    current_product_title or current_family_title_original or sheet_name
                                )
                        
                        base_name = prod_clean
                        
                        # Tratamento específico para BICO
                        if "conemang" in desc_norm:
                            base_name = re.sub(r"(?i)\bconemang\b", "", base_name).strip(" -:,")
                            desc_val = re.sub(r"(?i)\bconemang\b", "", desc_val).strip(" -:,")
                            if not supplier_clean:
                                supplier_clean = "Conemang Comercio"

                        # Determinar o label de variação do item:
                        # Se a descrição atual for uma especificação ou medida isolada, ela vira a variação
                        row_variation_label = ""
                        is_desc_spec_or_measure = is_row_prod_invalid or _is_measure_only or _is_spec_line
                        
                        clean_var_prefix = ""
                        if current_variation_label and not _is_redundant(base_name, current_variation_label):
                            clean_var_prefix = current_variation_label
                            
                        desc_to_use = desc_val if is_desc_spec_or_measure else ""

                        if clean_var_prefix:
                            if desc_to_use and not _is_redundant(clean_var_prefix, desc_to_use) and not _is_redundant(base_name, desc_to_use):
                                row_variation_label = f"{clean_var_prefix} - {desc_to_use}"
                            else:
                                row_variation_label = clean_var_prefix
                        elif desc_to_use and not _is_redundant(base_name, desc_to_use):
                            row_variation_label = desc_to_use
                        elif current_variation_label:
                            row_variation_label = current_variation_label

                        if not row_variation_label:
                            # Prefer the explicit description/measure when the row itself
                            # is an isolated measure or spec (common pattern: measure row
                            # + repeated product title + measure-with-price row). This
                            # ensures variations like '1"' are not lost as generic "Geral".
                            if is_desc_spec_or_measure and desc_val:
                                row_variation_label = desc_val
                            elif ctx.last_valid_thickness:
                                row_variation_label = ctx.last_valid_thickness
                            elif ctx.last_valid_dimension:
                                row_variation_label = ctx.last_valid_dimension
                            else:
                                row_variation_label = "Geral"

                        if ctx.last_valid_dimension and not _is_redundant(row_variation_label, ctx.last_valid_dimension):
                            row_variation_label = ctx.last_valid_dimension

                        medida_match = re.search(
                            r"(\d+(?:\.\d+)?(?:/\d+)?(?:\s*\"|\s*mm))",
                            row_variation_label or base_name,
                        )
                        if medida_match:
                            current_measure = medida_match.group(1).strip()
                        else:
                            current_measure = ctx.last_valid_dimension or ""

                        from app.modules.stock.measure_utils import normalize_measure
                        measure_norm = normalize_measure(
                            row_variation_label,
                            current_measure,
                            current_spec_text,
                            base_name
                        )
                        measure_aliases = measure_norm.aliases

                        item_meta = ctx.metadata_for_item()
                        if not current_spec_text and ctx.last_valid_dimension:
                            current_spec_text = ctx.last_valid_dimension

                        hash_payload = ctx.build_physical_key(
                            sheet=sheet_name,
                            family=current_family_node.title if current_family_node else "",
                            base_name=base_name,
                            variation_label=row_variation_label,
                            internal_code=code_val,
                        )
                        identity_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

                        # Verificar se o item já existe na importação atual
                        item = db.query(StockCatalogItem).filter(
                            StockCatalogItem.identity_hash == identity_hash
                        ).first()

                        # Construir nome amigável de exibição (sem redundâncias)
                        display_name = base_name
                        if current_product_title and not _is_redundant(base_name, current_product_title):
                            display_name += f" - {current_product_title}"
                        if row_variation_label and row_variation_label != current_product_title and not _is_redundant(display_name, row_variation_label):
                            display_name += f" - {row_variation_label}"
                        if current_spec_text and not _is_redundant(display_name, current_spec_text):
                            display_name += f" - ({current_spec_text})"

                        if not item:
                            total_items += 1
                            item = StockCatalogItem(
                                import_run_id=run.id,
                                source_sheet=sheet_name[:100],
                                family_node_id=current_family_node.id if current_family_node else None,
                                product_node_id=current_product_node.id if current_product_node else None,
                                variation_node_id=current_variation_node.id if current_variation_node else None,
                                display_name=display_name[:255],
                                base_name=base_name[:255],
                                normalized_name=_norm(display_name)[:255],
                                variation_label=row_variation_label[:100] if row_variation_label else None,
                                normalized_measure=current_measure[:100] if current_measure else None,
                                specification_text=current_spec_text,
                                identity_hash=identity_hash,
                                internal_code=code_val[:100] if code_val else None,
                                active=True,
                                needs_review=False,
                                quality_status="READY",
                                visibility_scope="COMMON",
                                metadata_json=item_meta or None,
                                measure_aliases_json=measure_aliases,
                            )
                            db.add(item)
                            db.flush()

                            for spec_key, spec_value in [
                                ("medida", current_spec_text),
                                ("peso", ctx.last_valid_weight),
                                ("espessura", ctx.last_valid_thickness),
                                ("dimensao", ctx.last_valid_dimension),
                            ]:
                                if spec_value:
                                    db.add(
                                        StockCatalogItemSpec(
                                            item_id=item.id,
                                            spec_key=spec_key,
                                            spec_value=spec_value[:255],
                                            normalized_value=_norm(spec_value),
                                        )
                                    )
                        else:
                            # Reutiliza o item existente, atualiza a run e garante que está ativo
                            item.import_run_id = run.id
                            item.active = True
                            item.display_name = display_name[:255]
                            item.base_name = base_name[:255]
                            item.normalized_name = _norm(display_name)[:255]
                            item.variation_label = row_variation_label[:100] if row_variation_label else None
                            item.normalized_measure = current_measure[:100] if current_measure else None
                            item.specification_text = current_spec_text
                            item.family_node_id = current_family_node.id if current_family_node else None
                            item.product_node_id = current_product_node.id if current_product_node else None
                            item.variation_node_id = current_variation_node.id if current_variation_node else None
                            item.measure_aliases_json = sorted(list(set((item.measure_aliases_json or []) + measure_aliases)))
                            if item_meta:
                                item.metadata_json = {**(item.metadata_json or {}), **item_meta}

                        last_item_created = item

                        # Tratar Fornecedor
                        supplier_name = supplier_clean or "FORNECEDOR NAO IDENTIFICADO"
                        supplier_norm = _norm(supplier_name)
                        
                        supplier_db = db.query(StockCatalogSupplier).filter(
                            StockCatalogSupplier.normalized_name == supplier_norm
                        ).first()
                        
                        if not supplier_db:
                            supplier_db = StockCatalogSupplier(
                                name=supplier_name[:255],
                                normalized_name=supplier_norm[:255],
                                email=email_val[:255] if email_val else None,
                                phone=phone_val[:50] if phone_val else None,
                                source="XLSX_IMPORT",
                                active=True
                            )
                            db.add(supplier_db)
                            db.flush()
                        else:
                            # Atualiza dados de contato se encontrados
                            if email_val:
                                supplier_db.email = email_val
                            if phone_val:
                                supplier_db.phone = phone_val
                                
                        # Criar Oferta de Preço
                        total_offers += 1
                        
                        # Inativar ofertas anteriores deste item do mesmo fornecedor
                        db.query(StockCatalogOffer).filter(
                            StockCatalogOffer.item_id == item.id,
                            StockCatalogOffer.supplier_id == supplier_db.id
                        ).update({"is_current": False})

                        offer = StockCatalogOffer(
                            item_id=item.id,
                            supplier_id=supplier_db.id,
                            import_run_id=run.id,
                            source_sheet=sheet_name[:100],
                            source_row=row_num,
                            price=price_val,
                            price_raw=str(row_cells[mapping["raw_price"]].value)[:50] if "raw_price" in mapping and mapping["raw_price"] < len(row_cells) and row_cells[mapping["raw_price"]].value else None,
                            final_value=final_val,
                            final_value_raw=str(row_cells[mapping["final_value"]].value)[:50] if "final_value" in mapping and mapping["final_value"] < len(row_cells) and row_cells[mapping["final_value"]].value else None,
                            currency="BRL",
                            unit=unit_val[:30] if unit_val else "un",
                            availability=None,
                            delivery_time=None,
                            contact_email=email_val[:255] if email_val else None,
                            contact_phone=phone_val[:50] if phone_val else None,
                            is_current=True,
                            is_consolidated_line=False,
                            confidence=1.0,
                            needs_review=False
                        )
                        db.add(offer)
                        db.flush()

                        # --- Validação e Fila de Revisão ---
                        # Regra: se não tem e-mail do fornecedor
                        needs_review = False
                        reasons = []
                        
                        if not supplier_db.email:
                            needs_review = True
                            reasons.append("Fornecedor sem e-mail cadastrado.")
                            
                        if not price_val:
                            needs_review = True
                            reasons.append("Oferta com preço zerado ou ausente.")
                            
                        if supplier_name == "FORNECEDOR NAO IDENTIFICADO":
                            needs_review = True
                            reasons.append("Não foi possível identificar o fornecedor na linha.")

                        if needs_review:
                            total_review += 1
                            item.needs_review = True
                            item.review_reason = " | ".join(reasons)
                            
                            review_entry = StockCatalogReviewQueue(
                                item_id=item.id,
                                import_run_id=run.id,
                                review_type="MISSING_SUPPLIER" if "fornecedor" in reasons[0].lower() else "MISSING_EMAIL",
                                severity="MEDIUM",
                                title=f"Revisar item: {item.display_name}"[:255],
                                description=" | ".join(reasons),
                                status="PENDING"
                            )
                            db.add(review_entry)

                        # --- 4. Alimentação do Índice de Busca ---
                        search_text = (
                            f"{item.display_name} {item.base_name} {item.variation_label or ''} "
                            f"{item.specification_text or ''} {item.internal_code or ''} "
                            f"{supplier_db.name} {sheet_name} "
                            f"{current_family_node.title if current_family_node else ''} "
                            f"{desc_val} {' '.join(measure_aliases)}"
                        )
                        normalized_search_text = _norm(search_text)
                        
                        # Gerar tokens simples
                        tokens = list(set([t for t in normalized_search_text.split() if len(t) > 1]))
                        
                        # Se já houver índice para esse item, atualizar, senão criar
                        search_index = db.query(StockCatalogSearchIndex).filter(
                            StockCatalogSearchIndex.item_id == item.id
                        ).first()
                        
                        if not search_index:
                            search_index = StockCatalogSearchIndex(
                                item_id=item.id,
                                search_text=search_text,
                                normalized_search_text=normalized_search_text,
                                tokens_json=tokens,
                                supplier_names=[supplier_db.name[:255]],
                                cybersul_code=None,
                                source_sheet=sheet_name[:100],
                                family_path=(current_family_node.path if current_family_node else sheet_name)[:1000],
                                last_price=price_val,
                                last_supplier=supplier_db.name[:255],
                                updated_at=datetime.now(timezone.utc)
                            )
                            db.add(search_index)
                        else:
                            search_index.search_text = search_text
                            search_index.normalized_search_text = normalized_search_text
                            search_index.tokens_json = tokens
                            if supplier_db.name not in search_index.supplier_names:
                                search_index.supplier_names.append(supplier_db.name[:255])
                            search_index.last_price = price_val
                            search_index.last_supplier = supplier_db.name[:255]
                            search_index.updated_at = datetime.now(timezone.utc)

            # Finalizar run com sucesso
            run.status = "SUCCESS"
            run.finished_at = datetime.now(timezone.utc)
            run.total_rows = total_rows
            run.total_items = total_items
            run.total_offers = total_offers
            run.total_review = total_review
            
            # Inativar itens obsoletos (que não foram tocados nesta execução)
            # para evitar que fiquem órfãos/duplicados no catálogo
            db.query(StockCatalogItem).filter(
                StockCatalogItem.import_run_id != run.id,
                StockCatalogItem.active == True
            ).update({"active": False}, synchronize_session=False)
            
            db.commit()

        except Exception as e:
            db.rollback()
            run.status = "FAILED"
            run.finished_at = datetime.now(timezone.utc)
            run.error_message = str(e)
            db.commit()
            raise e

        return run
