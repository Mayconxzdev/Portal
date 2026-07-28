"""Fail fast when the repository contains data that should not be public.

This is intentionally dependency-free so it can run before package installation in CI.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".cjs", ".mjs", ".md", ".json",
    ".yml", ".yaml", ".toml", ".ini", ".sh", ".ps1", ".bat", ".txt",
}
FORBIDDEN_FILE_NAMES = {".env", "id_rsa", "id_ed25519"}
FORBIDDEN_SUFFIXES = {".pem", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db"}
FORBIDDEN_TEXT = {
    "C:\\Users\\": "caminho de perfil Windows",
    "K:\\Maycon": "caminho pessoal de rede",
    "\\\\192.168.254.": "servidor privado legado",
    "Tecnico2": "identificador local",
    "@vesper.ind.br": "domínio corporativo real",
    "@ventrio.ind.br": "domínio corporativo real",
}
N8N_FORBIDDEN_KEYS = {
    "credentials", "webhookId", "instanceId", "versionId", "activeVersion",
    "shared", "staticData", "pinData",
}


def iter_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", "node_modules", ".venv", "dist", "target"} for part in path.parts):
            continue
        yield path


def walk_json(value, location="root"):
    findings = []
    if isinstance(value, dict):
        for key, child in value.items():
            current = f"{location}.{key}"
            if key in N8N_FORBIDDEN_KEYS:
                findings.append(f"{current}: chave exportada não permitida")
            findings.extend(walk_json(child, current))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(walk_json(child, f"{location}[{index}]"))
    return findings


def main() -> int:
    findings: list[str] = []

    uploads = ROOT / "storage" / "uploads"
    if uploads.exists():
        unexpected = [p for p in uploads.rglob("*") if p.is_file() and p.name != ".gitkeep"]
        findings.extend(f"upload operacional versionado: {p.relative_to(ROOT)}" for p in unexpected)

    for path in iter_files():
        rel = path.relative_to(ROOT)
        if path.name in FORBIDDEN_FILE_NAMES and path.name != ".env.example":
            findings.append(f"arquivo sensível: {rel}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"artefato local/sensível: {rel}")

        if path.resolve() == Path(__file__).resolve():
            continue

        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {".env.example", ".gitignore"}:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for marker, description in FORBIDDEN_TEXT.items():
                if marker in text:
                    findings.append(f"{rel}: {description} ({marker})")

    for path in (ROOT / "n8n" / "workflows").rglob("*.json"):
        rel = path.relative_to(ROOT)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(f"{rel}: JSON inválido ({exc})")
            continue
        if data.get("active") is True:
            findings.append(f"{rel}: workflow público ativo")
        findings.extend(f"{rel}: {item}" for item in walk_json(data))

    link_pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for path in ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for raw_target in link_pattern.findall(text):
            target = raw_target.strip().split(" ", 1)[0]
            if target.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            target = target.split("#", 1)[0]
            if target and not (path.parent / target).resolve().exists():
                findings.append(f"{path.relative_to(ROOT)}: link local inexistente ({target})")

    if findings:
        print("Falhas na auditoria pública:")
        for item in sorted(set(findings)):
            print(f"- {item}")
        return 1

    files_count = sum(1 for _ in iter_files())
    print(f"Auditoria pública concluída: {files_count} arquivos inspecionados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
