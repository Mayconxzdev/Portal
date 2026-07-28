import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger("vesper.legacy_importer.producao")

def import_producao(client, dry_run: bool):
    """
    Importa OPs e etapas de produção de um SQLite legado configurado.
    """
    logger.info("Executando adaptador de producao legado...")
    
    db_path = os.getenv("PORTAL_LEGACY_PRODUCAO_DB", "").strip()
    
    if not db_path or not os.path.exists(db_path):
        err_msg = "Fonte de produção não configurada ou indisponível. Defina PORTAL_LEGACY_PRODUCAO_DB."
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)
        
    try:
        conn = sqlite3.connect(db_path)
        # Permite acessar colunas por nome
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Obter todas as OPs
        cur.execute("SELECT * FROM ops")
        rows_db = cur.fetchall()
        
        logger.info(f"Detectadas {len(rows_db)} OPs no banco legada de Producao.")
        
        rows = []
        for r in rows_db:
            op_data = dict(r)
            
            # Normalização de dados
            normalized = {
                "numero_op": op_data.get("numero_op"),
                "empresa_grupo": op_data.get("empresa_grupo"),
                "cliente": op_data.get("cliente"),
                "modelo": op_data.get("modelo"),
                "quantidade": op_data.get("quantidade"),
                "data_inicio": op_data.get("data_inicio"),
                "data_entrega": op_data.get("data_entrega"),
                "status_geral": op_data.get("status_geral"),
                "percentual_pronto": op_data.get("percentual_pronto"),
                "pendencia_principal": op_data.get("pendencia_principal"),
                "observacao_geral": op_data.get("observacao_geral")
            }
            
            rows.append({
                "source_table_or_sheet": "ops",
                "source_row_id": str(op_data.get("numero_op") or op_data.get("id")),
                "entity_target": "PRODUCTION_OP",
                "raw_data_json": op_data,
                "normalized_data_json": normalized,
                "confidence_score": 1.0,
                "status": "PENDING_REVIEW"
            })
            
        conn.close()
        
    except Exception as e:
        logger.error(f"Erro ao ler banco de dados da Producao: {e}")
        raise
        
    if dry_run:
        logger.info(f"===== DRY-RUN PRODUCAO =====")
        logger.info(f"Extraidas {len(rows)} OPs reais do SQLite.")
        if rows:
            logger.info(f"Exemplo da primeira OP: {rows[0]['normalized_data_json']}")
    else:
        batch_id = client.create_batch(
            source_app="PRODUCAOAPP",
            source_name="Produção App Real SQLite Scan",
            source_path_masked="<configured legacy production database>",
            module_target="production",
            notes="Importação real de OPs a partir do SQLite legada da produção."
        )
        uploaded = client.upload_rows(batch_id, rows)
        logger.info(f"Importacao de Producao finalizada. {uploaded} OPs reais salvas no staging.")
