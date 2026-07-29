import sys
import pytest
from pathlib import Path

# Adiciona o diretório scripts ao path do python para importação do script de rotinas de TI
SCRIPTS_DIR = Path(__file__).parents[2] / "scripts"
sys.path.append(str(SCRIPTS_DIR))

try:
    import legacy_import_ti_routines as lit
except ImportError:
    lit = None


class MockSheet:
    def __init__(self, rows):
        self.rows_data = rows

    def iter_rows(self, values_only=True):
        return self.rows_data


def create_mock_rows(size, col_count=20):
    return [[None] * col_count for _ in range(size)]


def test_lit_import():
    assert lit is not None, "O script legacy_import_ti_routines.py deve ser importável."


def test_mask_secrets_recursively():
    raw_data = {
        "user": "Operador Demo",
        "anydesk_password": "senha-super-secreta-123",
        "nested": {
            "token": "token-xyz",
            "normal_field": "ok"
        },
        "list_field": [
            {"password": "123", "label": "p1"},
            {"label": "p2"}
        ]
    }
    
    sanitized = lit.mask_secrets_recursively(raw_data)
    
    assert sanitized["anydesk_password"] == "******"
    assert sanitized["nested"]["token"] == "******"
    assert sanitized["nested"]["normal_field"] == "ok"
    assert sanitized["list_field"][0]["password"] == "******"
    assert sanitized["list_field"][0]["label"] == "p1"
    assert sanitized["list_field"][1]["label"] == "p2"
    assert sanitized.get("has_secret") is True
    assert sanitized["nested"].get("has_secret") is True
    assert sanitized["list_field"][0].get("has_secret") is True


def test_parse_sheet_informacao():
    # Cria uma lista de 25 linhas válidas
    rows = create_mock_rows(25, 20)
    
    # Define as células específicas usadas pelo parser
    rows[7][2] = "Operador Demo"
    rows[8][2] = "projeto2-william"
    rows[9][2] = "192.168.1.116"
    rows[11][2] = "1 991 498 866"
    rows[11][3] = "senha-anydesk"
    rows[12][2] = "operador.demo"
    rows[12][3] = "senha-cybersul"
    rows[13][2] = "operador.nas"
    rows[13][3] = "senha-nas"
    rows[16][2] = "Fusion-Sim"
    rows[17][2] = "Windows 10 Pro"
    rows[18][2] = "Office 2019"
    rows[19][2] = "ESET Sim"
    rows[20][2] = "2027-12-31"
    rows[21][2] = "2027-06-30"
    
    # Adiciona especificações físicas
    rows[7][5] = "Monitor:"
    rows[7][6] = "Dell 27"
    rows[8][5] = "Mouse:"
    rows[8][6] = "Logitech"
    
    sheet = MockSheet(rows)
    results = lit.parse_sheet_informacao(sheet)
    
    assert len(results) == 1
    row = results[0]
    assert row["entity_target"] == "IT_ASSET"
    assert row["source_row_id"] == "demo_asset_01"
    assert row["raw_data_json"]["user"] == "Operador Demo"
    assert row["raw_data_json"]["anydesk_password"] == "senha-anydesk"
    assert row["normalized_data_json"]["anydesk_password"] == "******"
    assert row["normalized_data_json"]["cybersul_password"] == "******"
    assert row["normalized_data_json"]["nas_password"] == "******"
    assert row["normalized_data_json"]["specifications"]["Monitor"] == "Dell 27"
    assert row["normalized_data_json"]["specifications"]["Mouse"] == "Logitech"
    assert row["normalized_data_json"].get("has_secret") is True


def test_parse_sheet_infos():
    rows = create_mock_rows(25, 20)
    
    # Linha 7 (index 6): Usuários
    rows[6][0] = "Usuario"
    rows[6][1] = "Operador Demo"
    rows[6][2] = "Clícia"
    rows[6][3] = "Laser"
    
    # Linha 9 (index 8): Hostnames
    rows[8][0] = "Hostname"
    rows[8][1] = "projeto2-william"
    rows[8][2] = "vendas3-clicia"
    rows[8][3] = "projeto-galvolaser"
    
    # Linha 24 (index 23): Códigos do PC
    rows[23][0] = "PC"
    rows[23][1] = "PC-01"
    rows[23][2] = "PC-02"
    rows[23][3] = "PC-03"
    
    # Especificações (Linhas 10 a 22, coluna 0 é o nome da spec)
    rows[10][0] = "Monitor"
    rows[10][1] = "Dell 27"
    rows[10][2] = "PHL 27"
    rows[10][3] = "Samsung 24"
    
    rows[11][0] = "Mouse"
    rows[11][1] = "Bom"
    rows[11][2] = "bom"
    rows[11][3] = "Logitech"
    
    sheet = MockSheet(rows)
    results = lit.parse_sheet_infos(sheet)
    
    # Ele processa 14 colunas (1 a 14) de computadores
    assert len(results) == 14
    
    # Testa os dados preenchidos das 3 primeiras colunas
    pc01 = results[0]
    assert pc01["source_row_id"] == "pc-01"
    assert pc01["entity_target"] == "IT_ASSET"
    assert pc01["normalized_data_json"]["asset_code"] == "PC-01"
    assert pc01["normalized_data_json"]["assigned_user"] == "Operador Demo"
    assert pc01["normalized_data_json"]["hostname"] == "projeto2-william"
    assert pc01["normalized_data_json"]["specifications"]["Monitor"] == "Dell 27"
    
    pc02 = results[1]
    assert pc02["normalized_data_json"]["asset_code"] == "PC-02"
    assert pc02["normalized_data_json"]["assigned_user"] == "Clícia"
    assert pc02["normalized_data_json"]["specifications"]["Mouse"] == "bom"


def test_parse_sheet_cabo_rede():
    # Dados começam na linha 8 (index 7)
    rows = create_mock_rows(15, 20)
    
    # Linha 8 (index 7)
    rows[7][0] = "1"
    rows[7][1] = "Switch 1"
    rows[7][2] = "Porta 1"
    rows[7][3] = "Operador Demo"
    rows[7][4] = "PC-01"
    rows[7][5] = "Ok"
    
    # Linha 9 (index 8)
    rows[8][0] = "2"
    rows[8][1] = "Switch 1"
    rows[8][2] = "Porta 2"
    rows[8][3] = "Vago"
    rows[8][4] = "PC-02"
    rows[8][5] = "Parado"
    
    sheet = MockSheet(rows)
    results = lit.parse_sheet_cabo_rede(sheet)
    
    # Note que no loop o range inicia em 7 (linha 8)
    assert len(results) == 2
    row1 = results[0]
    assert row1["entity_target"] == "IT_NETWORK_PORT"
    assert row1["source_row_id"] == "port_porta_1_pc-01"
    assert row1["normalized_data_json"]["cable_id"] == "1"
    assert row1["normalized_data_json"]["origin_switch_rack"] == "Switch 1"
    assert row1["normalized_data_json"]["port"] == "Porta 1"
    assert row1["normalized_data_json"]["assigned_user"] == "Operador Demo"
    assert row1["normalized_data_json"]["pc_code"] == "PC-01"


def test_parse_sheet_ramais():
    rows = create_mock_rows(20, 20)
    
    # Dados começam na linha 10 (index 9)
    rows[9][1] = "DIRETORIA"
    rows[9][2] = None
    
    rows[10][1] = "Operador Demo"
    rows[10][2] = "201"
    
    rows[11][1] = "William"
    rows[11][2] = "202"
    
    sheet = MockSheet(rows)
    results = lit.parse_sheet_ramais(sheet)
    
    assert len(results) == 2
    r0 = results[0]
    assert r0["entity_target"] == "IT_EXTENSION"
    assert r0["source_row_id"] == "ext_201_operador_demo"
    assert r0["normalized_data_json"]["name"] == "Operador Demo"
    assert r0["normalized_data_json"]["extension"] == "201"
    assert r0["normalized_data_json"]["sector"] == "DIRETORIA"


def test_parse_sheet_anydesk():
    rows = create_mock_rows(20, 20)
    
    # Dados começam na linha 10 (index 9)
    rows[9][1] = None
    rows[9][2] = "Operador Demo"
    rows[9][3] = "projeto2-william"
    rows[9][4] = "1991498866"
    rows[9][5] = "senha-qualquer"
    
    rows[10][1] = None
    rows[10][2] = "Juliana"
    rows[10][3] = "Juliana Vesper"
    rows[10][4] = "123456789"
    rows[10][5] = "outra-senha"
    
    sheet = MockSheet(rows)
    results = lit.parse_sheet_anydesk(sheet)
    
    assert len(results) == 2
    r0 = results[0]
    assert r0["entity_target"] == "IT_REMOTE_ACCESS"
    assert r0["source_row_id"] == "anydesk_operador_demo"
    assert r0["normalized_data_json"]["user_name"] == "Operador Demo"
    assert r0["normalized_data_json"]["anydesk_id"] == "1991498866"
    assert r0["normalized_data_json"]["password"] == "******"
    assert r0["normalized_data_json"].get("has_secret") is True


def test_parse_sheet_cybersul():
    rows = create_mock_rows(15, 20)
    
    # Dados começam na linha 8 (index 7)
    rows[7][0] = "Operador Demo"
    rows[7][1] = "operador.demo"
    rows[7][2] = "senha-cybersul-erp"
    rows[7][5] = "gen_login"
    rows[7][6] = "gen_pass"
    
    sheet = MockSheet(rows)
    results = lit.parse_sheet_cybersul(sheet)
    
    # 1 conta pessoal + 1 genérica
    assert len(results) == 2
    
    r0 = results[0]
    assert r0["entity_target"] == "CREDENTIAL_METADATA"
    assert r0["source_row_id"] == "cyber_operador.demo"
    assert r0["normalized_data_json"]["user_name"] == "Operador Demo"
    assert r0["normalized_data_json"]["login"] == "operador.demo"
    assert r0["normalized_data_json"]["password"] == "******"
    assert r0["normalized_data_json"]["system"] == "Cybersul"
    assert r0["normalized_data_json"].get("has_secret") is True
    
    r1 = results[1]
    assert r1["source_row_id"] == "cyber_gen_gen_login"
    assert r1["normalized_data_json"]["user_name"] == "Generico_gen_login"
    assert r1["normalized_data_json"]["login"] == "gen_login"
    assert r1["normalized_data_json"]["password"] == "******"


def test_parse_sheet_nas():
    rows = create_mock_rows(20, 20)
    
    # Pastas na linha 8 (index 7)
    rows[7][4] = "Diretoria"
    rows[7][5] = "Financeiro"
    rows[7][6] = "Suporte"
    
    # Usuários começam na linha 9 (index 8)
    rows[8][1] = "Operador Demo"
    rows[8][2] = "operador.nas"
    rows[8][3] = "senha-nas-123"
    rows[8][4] = "X"
    rows[8][5] = "X"
    rows[8][6] = ""
    
    sheet = MockSheet(rows)
    results = lit.parse_sheet_nas(sheet)
    
    assert len(results) == 1
    r0 = results[0]
    assert r0["entity_target"] == "NAS_ACCESS"
    assert r0["source_row_id"] == "nas_operador.nas"
    assert r0["normalized_data_json"]["user_name"] == "Operador Demo"
    assert r0["normalized_data_json"]["login"] == "operador.nas"
    assert r0["normalized_data_json"]["password"] == "******"
    assert r0["normalized_data_json"]["permissions"]["Diretoria"] is True
    assert r0["normalized_data_json"]["permissions"]["Financeiro"] is True
    assert r0["normalized_data_json"]["permissions"]["Suporte"] is False
    assert r0["normalized_data_json"].get("has_secret") is True


def test_parse_sheet_certificados_programas():
    rows = create_mock_rows(15, 20)
    
    # Dados de certificados/programas começam na linha 8 (index 7)
    rows[7][0] = "PC-01"
    rows[7][1] = "Operador Demo"
    rows[7][2] = "Pro"
    rows[7][3] = "Windows 10"
    rows[7][4] = "Sim"
    rows[7][5] = "2019"
    rows[7][6] = "Sim"
    rows[7][7] = "2027-12-31"
    rows[7][8] = "2027-06-30"
    rows[7][9] = "192.168.1.116"
    rows[7][10] = "Sim"
    
    sheet = MockSheet(rows)
    results = lit.parse_sheet_certificados_programas(sheet)
    
    assert len(results) == 1
    r0 = results[0]
    assert r0["entity_target"] == "IT_SOFTWARE_CERTIFICATE"
    assert r0["source_row_id"] == "cert_pc-01"
    assert r0["normalized_data_json"]["pc_code"] == "PC-01"
    assert r0["normalized_data_json"]["user_name"] == "Operador Demo"
    assert r0["normalized_data_json"]["windows_version"] == "Windows 10"
    assert r0["normalized_data_json"]["eset_installed"] is True
    assert r0["normalized_data_json"]["vesper_certificate_expiry"] == "2027-12-31"


def test_parse_sheet_emails():
    rows = create_mock_rows(15, 20)
    
    # Cabeçalho na linha 7 (index 6) tem os usuários que acessam
    rows[6][2] = "Operador Demo"
    rows[6][3] = "Clícia"
    rows[6][4] = "Financeiro"
    
    # Dados começam na linha 8 (index 7)
    rows[7][0] = "diretoria@portal.example"
    rows[7][1] = "senha-email-diretoria"
    rows[7][2] = "X"
    rows[7][3] = ""
    rows[7][4] = "X"
    
    sheet = MockSheet(rows)
    results = lit.parse_sheet_emails(sheet)
    
    assert len(results) == 1
    r0 = results[0]
    assert r0["entity_target"] == "EMAIL_ACCOUNT_ACCESS"
    assert r0["source_row_id"] == "email_diretoria_portal_example"
    assert r0["normalized_data_json"]["email"] == "diretoria@portal.example"
    assert r0["normalized_data_json"]["password"] == "******"
    assert r0["normalized_data_json"]["assigned_users"] == ["Operador Demo", "Financeiro"]
    assert r0["normalized_data_json"].get("has_secret") is True


def test_parse_sheet_impacta():
    rows = create_mock_rows(15, 20)
    
    # Dados começam na linha 9 (index 8)
    rows[8][1] = "Operador Demo"
    rows[8][2] = "201"
    rows[8][3] = "senha-voip"
    rows[8][5] = "192.168.1.200"
    rows[8][6] = "5060"
    
    sheet = MockSheet(rows)
    results = lit.parse_sheet_impacta(sheet)
    
    assert len(results) == 1
    r0 = results[0]
    assert r0["entity_target"] == "VOIP_ACCOUNT"
    assert r0["source_row_id"] == "voip_201_operador_demo"
    assert r0["normalized_data_json"]["user_name"] == "Operador Demo"
    assert r0["normalized_data_json"]["extension"] == "201"
    assert r0["normalized_data_json"]["password"] == "******"
    assert r0["normalized_data_json"]["ip_address"] == "192.168.1.200"
    assert r0["normalized_data_json"]["port"] == "5060"
    assert r0["normalized_data_json"].get("has_secret") is True
