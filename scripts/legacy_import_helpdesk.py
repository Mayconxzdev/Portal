import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("vesper.legacy_importer.helpdesk")

DEFAULT_HELPDESK_DB = os.getenv("PORTAL_LEGACY_HELPDESK_DB", "")
SENSITIVE_KEYS = {"senha", "password", "passwd", "token", "secret", "api_key", "encryption_key"}


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, inner in value.items():
            if any(sensitive in str(key).lower() for sensitive in SENSITIVE_KEYS):
                sanitized[key] = "******"
            else:
                sanitized[key] = _sanitize_payload(inner)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    return value


def _fetch_table_rows(db_path: str, table: str) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        return [_sanitize_payload(dict(row)) for row in rows]


def _source_path_masked(db_path: str) -> str:
    path = Path(db_path)
    parts = path.parts
    if len(parts) <= 2:
        return db_path
    return os.path.join(parts[0], "...", path.name)


def extract_helpdesk_rows(db_path: str = DEFAULT_HELPDESK_DB) -> list[dict[str, Any]]:
    """
    Extrai dados reais do Helpdesk legado em modo somente leitura.

    Nao cria dados simulados e nao importa credenciais. Se a base real estiver
    vazia ou inacessivel, retorna lista vazia.
    """
    if not os.path.exists(db_path):
        logger.warning("Base real do Helpdesk nao encontrada: %s", _source_path_masked(db_path))
        return []

    rows_to_upload: list[dict[str, Any]] = []
    table_targets = {
        "tickets": "IT_TICKET",
        "estoque": "IT_ASSET",
        "anexos": "FILE_INDEX",
        "comentarios": "IT_TICKET_COMMENT",
        "historico": "IT_HISTORY",
        "clientes": "PERSON",
        "tags": "IT_TAG",
    }

    for table, entity_target in table_targets.items():
        try:
            rows = _fetch_table_rows(db_path, table)
        except sqlite3.Error as exc:
            logger.warning("Nao foi possivel ler a tabela %s do Helpdesk: %s", table, exc)
            continue

        logger.info("Helpdesk tabela %s: %s registros reais encontrados.", table, len(rows))
        for index, row in enumerate(rows, start=1):
            source_row_id = str(row.get("id") or row.get("codigo") or row.get("ticket_id") or index)
            rows_to_upload.append(
                {
                    "source_table_or_sheet": table,
                    "source_row_id": source_row_id,
                    "entity_target": entity_target,
                    "raw_data_json": row,
                    "confidence_score": 0.95,
                    "status": "PENDING_REVIEW",
                }
            )

    return rows_to_upload


def import_helpdesk(client, dry_run: bool):
    """
    Extrai dados reais do Helpdesk e envia ao staging quando autorizado.
    """
    db_path = os.getenv("LEGACY_HELPDESK_DB", DEFAULT_HELPDESK_DB)
    logger.info("Verificando base real de Helpdesk em %s", _source_path_masked(db_path))

    rows_to_upload = extract_helpdesk_rows(db_path)
    logger.info("Helpdesk: %s linhas reais preparadas para staging.", len(rows_to_upload))

    if dry_run:
        logger.info("===== DRY-RUN HELPDESK =====")
        for idx, row in enumerate(rows_to_upload[:10]):
            logger.info(
                "Linha %s: Target=%s | ID=%s | Tabela=%s",
                idx + 1,
                row["entity_target"],
                row["source_row_id"],
                row["source_table_or_sheet"],
            )
        if len(rows_to_upload) > 10:
            logger.info("... mais %s linhas reais extraidas.", len(rows_to_upload) - 10)
        if not rows_to_upload:
            logger.info("Nenhum registro real encontrado no Helpdesk para importar.")
        return

    if not rows_to_upload:
        logger.info("Nenhum registro real do Helpdesk para enviar ao staging.")
        return

    logger.info("Criando lote de staging no Portal...")
    batch_id = client.create_batch(
        source_app="HELPDESK",
        source_name="Base real de TI/Helpdesk",
        source_path_masked=_source_path_masked(db_path),
        module_target="it",
        notes="Importacao real de Helpdesk em staging, sem credenciais e sem dados simulados.",
    )

    logger.info("Fazendo upload de %s linhas de staging...", len(rows_to_upload))
    chunk_size = 50
    uploaded = 0
    for i in range(0, len(rows_to_upload), chunk_size):
        chunk = rows_to_upload[i : i + chunk_size]
        uploaded += client.upload_rows(batch_id, chunk)

    logger.info("Importacao de Helpdesk finalizada. %s linhas salvas no staging.", uploaded)
