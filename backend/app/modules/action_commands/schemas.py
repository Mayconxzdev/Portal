import uuid
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ActionCommandParseRequest(BaseModel):
    text: str = Field(..., description="Texto livre a ser interpretado")
    source: str = Field(..., description="Origem do comando: chat, global_bar, etc.")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Contexto extra de tela (e.g. module, entity_id)")

class ActionCommandPrepareRequest(BaseModel):
    action_key: str = Field(..., description="Identificador único da ação")
    source: str = Field(..., description="Origem da chamada: module_button, card_menu, drawer, etc.")
    source_module: Optional[str] = Field(None, description="Módulo de origem")
    source_entity_type: Optional[str] = Field(None, description="Tipo de entidade de origem")
    source_entity_id: Optional[str] = Field(None, description="ID da entidade de origem")
    initial_data: Optional[Dict[str, Any]] = Field(default=None, description="Dados iniciais preenchidos pelo contexto")

class ActionCommandConfirmRequest(BaseModel):
    override_data: Optional[Dict[str, Any]] = Field(default=None, description="Dados enviados pelo usuário para preenchimento de campos faltantes ou reajustes")

class ActionCommandDraftRead(BaseModel):
    id: uuid.UUID
    user_id: int
    source: str
    source_module: Optional[str] = None
    source_entity_type: Optional[str] = None
    source_entity_id: Optional[str] = None
    raw_text: Optional[str] = None
    action_key: str
    intent_type: str
    module: str
    status: str
    extracted_data: Dict[str, Any]
    enriched_data: Dict[str, Any]
    missing_fields: Dict[str, Any] = {}
    preview: Dict[str, Any]
    risk_level: str
    requires_confirmation: bool
    requires_approval: bool
    target_action_type: str
    created_entity_type: Optional[str] = None
    created_entity_id: Optional[str] = None
    action_intent_id: Optional[uuid.UUID] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AvailableAction(BaseModel):
    action_key: str
    title: str
    description: str
    module: str
    risk_level: str
    target_entity_type: Optional[str] = None
