"""Testes unitários do classificador global e máquina de estados ParserContext."""
import pytest

from app.modules.stock.measure_utils import (
    StringClassification,
    classify_string,
    humanize_product_name,
    is_invalid_product_name,
)
from app.modules.stock.parser_context import ParserContext, is_attribute_only, is_navigation_product


class TestClassifyString:
    def test_weight_not_product(self):
        assert classify_string("39,65 kg/m") == StringClassification.WEIGHT
        assert is_invalid_product_name("39,65 kg/m")

    def test_unit_not_product(self):
        assert classify_string("kg/m") == StringClassification.WEIGHT
        assert classify_string("metro") == StringClassification.UNIT

    def test_dimension_not_product(self):
        assert classify_string("2 x 1,25 m") == StringClassification.DIMENSION
        assert is_invalid_product_name("2 x 1,25 m")

    def test_thickness_not_product(self):
        assert classify_string("2 mm") == StringClassification.THICKNESS
        assert classify_string('3/16"') == StringClassification.THICKNESS

    def test_length_group(self):
        assert classify_string("2 m") == StringClassification.LENGTH_GROUP
        assert classify_string("3 m") == StringClassification.LENGTH_GROUP

    def test_technical_code_not_product(self):
        assert classify_string("F304") == StringClassification.TECHNICAL_CODE
        assert classify_string("F316L") == StringClassification.TECHNICAL_CODE

    def test_application_not_product(self):
        assert classify_string("P/Placa Equipamento") == StringClassification.APPLICATION_NOTE

    def test_header_quarantine(self):
        assert classify_string("Material / Descrição") == StringClassification.HEADER

    def test_formula_error_quarantine(self):
        assert classify_string("#NOME?") == StringClassification.FORMULA_ERROR

    def test_subtotal_quarantine(self):
        assert classify_string("Subtotal") == StringClassification.SUBTOTAL

    def test_valid_product_name(self):
        assert classify_string("Chapa Aço Inox 316 L") == StringClassification.PRODUCT_NAME
        assert not is_invalid_product_name("Chapa Aço Inox 316 L")

    def test_product_with_thickness(self):
        result = classify_string("Ch. Aço Inox 316 L - 2 mm")
        assert result == StringClassification.PRODUCT_NAME


class TestHumanizeProductName:
    def test_expands_abbreviations(self):
        assert "Chapa" in humanize_product_name("Ch. Aço Inox 316 L")
        assert "Galvanizado" in humanize_product_name("Tubo Galv. 2")


class TestParserContextSequential:
    def test_length_group_resets_weight(self):
        ctx = ParserContext()
        ctx.reset_on_length_group("2 m")
        ctx.apply_dimension("2 x 1,25 m")
        ctx.apply_weight("39,65 kg/m")
        assert ctx.last_valid_weight == "39,65 kg/m"

        ctx.reset_on_length_group("3 m")
        assert ctx.last_valid_weight is None
        assert ctx.last_valid_dimension is None

    def test_dimension_change_clears_weight(self):
        ctx = ParserContext()
        ctx.reset_on_length_group("2 m")
        ctx.apply_dimension("2 x 1,25 m")
        ctx.apply_weight("39,65 kg/m")

        ctx.apply_dimension("3 x 1,25 m")
        assert ctx.last_valid_weight is None

    def test_block_3m_gets_correct_weight(self):
        ctx = ParserContext()
        ctx.reset_on_length_group("2 m")
        ctx.apply_dimension("2 x 1,25 m")
        ctx.apply_weight("39,65 kg/m")

        ctx.reset_on_length_group("3 m")
        ctx.apply_dimension("3 x 1,25 m")
        ctx.apply_weight("59,48 kg/m")

        assert ctx.last_valid_weight == "59,48 kg/m"
        assert ctx.last_valid_dimension == "3 x 1,25 m"

    def test_physical_key_separates_dimensions(self):
        ctx_a = ParserContext()
        ctx_a.reset_on_length_group("2 m")
        ctx_a.apply_dimension("2 x 1,25 m")
        ctx_a.apply_weight("39,65 kg/m")

        ctx_b = ParserContext()
        ctx_b.reset_on_length_group("3 m")
        ctx_b.apply_dimension("3 x 1,25 m")
        ctx_b.apply_weight("59,48 kg/m")

        key_a = ctx_a.build_physical_key(
            sheet="Chapa e Tubo Inox",
            family="INOX",
            base_name="Chapa Aço Inox 316 L",
            variation_label="2 mm",
        )
        key_b = ctx_b.build_physical_key(
            sheet="Chapa e Tubo Inox",
            family="INOX",
            base_name="Chapa Aço Inox 316 L",
            variation_label="2 mm",
        )
        assert key_a != key_b

    def test_metadata_includes_weight_and_dimension(self):
        ctx = ParserContext()
        ctx.apply_thickness("2 mm")
        ctx.apply_dimension("2 x 1,22 m")
        ctx.apply_weight("38,64 kg/m")
        meta = ctx.metadata_for_item()
        assert meta["peso"] == "38,64 kg/m"
        assert meta["dimensao"] == "2 x 1,22 m"
        assert meta["espessura"] == "2 mm"

    def test_attribute_only_types(self):
        assert is_attribute_only(StringClassification.WEIGHT)
        assert is_attribute_only(StringClassification.DIMENSION)
        assert not is_attribute_only(StringClassification.PRODUCT_NAME)

    def test_navigation_classification_only_for_products(self):
        assert is_navigation_product(StringClassification.PRODUCT_NAME)
        assert not is_navigation_product(StringClassification.WEIGHT)
        assert not is_navigation_product(StringClassification.DIMENSION)
        assert not is_navigation_product(StringClassification.TECHNICAL_CODE)
