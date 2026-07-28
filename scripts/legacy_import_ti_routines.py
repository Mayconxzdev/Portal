import os
import re
import logging
import openpyxl
import argparse

logger = logging.getLogger("vesper.legacy_importer.ti_routines")

def mask_secrets_recursively(data):
    """
    Substitui recursivamente valores associados a senhas e chaves por '******'
    e adiciona a flag has_secret = True no dicionário se algum segredo for detectado.
    """
    if isinstance(data, dict):
        has_sec = False
        sanitized = {}
        for k, v in data.items():
            lower_k = k.lower()
            # Padrões para detecção de chaves/segredos
            if any(sub in lower_k for sub in ["senha", "password", "token", "secret", "key", "credential", "chave", "hash"]):
                sanitized[k] = "******"
                has_sec = True
            else:
                sanitized_val = mask_secrets_recursively(v)
                if isinstance(sanitized_val, dict) and sanitized_val.get("has_secret"):
                    has_sec = True
                sanitized[k] = sanitized_val
        if has_sec:
            sanitized["has_secret"] = True
        return sanitized
    elif isinstance(data, list):
        return [mask_secrets_recursively(item) for item in data]
    return data

def parse_sheet_informacao(sheet):
    """
    Aba Informação/Informaçao - ficha individual de um equipamento legado.
    Retorna uma lista de dicionários normalizados.
    """
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 22:
        return []
        
    # Extrai dados da ficha (baseados na inspeção estrutural)
    raw_data = {
        "user": str(rows[7][2]).strip() if rows[7][2] else "usuario_demo",
        "hostname": str(rows[8][2]).strip() if rows[8][2] else "",
        "ip": str(rows[9][2]).strip() if rows[9][2] else "",
        "anydesk_id": str(rows[11][2]).strip() if rows[11][2] else "",
        "anydesk_password": str(rows[11][3]).strip() if rows[11][3] else "",
        "cybersul_login": str(rows[12][2]).strip() if rows[12][2] else "",
        "cybersul_password": str(rows[12][3]).strip() if rows[12][3] else "",
        "nas_login": str(rows[13][2]).strip() if rows[13][2] else "",
        "nas_password": str(rows[13][3]).strip() if rows[13][3] else "",
        "fusion": str(rows[16][2]).strip() if rows[16][2] else "",
        "windows": str(rows[17][2]).strip() if rows[17][2] else "",
        "office": str(rows[18][2]).strip() if rows[18][2] else "",
        "eset": str(rows[19][2]).strip() if rows[19][2] else "",
        "certificate_expiry_primary": str(rows[20][2]).strip() if rows[20][2] else "",
        "certificate_expiry_secondary": str(rows[21][2]).strip() if rows[21][2] else "",
    }
    
    # Adiciona especificações físicas da aba
    specs = {}
    for idx in range(7, 21):
        if idx < len(rows) and rows[idx][5] and rows[idx][6]:
            key = str(rows[idx][5]).strip().replace(":", "")
            val = str(rows[idx][6]).strip()
            specs[key] = val
            
    raw_data["specifications"] = specs
    
    # Sanitiza segredos
    sanitized = mask_secrets_recursively(raw_data)
    
    return [{
        "source_row_id": "demo_asset_01",
        "entity_target": "IT_ASSET",
        "raw_data_json": raw_data,
        "normalized_data_json": sanitized,
        "confidence_score": 1.0,
        "status": "PENDING_REVIEW"
    }]

def parse_sheet_infos(sheet):
    """
    Aba Infos - Matriz de todos os computadores da rede (PC-01 a PC-15 ou mais)
    """
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 24:
        return []
        
    # Linha 7 tem os usuários (colunas 1 a 14)
    users = [str(x).strip() for x in rows[6][1:15] if x is not None]
    pcs = []
    
    # Linha 24 tem os códigos dos computadores (PC-01 a PC-14)
    # Vamos ler colunas 1 a 14 correspondentes
    for col_idx in range(1, 15):
        pc_id = str(rows[23][col_idx]).strip() if col_idx < len(rows[23]) and rows[23][col_idx] else f"PC-{col_idx:02d}"
        user = str(rows[6][col_idx]).strip() if col_idx < len(rows[6]) and rows[6][col_idx] else "Vago"
        hostname = str(rows[8][col_idx]).strip() if col_idx < len(rows[8]) and rows[8][col_idx] else ""
        
        # Reconstrói especificações
        specs = {}
        for r_idx in [10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22]:
            if r_idx < len(rows) and rows[r_idx][0] and rows[r_idx][col_idx]:
                key = str(rows[r_idx][0]).strip()
                val = str(rows[r_idx][col_idx]).strip()
                specs[key] = val
                
        raw_data = {
            "asset_code": pc_id,
            "assigned_user": user,
            "hostname": hostname,
            "specifications": specs
        }
        
        sanitized = mask_secrets_recursively(raw_data)
        
        pcs.append({
            "source_row_id": pc_id.lower(),
            "entity_target": "IT_ASSET",
            "raw_data_json": raw_data,
            "normalized_data_json": sanitized,
            "confidence_score": 1.0,
            "status": "PENDING_REVIEW"
        })
        
    return pcs

def parse_sheet_cabo_rede(sheet):
    """
    Aba Cabo-Rede - Mapeamento físico de portas de rede
    """
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 8:
        return []
        
    ports = []
    # Os cabeçalhos começam na linha 7, dados começam na linha 8
    for idx in range(7, len(rows)):
        row = rows[idx]
        if idx >= len(rows) or not any(x is not None for x in row[:6]):
            continue
            
        cable_id = str(row[0]).strip() if row[0] else "-"
        origin = str(row[1]).strip() if row[1] else "-"
        port = str(row[2]).strip() if row[2] else "-"
        user = str(row[3]).strip() if row[3] else "Vago"
        pc = str(row[4]).strip() if row[4] else "-"
        notes = str(row[5]).strip() if row[5] else ""
        
        # Ignora linhas de rodapé ou metadados extras
        if user == "Usuario" or cable_id == "ID do Cabo":
            continue
            
        raw_data = {
            "cable_id": cable_id,
            "origin_switch_rack": origin,
            "port": port,
            "assigned_user": user,
            "pc_code": pc,
            "notes": notes
        }
        
        sanitized = mask_secrets_recursively(raw_data)
        
        ports.append({
            "source_row_id": f"port_{port}_{pc}".replace(" ", "_").lower(),
            "entity_target": "IT_NETWORK_PORT",
            "raw_data_json": raw_data,
            "normalized_data_json": sanitized,
            "confidence_score": 0.9,
            "status": "PENDING_REVIEW"
        })
        
    return ports

def parse_sheet_ramais(sheet):
    """
    Aba Ramais - Mapeia ramais corporativos
    """
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 10:
        return []
        
    extensions = []
    current_sector = "Geral"
    
    # Lê a lista de ramais nas colunas 1 e 2
    for idx in range(9, len(rows)):
        row = rows[idx]
        if idx >= len(rows) or len(row) < 3:
            continue
            
        name = str(row[1]).strip() if row[1] else ""
        ext = str(row[2]).strip() if row[2] else ""
        
        if not name and not ext:
            continue
            
        # Detecta quebras de seção/setor
        if name and not ext:
            current_sector = name
            continue
            
        if name == "RAMAIS" or name == "Carla":
            # Pula cabeçalhos duplicados
            if name == "Carla" and ext == "200" and len(extensions) > 0:
                continue
                
        raw_data = {
            "name": name,
            "extension": ext,
            "sector": current_sector
        }
        
        sanitized = mask_secrets_recursively(raw_data)
        
        extensions.append({
            "source_row_id": f"ext_{ext}_{name}".replace(" ", "_").lower(),
            "entity_target": "IT_EXTENSION",
            "raw_data_json": raw_data,
            "normalized_data_json": sanitized,
            "confidence_score": 0.9,
            "status": "PENDING_REVIEW"
        })
        
    return extensions

def parse_sheet_anydesk(sheet):
    """
    Aba AnyDesk - Acessos remotos
    """
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 10:
        return []
        
    accesses = []
    # Cabeçalho na linha 9, dados começam na linha 10
    for idx in range(9, len(rows)):
        row = rows[idx]
        if idx >= len(rows) or not any(x is not None for x in row[1:6]):
            continue
            
        user = str(row[2]).strip() if row[2] else ""
        alias = str(row[3]).strip() if row[3] else ""
        anydesk_id = str(row[4]).strip() if row[4] else ""
        password = str(row[5]).strip() if row[5] else ""
        
        if not user and not anydesk_id:
            continue
            
        if user == "Nomes" or user == "PC":
            continue
            
        raw_data = {
            "user_name": user,
            "alias": alias,
            "anydesk_id": anydesk_id,
            "password": password
        }
        
        sanitized = mask_secrets_recursively(raw_data)
        
        accesses.append({
            "source_row_id": f"anydesk_{user}".replace(" ", "_").lower(),
            "entity_target": "IT_REMOTE_ACCESS",
            "raw_data_json": raw_data,
            "normalized_data_json": sanitized,
            "confidence_score": 0.95,
            "status": "PENDING_REVIEW"
        })
        
    return accesses

def parse_sheet_cybersul(sheet):
    """
    Aba Cybersul - Credenciais e contas do ERP Cybersul
    """
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 8:
        return []
        
    credentials = []
    # Dados de usuários começam na linha 8
    for idx in range(7, len(rows)):
        row = rows[idx]
        if idx >= len(rows) or len(row) < 3:
            continue
            
        user = str(row[0]).strip() if row[0] else ""
        login = str(row[1]).strip() if row[1] else ""
        password = str(row[2]).strip() if row[2] else ""
        
        if not user and not login:
            continue
            
        if user == "Usuario" or login == "Login":
            continue
            
        raw_data = {
            "user_name": user,
            "login": login,
            "password": password,
            "system": "Cybersul"
        }
        
        sanitized = mask_secrets_recursively(raw_data)
        
        credentials.append({
            "source_row_id": f"cyber_{login}".replace(" ", "_").lower(),
            "entity_target": "CREDENTIAL_METADATA",
            "raw_data_json": raw_data,
            "normalized_data_json": sanitized,
            "confidence_score": 0.95,
            "status": "PENDING_REVIEW"
        })
        
    # Extrai as credenciais genéricas das colunas 5 e 6
    for idx in range(7, len(rows)):
        row = rows[idx]
        if idx >= len(rows) or len(row) < 7:
            continue
        gen_login = str(row[5]).strip() if row[5] else ""
        gen_pass = str(row[6]).strip() if row[6] else ""
        
        if gen_login and gen_pass:
            raw_data = {
                "user_name": f"Generico_{gen_login}",
                "login": gen_login,
                "password": gen_pass,
                "system": "Cybersul"
            }
            sanitized = mask_secrets_recursively(raw_data)
            credentials.append({
                "source_row_id": f"cyber_gen_{gen_login}".lower(),
                "entity_target": "CREDENTIAL_METADATA",
                "raw_data_json": raw_data,
                "normalized_data_json": sanitized,
                "confidence_score": 0.95,
                "status": "PENDING_REVIEW"
            })
            
    return credentials

def parse_sheet_nas(sheet):
    """
    Aba NAS - Direitos e permissões de acesso ao NAS
    """
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 9:
        return []
        
    accesses = []
    # Linha 8 tem as pastas correspondentes
    folders = [str(x).strip() for x in rows[7][4:15] if x is not None]
    
    # Dados dos usuários começam na linha 9 até a 33
    for idx in range(8, min(33, len(rows))):
        row = rows[idx]
        if idx >= len(rows) or len(row) < 4:
            continue
            
        user = str(row[1]).strip() if row[1] else ""
        login = str(row[2]).strip() if row[2] else ""
        password = str(row[3]).strip() if row[3] else ""
        
        if not user and not login:
            continue
            
        # Mapeia permissões
        permissions = {}
        for col_idx in range(4, 15):
            if col_idx < len(row) and col_idx - 4 < len(folders):
                folder_name = folders[col_idx - 4]
                has_access = str(row[col_idx]).strip().upper() == "X"
                permissions[folder_name] = has_access
                
        raw_data = {
            "user_name": user,
            "login": login,
            "password": password,
            "permissions": permissions,
            "resource": "NAS_Vesper"
        }
        
        sanitized = mask_secrets_recursively(raw_data)
        
        accesses.append({
            "source_row_id": f"nas_{login}".replace(" ", "_").lower(),
            "entity_target": "NAS_ACCESS",
            "raw_data_json": raw_data,
            "normalized_data_json": sanitized,
            "confidence_score": 0.95,
            "status": "PENDING_REVIEW"
        })
        
    return accesses

def parse_sheet_certificados_programas(sheet):
    """
    Aba Certificados-Programas - Licenças de Software e Validade dos Certificados
    """
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 8:
        return []
        
    certificates = []
    # Dados começam na linha 8
    for idx in range(7, len(rows)):
        row = rows[idx]
        if idx >= len(rows) or not any(x is not None for x in row[:11]):
            continue
            
        pc = str(row[0]).strip() if row[0] else ""
        user = str(row[1]).strip() if row[1] else ""
        
        if not pc or pc == "Total" or pc.startswith("PC-") is False:
            continue
            
        raw_data = {
            "pc_code": pc,
            "user_name": user,
            "windows_license": str(row[2]).strip() if row[2] else "",
            "windows_version": str(row[3]).strip() if row[3] else "",
            "office_license": str(row[4]).strip() if row[4] else "",
            "office_year": str(row[5]).strip() if row[5] else "",
            "eset_installed": str(row[6]).strip() == "Sim",
            "vesper_certificate_expiry": str(row[7]).strip() if row[7] else "",
            "ventrio_certificate_expiry": str(row[8]).strip() if row[8] else "",
            "ip_address": str(row[9]).strip() if row[9] else "",
            "fusion_installed": str(row[10]).strip() == "Sim"
        }
        
        sanitized = mask_secrets_recursively(raw_data)
        
        certificates.append({
            "source_row_id": f"cert_{pc}".lower(),
            "entity_target": "IT_SOFTWARE_CERTIFICATE",
            "raw_data_json": raw_data,
            "normalized_data_json": sanitized,
            "confidence_score": 0.95,
            "status": "PENDING_REVIEW"
        })
        
    return certificates

def parse_sheet_emails(sheet):
    """
    Aba Emails - Acessos a contas de e-mail corporativo
    """
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 8:
        return []
        
    accounts = []
    # Cabeçalho na linha 7 tem os usuários que acessam (usuários e sistemas nas colunas 2 a 14)
    users = [str(x).strip() for x in rows[6][2:15] if x is not None]
    
    # Dados começam na linha 8
    for idx in range(7, len(rows)):
        row = rows[idx]
        if idx >= len(rows) or len(row) < 2:
            continue
            
        email = str(row[0]).strip() if row[0] else ""
        password = str(row[1]).strip() if row[1] else ""
        
        if not email or email == "Emails":
            continue
            
        # Remove ícones de status da planilha (como 🔴) no nome do e-mail
        email_clean = email.replace("🔴", "").replace("🟢", "").strip()
        
        # Filtra usuários designados
        assigned = []
        for col_idx in range(2, 15):
            if col_idx < len(row) and col_idx - 2 < len(users):
                user_name = users[col_idx - 2]
                if str(row[col_idx]).strip().upper() == "X":
                    assigned.append(user_name)
                    
        raw_data = {
            "email": email_clean,
            "password": password,
            "assigned_users": assigned,
            "account_type": "corporate_email"
        }
        
        sanitized = mask_secrets_recursively(raw_data)
        
        accounts.append({
            "source_row_id": f"email_{email_clean}".replace(".", "_").replace("@", "_").lower(),
            "entity_target": "EMAIL_ACCOUNT_ACCESS",
            "raw_data_json": raw_data,
            "normalized_data_json": sanitized,
            "confidence_score": 0.95,
            "status": "PENDING_REVIEW"
        })
        
    return accounts

def parse_sheet_impacta(sheet):
    """
    Aba Impacta - Central VOIP / Ramais IP
    """
    rows = list(sheet.iter_rows(values_only=True))
    if len(rows) < 9:
        return []
        
    accounts = []
    # Dados começam na linha 9 (Cabeçalho na linha 8: ['Usuario', 'Ramal Usuario', 'Senha Ramal', '', 'IP', 'PORTA'])
    for idx in range(8, len(rows)):
        row = rows[idx]
        if idx >= len(rows) or len(row) < 4:
            continue
            
        user = str(row[1]).strip() if row[1] else ""
        ext = str(row[2]).strip() if row[2] else ""
        password = str(row[3]).strip() if row[3] else ""
        ip = str(row[5]).strip() if len(row) > 5 and row[5] else ""
        port = str(row[6]).strip() if len(row) > 6 and row[6] else ""
        
        if not ext:
            continue
            
        if user == "Ramal Usuario" or ext == "Senha Ramal":
            continue
            
        raw_data = {
            "user_name": user or "Vago",
            "extension": ext,
            "password": password,
            "ip_address": ip,
            "port": port
        }
        
        sanitized = mask_secrets_recursively(raw_data)
        
        accounts.append({
            "source_row_id": f"voip_{ext}_{user}".replace(" ", "_").lower(),
            "entity_target": "VOIP_ACCOUNT",
            "raw_data_json": raw_data,
            "normalized_data_json": sanitized,
            "confidence_score": 0.95,
            "status": "PENDING_REVIEW"
        })
        
    return accounts

def import_ti_routines(client, dry_run: bool, file_path: str = None):
    """
    Importa os dados da planilha de TI para a área de staging.
    """
    if not file_path:
        file_path = os.getenv("PORTAL_LEGACY_TI_XLSM", "").strip()
    if not file_path:
        logger.error("Fonte de TI não configurada. Defina PORTAL_LEGACY_TI_XLSM ou informe file_path.")
        return

    logger.info(f"Iniciando leitura da planilha de TI: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"Planilha de TI nao encontrada: {file_path}")
        return
        
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    logger.info(f"Planilha carregada. Abas detectadas: {wb.sheetnames}")
    
    rows_to_upload = []
    
    # 1. Informação (ficha de equipamento)
    sheet_info_name = next((name for name in wb.sheetnames if "Informa" in name), None)
    if sheet_info_name:
        logger.info(f"Processando aba de Ficha de Maquina: {sheet_info_name}")
        rows = parse_sheet_informacao(wb[sheet_info_name])
        for r in rows:
            r["source_table_or_sheet"] = sheet_info_name
        rows_to_upload.extend(rows)
        
    # 2. Infos (Todos os computadores da rede)
    if "Infos" in wb.sheetnames:
        logger.info("Processando aba de Resumo de Computadores (Infos)")
        rows = parse_sheet_infos(wb["Infos"])
        for r in rows:
            r["source_table_or_sheet"] = "Infos"
        rows_to_upload.extend(rows)
        
    # 3. Cabo-Rede
    if "Cabo-Rede" in wb.sheetnames:
        logger.info("Processando aba de Cabo-Rede")
        rows = parse_sheet_cabo_rede(wb["Cabo-Rede"])
        for r in rows:
            r["source_table_or_sheet"] = "Cabo-Rede"
        rows_to_upload.extend(rows)
        
    # 4. Ramais
    if "Ramais" in wb.sheetnames:
        logger.info("Processando aba de Ramais")
        rows = parse_sheet_ramais(wb["Ramais"])
        for r in rows:
            r["source_table_or_sheet"] = "Ramais"
        rows_to_upload.extend(rows)
        
    # 5. AnyDesk
    if "AnyDesk" in wb.sheetnames:
        logger.info("Processando aba de AnyDesk")
        rows = parse_sheet_anydesk(wb["AnyDesk"])
        for r in rows:
            r["source_table_or_sheet"] = "AnyDesk"
        rows_to_upload.extend(rows)
        
    # 6. Cybersul
    if "Cybersul" in wb.sheetnames:
        logger.info("Processando aba de Cybersul")
        rows = parse_sheet_cybersul(wb["Cybersul"])
        for r in rows:
            r["source_table_or_sheet"] = "Cybersul"
        rows_to_upload.extend(rows)
        
    # 7. NAS
    if "NAS" in wb.sheetnames:
        logger.info("Processando aba de acessos NAS")
        rows = parse_sheet_nas(wb["NAS"])
        for r in rows:
            r["source_table_or_sheet"] = "NAS"
        rows_to_upload.extend(rows)
        
    # 8. Certificados-Programas
    if "Certificados-Programas" in wb.sheetnames:
        logger.info("Processando aba de Certificados e Programas")
        rows = parse_sheet_certificados_programas(wb["Certificados-Programas"])
        for r in rows:
            r["source_table_or_sheet"] = "Certificados-Programas"
        rows_to_upload.extend(rows)
        
    # 9. Emails
    if "Emails" in wb.sheetnames:
        logger.info("Processando aba de acessos a Emails")
        rows = parse_sheet_emails(wb["Emails"])
        for r in rows:
            r["source_table_or_sheet"] = "Emails"
        rows_to_upload.extend(rows)
        
    # 10. Impacta
    if "Impacta" in wb.sheetnames:
        logger.info("Processando aba de Central VoIP / Impacta")
        rows = parse_sheet_impacta(wb["Impacta"])
        for r in rows:
            r["source_table_or_sheet"] = "Impacta"
        rows_to_upload.extend(rows)
        
    logger.info(f"Processamento concluído. Total de {len(rows_to_upload)} linhas extraidas de TI.")
    
    if dry_run:
        logger.info("===== DRY-RUN TI ROUTINES =====")
        # Exibe um preview resumido e sanitizado das primeiras 10 linhas
        for idx, row in enumerate(rows_to_upload[:15]):
            logger.info(f"Linha {idx+1:02d}: Target={row['entity_target']} | ID={row['source_row_id']} | Normalizado={row['normalized_data_json']}")
        logger.info(f"... total de {len(rows_to_upload)} linhas processadas de forma segura.")
        
        # Gera o relatório local Markdown/JSON conforme o requisito
        report_path = r"scratch/ti_routines_dry_run_preview.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Relatório de Pré-visualização - Rotinas de TI (Staging)\n\n")
            f.write(f"Planilha de Origem: `{file_path}`\n")
            f.write(f"Total de Registros Higienizados: {len(rows_to_upload)}\n\n")
            f.write("## Resumo por Tipo de Entidade\n\n")
            
            # Conta os tipos
            counts = {}
            for r in rows_to_upload:
                counts[r["entity_target"]] = counts.get(r["entity_target"], 0) + 1
            for k, v in counts.items():
                f.write(f"* **{k}**: {v} registros\n")
                
            f.write("\n## Amostra Sanitizada de Registros (Primeiros 20)\n\n")
            f.write("| Aba de Origem | Tipo Entidade | ID Fonte | Dados Normalizados (Sanitizados) |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for r in rows_to_upload[:20]:
                norm_str = str(r["normalized_data_json"]).replace("{", "\\{").replace("}", "\\}")
                # Encurta string muito longa
                if len(norm_str) > 100:
                    norm_str = norm_str[:100] + "..."
                f.write(f"| {r['source_table_or_sheet']} | {r['entity_target']} | {r['source_row_id']} | `{norm_str}` |\n")
                
        logger.info(f"Relatório de pré-visualização salvo com sucesso em {report_path}")
    else:
        logger.info("Criando lote de staging de TI no Portal...")
        batch_id = client.create_batch(
            source_app="TI_ROUTINES_XLSM",
            source_name="RQ-CRT Controle de Rotinas de TI",
            source_path_masked=mask_secrets_recursively(file_path),
            module_target="it",
            notes="Importacao higienizada de computadores, ramais, acessos NAS, AnyDesk, emails e switches de TI."
        )
        
        logger.info(f"Fazendo upload de {len(rows_to_upload)} linhas para o lote {batch_id}...")
        chunk_size = 50
        uploaded = 0
        for i in range(0, len(rows_to_upload), chunk_size):
            chunk = rows_to_upload[i:i + chunk_size]
            uploaded += client.upload_rows(batch_id, chunk)
            
        logger.info(f"Importacao de TI finalizada. {uploaded} registros enviados para staging.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script para importação das rotinas de TI a partir da planilha XLSM.")
    parser.add_argument("--file", default=None, help="Caminho absoluto do arquivo .xlsm")
    parser.add_argument("--dry-run", action="store_true", help="Executar em modo preview sem enviar para a API")
    parser.add_argument("--url", default="http://localhost:8000", help="URL da API do Portal")
    parser.add_argument("--user", default="admin", help="Usuario de autenticacao")
    parser.add_argument("--password", default=os.getenv("PORTAL_ADMIN_PASSWORD", "portal-dev-only"), help="Senha local ou variável PORTAL_ADMIN_PASSWORD")
    
    args = parser.parse_args()
    
    # Execução autônoma de teste
    class DummyClient:
        def create_batch(self, **kwargs): return "dummy-uuid"
        def upload_rows(self, batch_id, rows): return len(rows)
        
    client = DummyClient()
    if not args.dry_run:
        from legacy_import_inventory import PortalLegacyClient
        client = PortalLegacyClient(args.url, args.user, args.password)
        if not client.login():
            print("Falha de autenticacao. Rodando em dry-run...")
            args.dry_run = True
            
    import_ti_routines(client, args.dry_run, args.file)
