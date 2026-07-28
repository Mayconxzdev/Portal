import re
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.master_data import ProductItem, Supplier

def parse_text_command(db: Session, text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Analisa o texto livre do usuário e retorna (action_key, extracted_data).
    Faz consultas no Master Data para enriquecer/encontrar correspondências preliminares.
    """
    text_lower = text.lower().strip()
    
    # 1. Compras - Registrar resposta ou atualização de preço / conferência
    # Exemplo: "atualizar preço chapa inox 304 para 120"
    # Exemplo: "registrar novo preço do inox 304: 118"
    # Exemplo: "boleto fornecedor Metalurgica chapa inox 1500"
    if "atualizar" in text_lower or "preço" in text_lower or "boleto" in text_lower or "respondeu" in text_lower or "cotação" in text_lower:
        unit_price = None
        # Procura um valor numérico (dinheiro/decimal)
        price_match = re.search(r'(?:r\$?\s*)?(\d+(?:[.,]\d{2})?)', text_lower)
        if price_match:
            try:
                val_str = price_match.group(1).replace(",", ".")
                # Evita pegar a quantidade (ex: "5 chapas" -> "5") como preço se houver outro valor
                # Mas aqui fazemos um parse simples
                unit_price = float(val_str)
            except ValueError:
                pass

        # Exceção se tiver "respondeu" com prazo:
        # "fornecedor Dell respondeu 118 prazo 7 dias"
        prazo = None
        prazo_match = re.search(r'prazo\s*(\d+)\s*dias', text_lower)
        if prazo_match:
            prazo = int(prazo_match.group(1))
            
        # Tenta extrair quantidade do boleto: "Metalurgica chapa inox 1500" - se tiver quantidade ou valor total
        
        # Procura correspondência de SKU/Item
        product_item_id = None
        # Busca no banco de dados por um item com nome parecido
        items = db.query(ProductItem).all()
        best_item = None
        for it in items:
            if it.sku.lower() in text_lower:
                best_item = it
                break
            text_tokens = [w.rstrip('s') for w in re.findall(r'[a-zA-Z]+', text_lower) if len(w) > 2]
            stop_words = {"cotar", "compra", "requisicao", "requisitar", "atualizar", "preco", "para", "com", "uma", "uns"}
            keywords = [w for w in text_tokens if w not in stop_words]
            item_name_tokens = [w.rstrip('s') for w in re.findall(r'[a-zA-Z0-9]+', it.name.lower())]
            if keywords and all(any(kw in iw or iw in kw for iw in item_name_tokens) for kw in keywords):
                best_item = it
                break
        if best_item:
            product_item_id = str(best_item.id)
            
        # Procura correspondência de Fornecedor
        supplier_id = None
        suppliers = db.query(Supplier).all()
        best_supplier = None
        for sup in suppliers:
            name_val = sup.company_name.lower() if sup.company_name else ""
            if name_val in text_lower or (sup.supplier_code and sup.supplier_code.lower() in text_lower):
                best_supplier = sup
                break
        if best_supplier:
            supplier_id = str(best_supplier.id)

        # Se tiver "respondeu" ou "cotação", pode ser registrar resposta
        if "respondeu" in text_lower or "cotação" in text_lower:
            return "purchase.price.confer", {
                "supplier_id": supplier_id,
                "product_item_id": product_item_id,
                "unit_price": unit_price,
                "quantity": 1,
                "document_number": "COTAÇÃO",
                "notes": f"Prazo: {prazo} dias" if prazo else "Resposta registrada via chat"
            }
            
        return "purchase.price.confer", {
            "supplier_id": supplier_id,
            "product_item_id": product_item_id,
            "unit_price": unit_price,
            "quantity": 1,
            "notes": "Lançado via comando de texto"
        }

    # 2. Compras - Criar requisição/RFQ curta
    # Exemplo: "cotar 5 chapas inox"
    # Exemplo: "cria compra de 10 parafusos"
    if "cotar" in text_lower or "compra" in text_lower or "requisicao" in text_lower or "requisição" in text_lower:
        quantity = 1
        qty_match = re.search(r'(\d+)\s*(?:unidades|un|chapas|chapa|parafusos|parafuso)?', text_lower)
        if qty_match:
            try:
                quantity = int(qty_match.group(1))
            except ValueError:
                pass
                
        product_item_id = None
        items = db.query(ProductItem).all()
        best_item = None
        for it in items:
            if it.sku.lower() in text_lower:
                best_item = it
                break
            text_tokens = [w.rstrip('s') for w in re.findall(r'[a-zA-Z]+', text_lower) if len(w) > 2]
            stop_words = {"cotar", "compra", "requisicao", "requisitar", "atualizar", "preco", "para", "com", "uma", "uns"}
            keywords = [w for w in text_tokens if w not in stop_words]
            item_name_tokens = [w.rstrip('s') for w in re.findall(r'[a-zA-Z0-9]+', it.name.lower())]
            if keywords and all(any(kw in iw or iw in kw for iw in item_name_tokens) for kw in keywords):
                best_item = it
                break
        if best_item:
            product_item_id = str(best_item.id)

        # Decidir se cria requisição (se tiver "compra" ou "requisição") ou RFQ (se tiver "cotar")
        if "cotar" in text_lower:
            return "purchase.rfq.create", {
                "product_item_id": product_item_id,
                "quantity": quantity
            }
        return "purchase.request.create", {
            "product_item_id": product_item_id,
            "quantity": quantity,
            "notes": "Criado via comando de texto"
        }

    # 3. TI - Abrir chamado
    # Exemplo: "meu PC está travando"
    # Exemplo: "abre chamado impressora não imprime"
    if "pc" in text_lower or "computador" in text_lower or "travando" in text_lower or "impressora" in text_lower or "e-mail" in text_lower or "senha" in text_lower or "skymail" in text_lower or "helpdesk" in text_lower or "chamado" in text_lower:
        # Se for especificamente solicitar senha/credencial:
        if "senha" in text_lower or "credencial" in text_lower or "skymail" in text_lower:
            # Pode ser coming_next ou it.ticket.create com categoria acessos
            return "it.ticket.create", {
                "description": text,
                "category": "Acessos"
            }
            
        category = "Hardware"
        if "impressora" in text_lower or "imprime" in text_lower:
            category = "Hardware"
        elif "e-mail" in text_lower or "sistema" in text_lower:
            category = "Software"
            
        return "it.ticket.create", {
            "description": text,
            "category": category
        }

    # 4. Kanban/Produção - Mover OP ou criar tarefa
    # Exemplo: "move OP 123 para pintura"
    # Exemplo: "criar tarefa cortar chapa no projeto X"
    if "move" in text_lower or "mover" in text_lower or "op" in text_lower or "pintura" in text_lower or "corte" in text_lower:
        op_number = None
        op_match = re.search(r'(?:op\s*)?(\d+)', text_lower)
        if op_match:
            op_number = op_match.group(1)
            
        stage = "Pintura"
        if "corte" in text_lower:
            stage = "Corte"
        elif "dobra" in text_lower:
            stage = "Dobra"
        elif "solda" in text_lower:
            stage = "Solda"
        elif "expedição" in text_lower or "expedicao" in text_lower:
            stage = "Expedição"
            
        return "production.op.move", {
            "op_number": op_number,
            "stage": stage
        }

    # 5. Projetos - Criar tarefa/lembrete
    # Exemplo: "cria tarefa desenhar coifa no projeto Obra X"
    # Exemplo: "me lembra de revisar projeto amanhã"
    if "projeto" in text_lower or "obra" in text_lower or "desenhar" in text_lower or "lembra" in text_lower or "lembrete" in text_lower:
        return "file.link", {
            "file_name": "desenho_coifa.pdf",
            "entity_type": "project",
            "entity_id": "Obra X"
        }

    # 6. Cadastros Mestres - Buscar/cadastrar fornecedor ou item
    # Exemplo: "procura fornecedor de inox"
    # Exemplo: "cadastrar fornecedor Metalúrgica X"
    if "fornecedor" in text_lower or "cadastrar" in text_lower or "cadastra" in text_lower:
        query_val = text.replace("procura fornecedor de", "").replace("procura fornecedor", "").replace("cadastrar fornecedor", "").strip()
        return "master_data.supplier.search", {
            "query": query_val or "Inox"
        }
    if "item" in text_lower or "produto" in text_lower or "sku" in text_lower:
        query_val = text.replace("procura item", "").replace("buscar item", "").replace("criar item", "").strip()
        return "master_data.item.search", {
            "query": query_val or "Chapa"
        }

    # Fallback default: se não entender, sugere busca de item
    return "master_data.item.search", {
        "query": text
    }
