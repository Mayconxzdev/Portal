import os
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger("vesper.legacy_importer.propostas")

def mask_path(path_str: str) -> str:
    """
    Mascara caminhos sensíveis do Windows para segurança.
    """
    if not path_str:
        return ""
    parts = list(os.path.split(path_str))
    if len(parts) >= 2:
        return os.path.join("K:\\...\\PropostasApp", parts[-1])
    return path_str

def get_file_hash(path: str) -> str:
    """
    Gera um hash md5 simples do arquivo para identificacao única.
    """
    try:
        hasher = hashlib.md5()
        with open(path, "rb") as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception:
        return ""

def import_propostas(client, dry_run: bool):
    """
    Importa arquivos, templates e propostas de uma fonte legada configurada.
    """
    logger.info("Executando adaptador de propostas legado...")
    
    base_dir = os.getenv("PORTAL_LEGACY_PROPOSTAS_DIR", "").strip()
    
    if not base_dir or not os.path.exists(base_dir):
        err_msg = "Fonte de propostas não configurada ou indisponível. Defina PORTAL_LEGACY_PROPOSTAS_DIR."
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)
        
    extensions = [".odt", ".docx", ".html", ".pdf"]
    
    rows = []
    
    try:
        # Varrer os arquivos recursivamente
        for root, dirs, files in os.walk(base_dir):
            if any(p in root for p in [".venv", ".git", "node_modules", "build", "dist", "__pycache__"]):
                continue
                
            for file_name in files:
                ext = os.path.splitext(file_name)[1].lower()
                if ext not in extensions:
                    continue
                    
                full_path = os.path.join(root, file_name)
                try:
                    stat = os.stat(full_path)
                    size_bytes = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    file_hash = get_file_hash(full_path)
                    
                    # Determinar categoria (TEMPLATE ou PROPOSAL_DOCUMENT)
                    is_template = "template" in file_name.lower() or "templates" in root.lower()
                    entity_target = "TEMPLATE" if is_template else "PROPOSAL_DOCUMENT"
                    
                    raw_data = {
                        "file_name": file_name,
                        "file_path": full_path,
                        "file_size": size_bytes,
                        "file_type": ext[1:].upper(),
                        "modified_at": mtime,
                        "file_hash": file_hash
                    }
                    
                    normalized = {
                        "file_name": file_name,
                        "file_path_masked": mask_path(full_path),
                        "file_type": ext[1:].upper(),
                        "file_size_bytes": size_bytes,
                        "category": "TEMPLATE" if is_template else "PROPOSAL",
                        "suggested_module": "proposals",
                        "tags": ["legado", "propostas"] if not is_template else ["legado", "templates"]
                    }
                    
                    rows.append({
                        "source_table_or_sheet": "files",
                        "source_row_id": file_hash or file_name,
                        "entity_target": entity_target,
                        "raw_data_json": raw_data,
                        "normalized_data_json": normalized,
                        "confidence_score": 1.0,
                        "status": "PENDING_REVIEW"
                    })
                except Exception as ex:
                    logger.warning(f"Erro ao processar metadados do arquivo {file_name}: {ex}")
                    
        logger.info(f"Detectados {len(rows)} arquivos/templates de propostas no legado.")
        
    except Exception as e:
        logger.error(f"Erro ao varrer arquivos de propostas: {e}")
        raise
        
    if dry_run:
        logger.info(f"===== DRY-RUN PROPOSTAS =====")
        logger.info(f"Extraidos {len(rows)} metadados de arquivos/templates reais.")
        if rows:
            logger.info(f"Exemplo do primeiro arquivo: {rows[0]['normalized_data_json']}")
    else:
        batch_id = client.create_batch(
            source_app="PROPOSTASAPP",
            source_name="Propostas App Real File Index Scan",
            source_path_masked="K:\\...\\PropostasApp",
            module_target="proposals",
            notes="Indexação real de templates e propostas legadas a partir de arquivos físicos."
        )
        uploaded = client.upload_rows(batch_id, rows)
        logger.info(f"Importacao de Propostas finalizada. {uploaded} arquivos reais salvos no staging.")
