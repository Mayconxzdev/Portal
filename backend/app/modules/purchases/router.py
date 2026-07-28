import uuid

from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.modules.purchases.service import PurchasesService
from app.modules.purchases.schemas import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
    PurchaseRequestCreate,
    PurchaseRequestUpdate,
    PurchaseRequestResponse,
    PurchaseRequestDetailResponse,
    PurchaseNeedParseTextPayload,
    PurchaseNeedImportLinkPayload,
    PurchaseNeedImportCartPayload,
    PurchaseNeedImportPreviewResponse,
    PurchaseItemCreate,
    PurchaseItemUpdate,
    PurchaseItemResponse,
    PurchaseItemOptionResponse,
    PurchaseItemOptionCreate,
    PurchaseResearchSessionCreate,
    PurchaseResearchSessionResponse,
    PurchaseRecommendationResponse,
    PurchaseItemApprovalPayload,
    PrepareSupplierRFQPayload,
    PrepareSupplierRFQResponse,
    PurchaseSuggestionResponse,
    PurchaseAnalyzeRequest,
    PurchaseAnalyzeResponse,
    PurchaseItemSplitPayload,
    PurchaseItemsMergePayload,
    PurchaseIdempotencyLookupResponse,
    PurchasePlaceOrderPayload,
    PurchaseReceiveDeliveryPayload,
    PurchaseOrderCreate,
    PurchaseDeliveryCreate,
    QuotationCreate,
    QuotationResponse,
    PurchasesSummaryResponse,
    PurchasesOverviewResponse,
    PurchaseAttentionItemResponse,
    PurchaseQuoteCreate,
    PurchaseQuoteUpdate,
    PurchaseQuoteItemCreate,
    PurchaseQuoteDetailResponse,
    PurchaseQuoteParseListPayload,
    PurchaseQuoteParsedLine,
    PurchaseQuoteSupplierSelectionPayload,
    PurchaseQuoteSupplierSuggestion,
    PurchaseQuoteEmailPreview,
    PurchaseSenderAccountResponse,
    PurchaseSenderAccountCreate,
    PurchaseSenderAccountUpdate,
    PurchaseEmailMessageUpdate,
    PurchaseEmailMessageResponse,
    PurchaseEmailSendResponse,
    PurchaseMonitoringCallbackResponse,
    PurchaseInboundMessageResponse,
    PurchaseResponseCandidateResponse,
    PurchaseInboundLinkPayload,
    PurchaseResponseCandidateDecisionResponse,
    PurchaseResponseExtractionResponse,
    PurchaseResponseExtractionReviewPayload,
    PurchaseResponseExtractionReviewResponse,
    PurchaseRFQCreate,
    PurchaseRFQResponse,
    PurchaseRFQSupplierCreate,
    PurchaseRFQSupplierResponse,
    RFQDraftResponse,
    PurchaseQuoteResponseCreate,
    PurchaseQuoteResponseResponse,
    PurchaseComparisonResponse,
    PurchasePriceEvidenceCreate,
    PurchasePriceEvidenceResponse,
    PurchasePriceHistoryResponse,
    PurchasePriceReferenceResponse,
    PurchasePriceSuggestionResponse,
    PurchasePriceSuggestionReview,
    PurchaseProductPriceFamilyResponse,
    PurchaseProductPriceUpdatePayload,
    PurchaseProductPriceUpdateResponse,
    PurchaseProductsPricesResponse,
    PurchaseCatalogItemDetailResponse,
    PurchaseCatalogSummaryResponse,
    PurchaseCatalogSyncResponse,
    PurchaseSupplierOfferUpdatePayload,
    PurchaseSupplierOffersResponse,
    PurchaseXlsxExportResponse,
    PurchaseXlsxReconciliationResponse,
    PurchaseXlsxSupplierContactPayload,
    PurchaseXlsxUpdatePricePayload,
    ChooseSupplierPayload,
)

router = APIRouter()
public_router = APIRouter()

# ---------------------------------------------------------------------------
# Central de Compras
# ---------------------------------------------------------------------------

@public_router.post("/monitoring/email/callback", response_model=PurchaseMonitoringCallbackResponse)
async def purchase_email_monitoring_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """Callback assinado usado pelo n8n/IMAP para registrar respostas de fornecedores."""
    raw_body = await request.body()
    status_code, payload = PurchasesService.process_monitoring_email_callback(db, raw_body, request.headers)
    response_payload = {}
    for key, value in payload.items():
        if isinstance(value, uuid.UUID):
            response_payload[key] = str(value)
        elif key == "candidate_ids":
            response_payload[key] = [str(item) for item in value]
        else:
            response_payload[key] = value
    return JSONResponse(status_code=status_code, content=response_payload)


@router.get("/overview", response_model=PurchasesOverviewResponse)
def get_purchases_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna a visao operacional da Central de Compras."""
    return PurchasesService.get_overview(db, current_user)


@router.get("/attention", response_model=List[PurchaseAttentionItemResponse])
def get_purchases_attention(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista situacoes reais que precisam de acao do responsavel por Compras."""
    return PurchasesService.get_attention(db, current_user, limit)


@router.get("/suggestions", response_model=List[PurchaseSuggestionResponse])
def get_purchase_suggestions(
    q: str,
    context: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sugere itens, codigos, historico e ativos conforme a pessoa digita."""
    return PurchasesService.suggest_purchases(db, q, context, current_user)


@router.post("/analyze", response_model=PurchaseAnalyzeResponse)
def analyze_purchase_need(
    payload: PurchaseAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Interpreta uma nova compra e salva apenas um rascunho revisavel."""
    return PurchasesService.analyze_purchase_need(db, payload, current_user)


@router.get("/needs", response_model=List[PurchaseRequestResponse])
def list_purchase_needs(
    queue_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Alias humano para listar necessidades/requisicoes de compra."""
    return PurchasesService.list_purchase_requests(db, current_user, queue_filter)


@router.post("/needs", response_model=PurchaseRequestResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_need(
    payload: PurchaseRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria uma necessidade de compra persistente usando o modelo de requisicao existente."""
    return PurchasesService.create_purchase_request(db, payload, current_user)


@router.post("/needs/parse-text", response_model=List[PurchaseQuoteParsedLine])
def parse_purchase_need_text(
    payload: PurchaseNeedParseTextPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analisa uma lista colada sem persistir dados antes da revisao humana."""
    return PurchasesService.parse_purchase_need_text(db, payload, current_user)


@router.post("/needs/import-link", response_model=PurchaseNeedImportPreviewResponse)
def preview_purchase_need_link(
    payload: PurchaseNeedImportLinkPayload,
    current_user: User = Depends(get_current_user),
):
    """Valida link externo e retorna limite operacional sem scraping fragil."""
    return PurchasesService.preview_purchase_need_link(payload, "external_link")


@router.post("/needs/import-cart", response_model=PurchaseNeedImportPreviewResponse)
def preview_purchase_need_cart(
    payload: PurchaseNeedImportCartPayload,
    current_user: User = Depends(get_current_user),
):
    """Valida link de carrinho e orienta revisao manual quando nao ha contrato real."""
    return PurchasesService.preview_purchase_need_link(payload, "external_cart")


@router.get("/needs/{request_id}", response_model=PurchaseRequestDetailResponse)
def get_purchase_need_detail(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Abre uma necessidade de compra persistente."""
    return PurchasesService.get_purchase_request(db, request_id, current_user)


@router.get("/external-search")
def external_search(
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Realiza a busca externa em provedores de shopping e mercado."""
    return PurchasesService.external_search(db, q, current_user)


@router.post("/items/{item_id}/options", response_model=PurchaseItemOptionResponse, status_code=status.HTTP_201_CREATED)
def add_item_option(
    item_id: uuid.UUID,
    payload: PurchaseItemOptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Adiciona uma opção de cotação/fornecimento para um item de compra."""
    return PurchasesService.add_item_option(db, item_id, payload, current_user)


@router.post("/items/{item_id}/research-sessions", response_model=PurchaseResearchSessionResponse)
def create_item_research_session(
    item_id: uuid.UUID,
    payload: PurchaseResearchSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria uma pesquisa persistente e progressiva para um item de compra."""
    return PurchasesService.create_item_research_session(db, item_id, payload, current_user)


@router.get("/research-sessions/{session_id}", response_model=PurchaseResearchSessionResponse)
def get_research_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna o estado persistido de uma pesquisa de compra."""
    return PurchasesService.get_research_session(db, session_id, current_user)


@router.post("/research-sessions/{session_id}/refresh", response_model=PurchaseResearchSessionResponse)
def refresh_research_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Continua ou atualiza uma pesquisa sem depender do estado local do navegador."""
    return PurchasesService.refresh_research_session(db, session_id, current_user)


@router.post("/research-sessions/{session_id}/cancel", response_model=PurchaseResearchSessionResponse)
def cancel_research_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancela uma pesquisa persistente ainda nao concluida."""
    return PurchasesService.cancel_research_session(db, session_id, current_user)


@router.post("/research-sessions/{session_id}/verify-offer", response_model=PurchaseResearchSessionResponse)
def verify_research_offer(
    session_id: uuid.UUID,
    option_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirma campos de uma oferta na fonte real quando tecnicamente possivel."""
    return PurchasesService.verify_research_offer(db, session_id, option_id, current_user)


@router.post("/options/{option_id}/revalidate", response_model=PurchaseItemOptionResponse)
def revalidate_purchase_option(
    option_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revalida uma opcao de compra e atualiza evidencias por campo."""
    return PurchasesService.revalidate_purchase_option(db, option_id, current_user)


@router.get("/items/{item_id}/recommendation", response_model=PurchaseRecommendationResponse)
def get_item_recommendation(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Gera recomendacao humana a partir de ofertas e evidencias confirmadas."""
    return PurchasesService.get_item_recommendation(db, item_id, current_user)


@router.post("/items/{item_id}/request-approval", response_model=PurchaseRequestResponse)
def request_item_approval(
    item_id: uuid.UUID,
    payload: PurchaseItemApprovalPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envia somente este item/opcao para aprovacao quando a pessoa escolher."""
    return PurchasesService.request_item_approval(db, item_id, payload, current_user)


@router.post("/items/{item_id}/prepare-supplier-rfq", response_model=PrepareSupplierRFQResponse)
def prepare_supplier_rfq_for_item(
    item_id: uuid.UUID,
    payload: PrepareSupplierRFQPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Prepara cotacao direta para fornecedores cadastrados de um item interno."""
    return PurchasesService.prepare_supplier_rfq_for_item(db, item_id, payload, current_user)


@router.post("/items/{item_id}/options/{option_id}/select", response_model=PurchaseItemResponse)
def select_item_option(
    item_id: uuid.UUID,
    option_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seleciona uma opção específica como vencedora para o item de compra."""
    return PurchasesService.select_item_option(db, item_id, option_id, current_user)


@router.get("/items/{item_id}/options", response_model=List[PurchaseItemOptionResponse])
def list_item_options(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista as opções de cotação/mercado cadastradas para um item."""
    return PurchasesService.list_item_options(db, item_id, current_user)


@router.patch("/items/{item_id}", response_model=PurchaseItemResponse)
def update_purchase_item(
    item_id: uuid.UUID,
    payload: PurchaseItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edita item enquanto ele ainda esta em revisao segura."""
    return PurchasesService.update_request_item(db, item_id, payload, current_user)


@router.delete("/items/{item_id}", response_model=PurchaseItemResponse)
def delete_purchase_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove item apenas quando ainda e um rascunho seguro."""
    return PurchasesService.delete_request_item(db, item_id, current_user)


@router.post("/items/{item_id}/split", response_model=PurchaseItemResponse)
def split_purchase_item(
    item_id: uuid.UUID,
    payload: PurchaseItemSplitPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Divide um item em dois enquanto a compra ainda esta em revisao."""
    return PurchasesService.split_request_item(db, item_id, payload, current_user)


@router.post("/items/merge", response_model=PurchaseItemResponse)
def merge_purchase_items(
    payload: PurchaseItemsMergePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Une itens duplicados enquanto a compra ainda esta em revisao."""
    return PurchasesService.merge_request_items(db, payload, current_user)


@router.patch("/needs/{request_id}", response_model=PurchaseRequestResponse)
def update_purchase_need(
    request_id: uuid.UUID,
    payload: PurchaseRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza uma necessidade de compra em rascunho."""
    return PurchasesService.update_purchase_request(db, request_id, payload, current_user)


@router.post("/needs/{request_id}/place-order", response_model=PurchaseRequestResponse)
def place_purchase_order(
    request_id: uuid.UUID,
    payload: PurchasePlaceOrderPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra o pedido de compra, seja gerando cotação vencedora ou compra de mercado externo."""
    return PurchasesService.place_order(db, request_id, payload, current_user)


@router.post("/needs/{request_id}/receive-delivery", response_model=PurchaseRequestResponse)
def receive_purchase_delivery(
    request_id: uuid.UUID,
    payload: PurchaseReceiveDeliveryPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registra o recebimento parcial ou integral da entrega e atualiza estoque/catálogo."""
    return PurchasesService.receive_delivery(db, request_id, payload, current_user)


@router.post("/orders", response_model=PurchaseRequestResponse)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Alias operacional para registrar pedido a partir da Central de Compras."""
    return PurchasesService.place_order(db, payload.request_id, payload, current_user)


@router.post("/deliveries", response_model=PurchaseRequestResponse)
def create_purchase_delivery(
    payload: PurchaseDeliveryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Alias operacional para registrar recebimento a partir da Central de Compras."""
    return PurchasesService.receive_delivery(db, payload.request_id, payload, current_user)


@router.get("/quotes", response_model=List[PurchaseRFQResponse])
def list_purchase_quotes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Alias operacional para listar cotacoes/RFQs em andamento."""
    return PurchasesService.list_rfqs(db, current_user)


@router.post("/quotes", response_model=PurchaseQuoteDetailResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_quote(
    payload: PurchaseQuoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria uma cotacao operacional em rascunho sem exigir aprovacao previa."""
    return PurchasesService.create_quote(db, payload, current_user)


@router.get("/quotes/{quote_id}", response_model=PurchaseQuoteDetailResponse)
def get_purchase_quote(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna a cotacao operacional usando o ID publico da RFQ."""
    return PurchasesService.get_quote_detail(db, quote_id, current_user)


@router.patch("/quotes/{quote_id}", response_model=PurchaseQuoteDetailResponse)
def update_purchase_quote(
    quote_id: uuid.UUID,
    payload: PurchaseQuoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.update_quote(db, quote_id, payload, current_user)


@router.post("/quotes/{quote_id}/items", response_model=PurchaseItemResponse, status_code=status.HTTP_201_CREATED)
def add_purchase_quote_item(
    quote_id: uuid.UUID,
    payload: PurchaseQuoteItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.add_quote_item(db, quote_id, payload, current_user)


@router.post("/quotes/{quote_id}/parse-list", response_model=List[PurchaseQuoteParsedLine])
def parse_purchase_quote_list(
    quote_id: uuid.UUID,
    payload: PurchaseQuoteParseListPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.parse_quote_list(db, quote_id, payload, current_user)


@router.get("/quotes/{quote_id}/supplier-suggestions", response_model=List[PurchaseQuoteSupplierSuggestion])
def get_purchase_quote_supplier_suggestions(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.supplier_suggestions(db, quote_id, current_user)


@router.post("/quotes/{quote_id}/supplier-selection", response_model=PurchaseQuoteDetailResponse)
def save_purchase_quote_supplier_selection(
    quote_id: uuid.UUID,
    payload: PurchaseQuoteSupplierSelectionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.save_supplier_selection(db, quote_id, payload, current_user)


@router.get("/quotes/{quote_id}/email-previews", response_model=List[PurchaseQuoteEmailPreview])
def get_purchase_quote_email_previews(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.email_previews(db, quote_id, current_user)


@router.post("/quotes/{quote_id}/email-previews/regenerate", response_model=List[PurchaseQuoteEmailPreview])
def regenerate_purchase_quote_email_previews(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.email_previews(db, quote_id, current_user)


@router.get("/quotes/{quote_id}/email-messages", response_model=List[PurchaseEmailMessageResponse])
def list_purchase_quote_email_messages(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.get_email_messages(db, quote_id, current_user)


@router.post("/quotes/{quote_id}/send", response_model=List[PurchaseEmailSendResponse])
def send_purchase_quote_messages(
    quote_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.send_quote(db, quote_id, current_user)


@router.get("/email-messages/{message_id}", response_model=PurchaseEmailMessageResponse)
def get_purchase_email_message(
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService._email_message_payload(PurchasesService.get_email_message(db, message_id, current_user))


@router.patch("/email-messages/{message_id}", response_model=PurchaseEmailMessageResponse)
def update_purchase_email_message(
    message_id: uuid.UUID,
    payload: PurchaseEmailMessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.update_email_message(db, message_id, payload, current_user)


@router.post("/email-messages/{message_id}/send", response_model=PurchaseEmailSendResponse)
def send_purchase_email_message(
    message_id: uuid.UUID,
    mode: str = "real",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.send_email_message(db, message_id, current_user, mode)


@router.get("/inbound-messages", response_model=List[PurchaseInboundMessageResponse])
def list_purchase_inbound_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.list_inbound_messages(db, current_user)


@router.get("/inbound-messages/{inbound_message_id}", response_model=PurchaseInboundMessageResponse)
def get_purchase_inbound_message(
    inbound_message_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService._inbound_payload(PurchasesService.get_inbound_message(db, inbound_message_id, current_user))


@router.post("/inbound-messages/{inbound_message_id}/link", response_model=PurchaseResponseCandidateResponse)
def link_purchase_inbound_message(
    inbound_message_id: uuid.UUID,
    payload: PurchaseInboundLinkPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.link_inbound_message(db, inbound_message_id, payload, current_user)


@router.get("/response-candidates", response_model=List[PurchaseResponseCandidateResponse])
def list_purchase_response_candidates(
    include_resolved: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.list_response_candidates(db, current_user, include_resolved=include_resolved)


@router.get("/response-candidates/{candidate_id}", response_model=PurchaseResponseCandidateResponse)
def get_purchase_response_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService._candidate_payload(PurchasesService.get_response_candidate(db, candidate_id, current_user))


@router.post("/response-candidates/{candidate_id}/confirm", response_model=PurchaseResponseCandidateDecisionResponse)
def confirm_purchase_response_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.decide_response_candidate(db, candidate_id, "confirm", current_user)


@router.post("/response-candidates/{candidate_id}/reject", response_model=PurchaseResponseCandidateDecisionResponse)
def reject_purchase_response_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.decide_response_candidate(db, candidate_id, "reject", current_user)


@router.post("/response-candidates/{candidate_id}/ignore", response_model=PurchaseResponseCandidateDecisionResponse)
def ignore_purchase_response_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.decide_response_candidate(db, candidate_id, "ignore", current_user)


@router.post("/response-candidates/{candidate_id}/extract", response_model=PurchaseResponseExtractionResponse)
def extract_purchase_response_candidate(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.create_response_extraction(db, candidate_id, current_user)


@router.get("/response-candidates/{candidate_id}/extraction", response_model=PurchaseResponseExtractionResponse)
def get_purchase_response_candidate_extraction(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.get_response_extraction_for_candidate(db, candidate_id, current_user)


@router.post("/response-extractions/{extraction_id}/review", response_model=PurchaseResponseExtractionReviewResponse)
def review_purchase_response_extraction(
    extraction_id: uuid.UUID,
    payload: PurchaseResponseExtractionReviewPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.review_response_extraction(db, extraction_id, payload, current_user)


@router.get("/monitoring/events")
def list_purchase_monitoring_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.list_monitoring_events(db, current_user)


@router.post("/stock-items/{stock_catalog_item_id}/quote-draft", status_code=status.HTTP_201_CREATED)
def create_purchase_quote_from_stock_item(
    stock_catalog_item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.create_quote_from_stock_item(db, stock_catalog_item_id, current_user)


@router.get("/sender-accounts", response_model=List[PurchaseSenderAccountResponse])
def list_purchase_sender_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.sender_accounts(db, current_user)


@router.get("/sender-accounts/{account_id}", response_model=PurchaseSenderAccountResponse)
def get_purchase_sender_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.get_sender_account(db, account_id, current_user)


@router.post("/sender-accounts", response_model=PurchaseSenderAccountResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_sender_account(
    payload: PurchaseSenderAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.create_sender_account(db, payload, current_user)


@router.patch("/sender-accounts/{account_id}", response_model=PurchaseSenderAccountResponse)
def update_purchase_sender_account(
    account_id: str,
    payload: PurchaseSenderAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.update_sender_account(db, account_id, payload, current_user)


@router.post("/sender-accounts/{account_id}/test", response_model=PurchaseSenderAccountResponse)
def test_purchase_sender_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.test_sender_account(db, account_id, current_user)


@router.post("/sender-accounts/{account_id}/disable", response_model=PurchaseSenderAccountResponse)
def disable_purchase_sender_account(
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchasesService.disable_sender_account(db, account_id, current_user)

# ---------------------------------------------------------------------------
# Fornecedores (Suppliers)
# ---------------------------------------------------------------------------

@router.get("/suppliers", response_model=List[SupplierResponse])
def list_suppliers(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna a lista de fornecedores ativos cadastrados."""
    return PurchasesService.list_suppliers(db, active_only)


@router.post("/suppliers", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cadastra um novo fornecedor. Requer permissão de MANAGER ou superior."""
    return PurchasesService.create_supplier(db, payload, current_user)


@router.patch("/suppliers/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza as informações de um fornecedor cadastrado. Requer MANAGER."""
    return PurchasesService.update_supplier(db, supplier_id, payload, current_user)


@router.delete("/suppliers/{supplier_id}", response_model=SupplierResponse)
def delete_supplier(
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Inativa o fornecedor informado. Requer MANAGER."""
    return PurchasesService.delete_supplier(db, supplier_id, current_user)


# ---------------------------------------------------------------------------
# Requisições de Compra (Purchase Requests)
# ---------------------------------------------------------------------------

@router.get("/requests", response_model=List[PurchaseRequestResponse])
def list_purchase_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna a lista de requisições de compras cadastradas:
    - Gerentes de compras e administradores veem todas.
    - Usuários comuns veem apenas as requisições que abriram.
    """
    return PurchasesService.list_purchase_requests(db, current_user)


@router.get("/requests/by-idempotency/{key}", response_model=PurchaseIdempotencyLookupResponse)
def get_purchase_request_by_idempotency(
    key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulta uma criacao por chave idempotente depois de timeout ou duplo clique."""
    return PurchasesService.get_purchase_request_by_idempotency_key(db, key, current_user)


@router.get("/requests/{request_id}", response_model=PurchaseRequestDetailResponse)
def get_purchase_request_detail(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca detalhes completos de uma requisição de compras, incluindo cotações e log de atividades."""
    return PurchasesService.get_purchase_request(db, request_id, current_user)


@router.post("/requests", response_model=PurchaseRequestResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_request(
    payload: PurchaseRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria uma nova requisição de compras com múltiplos itens. Começa como DRAFT."""
    return PurchasesService.create_purchase_request(db, payload, current_user)


@router.patch("/requests/{request_id}", response_model=PurchaseRequestResponse)
def update_purchase_request(
    request_id: uuid.UUID,
    payload: PurchaseRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Edita dados básicos de uma requisição. Apenas permitido se estiver em DRAFT."""
    return PurchasesService.update_purchase_request(db, request_id, payload, current_user)


@router.post("/requests/{request_id}/send-to-approval", response_model=PurchaseRequestResponse)
async def send_to_approval(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Envia a requisição para aprovação:
    - Menores de R$ 1.000,00 são auto-aprovadas (APPROVED).
    - Maiores criam uma solicitação de liberação financeira na Central de Aprovações (PENDING_APPROVAL).
    """
    return await PurchasesService.send_to_approval(db, request_id, current_user)


@router.post("/requests/{request_id}/cancel", response_model=PurchaseRequestResponse)
async def cancel_purchase_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancela a requisição de compras e qualquer aprovação pendente relacionada."""
    return await PurchasesService.cancel_purchase_request(db, request_id, current_user)


# ---------------------------------------------------------------------------
# Itens de Requisição
# ---------------------------------------------------------------------------

@router.post("/requests/{request_id}/items", response_model=PurchaseItemResponse, status_code=status.HTTP_201_CREATED)
def add_item_to_request(
    request_id: uuid.UUID,
    payload: PurchaseItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Adiciona um item a uma requisição em DRAFT."""
    return PurchasesService.add_item_to_request(db, request_id, payload, current_user)


@router.patch("/request-items/{item_id}", response_model=PurchaseItemResponse)
def update_request_item(
    item_id: uuid.UUID,
    payload: PurchaseItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Edita dados de um item específico de uma requisição em DRAFT."""
    return PurchasesService.update_request_item(db, item_id, payload, current_user)


@router.delete("/request-items/{item_id}", response_model=PurchaseItemResponse)
def delete_request_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove um item de uma requisição em DRAFT."""
    return PurchasesService.delete_request_item(db, item_id, current_user)


# ---------------------------------------------------------------------------
# RFQ Inteligente (PurchaseRFQ)
# ---------------------------------------------------------------------------

@router.post("/requests/{request_id}/rfqs", response_model=PurchaseRFQResponse, status_code=status.HTTP_201_CREATED)
def create_rfq(
    request_id: uuid.UUID,
    payload: PurchaseRFQCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria um processo de RFQ para a requisição informada."""
    return PurchasesService.create_rfq(db, request_id, payload, current_user)


@router.get("/rfqs", response_model=List[PurchaseRFQResponse])
def list_rfqs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista as RFQs ativas no sistema."""
    return PurchasesService.list_rfqs(db, current_user)


@router.get("/rfqs/{rfq_id}", response_model=PurchaseRFQResponse)
def get_rfq_detail(
    rfq_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna os detalhes de uma RFQ específica."""
    return PurchasesService.get_rfq(db, rfq_id, current_user)


@router.post("/rfqs/{rfq_id}/suppliers", response_model=PurchaseRFQSupplierResponse, status_code=status.HTTP_201_CREATED)
def add_supplier_to_rfq(
    rfq_id: uuid.UUID,
    payload: PurchaseRFQSupplierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Associa um fornecedor participante à RFQ."""
    return PurchasesService.add_supplier_to_rfq(db, rfq_id, payload, current_user)


@router.post("/rfqs/{rfq_id}/generate-drafts", response_model=List[PurchaseRFQSupplierResponse])
def generate_rfq_drafts(
    rfq_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Gera rascunhos de e-mails para cada fornecedor (sem envio real)."""
    return PurchasesService.generate_rfq_drafts(db, rfq_id, current_user)


@router.get("/rfqs/{rfq_id}/drafts", response_model=List[RFQDraftResponse])
def get_rfq_drafts(
    rfq_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista os rascunhos de e-mail gerados para a RFQ."""
    return PurchasesService.get_rfq_drafts(db, rfq_id, current_user)


@router.post("/rfqs/{rfq_id}/responses", response_model=PurchaseQuoteResponseResponse, status_code=status.HTTP_201_CREATED)
def create_quote_response(
    rfq_id: uuid.UUID,
    payload: PurchaseQuoteResponseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registra uma resposta/cotação recebida de um fornecedor participante."""
    return PurchasesService.create_quote_response(db, rfq_id, payload, current_user)


@router.get("/rfqs/{rfq_id}/comparison", response_model=PurchaseComparisonResponse)
def get_rfq_comparison(
    rfq_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calcula e retorna a comparação side-by-side dos fornecedores."""
    return PurchasesService.get_rfq_comparison(db, rfq_id, current_user)


@router.post("/rfqs/{rfq_id}/request-send-approval", response_model=dict)
def request_send_approval(
    rfq_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    """Compatibilidade: cotacao para fornecedor nao exige aprovacao formal."""
    return PurchasesService.request_send_approval(db, rfq_id, current_user)


@router.post("/rfqs/{rfq_id}/send", response_model=PurchaseRFQResponse)
def send_rfq_emails(
    rfq_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Envia as cotações aos fornecedores diretamente via SMTP (ou simula em testes)."""
    return PurchasesService.send_rfq_emails(db, rfq_id, current_user)


@router.post("/rfqs/{rfq_id}/suppliers/{supplier_id}/resend", response_model=PurchaseRFQSupplierResponse)
def resend_supplier_email(
    rfq_id: uuid.UUID,
    supplier_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reenvia o e-mail de cotação para um fornecedor específico."""
    return PurchasesService.resend_supplier_email(db, rfq_id, supplier_id, current_user)


@router.post("/rfqs/{rfq_id}/choose-supplier", response_model=PurchaseRequestResponse)
def choose_supplier(
    rfq_id: uuid.UUID,
    payload: ChooseSupplierPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Seleciona a proposta vencedora da RFQ e homologa os preços diretamente."""
    return PurchasesService.choose_supplier(db, rfq_id, payload.quote_response_id, current_user)



# ---------------------------------------------------------------------------
# Cotações Legadas (Quotations)
# ---------------------------------------------------------------------------

@router.post("/requests/{request_id}/quotations", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
def create_quotation(
    request_id: uuid.UUID,
    payload: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra a proposta de preço de um fornecedor para a requisição indicada.
    Permitido apenas se a requisição estiver APPROVED ou QUOTING. Requer MANAGER de compras.
    """
    return PurchasesService.create_quotation(db, request_id, payload, current_user)


@router.post("/requests/{request_id}/select-quotation/{quotation_id}", response_model=PurchaseRequestResponse)
async def select_quotation(
    request_id: uuid.UUID,
    quotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Seleciona a cotação vencedora para a requisição de compras.
    Status finalizado para ORDERED. Requer MANAGER de compras.
    """
    return await PurchasesService.select_quotation(db, request_id, quotation_id, current_user)


# ---------------------------------------------------------------------------
# Métricas / Dashboard
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=PurchasesSummaryResponse)
def get_purchases_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna estatísticas resumidas das compras para o dashboard e painéis."""
    return PurchasesService.get_summary(db, current_user)


# ---------------------------------------------------------------------------
# Rastreabilidade de Preços de Compra (Price Traceability)
# ---------------------------------------------------------------------------

@router.get("/products-prices", response_model=PurchaseProductsPricesResponse)
def list_products_prices(
    search: Optional[str] = None,
    limit: int = 80,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista familias e variacoes compraveis com preco atual, busca e paginacao."""
    return PurchasesService.get_products_prices(db, current_user, search, limit, offset)


@router.get("/products-prices/families/{family_id}", response_model=PurchaseProductPriceFamilyResponse)
def get_products_prices_family(
    family_id: uuid.UUID,
    search: Optional[str] = None,
    limit: int = 80,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Carrega as variacoes de uma familia sob demanda."""
    return PurchasesService.get_product_price_family(db, family_id, current_user, search, limit, offset)


@router.post("/products-prices/items/{item_id}/price", response_model=PurchaseProductPriceUpdateResponse)
def update_product_variation_price(
    item_id: uuid.UUID,
    payload: PurchaseProductPriceUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza o preco atual de uma variacao compravel especifica."""
    return PurchasesService.update_product_variation_price(db, item_id, payload, current_user)


@router.post("/catalog/sync-from-xlsx", response_model=PurchaseCatalogSyncResponse)
def sync_catalog_from_xlsx(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza o catalogo operacional usando a planilha real em modo somente leitura."""
    return PurchasesService.sync_catalog_from_xlsx(db, current_user)


@router.get("/catalog/summary", response_model=PurchaseCatalogSummaryResponse)
def get_catalog_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resumo rapido do catalogo de compras persistido no Portal."""
    return PurchasesService.get_catalog_summary(db, current_user)


@router.get("/catalog/families", response_model=PurchaseProductsPricesResponse)
def get_catalog_families(
    search: Optional[str] = None,
    limit: int = 80,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista categorias/familias do catalogo com busca tolerante e paginacao."""
    return PurchasesService.get_catalog_families(db, current_user, search, limit, offset)


@router.get("/catalog/families/{family_id}/variations", response_model=PurchaseProductPriceFamilyResponse)
def get_catalog_family_variations(
    family_id: uuid.UUID,
    search: Optional[str] = None,
    limit: int = 80,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Carrega variacoes compraveis de uma familia sob demanda."""
    return PurchasesService.get_catalog_family_variations(db, family_id, current_user, search, limit, offset)


@router.get("/catalog/items/{item_id}", response_model=PurchaseCatalogItemDetailResponse)
def get_catalog_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalhe de uma variacao compravel com ofertas e linhas de origem."""
    return PurchasesService.get_catalog_item(db, item_id, current_user)


@router.get("/catalog/items/{item_id}/supplier-offers", response_model=PurchaseSupplierOffersResponse)
def get_catalog_supplier_offers(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista fornecedores/precos cotados para uma variacao compravel."""
    return PurchasesService.get_catalog_supplier_offers(db, item_id, current_user)


@router.post("/catalog/items/{item_id}/supplier-offers/{offer_id}/update-price", response_model=PurchaseProductPriceUpdateResponse)
def update_catalog_supplier_offer_price(
    item_id: uuid.UUID,
    offer_id: uuid.UUID,
    payload: PurchaseSupplierOfferUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza o preco de uma oferta especifica e torna esse valor o preco atual da variacao."""
    return PurchasesService.update_catalog_supplier_offer_price(db, item_id, offer_id, payload, current_user)


@router.get("/xlsx-reconciliation", response_model=PurchaseXlsxReconciliationResponse)
def get_xlsx_reconciliation(
    search: Optional[str] = None,
    status_filter: str = "all",
    limit: int = 80,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confere a planilha Compras Nova.xlsx contra fornecedores, produtos e precos do Portal."""
    return PurchasesService.get_xlsx_reconciliation(db, current_user, search, status_filter, limit, offset)


@router.post("/xlsx-reconciliation/update-price", response_model=PurchaseProductPriceUpdateResponse)
def update_price_from_xlsx_reconciliation(
    payload: PurchaseXlsxUpdatePricePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza explicitamente o preco de uma variacao usando o valor conferido na planilha."""
    return PurchasesService.update_price_from_xlsx_reconciliation(db, payload, current_user)


@router.post("/xlsx-reconciliation/supplier-contact", response_model=SupplierResponse)
def update_supplier_contact_from_xlsx(
    payload: PurchaseXlsxSupplierContactPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Corrige email/telefone de fornecedor a partir da conferencia da planilha."""
    return PurchasesService.update_supplier_contact_from_xlsx(db, payload, current_user)


@router.post("/xlsx-reconciliation/export", response_model=PurchaseXlsxExportResponse)
def export_xlsx_reconciliation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta a conferencia da planilha para a pasta de relatórios de Compras."""
    return PurchasesService.export_xlsx_reconciliation(db, current_user)


@router.get("/prices/references", response_model=List[PurchasePriceReferenceResponse])
def list_price_references(
    product_item_id: Optional[uuid.UUID] = None,
    supplier_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista os preços de referência ativos cadastrados no sistema."""
    return PurchasesService.list_price_references(db, current_user, product_item_id, supplier_id)


@router.get("/prices/history", response_model=List[PurchasePriceHistoryResponse])
def list_price_history(
    product_item_id: Optional[uuid.UUID] = None,
    supplier_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todos os preços de compras históricos registrados."""
    return PurchasesService.list_price_history(db, current_user, product_item_id, supplier_id)


@router.get("/prices/suggestions", response_model=List[PurchasePriceSuggestionResponse])
def list_price_suggestions(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna a fila de sugestões de atualização de preço de referência."""
    return PurchasesService.list_price_suggestions(db, current_user, status)


@router.get("/prices/suggestions/{suggestion_id}", response_model=PurchasePriceSuggestionResponse)
def get_price_suggestion(
    suggestion_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Busca detalhes de uma sugestão de reajuste específica."""
    return PurchasesService.get_price_suggestion(db, suggestion_id, current_user)


@router.get("/prices/items/{item_id}/timeline", response_model=List[PurchasePriceHistoryResponse])
def get_item_price_timeline(
    item_id: uuid.UUID,
    limit: int = 40,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna a linha do tempo cronológica de flutuação de preço para determinado item."""
    return PurchasesService.get_item_price_timeline(db, item_id, current_user, limit, offset)


@router.post("/prices/evidences", response_model=PurchasePriceEvidenceResponse, status_code=status.HTTP_201_CREATED)
def create_price_evidence(
    payload: PurchasePriceEvidenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra uma nova evidência física de preço (Boleto, Nota Fiscal, Cotação).
    Calcula variações e gera automaticamente uma sugestão de reajuste pendente.
    """
    return PurchasesService.create_price_evidence(db, payload, current_user)


@router.post("/prices/suggestions/{suggestion_id}/approve", response_model=PurchasePriceSuggestionResponse)
def approve_price_suggestion(
    suggestion_id: uuid.UUID,
    payload: PurchasePriceSuggestionReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aprova a sugestão de reajuste, homologando o novo preço de referência ativo."""
    return PurchasesService.approve_price_suggestion(db, suggestion_id, payload.review_notes, current_user)


@router.post("/prices/suggestions/{suggestion_id}/reject", response_model=PurchasePriceSuggestionResponse)
def reject_price_suggestion(
    suggestion_id: uuid.UUID,
    payload: PurchasePriceSuggestionReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rejeita a sugestão de reajuste de preço de referência, informando justificativa."""
    return PurchasesService.reject_price_suggestion(db, suggestion_id, payload.review_notes, current_user)


# ---------------------------------------------------------------------------
# Administração e Limpeza de Dados de Teste
# ---------------------------------------------------------------------------

@router.post("/admin/test-data/preview")
def preview_test_data_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Preview de todos os registros de teste e rascunhos que podem ser limpos."""
    return PurchasesService.preview_test_data(db, current_user)


@router.post("/admin/test-data/purge")
def purge_test_data_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Exclui fisicamente do banco de dados os registros de teste permitidos."""
    return PurchasesService.purge_test_data(db, current_user)
