import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger("vesper.legacy_importer.projeto")

def import_projeto(client, dry_run: bool):
    """
    Importa projetos e tarefas de um SQLite legado configurado.
    """
    logger.info("Executando adaptador de projetos legado...")
    
    db_path = os.getenv("PORTAL_LEGACY_PROJETO_DB", "").strip()
    
    if not db_path or not os.path.exists(db_path):
        err_msg = "Fonte de projetos não configurada ou indisponível. Defina PORTAL_LEGACY_PROJETO_DB."
        logger.error(err_msg)
        raise FileNotFoundError(err_msg)
        
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Obter itens com seus respectivos status e responsaveis
        query = """
            SELECT 
                i.id, i.title, i.active, i.created_at, i.updated_at,
                s.name as status_name, s.color as status_color,
                u.full_name as responsible_name, u.username as responsible_username
            FROM items i
            LEFT JOIN board_statuses s ON i.status_id = s.id
            LEFT JOIN users u ON i.responsible_user_id = u.id
        """
        cur.execute(query)
        rows_db = cur.fetchall()
        
        logger.info(f"Detectados {len(rows_db)} itens de projeto no banco legada.")
        
        # Mapeamento de valores adicionais
        cur.execute("SELECT * FROM item_field_values")
        field_values = cur.fetchall()
        
        # Agrupa valores extras por item_id
        extras_by_item = {}
        for fv in field_values:
            item_id = fv["item_id"]
            if item_id not in extras_by_item:
                extras_by_item[item_id] = []
            
            # Pega o valor ativo
            val = None
            if fv["value_text"] is not None:
                val = fv["value_text"]
            elif fv["value_number"] is not None:
                val = float(fv["value_number"])
            elif fv["value_date"] is not None:
                val = fv["value_date"]
            elif fv["value_bool"] is not None:
                val = bool(fv["value_bool"])
            elif fv["value_percent"] is not None:
                val = float(fv["value_percent"])
                
            if val is not None:
                extras_by_item[item_id].append({
                    "field_id": fv["field_id"],
                    "value": val
                })
                
        rows = []
        for r in rows_db:
            item_data = dict(r)
            item_id = item_data["id"]
            
            # Acoplar valores customizados
            item_data["custom_fields"] = extras_by_item.get(item_id, [])
            
            normalized = {
                "title": item_data.get("title"),
                "status": item_data.get("status_name"),
                "status_color": item_data.get("status_color"),
                "responsible": item_data.get("responsible_name"),
                "created_at": item_data.get("created_at"),
                "updated_at": item_data.get("updated_at"),
                "active": bool(item_data.get("active"))
            }
            
            rows.append({
                "source_table_or_sheet": "items",
                "source_row_id": str(item_id),
                "entity_target": "PROJECT_TASK",
                "raw_data_json": item_data,
                "normalized_data_json": normalized,
                "confidence_score": 1.0,
                "status": "PENDING_REVIEW"
            })
            
        conn.close()
        
    except Exception as e:
        logger.error(f"Erro ao ler banco de dados de Projetos: {e}")
        raise
        
    if dry_run:
        logger.info(f"===== DRY-RUN PROJETOS =====")
        logger.info(f"Extraidos {len(rows)} itens de projeto reais do SQLite.")
        if rows:
            logger.info(f"Exemplo do primeiro item: {rows[0]['normalized_data_json']}")
    else:
        batch_id = client.create_batch(
            source_app="PROJETOAPP",
            source_name="Projeto App Real SQLite Scan",
            source_path_masked="K:\\...\\data\\kanban_operacional.db",
            module_target="projects",
            notes="Importação real de tarefas a partir do SQLite legada de projetos."
        )
        uploaded = client.upload_rows(batch_id, rows)
        logger.info(f"Importacao de Projetos finalizada. {uploaded} itens reais salvos no staging.")
