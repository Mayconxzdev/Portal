import sys
import os
import shutil
import pytest
from pathlib import Path

# Adiciona o diretório scripts ao path do python para importação do script de inventário
SCRIPTS_DIR = Path(__file__).parents[2] / "scripts"
sys.path.append(str(SCRIPTS_DIR))

# Importa as funções que queremos testar do script
try:
    import legacy_purchases_inventory as lpi
except ImportError:
    # Fallback se rodado fora do contexto correto, apenas para evitar quebrar import no pytest discovery
    lpi = None

def test_lpi_import():
    assert lpi is not None, "O script legacy_purchases_inventory.py deve ser importável."

def test_normalize_cnpj_cpf():
    assert lpi.normalize_cnpj_cpf("12.345.678/0001-99") == "12345678000199"
    assert lpi.normalize_cnpj_cpf("123.456.789-00") == "12345678900"
    assert lpi.normalize_cnpj_cpf("   123-45  ") == "00000012345"  # Preenchimento com zeros
    assert lpi.normalize_cnpj_cpf(None) == ""
    assert lpi.normalize_cnpj_cpf(123456789) == "00123456789" # Preenche se numérico curto

def test_normalize_email():
    assert lpi.normalize_email(" COMERCIAL@DELL.COM.BR  ") == "comercial@fornecedor-hardware.example"
    assert lpi.normalize_email("invalido.com") == ""
    assert lpi.normalize_email(None) == ""

def test_normalize_name():
    assert lpi.normalize_name("  Dell    Computadores   Ltda ") == "Dell Computadores Ltda"
    assert lpi.normalize_name(None) == ""

def test_normalize_price():
    assert lpi.normalize_price("R$ 1.200,50") == 1200.50
    assert lpi.normalize_price("150,00") == 150.00
    assert lpi.normalize_price(350.25) == 350.25
    assert lpi.normalize_price(None) == 0.0
    assert lpi.normalize_price("invalido") == 0.0

def test_normalize_date():
    assert lpi.normalize_date("10/05/2026") == "2026-05-10"
    assert lpi.normalize_date("2026-05-12T00:00:00Z") == "2026-05-12"
    assert lpi.normalize_date(None) == ""
    assert lpi.normalize_date("data-invalida") == ""

def test_normalize_percentage():
    assert lpi.normalize_percentage("15%") == 0.15
    assert lpi.normalize_percentage("0,05") == 0.05
    assert lpi.normalize_percentage(0.12) == 0.12
    assert lpi.normalize_percentage(None) == 0.0

def test_mask_sensitive_data():
    # E-mail
    assert lpi.mask_email("vendas@fornecedor-hardware.example", redact=True) == "v****s@fornecedor-hardware.example"
    assert lpi.mask_email("comercial@fornecedor-hardware.example", redact=False) == "comercial@fornecedor-hardware.example"
    assert lpi.mask_email(None, redact=True) == ""
    
    # CNPJ
    assert lpi.mask_cnpj_cpf("72381189000110", redact=True) == "72.***.***/0001-10"
    assert lpi.mask_cnpj_cpf("72381189000110", redact=False) == "72381189000110"
    
    # Telefone
    assert lpi.mask_phone("0800 970 3355", redact=True) == "(08) ****-3355"
    assert lpi.mask_phone("11999998888", redact=True) == "(11) ****-8888"

def test_detect_duplicates():
    suppliers = [
        {"name": "Dell Computadores", "cnpj_cpf_normalized": "72381189000110", "email_normalized": "vendas@fornecedor-hardware.example"},
        {"name": "Dell Brasil", "cnpj_cpf_normalized": "72381189000110", "email_normalized": "suporte@fornecedor-hardware.example"}, # Mesmo CNPJ
        {"name": "Lenovo Brasil", "cnpj_cpf_normalized": "07851399000109", "email_normalized": "vendas@fornecedor-hardware.example"},
        {"name": "Lenovo Duplicado", "cnpj_cpf_normalized": "99999999000199", "email_normalized": "vendas@fornecedor-hardware.example"}, # Mesmo E-mail
        {"name": "Aços Inox Vesper", "cnpj_cpf_normalized": "12345678000199", "email_normalized": "carlos@acos.com"},
        {"name": "Aços Inox Vesper", "cnpj_cpf_normalized": "45678901000199", "email_normalized": "vendas@acos.com"} # Mesmo nome normalizado
    ]
    
    duplicates = lpi.detect_duplicates(suppliers)
    
    assert len(duplicates) == 3
    types = [d["type"] for d in duplicates]
    assert "CNPJ/CPF Duplicado" in types
    assert "E-mail Duplicado" in types
    assert "Nome Idêntico" in types

def test_synthetic_data_classification():
    data = lpi.create_synthetic_data()
    assert "Chapas e Insumos" in data
    assert "Fornecedores" in data
    assert "Histórico de Cotações" in data
    
    # Valida separação e classificação lógica
    items = data["Chapas e Insumos"]
    suppliers = data["Fornecedores"]
    quotes = data["Histórico de Cotações"]
    
    # Cadastro Mestre (Item e Fornecedor)
    assert len(items) == 5
    assert all("Código" in x and "Material" in x for x in items)
    assert len(suppliers) == 6
    assert all("Empresa" in x and "CNPJ" in x for x in suppliers)
    
    # Histórico Transacional (Cotações)
    assert len(quotes) == 3
    assert all("Preço Unitário (R$)" in x and "Fornecedor" in x for x in quotes)

def test_report_generation(tmp_path):
    output_dir = tmp_path / "legacy-purchases"
    
    # Executa o script principal apontando para o output temporário
    # Simula o CLI definindo os sys.argv
    test_args = [
        "legacy_purchases_inventory.py",
        "--output-dir", str(output_dir),
        "--dry-run",
        "--output-json",
        "--output-md"
    ]
    
    import unittest.mock
    with unittest.mock.patch("sys.argv", test_args):
        lpi.main()
        
    # Verifica a existência dos arquivos gerados no diretório temporário
    assert (output_dir / "LEGACY_PURCHASES_DATA_INVENTORY.md").exists()
    assert (output_dir / "LEGACY_PURCHASES_DATA_DICTIONARY.md").exists()
    assert (output_dir / "LEGACY_PURCHASES_IMPORT_PREVIEW_SAMPLE.json").exists()
    assert (output_dir / "legacy_purchases_inventory_sanitized.json").exists()
