from typing import Dict, Any

INTENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "purchase.price.confer": {
        "action_key": "purchase.price.confer",
        "title": "Registrar Preço (Conferência de Documento)",
        "description": "Lança um valor unitário observado em boleto ou nota fiscal de entrega para auditoria e histórico de compras.",
        "module": "purchases",
        "risk_level": "MEDIUM",
        "target_action_type": "create_price_evidence",
        "required_fields": [
            {"name": "supplier_id", "label": "Fornecedor", "type": "select", "source_module": "master_data", "source_entity": "supplier"},
            {"name": "product_item_id", "label": "Item / Insumo (SKU)", "type": "select", "source_module": "master_data", "source_entity": "product_item"},
            {"name": "unit_price", "label": "Preço Unitário (R$)", "type": "currency"}
        ],
        "optional_fields": [
            {"name": "quantity", "label": "Quantidade", "type": "number"},
            {"name": "document_number", "label": "Número do Documento", "type": "text"},
            {"name": "notes", "label": "Observações", "type": "textarea"}
        ]
    },
    "purchase.price.lookup": {
        "action_key": "purchase.price.lookup",
        "title": "Consultar Histórico de Preço",
        "description": "Busca a curva histórica de variações e cotações pagas para um item do catálogo de compras.",
        "module": "purchases",
        "risk_level": "LOW",
        "target_action_type": "lookup_price_history",
        "required_fields": [
            {"name": "product_item_id", "label": "Item / Insumo (SKU)", "type": "select", "source_module": "master_data", "source_entity": "product_item"}
        ],
        "optional_fields": []
    },
    "purchase.request.create": {
        "action_key": "purchase.request.create",
        "title": "Criar Requisição de Compra",
        "description": "Cria uma solicitação interna de compra de material para posterior cotação ou reposição de estoque.",
        "module": "purchases",
        "risk_level": "LOW",
        "target_action_type": "create_purchase_request",
        "required_fields": [
            {"name": "product_item_id", "label": "Item / Insumo (SKU)", "type": "select", "source_module": "master_data", "source_entity": "product_item"},
            {"name": "quantity", "label": "Quantidade", "type": "number"}
        ],
        "optional_fields": [
            {"name": "notes", "label": "Observações", "type": "textarea"}
        ]
    },
    "purchase.rfq.create": {
        "action_key": "purchase.rfq.create",
        "title": "Criar Processo de Cotação (RFQ)",
        "description": "Prepara um processo de RFQ (Request for Quote) agrupando fornecedores por categoria para envio por e-mail.",
        "module": "purchases",
        "risk_level": "MEDIUM",
        "target_action_type": "create_rfq",
        "required_fields": [
            {"name": "product_item_id", "label": "Item / Insumo (SKU)", "type": "select", "source_module": "master_data", "source_entity": "product_item"}
        ],
        "optional_fields": [
            {"name": "supplier_ids", "label": "Fornecedores", "type": "multi-select", "source_module": "master_data", "source_entity": "supplier"}
        ]
    },
    "it.ticket.create": {
        "action_key": "it.ticket.create",
        "title": "Abrir Chamado de Suporte TI",
        "description": "Abre um ticket de helpdesk na equipe de TI para resolver incidentes em equipamentos ou sistemas.",
        "module": "it",
        "risk_level": "LOW",
        "target_action_type": "create_ticket",
        "required_fields": [
            {"name": "description", "label": "O que está acontecendo?", "type": "textarea"}
        ],
        "optional_fields": [
            {"name": "category", "label": "Categoria", "type": "select", "options": ["Hardware", "Software", "Rede", "Acessos", "Outros"]},
            {"name": "asset_id", "label": "Equipamento / PC", "type": "select", "source_module": "it", "source_entity": "asset"}
        ]
    },
    "master_data.supplier.search": {
        "action_key": "master_data.supplier.search",
        "title": "Buscar Fornecedor",
        "description": "Pesquisa fornecedores no cadastro mestre por razão social, CNPJ ou categoria.",
        "module": "master_data",
        "risk_level": "LOW",
        "target_action_type": "search_supplier",
        "required_fields": [
            {"name": "query", "label": "Razão Social, CNPJ ou Nome", "type": "text"}
        ],
        "optional_fields": []
    },
    "master_data.item.search": {
        "action_key": "master_data.item.search",
        "title": "Buscar Item de Catálogo",
        "description": "Pesquisa insumos ou ferramentas cadastradas no Master Data por nome ou SKU.",
        "module": "master_data",
        "risk_level": "LOW",
        "target_action_type": "search_item",
        "required_fields": [
            {"name": "query", "label": "Nome ou SKU do Item", "type": "text"}
        ],
        "optional_fields": []
    },
    # Handlers em Preview (Coming Next)
    "proposal.create": {
        "action_key": "proposal.create",
        "title": "Criar Proposta Comercial (Preview)",
        "description": "Prepara um rascunho de orçamento comercial e gera o PDF final usando LibreOffice (Próxima PR).",
        "module": "proposals",
        "risk_level": "MEDIUM",
        "target_action_type": "coming_next_preview",
        "required_fields": [
            {"name": "customer_id", "label": "Cliente", "type": "select", "source_module": "master_data", "source_entity": "customer"}
        ],
        "optional_fields": [
            {"name": "discount_percent", "label": "Desconto (%)", "type": "number"}
        ]
    },
    "production.op.move": {
        "action_key": "production.op.move",
        "title": "Mover Estágio da OP (Preview)",
        "description": "Altera a fase de fabricação da Ordem de Produção no painel Kanban de produção (Próxima PR).",
        "module": "kanban",
        "risk_level": "MEDIUM",
        "target_action_type": "coming_next_preview",
        "required_fields": [
            {"name": "op_number", "label": "Número da OP", "type": "text"},
            {"name": "stage", "label": "Estágio de Destino", "type": "select", "options": ["Corte", "Dobra", "Solda", "Pintura", "Expedição"]}
        ],
        "optional_fields": []
    },
    "file.link": {
        "action_key": "file.link",
        "title": "Vincular Arquivo Técnico (Preview)",
        "description": "Mapeia um documento ou desenho CAD do NAS local a um card ou chamado (Próxima PR).",
        "module": "files",
        "risk_level": "LOW",
        "target_action_type": "coming_next_preview",
        "required_fields": [
            {"name": "file_name", "label": "Nome do Arquivo", "type": "text"},
            {"name": "entity_type", "label": "Tipo de Entidade", "type": "text"},
            {"name": "entity_id", "label": "ID da Entidade", "type": "text"}
        ],
        "optional_fields": []
    }
}
