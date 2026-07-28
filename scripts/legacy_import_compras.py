import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("vesper.legacy_importer.compras")

DEFAULT_COMPRAS_BASE = os.getenv("PORTAL_LEGACY_COMPRAS_DIR", "")
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


def _mask_path(path_str: str) -> str:
    path = Path(path_str)
    parts = path.parts
    if len(parts) <= 2:
        return path_str
    return os.path.join(parts[0], "...", path.name)


def _find_sqlite_sources(base_path: str) -> list[str]:
    if not os.path.exists(base_path):
        return []

    sources: list[str] = []
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d.lower() not in {".git", ".venv", "venv", "node_modules", "__pycache__"}]
        for filename in files:
            if Path(filename).suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
                sources.append(os.path.join(root, filename))
    return sorted(sources)


def _fetch_rows(db_path: str, table: str) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        return [_sanitize_payload(dict(row)) for row in rows]


def _table_names(db_path: str) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        return [row[0] for row in rows]


def _entity_target_for_table(table_name: str) -> str:
    lower = table_name.lower()
    if "supplier" in lower or "fornecedor" in lower:
        return "SUPPLIER"
    if "item" in lower or "produto" in lower:
        return "PRODUCT_ITEM"
    if "price" in lower or "preco" in lower:
        return "PRICE_HISTORY"
    if "workflow" in lower or "rfq" in lower:
        return "PURCHASE_OPERATIONAL_RECORD"
    return "PURCHASE_LEGACY_RECORD"


def extract_compras_rows(base_path: str = DEFAULT_COMPRAS_BASE) -> list[dict[str, Any]]:
    """
    Extrai dados reais de SQLite do ComprasApp2 em modo somente leitura.

    Nao cria fornecedor, produto ou historico de preco simulado. Se as bases
    reais estiverem vazias, retorna lista vazia.
    """
    sqlite_sources = _find_sqlite_sources(base_path)
    if not sqlite_sources:
        logger.warning("Nenhuma base SQLite real de Compras encontrada em %s", _mask_path(base_path))
        return []

    rows_to_upload: list[dict[str, Any]] = []
    for db_path in sqlite_sources:
        for table in _table_names(db_path):
            try:
                rows = _fetch_rows(db_path, table)
            except sqlite3.Error as exc:
                logger.warning("Nao foi possivel ler %s em %s: %s", table, _mask_path(db_path), exc)
                continue

            logger.info("Compras %s/%s: %s registros reais encontrados.", _mask_path(db_path), table, len(rows))
            for index, row in enumerate(rows, start=1):
                source_row_id = str(
                    row.get("id")
                    or row.get("supplier_id")
                    or row.get("supplier_key")
                    or row.get("item_id")
                    or row.get("rfq_id")
                    or index
                )
                rows_to_upload.append(
                    {
                        "source_table_or_sheet": f"{Path(db_path).name}:{table}",
                        "source_row_id": source_row_id,
                        "entity_target": _entity_target_for_table(table),
                        "raw_data_json": row,
                        "confidence_score": 0.9,
                        "status": "PENDING_REVIEW",
                    }
                )

    return rows_to_upload


def import_compras(client, dry_run: bool):
    """
    Extrai dados reais de Compras e envia ao staging quando autorizado.
    """
    base_path = os.getenv("LEGACY_COMPRAS_BASE", DEFAULT_COMPRAS_BASE)
    logger.info("Verificando fontes reais de Compras em %s", _mask_path(base_path))

    rows_to_upload = extract_compras_rows(base_path)
    logger.info("Compras: %s linhas reais preparadas para staging.", len(rows_to_upload))

    if dry_run:
        logger.info("===== DRY-RUN COMPRAS =====")
        for idx, row in enumerate(rows_to_upload[:10]):
            logger.info(
                "Linha %s: Target=%s | ID=%s | Origem=%s",
                idx + 1,
                row["entity_target"],
                row["source_row_id"],
                row["source_table_or_sheet"],
            )
        if len(rows_to_upload) > 10:
            logger.info("... mais %s linhas reais extraidas.", len(rows_to_upload) - 10)
        if not rows_to_upload:
            logger.info("Nenhum registro real encontrado em Compras para importar.")
        return

    if not rows_to_upload:
        logger.info("Nenhum registro real de Compras para enviar ao staging.")
        return

    logger.info("Criando lote de staging no Portal...")
    batch_id = client.create_batch(
        source_app="COMPRASAPP2",
        source_name="Bases reais SQLite do ComprasApp2",
        source_path_masked=_mask_path(base_path),
        module_target="purchases",
        notes="Importacao real de Compras em staging, sem dados simulados.",
    )

    logger.info("Fazendo upload de %s linhas de staging...", len(rows_to_upload))
    chunk_size = 50
    uploaded = 0
    for i in range(0, len(rows_to_upload), chunk_size):
        chunk = rows_to_upload[i : i + chunk_size]
        uploaded += client.upload_rows(batch_id, chunk)

    logger.info("Importacao de Compras finalizada. %s linhas salvas no staging.", uploaded)
