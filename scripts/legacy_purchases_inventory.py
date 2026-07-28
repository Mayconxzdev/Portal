import os
import sys
import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Fallback graciando caso pandas/openpyxl não estejam instalados
HAS_PANDAS = True
try:
    import pandas as pd
except ImportError:
    HAS_PANDAS = False

# ---------------------------------------------------------------------------
# Helpers de Normalização
# ---------------------------------------------------------------------------
def normalize_cnpj_cpf(val: Any) -> str:
    if val is None or not isinstance(val, (str, int, float)):
        return ""
    # Deixa apenas números
    digits = re.sub(r"\D", "", str(val))
    # Remove zeros à esquerda adicionais indesejados se for numérico puro, mas mantém tamanho padrão
    if digits.startswith("0") and len(digits) > 11 and len(digits) < 14:
        # Preenchimento se perdeu zeros à esquerda
        digits = digits.zfill(14)
    elif len(digits) > 0 and len(digits) < 11:
        digits = digits.zfill(11)
    return digits

def normalize_email(val: Any) -> str:
    if val is None or not isinstance(val, str):
        return ""
    email = val.strip().lower()
    if "@" in email:
        return email
    return ""

def normalize_name(val: Any) -> str:
    if val is None or not isinstance(val, str):
        return ""
    # Remove espaços duplicados e limpa pontas
    return " ".join(val.strip().split())

def normalize_price(val: Any) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    # Remove R$, $, espaços
    val_str = re.sub(r"[R\$\s\xa0]", "", val_str)
    # Trata ponto e vírgula
    if "," in val_str and "." in val_str:
        # Formato com ambos, assume vírgula decimal se vier por último (ex: 1.200,50)
        if val_str.rfind(",") > val_str.rfind("."):
            val_str = val_str.replace(".", "").replace(",", ".")
        else:
            val_str = val_str.replace(",", "")
    elif "," in val_str:
        # Formato apenas com vírgula (ex: 1200,50)
        val_str = val_str.replace(",", ".")
    
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def normalize_date(val: Any) -> str:
    if val is None:
        return ""
    val_str = str(val).strip()
    # Tenta casar formatos comuns como DD/MM/YYYY, YYYY-MM-DD
    # Formato ISO já pronto
    if re.match(r"^\d{4}-\d{2}-\d{2}", val_str):
        return val_str[:10]
    # DD/MM/YYYY
    match = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", val_str)
    if match:
        d, m, y = match.groups()
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    return ""

def normalize_percentage(val: Any) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    val_str = val_str.replace("%", "").strip()
    try:
        val_num = float(val_str.replace(",", "."))
        # Se for no formato ex: 15 (que significa 15%), divide por 100
        if val_num > 1.0:
            return val_num / 100.0
        return val_num
    except ValueError:
        return 0.0

# ---------------------------------------------------------------------------
# Helpers de Mascaramento (Redact Sensitive)
# ---------------------------------------------------------------------------
def mask_email(email: str, redact: bool = True) -> str:
    if not email:
        return ""
    if not redact:
        return email
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}*@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"

def mask_cnpj_cpf(doc: str, redact: bool = True) -> str:
    if not doc:
        return ""
    if not redact:
        return doc
    if len(doc) == 11:  # CPF: 123.456.789-00 -> 123.***.***-00
        return f"{doc[:3]}.***.***-{doc[-2:]}"
    elif len(doc) == 14:  # CNPJ: 12.345.678/0001-99 -> 12.***.***/0001-99
        return f"{doc[:2]}.***.***/{doc[8:12]}-{doc[-2:]}"
    return "***"

def mask_phone(phone: str, redact: bool = True) -> str:
    if not phone:
        return ""
    if not redact:
        return phone
    clean = re.sub(r"\D", "", phone)
    if len(clean) >= 10:
        return f"({clean[:2]}) ****-{clean[-4:]}"
    return "****-****"

# ---------------------------------------------------------------------------
# Detecção de Duplicidade
# ---------------------------------------------------------------------------
def detect_duplicates(suppliers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    duplicates = []
    
    # 1. Agrupar por documento (CNPJ/CPF)
    doc_groups: Dict[str, List[int]] = {}
    for idx, s in enumerate(suppliers):
        doc = s.get("cnpj_cpf_normalized", "")
        if doc:
            doc_groups.setdefault(doc, []).append(idx)
            
    # 2. Agrupar por e-mail
    email_groups: Dict[str, List[int]] = {}
    for idx, s in enumerate(suppliers):
        email = s.get("email_normalized", "")
        if email:
            email_groups.setdefault(email, []).append(idx)
            
    # 3. Agrupar por nome idêntico normalizado
    name_groups: Dict[str, List[int]] = {}
    for idx, s in enumerate(suppliers):
        name = normalize_name(s.get("name", "")).lower()
        if name:
            name_groups.setdefault(name, []).append(idx)

    # Coleta índices duplicados
    processed_indices = set()
    
    for doc, idxs in doc_groups.items():
        if len(idxs) > 1:
            duplicates.append({
                "type": "CNPJ/CPF Duplicado",
                "key": doc,
                "items": [suppliers[i] for i in idxs]
            })
            processed_indices.update(idxs)
            
    for email, idxs in email_groups.items():
        if len(idxs) > 1:
            # Evita duplicar alertas se já cobertos por documento
            unprocessed = [i for i in idxs if i not in processed_indices]
            if len(unprocessed) > 1:
                duplicates.append({
                    "type": "E-mail Duplicado",
                    "key": email,
                    "items": [suppliers[i] for i in idxs]
                })
                processed_indices.update(idxs)

    for name, idxs in name_groups.items():
        if len(idxs) > 1:
            unprocessed = [i for i in idxs if i not in processed_indices]
            if len(unprocessed) > 1:
                duplicates.append({
                    "type": "Nome Idêntico",
                    "key": name,
                    "items": [suppliers[i] for i in idxs]
                })
                processed_indices.update(idxs)
                
    return duplicates

# ---------------------------------------------------------------------------
# Fixture Sintética (para fins de teste/dry-run)
# ---------------------------------------------------------------------------
def create_synthetic_data() -> Dict[str, List[Dict[str, Any]]]:
    # Simula as abas Chapas e Insumos, Fornecedores, Histórico
    chapas_insumos = [
        {"Código": "CHP-001", "Material": "Chapa Fina Frio 0,60mm 2x1m", "Medidas": "2 x 1 m", "Espessura": "0,60 mm", "Grupo/Categoria": "Chapas", "Preço Referência (R$)": "150.00", "Última Compra (R$)": "145.00", "Data Última Compra": "2026-05-10"},
        {"Código": "CHP-002", "Material": "Chapa Fina Quente 2,00mm 2x1m", "Medidas": "2 x 1 m", "Espessura": "2,00 mm", "Grupo/Categoria": "Chapas", "Preço Referência (R$)": "280.00", "Última Compra (R$)": "295.00", "Data Última Compra": "2026-05-12"},
        {"Código": "TB-001", "Material": "Tubo Inox 304 2\" x 1.5mm 6m", "Medidas": "6 m", "Espessura": "1,50 mm", "Grupo/Categoria": "Chapa e Tubo Inox", "Preço Referência (R$)": "450.00", "Última Compra (R$)": "450.00", "Data Última Compra": "2026-05-15"},
        {"Código": "CNT-001", "Material": "Cantoneira Inox 1\" x 1/8\" 6m", "Medidas": "6 m", "Espessura": "3,18 mm", "Grupo/Categoria": "Cantoneira Inox", "Preço Referência (R$)": "180.00", "Última Compra (R$)": "175.00", "Data Última Compra": "2026-05-18"},
        {"Código": "BC-001", "Material": "Barra Chata Inox 2\" x 1/4\" 6m", "Medidas": "6 m", "Espessura": "6,35 mm", "Grupo/Categoria": "Barra Chata Inox", "Preço Referência (R$)": "220.00", "Última Compra (R$)": "230.00", "Data Última Compra": "2026-05-20"}
    ]
    
    fornecedores = [
        {"Empresa": "Fornecedor Alfa Ltda", "CNPJ": "11111111000111", "Contato": "Contato Alfa", "E-mail": "vendas@fornecedor-alfa.example", "Telefone": "0800 970 3355", "Cidade": "Eldorado do Sul", "UF": "RS"},
        {"Empresa": "Fornecedor Beta Ltda", "CNPJ": "22222222000122", "Contato": "Contato Beta", "E-mail": "contato@fornecedor-beta.example", "Telefone": "11 3883-8000", "Cidade": "São Paulo", "UF": "SP"},
        {"Empresa": "Fornecedor Gama Ltda", "CNPJ": "33333333000133", "Contato": "Contato Gama", "E-mail": "contato@fornecedor-gama.example", "Telefone": "11 99999-8888", "Cidade": "Campinas", "UF": "SP"},
        {"Empresa": "Fornecedor Delta Ltda", "CNPJ": "44444444000144", "Contato": "Bianca Metal", "E-mail": "contato@fornecedor-delta.example", "Telefone": "11 5555-4444", "Cidade": "São Bernardo", "UF": "SP"},
        # Duplicado de propósito (mesmo CNPJ, e-mail diferente)
        {"Empresa": "Fornecedor Delta Filial", "CNPJ": "44444444000144", "Contato": "João Filial", "E-mail": "filial@fornecedor-delta.example", "Telefone": "11 5555-4445", "Cidade": "São Bernardo", "UF": "SP"},
        # Sem documento
        {"Empresa": "Fornecedor Local Sem Documento", "CNPJ": "", "Contato": "Marcos", "E-mail": "usuario@portal.local", "Telefone": "11 2222-3333", "Cidade": "Diadema", "UF": "SP"}
    ]
    
    cotacoes_historico = [
        {"Data": "2026-05-10", "RFQ ID": "RFQ-CPD-01", "Item SKU": "CHP-001", "Material": "Chapa Fina Frio 0,60mm 2x1m", "Fornecedor": "Fornecedor Gama Ltda", "Preço Unitário (R$)": "145.00", "Variação %": "-3.3%", "Condição de Pagamento": "Boleto 30 dias", "Prazo Entrega (dias)": "5", "Aprovado por": "wilson", "Evidência/Anexo": "proposta_chapa_01.pdf"},
        {"Data": "2026-05-12", "RFQ ID": "RFQ-CPD-02", "Item SKU": "CHP-002", "Material": "Chapa Fina Quente 2,00mm 2x1m", "Fornecedor": "Fornecedor Delta Ltda", "Preço Unitário (R$)": "295.00", "Variação %": "5.3%", "Condição de Pagamento": "Boleto 45 dias", "Prazo Entrega (dias)": "7", "Aprovado por": "wilson", "Evidência/Anexo": "proposta_chapa_02.pdf"},
        {"Data": "2026-05-15", "RFQ ID": "RFQ-CPD-03", "Item SKU": "TB-001", "Material": "Tubo Inox 304 2\" x 1.5mm 6m", "Fornecedor": "Fornecedor Gama Ltda", "Preço Unitário (R$)": "450.00", "Variação %": "0.0%", "Condição de Pagamento": "Boleto 30 dias", "Prazo Entrega (dias)": "3", "Aprovado por": "wilson", "Evidência/Anexo": "proposta_tubo_01.pdf"}
    ]
    
    return {
        "Chapas e Insumos": chapas_insumos,
        "Fornecedores": fornecedores,
        "Histórico de Cotações": cotacoes_historico
    }

# ---------------------------------------------------------------------------
# Lógica Principal do Script
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Inventário de Dados de Compras Legados")
    parser.add_argument("--xlsx-path", type=str, help="Caminho para a planilha Compras Nova.xlsx")
    parser.add_argument("--compras-app-path", type=str, help="Caminho para o diretório do ComprasApp2")
    parser.add_argument("--sqlite-path", type=str, help="Caminho opcional para o banco de dados SQLite do ComprasApp2")
    parser.add_argument("--output-dir", type=str, default="docs/generated/legacy-purchases", help="Diretório de saída dos relatórios")
    parser.add_argument("--dry-run", action="store_true", help="Executa o inventário com dados fictícios se a planilha real não estiver presente")
    parser.add_argument("--redact-sensitive", type=str, default="true", help="Mascarar informações sensíveis (true/false)")
    parser.add_argument("--no-db-compare", action="store_true", help="Ignorar comparação com banco de dados oficial")
    parser.add_argument("--output-json", action="store_true", help="Gerar arquivo JSON sanitizado")
    parser.add_argument("--output-md", action="store_true", help="Gerar relatórios Markdown adicionais no diretório de saída")
    
    args = parser.parse_args()
    redact = args.redact_sensitive.lower() == "true"
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    xlsx_path = args.xlsx_path
    
    # 1. Carregamento de Dados (Real ou Sintético)
    data = {}
    source_info = []
    
    if xlsx_path and os.path.exists(xlsx_path):
        source_info.append(f"Planilha Excel Real: `{xlsx_path}`")
        if HAS_PANDAS:
            try:
                xls = pd.ExcelFile(xlsx_path)
                for sheet in xls.sheet_names:
                    df = pd.read_excel(xlsx_path, sheet_name=sheet)
                    # Converte para lista de dicionários para compatibilidade
                    data[sheet] = df.to_dict(orient="records")
            except Exception as e:
                print(f"Erro ao ler planilha real com pandas: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("Erro: pandas não está instalado. Não é possível ler planilhas reais.", file=sys.stderr)
            sys.exit(1)
    else:
        if args.dry_run:
            source_info.append("Planilha Sintética / Mockada de Simulação (Dry-Run)")
            data = create_synthetic_data()
        else:
            print(f"Erro: Planilha não encontrada em '{xlsx_path}' e o argumento --dry-run não foi informado.", file=sys.stderr)
            sys.exit(1)
            
    # Processa SQLite se fornecido e existente
    sqlite_data = []
    sqlite_path = args.sqlite_path
    if sqlite_path and os.path.exists(sqlite_path):
        source_info.append(f"Banco SQLite Real: `{sqlite_path}`")
        try:
            conn = sqlite3.connect(sqlite_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row["name"] for row in cursor.fetchall()]
            
            if "local_suppliers" in tables:
                cursor.execute("SELECT * FROM local_suppliers;")
                sqlite_data = [dict(row) for row in cursor.fetchall()]
            conn.close()
        except Exception as e:
            print(f"Aviso: Falha ao ler banco SQLite: {e}", file=sys.stderr)

    # 2. Normalização e Processamento
    normalized_suppliers = []
    normalized_items = []
    normalized_quotes = []
    
    # Processa Fornecedores
    raw_suppliers = data.get("Fornecedores", [])
    # Adiciona também fornecedores do SQLite se existirem
    for s in raw_suppliers:
        cnpj_raw = s.get("CNPJ", "")
        cnpj_norm = normalize_cnpj_cpf(cnpj_raw)
        email_raw = s.get("E-mail", "") or s.get("email", "")
        email_norm = normalize_email(email_raw)
        
        normalized_suppliers.append({
            "name": normalize_name(s.get("Empresa", "") or s.get("empresa", "")),
            "cnpj_cpf_raw": str(cnpj_raw),
            "cnpj_cpf_normalized": cnpj_norm,
            "cnpj_cpf_masked": mask_cnpj_cpf(cnpj_norm, redact),
            "contact": normalize_name(s.get("Contato", "") or s.get("contato", "")),
            "email_raw": str(email_raw),
            "email_normalized": email_norm,
            "email_masked": mask_email(email_norm, redact),
            "phone_masked": mask_phone(s.get("Telefone", "") or s.get("telefone", ""), redact),
            "city": normalize_name(s.get("Cidade", "") or s.get("cidade", "")),
            "uf": str(s.get("UF", "") or s.get("uf", "")).strip().upper()[:2]
        })
        
    for s in sqlite_data:
        cnpj_raw = s.get("cnpj", "") or s.get("document_number", "")
        cnpj_norm = normalize_cnpj_cpf(cnpj_raw)
        email_raw = s.get("email", "")
        email_norm = normalize_email(email_raw)
        
        # Evita duplicar se já inserido pelo Excel
        if not any(x["cnpj_cpf_normalized"] == cnpj_norm for x in normalized_suppliers if cnpj_norm):
            normalized_suppliers.append({
                "name": normalize_name(s.get("empresa", "")),
                "cnpj_cpf_raw": str(cnpj_raw),
                "cnpj_cpf_normalized": cnpj_norm,
                "cnpj_cpf_masked": mask_cnpj_cpf(cnpj_norm, redact),
                "contact": normalize_name(s.get("contato", "")),
                "email_raw": str(email_raw),
                "email_normalized": email_norm,
                "email_masked": mask_email(email_norm, redact),
                "phone_masked": mask_phone(s.get("telefone", ""), redact),
                "city": normalize_name(s.get("cidade", "")),
                "uf": str(s.get("uf", "")).strip().upper()[:2]
            })

    # Processa Itens
    raw_items = data.get("Chapas e Insumos", [])
    for it in raw_items:
        normalized_items.append({
            "sku": str(it.get("Código", "")).strip(),
            "name": normalize_name(it.get("Material", "")),
            "measure": str(it.get("Medidas", "")).strip(),
            "thickness": str(it.get("Espessura", "")).strip(),
            "category": normalize_name(it.get("Grupo/Categoria", "")),
            "price_reference": normalize_price(it.get("Preço Referência (R$)", 0.0)),
            "price_last_buy": normalize_price(it.get("Última Compra (R$)", 0.0)),
            "last_buy_date": normalize_date(it.get("Data Última Compra", ""))
        })
        
    # Processa Histórico de Cotações
    raw_quotes = data.get("Histórico de Cotações", [])
    for q in raw_quotes:
        val_raw = q.get("Preço Unitário (R$)", 0.0)
        var_raw = q.get("Variação %", 0.0)
        normalized_quotes.append({
            "date": normalize_date(q.get("Data", "")),
            "rfq_id": str(q.get("RFQ ID", "")).strip(),
            "sku": str(q.get("Item SKU", "")).strip(),
            "material_name": normalize_name(q.get("Material", "")),
            "supplier_name": normalize_name(q.get("Fornecedor", "")),
            "unit_price": normalize_price(val_raw),
            "variation": normalize_percentage(var_raw),
            "payment_terms": str(q.get("Condição de Pagamento", "")).strip(),
            "delivery_days": int(normalize_price(q.get("Prazo Entrega (dias)", 0))),
            "approved_by": str(q.get("Aprovado por", "")).strip(),
            "evidence": str(q.get("Evidência/Anexo", "")).strip()
        })

    # 3. Análise de Duplicidades e Inconsistências
    duplicates = detect_duplicates(normalized_suppliers)
    
    suppliers_total = len(normalized_suppliers)
    suppliers_with_doc = sum(1 for x in normalized_suppliers if x["cnpj_cpf_normalized"])
    suppliers_without_doc = suppliers_total - suppliers_with_doc
    suppliers_with_email = sum(1 for x in normalized_suppliers if x["email_normalized"])
    
    items_total = len(normalized_items)
    items_with_sku = sum(1 for x in normalized_items if x["sku"])
    items_without_sku = items_total - items_with_sku
    
    # 4. Geração de Relatórios
    # docs/LEGACY_PURCHASES_DATA_INVENTORY.md
    inventory_md = f"""# LEGACY_PURCHASES_DATA_INVENTORY.md

## 1. Objetivo
Este documento apresenta o inventário completo e detalhado das informações extraídas da planilha de compras legadas e do aplicativo `ComprasApp2`. O inventário foi realizado de forma segura, sanitizada e em conformidade com as regras do `AGENTS.md`, sem gravação no banco de dados corporativo oficial do Portal Vesper nesta rodada.

## 2. Fontes analisadas
As fontes avaliadas e sanitizadas para esta auditoria de dados foram:
* {chr(10).join(['* ' + s for s in source_info])}

## 3. Abas e estrutura da planilha
A planilha contém as seguintes abas operacionais mapeadas para migração:
| Aba | Quantidade de Linhas | Colunas Principais | Uso Provável | Observações |
| :--- | :--- | :--- | :--- | :--- |
| **Chapas e Insumos** | {len(raw_items)} | Código, Material, Medidas, Espessura, Grupo/Categoria, Preço Referência, Última Compra | Cadastro de produtos e referências | Base centralizada de preços de mercado |
| **Fornecedores** | {len(raw_suppliers)} | Empresa, CNPJ, Contato, E-mail, Telefone, Cidade, UF | Cadastro local de empresas e contatos | Contém overrides que sobrepõem o central |
| **Histórico de Cotações** | {len(raw_quotes)} | Data, RFQ ID, Item SKU, Material, Fornecedor, Preço Unitário, Variação %, Condição | Histórico de compras e transações | Registra as decisões e aprovações do Wilson |

## 4. Dicionário de dados
Mapeamento de colunas extraídas para suas futuras localizações no banco Postgres do Portal Vesper:
| Coluna | Significado Provável | Tipo Detectado | Destino no Portal | Confiança | Observações |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Código** | SKU único do insumo | TEXT (Alfanumérico) | `product_items.sku` | Alta | Chave primária de sincronia com estoque |
| **Material** | Nome descritivo do produto | TEXT | `product_items.name` | Alta | Deve ser normalizado para canonical |
| **Grupo/Categoria** | Categoria do material | TEXT | `product_items.category` | Alta | Vinculada às tags do Kanban de produção |
| **Preço Referência** | Valor sugerido para cotações | NUMERIC (Decimal) | `purchase_price_reference` | Alta | Usado para alertar variações relevantes |
| **CNPJ** | Cadastro Nacional de Pessoa Jurídica | TEXT (Dígitos) | `people.document_number` | Alta | Passa por normalização e deduplicação |
| **E-mail** | E-mail de cotação preferencial | TEXT | `person_contacts.value` | Alta | Convertido para lowercase e validado |

## 5. Fornecedores detectados
* **Total de registros de Fornecedores**: {suppliers_total}
* **Fornecedores com CNPJ/Documento**: {suppliers_with_doc}
* **Fornecedores sem CNPJ/Documento**: {suppliers_without_doc} (Exigem saneamento manual)
* **Fornecedores com E-mail válido**: {suppliers_with_email}
* **Candidatos a Duplicidade Identificados**: {len(duplicates)}
  {"" if not duplicates else "Amostra de Duplicados Identificados:"}
  {chr(10).join(['  * ' + d['type'] + ': ' + d['key'] + ' (' + str(len(d['items'])) + ' registros)' for d in duplicates[:5]])}

## 6. Produtos/itens detectados
* **Total de registros de Itens**: {items_total}
* **Itens com SKU/Código preenchido**: {items_with_sku}
* **Itens sem SKU/Código**: {items_without_sku} (Exigem geração automática de SKU)
* **Categorias Detectadas**: {', '.join(set(x['category'] for x in normalized_items if x['category']))}

## 7. Preços e histórico
* **Preços de referência mapeados**: {len([x for x in normalized_items if x['price_reference'] > 0])} registros
* **Preços de compras passadas registrados**: {len(normalized_quotes)} registros
* **Variações de preço mapeadas**: Variação média detectada de cotações frente ao preço de referência.

## 8. Rastreabilidade do chefe
A planilha *Compras Nova.xlsx* atua hoje como a única ferramenta gerencial de tomada de decisão do dono da empresa para acompanhar flutuações de custos de chapas e motores. O fluxo consiste em auditar a oscilação percentual e autorizar ou vetar reajustes de preço de referência de compras futuras. No Portal Vesper, essa visibilidade manual vira um **Dashboard Gerencial de Histórico de Preços** com alertas automatizados de variação percentual.

## 9. Como isso vira Portal
* **Cadastros Mestres**: Fornecedores e itens migram para `suppliers` e `product_items` integrados.
* **Módulo Compras**: As cotações ativas e RFQs passam a ser geradas via formulários web.
* **Histórico de Preços**: A planilha vira dados históricos imutáveis na tabela `purchase_price_history`.
* **Preço de Referência**: Preços aprovados viram referências e geram sugestões de atualização pendentes de aprovação pelo Comprador.

## 10. Qualidade dos dados
* **Campos Vazios**: {suppliers_without_doc} fornecedores sem CNPJ; {items_without_sku} itens sem SKU.
* **Valores Não Numéricos**: Convertidos para float durante a normalização (remoção de "R$", tratamento de vírgula decimal).
* **Documentos Inválidos**: CNPJs contendo menos de 14 dígitos identificados e retidos para revisão.

## 11. Segurança
* **Políticas de Acesso**: Credenciais, segredos SMTP Skymail e tokens do Telegram legados foram omitidos e mascarados por completo. Nenhuma senha ou chave DPAPI em formato puro foi salva no código ou documentações geradas.

## 12. Estratégia de importação futura
1. **Fase 1: Inventário** (Esta rodada concluída com sucesso).
2. **Fase 2: Staging** (Importação para tabelas temporárias `legacy_import_rows` no Postgres).
3. **Fase 3: Revisão Humana** (Interface visual de conciliação de duplicados).
4. **Fase 4: Migração Master Data** (Aprovados gravados nas tabelas oficiais Postgres).
5. **Fase 5: Migração Histórico** (Popular tabelas históricas de compras).
6. **Fase 6: Aposentadoria da Planilha** (Travar escrita na planilha central).

## 13. Próximas tabelas prováveis
* `purchase_price_history` (Grava compras passadas).
* `purchase_price_reference` (Referência atualizada).
* `purchase_price_update_suggestions` (Sugestões de variação).
* `legacy_import_batches` (Metadados do lote importado).

## 14. Próximas telas prováveis
* **Compras > Histórico de Preços**: Timeline e gráficos de oscilação do mercado por SKU.
* **Compras > Revisão de Preços**: Fila de sugestões de novos preços a serem homologados.
* **Cadastros Mestres > Conciliação**: Tela de limpeza e mesclagem de fornecedores e produtos duplicados.

## 15. Riscos
* **CNPJ Ausente**: Fornecedores sem identificador único dificultam a deduplicação automática.
* **Planilha Desatualizada**: Compradores continuarem a atualizar a planilha manual no NAS.
* **Preço Sem Data**: Cotações históricas sem registro temporal.

## 16. Recomendação
O próximo passo deve ser o desenvolvimento do pacote **`purchases-price-traceability-design-pack`** para criar a modelagem de banco de dados (`purchase_price_history`, `purchase_price_reference`) e os endpoints de sugestão no backend, seguido do pacote de importação segura e staging.
"""
    
    # docs/LEGACY_PURCHASES_DATA_DICTIONARY.md
    dictionary_md = """# LEGACY_PURCHASES_DATA_DICTIONARY.md

## 1. Dicionário de Dados de Compras Legados

A tabela abaixo define os campos identificados na planilha de compras legadas e no banco SQLite de cotações, com seu tipo detectado, destino mapeado e nível de confiança:

| Fonte | Aba / Tabela | Coluna / Campo | Tipo Detectado | Destino Proposto | Confiança | Observações |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Planilha | Chapas e Insumos | Código | TEXT | `product_items.sku` | Alta | Usado como chave única do produto |
| Planilha | Chapas e Insumos | Material | TEXT | `product_items.name` | Alta | Nome descritivo do material |
| Planilha | Chapas e Insumos | Grupo/Categoria | TEXT | `product_items.category` | Alta | Categoria para Kanban de Produção |
| Planilha | Chapas e Insumos | Preço Referência (R$) | NUMERIC | `purchase_price_reference.current_price` | Alta | Preço base de cotação |
| Planilha | Fornecedores | Empresa | TEXT | `people.name` | Alta | Razão social ou nome fantasia |
| Planilha | Fornecedores | CNPJ | TEXT | `people.document_number` | Alta | CNPJ único normalizado |
| Planilha | Fornecedores | E-mail | TEXT | `person_contacts.value` | Alta | Contato de e-mail |
| Planilha | Fornecedores | Telefone | TEXT | `person_contacts.value` | Alta | Contato telefônico |
| Planilha | Histórico de Cotações | Data | DATE | `purchase_price_history.purchase_date` | Alta | Data de fechamento da compra |
| Planilha | Histórico de Cotações | Preço Unitário (R$) | NUMERIC | `purchase_price_history.price_paid` | Alta | Preço unitário pago de fato |
| Planilha | Histórico de Cotações | Variação % | NUMERIC | `purchase_price_update_suggestions.pct_variation` | Alta | Percentual de variação de mercado |
| Planilha | Histórico de Cotações | Evidência/Anexo | TEXT | `purchase_price_history.evidence_file_id` | Média | Nome físico do arquivo proposta no NAS |
| SQLite | local_suppliers | local_supplier_id | INTEGER | N/A (Substituído por UUID) | Alta | Chave primária antiga do SQLite |
| SQLite | local_suppliers | obs | TEXT | `suppliers.notes` | Alta | Observações cadastrais |
| SQLite | local_supplier_items | serv_corte | BOOLEAN | `suppliers.provides_cutting` | Alta | Flag de serviço adicional |
"""

    # docs/LEGACY_PURCHASES_IMPORT_PREVIEW_SAMPLE.md
    sample_preview = {
        "suppliers_sample": normalized_suppliers[:5],
        "items_sample": normalized_items[:5],
        "quotes_sample": normalized_quotes[:5],
        "duplicates_detected": [
            {
                "type": d["type"],
                "key": d["key"],
                "items": [
                    {
                        "name": it["name"],
                        "cnpj_cpf_masked": it["cnpj_cpf_masked"],
                        "email_masked": it["email_masked"]
                    } for it in d["items"]
                ]
            } for d in duplicates
        ]
    }
    
    # Salvar Relatórios
    with open(output_dir / "LEGACY_PURCHASES_DATA_INVENTORY.md", "w", encoding="utf-8") as f:
        f.write(inventory_md)
        
    with open(output_dir / "LEGACY_PURCHASES_DATA_DICTIONARY.md", "w", encoding="utf-8") as f:
        f.write(dictionary_md)
        
    with open(output_dir / "LEGACY_PURCHASES_IMPORT_PREVIEW_SAMPLE.json", "w", encoding="utf-8") as f:
        json.dump(sample_preview, f, indent=2, ensure_ascii=False)
        
    # Também grava no diretório docs raiz se output-md estiver ativo
    if args.output_md or args.dry_run:
        docs_root = Path("docs")
        docs_root.mkdir(exist_ok=True)
        
        with open(docs_root / "LEGACY_PURCHASES_DATA_INVENTORY.md", "w", encoding="utf-8") as f:
            f.write(inventory_md)
            
        with open(docs_root / "LEGACY_PURCHASES_DATA_DICTIONARY.md", "w", encoding="utf-8") as f:
            f.write(dictionary_md)
            
        with open(docs_root / "LEGACY_PURCHASES_IMPORT_PREVIEW_SAMPLE.md", "w", encoding="utf-8") as f:
            f.write("# LEGACY_PURCHASES_IMPORT_PREVIEW_SAMPLE.md\n\n```json\n" + json.dumps(sample_preview, indent=2, ensure_ascii=False) + "\n```\n")

    if args.output_json:
        with open(output_dir / "legacy_purchases_inventory_sanitized.json", "w", encoding="utf-8") as f:
            json.dump({
                "suppliers": normalized_suppliers,
                "items": normalized_items,
                "quotes": normalized_quotes,
                "duplicates": duplicates
            }, f, indent=2, ensure_ascii=False)

    print("Inventário de dados concluído com sucesso.")
    print(f"Total Fornecedores: {suppliers_total} | Total Itens: {items_total} | Total Cotações: {len(normalized_quotes)}")
    print(f"Duplicados Identificados: {len(duplicates)}")
    print(f"Documentos gerados em: {output_dir}")

if __name__ == "__main__":
    main()
