"""Audit the public n8n templates before they are committed.

The repository intentionally publishes disabled, credential-free workflow templates.
This script fails when an export still contains activation state, credential bindings,
instance metadata or webhook identifiers that should be configured after import.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORBIDDEN_KEYS = {
    "credentials",
    "webhookId",
    "instanceId",
    "versionId",
    "activeVersion",
    "shared",
    "staticData",
    "pinData",
}


def walk(value: Any, location: str = "root") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{location}.{key}"
            if key in FORBIDDEN_KEYS:
                findings.append(f"{current}: chave privada/exportada presente")
            findings.extend(walk(child, current))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(walk(child, f"{location}[{index}]"))
    return findings


def audit_file(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    findings = walk(data)
    if data.get("active") is True:
        findings.append("root.active: workflow público não pode estar ativo")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita templates públicos do n8n")
    parser.add_argument(
        "path",
        nargs="?",
        default="n8n/workflows",
        help="Diretório de workflows (padrão: n8n/workflows)",
    )
    args = parser.parse_args()

    root = Path(args.path)
    files = sorted(root.rglob("*.json"))
    if not files:
        print(f"Nenhum workflow encontrado em {root}")
        return 1

    errors = 0
    for path in files:
        try:
            findings = audit_file(path)
        except (OSError, json.JSONDecodeError) as exc:
            findings = [f"JSON inválido ou ilegível: {exc}"]
        if findings:
            errors += 1
            print(f"[FALHA] {path}")
            for finding in findings:
                print(f"  - {finding}")
        else:
            print(f"[OK] {path}")

    print(f"\nArquivos auditados: {len(files)} | arquivos com falha: {errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
