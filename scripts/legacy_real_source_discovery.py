#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Descoberta segura e somente leitura de fontes reais legadas do Portal Vesper.

O script inventaria bancos, planilhas, documentos, imagens, configuracoes e
anexos sem abrir conteudo sensivel e sem alterar os caminhos originais.
"""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SOURCES: dict[str, str] = {
    name: value
    for name, value in {
        "Compras": os.getenv("PORTAL_LEGACY_COMPRAS_DIR", ""),
        "Helpdesk": os.getenv("PORTAL_LEGACY_HELPDESK_DIR", ""),
        "Producao": os.getenv("PORTAL_LEGACY_PRODUCAO_DIR", ""),
        "Projeto": os.getenv("PORTAL_LEGACY_PROJETO_DIR", ""),
        "Propostas": os.getenv("PORTAL_LEGACY_PROPOSTAS_DIR", ""),
        "Rede": os.getenv("PORTAL_LEGACY_NETWORK_DIR", ""),
        "Local": os.getenv("PORTAL_LEGACY_LOCAL_DIR", ""),
    }.items()
    if value.strip()
}


EXTENSIONS: set[str] = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".xlsx",
    ".xlsm",
    ".xls",
    ".csv",
    ".ods",
    ".odt",
    ".doc",
    ".docx",
    ".pdf",
    ".html",
    ".htm",
    ".json",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".yaml",
    ".yml",
    ".log",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
}

SKIP_DIR_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    "playwright-report",
}

SENSITIVE_NAME_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.I), "<email>"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}[\s/_-]?\d{4}-?\d{2}\b"), "<cnpj>"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "<cpf>"),
    (re.compile(r"(?i)(senha|password|passwd|token|secret|api[_-]?key)[^\\/]*"), "<sensitive-name>"),
]


def sanitize_text(value: str) -> str:
    safe = value or ""
    for pattern, replacement in SENSITIVE_NAME_PATTERNS:
        safe = pattern.sub(replacement, safe)
    return safe


def mask_path(path_str: str) -> str:
    """Preserva origem e arquivo final, mas remove a trilha interna completa."""
    if not path_str:
        return ""

    safe_path = sanitize_text(path_str)
    parts = list(Path(safe_path).parts)
    if len(parts) <= 3:
        return safe_path

    if safe_path.startswith("\\\\"):
        # UNC: \\host\share\...\arquivo.ext
        host_share = "\\".join(parts[:2])
        return os.path.join(host_share, "...", parts[-1])

    return os.path.join(parts[0], "...", parts[-1])


def categorize_file(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext in {".db", ".sqlite", ".sqlite3"}:
        return "database"
    if ext in {".xlsx", ".xlsm", ".xls", ".csv", ".ods"}:
        return "spreadsheet"
    if ext in {".doc", ".docx", ".odt", ".pdf", ".html", ".htm"}:
        return "document"
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico"}:
        return "asset"
    if ext in {".json", ".ini", ".cfg", ".conf", ".env", ".yaml", ".yml"}:
        return "configuration"
    if ext in {".log", ".txt"}:
        return "log_or_text"
    return "other"


def suggest_destination(source_name: str, category: str, file_name: str) -> str:
    source = source_name.lower()
    name = file_name.lower()
    if "compra" in source:
        return "Compras / Cadastros / Historico de precos"
    if "helpdesk" in source or "suporte" in source:
        return "TI / Help Desk / Arquivos"
    if "producao" in source:
        return "Producao / Registros operacionais"
    if "projeto" in source:
        return "Projetos / Registros operacionais"
    if "proposta" in source or "proposta" in name:
        return "Propostas / Clientes / Arquivos"
    if category == "asset":
        return "Arquivos / Knowledge / Assets"
    if category == "configuration":
        return "TI / Cofre ou Sistemas, com revisao manual"
    return "Arquivos / Knowledge"


def should_skip_dir(root: str) -> bool:
    lower_parts = {part.lower() for part in Path(root).parts}
    return bool(lower_parts.intersection(SKIP_DIR_PARTS))


def scan_sources() -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}

    for source_name, base_path in SOURCES.items():
        source_result: dict[str, Any] = {
            "base_path": base_path,
            "masked_base_path": mask_path(base_path),
            "exists": os.path.exists(base_path),
            "files": [],
            "counts_by_category": Counter(),
            "counts_by_extension": Counter(),
        }
        results[source_name] = source_result

        if not source_result["exists"]:
            continue

        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIR_PARTS]
            if should_skip_dir(root):
                continue

            for filename in files:
                file_path = os.path.join(root, filename)
                ext = Path(filename).suffix.lower()
                if ext not in EXTENSIONS and filename.lower() != "config.json":
                    continue

                try:
                    stat = os.stat(file_path)
                except OSError:
                    continue

                category = categorize_file(file_path)
                safe_name = sanitize_text(filename)
                source_result["counts_by_category"][category] += 1
                source_result["counts_by_extension"][ext or "<sem-extensao>"] += 1
                source_result["files"].append(
                    {
                        "name": safe_name,
                        "type": ext or "config",
                        "category": category,
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                        "masked_path": mask_path(file_path),
                        "suggested_destination": suggest_destination(source_name, category, safe_name),
                    }
                )

    return results


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def generate_report(results: dict[str, dict[str, Any]], output_path: str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8") as report:
        report.write("# Relatorio de Descoberta de Fontes Reais Legadas\n\n")
        report.write(f"Gerado em: `{datetime.now(timezone.utc).isoformat()}`\n\n")
        report.write("Este inventario e somente leitura. Ele nao executa apps legados, macros, workflows, scripts externos, nem altera NAS, planilhas ou bancos antigos.\n\n")

        report.write("## 1. Origens Mapeadas\n\n")
        report.write("| Origem | Caminho mascarado | Status | Arquivos | Bancos | Planilhas | Docs | Assets | Configs |\n")
        report.write("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |\n")
        for source_name, data in results.items():
            counts = data["counts_by_category"]
            status = "Disponivel" if data["exists"] else "Indisponivel"
            report.write(
                f"| {source_name} | `{data['masked_base_path']}` | {status} | {len(data['files'])} | "
                f"{counts['database']} | {counts['spreadsheet']} | {counts['document']} | {counts['asset']} | {counts['configuration']} |\n"
            )

        report.write("\n## 2. Politica de Seguranca Aplicada\n\n")
        report.write("- Caminhos completos foram mascarados, preservando somente origem e arquivo final.\n")
        report.write("- E-mails, CPF/CNPJ e nomes de arquivos com padrao de senha/token foram redigidos.\n")
        report.write("- Arquivos de configuracao foram inventariados por metadados; conteudo nao foi aberto nem exibido.\n")
        report.write("- Nenhum segredo, senha, token ou chave de API deve aparecer neste relatorio.\n")
        report.write("- Fontes inacessiveis ficam marcadas como indisponiveis; o script nao inventa registros.\n\n")

        report.write("## 3. Inventario por Origem\n\n")
        for source_name, data in results.items():
            report.write(f"### {source_name}\n\n")
            report.write(f"Base: `{data['masked_base_path']}`\n\n")
            if not data["exists"]:
                report.write("Origem nao encontrada ou inacessivel neste ambiente.\n\n")
                continue
            if not data["files"]:
                report.write("Nenhum arquivo relevante detectado.\n\n")
                continue

            report.write("Resumo por extensao:\n\n")
            report.write("| Extensao | Quantidade |\n")
            report.write("| --- | ---: |\n")
            for ext, count in sorted(data["counts_by_extension"].items()):
                report.write(f"| `{ext}` | {count} |\n")

            report.write("\nArquivos detectados:\n\n")
            report.write("| Arquivo mascarado | Categoria | Tipo | Tamanho | Modificado UTC | Destino sugerido |\n")
            report.write("| --- | --- | --- | ---: | --- | --- |\n")
            for file_info in sorted(data["files"], key=lambda item: (item["category"], item["name"])):
                report.write(
                    f"| `{file_info['masked_path']}` | {file_info['category']} | `{file_info['type']}` | "
                    f"{format_size(file_info['size_bytes'])} | `{file_info['modified_at']}` | {file_info['suggested_destination']} |\n"
                )
            report.write("\n")

        report.write("## 4. Uso Recomendado para Go-live\n\n")
        report.write("- Use este relatorio para escolher quais lotes entram em staging primeiro.\n")
        report.write("- Promova dados somente por API oficial do Portal, com decisao humana quando houver duplicidade.\n")
        report.write("- Senhas descobertas em apps antigos devem entrar apenas no Cofre criptografado, nunca em CSV, log ou markdown.\n")
        report.write("- Antes de ativar modulos para usuarios finais, rode importadores em `--dry-run` e revise duplicidades.\n")

    print(f"Relatorio gerado em: {output_path}")


def print_dry_run(results: dict[str, dict[str, Any]]) -> None:
    for source_name, data in results.items():
        print(f"\nOrigem: {source_name} | existe={data['exists']} | arquivos={len(data['files'])}")
        print(f"Base: {data['masked_base_path']}")
        for category, count in sorted(data["counts_by_category"].items()):
            print(f"  {category}: {count}")
        for file_info in data["files"][:10]:
            print(f"  - {file_info['category']} {format_size(file_info['size_bytes'])} -> {file_info['masked_path']}")
        if len(data["files"]) > 10:
            print(f"  ... mais {len(data['files']) - 10} arquivos.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Descoberta segura de fontes reais legadas.")
    parser.add_argument("--dry-run", action="store_true", help="Mostra resumo no console sem gerar arquivo.")
    parser.add_argument("--output", default="docs/generated/legacy-real-source-discovery.md", help="Caminho do relatorio.")
    args = parser.parse_args()

    print("Iniciando descoberta segura de fontes reais...")
    results = scan_sources()
    if args.dry_run:
        print_dry_run(results)
        return

    generate_report(results, args.output)


if __name__ == "__main__":
    main()
