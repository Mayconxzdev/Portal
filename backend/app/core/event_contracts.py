import json
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.core.config import settings

logger = logging.getLogger("vesper.events")

# Schemas Pydantic para os eventos conhecidos do Portal

class AuthUserLoggedInPayload(BaseModel):
    username: str = Field(..., description="Nome do usuario")
    email: str = Field(..., description="E-mail do usuario")
    role: str = Field(..., description="Papel/Funcao do usuario")
    ip_address: Optional[str] = Field(None, description="IP do cliente")

class ApprovalCreatedPayload(BaseModel):
    approval_id: int = Field(..., description="ID da aprovacao")
    title: str = Field(..., description="Titulo da aprovacao")
    module_slug: str = Field(..., description="Slug do modulo requisitante")
    risk_level: str = Field(..., description="Nivel de risco")
    action_type: str = Field(..., description="Tipo de acao a ser tomada")

# Kanban Payloads
class KanbanCardCreatedPayload(BaseModel):
    card_id: int = Field(..., description="ID do card")
    board_id: int = Field(..., description="ID do quadro")
    title: str = Field(..., description="Titulo do card")
    assigned_to_user_id: Optional[int] = Field(None, description="ID do usuario atribuido")
    created_by_user_id: int = Field(..., description="ID do criador")

class KanbanCardMovedPayload(BaseModel):
    card_id: int = Field(..., description="ID do card")
    board_id: int = Field(..., description="ID do quadro")
    title: str = Field(..., description="Titulo do card")
    from_column_id: int = Field(..., description="ID da coluna de origem")
    to_column_id: int = Field(..., description="ID da coluna de destino")
    from_column_name: str = Field(..., description="Nome da coluna de origem")
    to_column_name: str = Field(..., description="Nome da coluna de destino")
    assigned_to_user_ids: List[int] = Field(default_factory=list, description="Lista de IDs dos usuarios atribuidos")
    moved_by_user_id: int = Field(..., description="ID de quem moveu o card")

class KanbanCardAssignedPayload(BaseModel):
    card_id: int = Field(..., description="ID do card")
    board_id: int = Field(..., description="ID do quadro")
    title: str = Field(..., description="Titulo do card")
    assigned_user_id: int = Field(..., description="ID do usuario atribuido")
    assigned_by_user_id: int = Field(..., description="ID do usuario que atribuiu")

class KanbanCardCompletedPayload(BaseModel):
    card_id: int = Field(..., description="ID do card")
    board_id: int = Field(..., description="ID do quadro")
    title: str = Field(..., description="Titulo do card")
    completed_by_user_id: int = Field(..., description="ID de quem concluiu o card")
    assigned_to_user_ids: List[int] = Field(default_factory=list, description="Lista de IDs dos usuarios atribuidos")

class KanbanCardCommentCreatedPayload(BaseModel):
    card_id: int = Field(..., description="ID do card")
    board_id: int = Field(..., description="ID do quadro")
    title: str = Field(..., description="Titulo do card")
    comment_id: int = Field(..., description="ID do comentario")
    comment_text: str = Field(..., description="Texto do comentario")
    author_user_id: int = Field(..., description="ID do autor do comentario")
    assigned_to_user_ids: List[int] = Field(default_factory=list, description="Lista de IDs dos usuarios atribuidos")

# TI Payloads
class ITTicketCreatedPayload(BaseModel):
    ticket_id: int = Field(..., description="ID do chamado")
    ticket_number: str = Field(..., description="Numero do chamado")
    title: str = Field(..., description="Titulo do chamado")
    category: str = Field(..., description="Categoria do chamado")
    assigned_tech_id: Optional[int] = Field(None, description="ID do tecnico atribuido")

class ITTicketStatusChangedPayload(BaseModel):
    ticket_id: int = Field(..., description="ID do chamado")
    ticket_number: str = Field(..., description="Numero do chamado")
    title: str = Field(..., description="Titulo do chamado")
    old_status: str = Field(..., description="Status anterior")
    new_status: str = Field(..., description="Novo status")
    requester_id: int = Field(..., description="ID do solicitante")

class ITTicketAssignedPayload(BaseModel):
    ticket_id: int = Field(..., description="ID do chamado")
    ticket_number: str = Field(..., description="Numero do chamado")
    title: str = Field(..., description="Titulo do chamado")
    assigned_tech_id: int = Field(..., description="ID do tecnico designado")
    assigned_by_id: int = Field(..., description="ID do usuario que atribuiu")

class ITTicketResolvedPayload(BaseModel):
    ticket_id: int = Field(..., description="ID do chamado")
    ticket_number: str = Field(..., description="Numero do chamado")
    title: str = Field(..., description="Titulo do chamado")
    requester_id: int = Field(..., description="ID do solicitante")
    resolved_by_id: int = Field(..., description="ID de quem resolveu")

class ITAccessRequestedPayload(BaseModel):
    request_id: int = Field(..., description="ID da solicitacao de acesso")
    title: str = Field(..., description="Titulo/Resumo do pedido")
    requester_id: int = Field(..., description="ID do solicitante")
    system_name: str = Field(..., description="Nome do sistema solicitado")

# Chat Payloads
class ChatMessageCreatedPayload(BaseModel):
    message_id: int = Field(..., description="ID da mensagem")
    conversation_id: int = Field(..., description="ID da conversa")
    sender_user_id: int = Field(..., description="ID do remetente")
    body_preview: str = Field(..., description="Previa da mensagem")
    message_type: str = Field(..., description="Tipo de mensagem")

class ChatMessageMentionedPayload(BaseModel):
    message_id: int = Field(..., description="ID da mensagem")
    conversation_id: int = Field(..., description="ID da conversa")
    sender_user_id: int = Field(..., description="ID do remetente")
    mentioned_user_id: int = Field(..., description="ID do usuario mencionado")
    body_preview: str = Field(..., description="Previa da mensagem")

class ChatFileUploadedPayload(BaseModel):
    message_id: int = Field(..., description="ID da mensagem")
    conversation_id: int = Field(..., description="ID da conversa")
    sender_user_id: int = Field(..., description="ID do remetente")
    file_id: int = Field(..., description="ID do arquivo anexo")

# Approvals Payloads
class ApprovalApprovedPayload(BaseModel):
    approval_id: int = Field(..., description="ID da aprovacao")
    title: str = Field(..., description="Titulo da aprovacao")
    requester_user_id: int = Field(..., description="ID do solicitante")
    approver_user_id: int = Field(..., description="ID do aprovador")

class ApprovalRejectedPayload(BaseModel):
    approval_id: int = Field(..., description="ID da aprovacao")
    title: str = Field(..., description="Titulo da aprovacao")
    requester_user_id: int = Field(..., description="ID do solicitante")
    approver_user_id: int = Field(..., description="ID de quem rejeitou")
    reason: Optional[str] = Field(None, description="Motivo da rejeicao")

class ApprovalCommentCreatedPayload(BaseModel):
    approval_id: int = Field(..., description="ID da aprovacao")
    title: str = Field(..., description="Titulo da aprovacao")
    comment_id: int = Field(..., description="ID do comentario")
    comment_text: str = Field(..., description="Texto do comentario")
    author_user_id: int = Field(..., description="ID do autor do comentario")
    requester_user_id: int = Field(..., description="ID do solicitante")

# Master Data Payloads
class MasterDataPersonPayload(BaseModel):
    id: str = Field(..., description="ID UUID da Pessoa")
    type: str = Field(..., description="Tipo da Pessoa (INDIVIDUAL/COMPANY)")
    name: str = Field(..., description="Nome ou Razao Social")
    document_number: Optional[str] = Field(None, description="Numero do documento (mascarado)")
    actor_user_id: int = Field(..., description="ID do usuario autor da acao")
    action_url: Optional[str] = Field(None, description="Link do cadastro no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

class MasterDataCustomerPayload(BaseModel):
    id: str = Field(..., description="ID UUID do Cliente")
    person_id: str = Field(..., description="ID UUID da Pessoa vinculada")
    name: str = Field(..., description="Nome do Cliente")
    customer_code: Optional[str] = Field(None, description="Codigo do Cliente")
    status: str = Field(..., description="Status do Cliente")
    actor_user_id: int = Field(..., description="ID do usuario autor da acao")
    action_url: Optional[str] = Field(None, description="Link do cadastro no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

class MasterDataSupplierPayload(BaseModel):
    id: str = Field(..., description="ID UUID do Fornecedor")
    person_id: str = Field(..., description="ID UUID da Pessoa vinculada")
    name: str = Field(..., description="Nome do Fornecedor")
    supplier_code: Optional[str] = Field(None, description="Codigo do Fornecedor")
    status: str = Field(..., description="Status do Fornecedor")
    actor_user_id: int = Field(..., description="ID do usuario autor da acao")
    action_url: Optional[str] = Field(None, description="Link do cadastro no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

class MasterDataItemPayload(BaseModel):
    id: str = Field(..., description="ID UUID do Produto/Item")
    sku: str = Field(..., description="SKU/Codigo do Produto")
    name: str = Field(..., description="Nome do Produto")
    item_type: str = Field(..., description="Tipo do Produto")
    is_active: bool = Field(..., description="Status ativo do Produto")
    actor_user_id: int = Field(..., description="ID do usuario autor da acao")
    action_url: Optional[str] = Field(None, description="Link do cadastro no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

class MasterDataServicePayload(BaseModel):
    id: str = Field(..., description="ID UUID do Servico")
    code: str = Field(..., description="Codigo do Servico")
    name: str = Field(..., description="Nome do Servico")
    is_active: bool = Field(..., description="Status ativo do Servico")
    actor_user_id: int = Field(..., description="ID do usuario autor da acao")
    action_url: Optional[str] = Field(None, description="Link do cadastro no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

# Purchases Payloads
class PurchaseRequestPayload(BaseModel):
    id: str = Field(..., description="ID UUID da Requisicao de Compra")
    title: str = Field(..., description="Titulo da Requisicao")
    requester_user_id: int = Field(..., description="ID do usuario solicitante")
    status: str = Field(..., description="Status da Requisicao")
    action_url: Optional[str] = Field(None, description="Link no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

class PurchaseRFQPayload(BaseModel):
    id: str = Field(..., description="ID UUID da RFQ")
    request_id: str = Field(..., description="ID UUID da Requisicao de Compra vinculada")
    title: str = Field(..., description="Titulo da RFQ")
    status: str = Field(..., description="Status da RFQ")
    action_url: Optional[str] = Field(None, description="Link no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

class PurchaseRFQSupplierPayload(BaseModel):
    rfq_id: str = Field(..., description="ID UUID da RFQ")
    supplier_id: str = Field(..., description="ID UUID do Fornecedor")
    supplier_name: str = Field(..., description="Nome do Fornecedor")
    status: str = Field(..., description="Status da participacao")
    action_url: Optional[str] = Field(None, description="Link no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

class PurchaseRFQDraftGeneratedPayload(BaseModel):
    rfq_id: str = Field(..., description="ID UUID da RFQ")
    supplier_id: str = Field(..., description="ID UUID do Fornecedor")
    contact_email: Optional[str] = Field(None, description="Email de contato")
    action_url: Optional[str] = Field(None, description="Link no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

class PurchaseQuoteResponsePayload(BaseModel):
    id: str = Field(..., description="ID UUID da Resposta")
    rfq_id: Optional[str] = Field(None, description="ID UUID da RFQ")
    supplier_id: str = Field(..., description="ID UUID do Fornecedor")
    supplier_name: str = Field(..., description="Nome do Fornecedor")
    total_amount: Optional[float] = Field(None, description="Valor total da cotacao")
    status: str = Field(..., description="Status da cotacao")
    action_url: Optional[str] = Field(None, description="Link no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

class PurchaseComparisonPayload(BaseModel):
    rfq_id: str = Field(..., description="ID UUID da RFQ")
    best_supplier_id: Optional[str] = Field(None, description="ID UUID do melhor fornecedor")
    recommendation_summary: Optional[str] = Field(None, description="Resumo da recomendacao")
    action_url: Optional[str] = Field(None, description="Link no Portal")
    summary: str = Field(..., description="Resumo amigavel do evento")

class PurchaseActionIntentRequestedPayload(BaseModel):
    action_intent_id: str = Field(..., description="ID UUID da ActionIntent")
    rfq_id: str = Field(..., description="ID UUID da RFQ")
    proposed_action: str = Field(..., description="Acao proposta")
    summary: str = Field(..., description="Resumo da solicitacao")


# Price Traceability Payloads
class PurchasePriceEvidencePayload(BaseModel):
    id: str = Field(..., description="ID UUID da evidência física de preço")
    source_type: str = Field(..., description="Tipo de origem (BOLETO, NF, etc.)")
    product_item_id: str = Field(..., description="ID UUID do item de produto")
    supplier_id: Optional[str] = Field(None, description="ID UUID do fornecedor")
    unit_price: float = Field(..., description="Valor unitário observado")
    actor_user_id: int = Field(..., description="ID do usuário que registrou")
    summary: str = Field(..., description="Resumo do evento")

class PurchasePriceHistoryPayload(BaseModel):
    id: str = Field(..., description="ID UUID do registro histórico de preço")
    product_item_id: str = Field(..., description="ID UUID do item de produto")
    supplier_id: Optional[str] = Field(None, description="ID UUID do fornecedor")
    unit_price: float = Field(..., description="Valor unitário")
    observed_at: str = Field(..., description="Data da observação")
    actor_user_id: int = Field(..., description="ID do usuário que registrou")
    summary: str = Field(..., description="Resumo do evento")

class PurchasePriceSuggestionPayload(BaseModel):
    id: str = Field(..., description="ID UUID da sugestão na fila de reajustes")
    product_item_id: str = Field(..., description="ID UUID do item de produto")
    supplier_id: Optional[str] = Field(None, description="ID UUID do fornecedor")
    old_unit_price: Optional[float] = Field(None, description="Preço unitário de referência anterior")
    new_unit_price: float = Field(..., description="Novo preço unitário proposto")
    pct_variation: Optional[float] = Field(None, description="Variação percentual")
    variation_direction: str = Field(..., description="Direção da variação (INCREASE, DECREASE, etc.)")
    created_by_user_id: int = Field(..., description="ID do usuário que criou a sugestão")
    summary: str = Field(..., description="Resumo do evento")

class PurchasePriceSuggestionApprovedPayload(BaseModel):
    id: str = Field(..., description="ID UUID da sugestão aprovada")
    product_item_id: str = Field(..., description="ID UUID do item de produto")
    supplier_id: Optional[str] = Field(None, description="ID UUID do fornecedor")
    new_unit_price: float = Field(..., description="Preço unitário homologado")
    approved_by_user_id: int = Field(..., description="ID do usuário que aprovou")
    created_by_user_id: int = Field(..., description="ID do usuário que criou a sugestão original")
    summary: str = Field(..., description="Resumo do evento")

class PurchasePriceSuggestionRejectedPayload(BaseModel):
    id: str = Field(..., description="ID UUID da sugestão rejeitada")
    product_item_id: str = Field(..., description="ID UUID do item de produto")
    supplier_id: Optional[str] = Field(None, description="ID UUID do fornecedor")
    new_unit_price: float = Field(..., description="Preço unitário rejeitado")
    rejected_by_user_id: int = Field(..., description="ID do usuário que rejeitou")
    created_by_user_id: int = Field(..., description="ID do usuário que criou a sugestão original")
    reason: Optional[str] = Field(None, description="Motivo da rejeição")
    summary: str = Field(..., description="Resumo do evento")

class PurchasePriceReferencePayload(BaseModel):
    id: str = Field(..., description="ID UUID do preço de referência")
    product_item_id: str = Field(..., description="ID UUID do item de produto")
    supplier_id: Optional[str] = Field(None, description="ID UUID do fornecedor")
    current_unit_price: float = Field(..., description="Preço unitário de referência atual")
    approved_by_user_id: int = Field(..., description="ID do aprovador")
    summary: str = Field(..., description="Resumo do evento")


class PurchaseResearchSessionPayload(BaseModel):
    session_id: str = Field(..., description="ID UUID da sessao de pesquisa")
    purchase_request_id: str = Field(..., description="ID UUID da compra")
    purchase_item_id: str = Field(..., description="ID UUID do item da compra")
    status: str = Field(..., description="Estado atual da pesquisa")
    progress_percent: int = Field(..., description="Progresso da pesquisa")
    action_url: Optional[str] = Field(None, description="Link interno seguro")
    summary: str = Field(..., description="Resumo humano do evento")


class PurchaseItemEventPayload(BaseModel):
    purchase_request_id: str = Field(..., description="ID UUID da compra")
    purchase_item_id: str = Field(..., description="ID UUID do item da compra")
    action_url: Optional[str] = Field(None, description="Link interno seguro")
    summary: str = Field(..., description="Resumo humano do evento")


class StockPriceUpdatedPayload(BaseModel):
    item_id: str = Field(..., description="ID UUID do item do Estoque")
    supplier_id: str = Field(..., description="ID UUID do fornecedor")
    supplier_name: str = Field(..., description="Nome do fornecedor")
    old_price: Optional[float] = Field(None, description="Preco anterior")
    new_price: float = Field(..., description="Novo preco")
    actor_user_id: Optional[int] = Field(None, description="ID do usuario autor")
    summary: str = Field(..., description="Resumo amigavel do evento")


class StockPurchaseRequestedPayload(BaseModel):
    item_id: str = Field(..., description="ID UUID do item do Estoque")
    request_id: str = Field(..., description="ID UUID da necessidade de compra")
    quote_id: str = Field(..., description="ID UUID da cotacao")
    actor_user_id: Optional[int] = Field(None, description="ID do usuario solicitante")
    action_url: str = Field(..., description="Link para abrir a cotacao")
    summary: str = Field(..., description="Resumo amigavel do evento")


# Legacy Import Payloads
class LegacyImportBatchCreatedPayload(BaseModel):
    batch_id: str = Field(..., description="ID UUID do Lote de importacao")
    source_app: str = Field(..., description="Nome do sistema legado de origem")
    source_name: str = Field(..., description="Nome do arquivo ou lote")
    module_target: str = Field(..., description="Modulo destino")
    actor_user_id: Optional[int] = Field(None, description="ID do usuario autor")
    summary: str = Field(..., description="Resumo do evento")

class LegacyImportBatchCompletedPayload(BaseModel):
    batch_id: str = Field(..., description="ID UUID do Lote")
    source_app: str = Field(..., description="Sistema legado de origem")
    source_name: str = Field(..., description="Nome do arquivo ou lote")
    module_target: str = Field(..., description="Modulo destino")
    total_rows: int = Field(..., description="Total de linhas processadas")
    valid_rows: int = Field(..., description="Linhas validas sem duplicados")
    duplicate_rows: int = Field(..., description="Linhas com duplicidade detectada")
    error_rows: int = Field(..., description="Linhas que falharam no processamento")
    actor_user_id: Optional[int] = Field(None, description="ID do usuario autor")
    summary: str = Field(..., description="Resumo do evento")

class LegacyImportRowReviewedPayload(BaseModel):
    row_id: str = Field(..., description="ID UUID da linha de staging")
    batch_id: str = Field(..., description="ID UUID do lote")
    entity_target: str = Field(..., description="Entidade destino")
    decision: str = Field(..., description="Decisao registrada (ACCEPT/REJECT/etc.)")
    actor_user_id: int = Field(..., description="ID do administrador autor")
    summary: str = Field(..., description="Resumo da decisao")

class LegacyImportDuplicateDetectedPayload(BaseModel):
    row_id: str = Field(..., description="ID UUID da linha de staging")
    batch_id: str = Field(..., description="ID UUID do lote")
    entity_target: str = Field(..., description="Entidade destino")
    match_type: str = Field(..., description="Tipo de colisao cadastral")
    score: float = Field(..., description="Grau de similaridade")
    summary: str = Field(..., description="Resumo do evento")

class LegacyImportReadyForReviewPayload(BaseModel):
    batch_id: str = Field(..., description="ID UUID do Lote")
    source_app: str = Field(..., description="Sistema de origem")
    source_name: str = Field(..., description="Nome do arquivo")
    module_target: str = Field(..., description="Modulo destino")
    total_rows: int = Field(..., description="Total de linhas")
    summary: str = Field(..., description="Resumo")

class LegacyImportFailedPayload(BaseModel):
    batch_id: str = Field(..., description="ID UUID do Lote")
    source_app: str = Field(..., description="Sistema de origem")
    error_message: str = Field(..., description="Mensagem de erro")
    summary: str = Field(..., description="Resumo do erro")


class RealDataActivationPayload(BaseModel):
    summary: str = Field(..., description="Resumo da ativacao real")
    actor_user_id: Optional[int] = Field(None, description="ID do usuario autor")
    batches: Optional[int] = Field(None, description="Total de lotes envolvidos")
    rows: Optional[int] = Field(None, description="Total de linhas reais envolvidas")
    contains_secrets: Optional[bool] = Field(False, description="Indica se o payload contem segredo")


# Registro central de contratos de eventos
EVENT_CONTRACTS: Dict[str, Any] = {
    "auth.user.logged_in": AuthUserLoggedInPayload,
    "approval.created": ApprovalCreatedPayload,
    "approval.approved": ApprovalApprovedPayload,
    "approval.rejected": ApprovalRejectedPayload,
    "approval.comment.created": ApprovalCommentCreatedPayload,
    "kanban.card.created": KanbanCardCreatedPayload,
    "kanban.card.moved": KanbanCardMovedPayload,
    "kanban.card.assigned": KanbanCardAssignedPayload,
    "kanban.card.completed": KanbanCardCompletedPayload,
    "kanban.card.comment.created": KanbanCardCommentCreatedPayload,
    "it.ticket.created": ITTicketCreatedPayload,
    "it.ticket.status_changed": ITTicketStatusChangedPayload,
    "it.ticket.assigned": ITTicketAssignedPayload,
    "it.ticket.resolved": ITTicketResolvedPayload,
    "it.access.requested": ITAccessRequestedPayload,
    "chat.message.created": ChatMessageCreatedPayload,
    "chat.message.mentioned": ChatMessageMentionedPayload,
    "chat.file.uploaded": ChatFileUploadedPayload,
    # Master Data Contracts
    "master_data.person.created": MasterDataPersonPayload,
    "master_data.person.updated": MasterDataPersonPayload,
    "master_data.customer.created": MasterDataCustomerPayload,
    "master_data.customer.updated": MasterDataCustomerPayload,
    "master_data.supplier.created": MasterDataSupplierPayload,
    "master_data.supplier.updated": MasterDataSupplierPayload,
    "master_data.item.created": MasterDataItemPayload,
    "master_data.item.updated": MasterDataItemPayload,
    "master_data.service.created": MasterDataServicePayload,
    "master_data.service.updated": MasterDataServicePayload,
    # Purchases Contracts
    "purchase.request.created": PurchaseRequestPayload,
    "purchase.request.updated": PurchaseRequestPayload,
    "purchase.rfq.created": PurchaseRFQPayload,
    "purchase.rfq.ready_for_review": PurchaseRFQPayload,
    "purchase.rfq.supplier.added": PurchaseRFQSupplierPayload,
    "purchase.rfq.draft_generated": PurchaseRFQDraftGeneratedPayload,
    "purchase.quote_response.created": PurchaseQuoteResponsePayload,
    "purchase.comparison.generated": PurchaseComparisonPayload,
    "purchase.action_intent.requested": PurchaseActionIntentRequestedPayload,
    # Price Traceability Contracts
    "purchase.price.evidence.created": PurchasePriceEvidencePayload,
    "purchase.price.history.created": PurchasePriceHistoryPayload,
    "purchase.price.suggestion.created": PurchasePriceSuggestionPayload,
    "purchase.price.suggestion.approved": PurchasePriceSuggestionApprovedPayload,
    "purchase.price.suggestion.rejected": PurchasePriceSuggestionRejectedPayload,
    "purchase.price.reference.created": PurchasePriceReferencePayload,
    "purchase.price.reference.updated": PurchasePriceReferencePayload,
    "purchase.research.started": PurchaseResearchSessionPayload,
    "purchase.research.updated": PurchaseResearchSessionPayload,
    "purchase.offer.verified": PurchaseResearchSessionPayload,
    "purchase.recommendation.updated": PurchaseResearchSessionPayload,
    "purchase.item.approval_requested": PurchaseItemEventPayload,
    "purchase.item.approval_decided": PurchaseItemEventPayload,
    "purchase.rfq.ready": PurchaseItemEventPayload,
    "purchase.order.placed": PurchaseItemEventPayload,
    "purchase.delivery.received": PurchaseItemEventPayload,
    # Stock Contracts
    "stock.price_updated": StockPriceUpdatedPayload,
    "stock.purchase_requested": StockPurchaseRequestedPayload,
    # Legacy Import Contracts
    "legacy.import.batch.created": LegacyImportBatchCreatedPayload,
    "legacy.import.batch.completed": LegacyImportBatchCompletedPayload,
    "legacy.import.row.reviewed": LegacyImportRowReviewedPayload,
    "legacy.import.duplicate.detected": LegacyImportDuplicateDetectedPayload,
    "legacy.import.ready_for_review": LegacyImportReadyForReviewPayload,
    "legacy.import.failed": LegacyImportFailedPayload,
    "real_data.activation.started": RealDataActivationPayload,
    "real_data.activation.completed": RealDataActivationPayload,
}

def validate_event_payload(event_type: str, payload: dict) -> dict:
    """
    Valida e normaliza o payload do evento com base no tipo do evento (event_type).
    Respeita a configuração settings.EVENT_PAYLOAD_VALIDATION_MODE:
    - "off": ignora todas as validações e retorna o payload original.
    - "warn": valida eventos conhecidos, levanta warning/log se inválidos ou se o evento for desconhecido.
    - "strict": rejeita eventos conhecidos inválidos ou eventos desconhecidos com exceções.
    """
    mode = getattr(settings, "EVENT_PAYLOAD_VALIDATION_MODE", "warn").lower()
    
    if mode == "off":
        return payload

    if not isinstance(payload, dict):
        raise ValueError(f"O payload do evento deve ser um dicionario JSON-serializavel. Recebido: {type(payload)}")

    # Garante que o payload é serializável
    try:
        json.dumps(payload)
    except Exception as json_err:
        raise ValueError(f"Payload nao e serializavel em JSON: {json_err}")

    if event_type in EVENT_CONTRACTS:
        schema = EVENT_CONTRACTS[event_type]
        try:
            validated_model = schema(**payload)
            return validated_model.model_dump()
        except Exception as e:
            # Mascarar campos sensiveis (se existirem) em logs/erros de validacao
            # para evitar vazamento em traces
            safe_payload = payload.copy()
            for key in ["password", "token", "secret", "hashed_password"]:
                if key in safe_payload:
                    safe_payload[key] = "******"
            
            # Limpar valores sensiveis do str(e) tambem
            error_msg_str = str(e)
            for key in ["password", "token", "secret", "hashed_password"]:
                if key in payload:
                    val = str(payload[key])
                    if val and val != "******":
                        error_msg_str = error_msg_str.replace(val, "******")
            
            error_msg = (
                f"[CONTRATO EVENTO] Payload invalido para tipo '{event_type}'. "
                f"Erro: {error_msg_str} | Payload enviado: {safe_payload}"
            )
            
            if mode == "strict":
                raise ValueError(error_msg)
            else:
                logger.warning(error_msg)
                return payload
    else:
        # Evento desconhecido
        error_msg = f"[CONTRATO EVENTO] Evento desconhecido '{event_type}' emitido (modo: {mode})."
        if mode == "strict":
            raise ValueError(error_msg)
        else:
            logger.warning(error_msg)
            return payload
