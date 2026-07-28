"""Máquina de estados sequencial para importação do catálogo de estoque."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.modules.stock.measure_utils import StringClassification, humanize_product_name


@dataclass
class ParserContext:
    """Contexto sequencial de bloco físico — evita herança cega entre seções."""

    last_valid_category: Optional[str] = None
    last_valid_product: Optional[str] = None
    last_valid_material: Optional[str] = None
    last_valid_thickness: Optional[str] = None
    last_valid_length_group: Optional[str] = None
    last_valid_dimension: Optional[str] = None
    last_valid_weight: Optional[str] = None
    last_valid_supplier: Optional[str] = None
    last_valid_price: Optional[float] = None
    current_section_type: Optional[str] = None
    current_block_context: Dict[str, Any] = field(default_factory=dict)
    pending_technical_code: Optional[str] = None
    pending_application: Optional[str] = None
    raw_source_text: Optional[str] = None

    def reset_on_family(self, category: Optional[str] = None) -> None:
        if category:
            self.last_valid_category = category
        self.last_valid_product = None
        self.last_valid_material = None
        self._reset_block()

    def reset_on_product(self, product: str, raw: Optional[str] = None) -> None:
        self.last_valid_product = humanize_product_name(product) or product
        self.raw_source_text = raw or product
        self._reset_block()

    def reset_on_length_group(self, value: str) -> None:
        self.last_valid_length_group = value.strip()
        self.last_valid_dimension = None
        self.last_valid_weight = None
        self.current_section_type = "length_block"
        self.current_block_context = {
            "length_group": self.last_valid_length_group,
            "product": self.last_valid_product,
            "thickness": self.last_valid_thickness,
        }

    def apply_dimension(self, value: str) -> None:
        self.last_valid_dimension = value.strip()
        self.last_valid_weight = None
        self.current_section_type = "dimension_spec"
        self.current_block_context = {
            **self.current_block_context,
            "dimension": self.last_valid_dimension,
            "length_group": self.last_valid_length_group,
            "weight": None,
        }

    def apply_weight(self, value: str) -> None:
        self.last_valid_weight = value.strip()
        self.current_block_context = {
            **self.current_block_context,
            "weight": self.last_valid_weight,
            "dimension": self.last_valid_dimension,
            "length_group": self.last_valid_length_group,
        }

    def apply_thickness(self, value: str) -> None:
        self.last_valid_thickness = value.strip()
        self.current_block_context = {
            **self.current_block_context,
            "thickness": self.last_valid_thickness,
        }

    def apply_technical_code(self, value: str) -> None:
        self.pending_technical_code = value.strip()

    def apply_application(self, value: str) -> None:
        self.pending_application = value.strip()

    def apply_supplier(self, supplier: Optional[str]) -> None:
        if supplier:
            self.last_valid_supplier = supplier

    def apply_price(self, price: Optional[float]) -> None:
        if price is not None and price > 0:
            self.last_valid_price = price

    def _reset_block(self) -> None:
        self.last_valid_thickness = None
        self.last_valid_length_group = None
        self.last_valid_dimension = None
        self.last_valid_weight = None
        self.pending_technical_code = None
        self.pending_application = None
        self.current_section_type = None
        self.current_block_context = {}

    def snapshot(self) -> Dict[str, Any]:
        return {
            "category": self.last_valid_category,
            "product": self.last_valid_product,
            "material": self.last_valid_material,
            "thickness": self.last_valid_thickness,
            "length_group": self.last_valid_length_group,
            "dimension": self.last_valid_dimension,
            "weight": self.last_valid_weight,
            "supplier": self.last_valid_supplier,
            "section_type": self.current_section_type,
            "technical_code": self.pending_technical_code,
            "application": self.pending_application,
        }

    def build_physical_key(
        self,
        *,
        sheet: str,
        family: str,
        base_name: str,
        variation_label: str = "",
        internal_code: str = "",
    ) -> str:
        parts = [
            sheet,
            family,
            base_name,
            self.last_valid_thickness or "",
            self.last_valid_length_group or "",
            self.last_valid_dimension or variation_label,
            self.last_valid_weight or "",
            internal_code,
        ]
        return "|".join(p.strip() for p in parts)

    def metadata_for_item(self) -> Dict[str, Any]:
        meta: Dict[str, Any] = {}
        if self.last_valid_weight:
            meta["peso"] = self.last_valid_weight
        if self.last_valid_thickness:
            meta["espessura"] = self.last_valid_thickness
        if self.last_valid_dimension:
            meta["dimensao"] = self.last_valid_dimension
        if self.last_valid_length_group:
            meta["length_group"] = self.last_valid_length_group
        if self.pending_technical_code:
            meta["codigo_tecnico"] = self.pending_technical_code
        if self.pending_application:
            meta["aplicacao"] = self.pending_application
        if self.raw_source_text:
            meta["raw_name"] = self.raw_source_text
        return meta


# Tipos que nunca devem virar nó de navegação (product/variation principal)
NON_NAVIGATION_TYPES = {
    StringClassification.WEIGHT,
    StringClassification.UNIT,
    StringClassification.DIMENSION,
    StringClassification.THICKNESS,
    StringClassification.LENGTH_GROUP,
    StringClassification.TECHNICAL_CODE,
    StringClassification.APPLICATION_NOTE,
    StringClassification.HEADER,
    StringClassification.SUBTOTAL,
    StringClassification.FORMULA_ERROR,
    StringClassification.EMPTY,
    StringClassification.EMAIL,
    StringClassification.PHONE,
    StringClassification.CONTACT,
    StringClassification.PRICE,
    StringClassification.QUARANTINE_CANDIDATE,
    StringClassification.UNKNOWN,
}

QUARANTINE_TYPES = {
    StringClassification.HEADER,
    StringClassification.SUBTOTAL,
    StringClassification.FORMULA_ERROR,
    StringClassification.QUARANTINE_CANDIDATE,
}


def is_navigation_product(classification: str) -> bool:
    return classification in {
        StringClassification.PRODUCT_NAME,
        StringClassification.CATEGORY_HEADER,
    }


def is_attribute_only(classification: str) -> bool:
    return classification in {
        StringClassification.WEIGHT,
        StringClassification.DIMENSION,
        StringClassification.THICKNESS,
        StringClassification.LENGTH_GROUP,
        StringClassification.TECHNICAL_CODE,
        StringClassification.APPLICATION_NOTE,
        StringClassification.UNIT,
    }
