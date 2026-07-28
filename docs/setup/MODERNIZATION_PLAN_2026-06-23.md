# Portal Vesper - Plano de Modernizacao do Ambiente

Data: 2026-06-23

## Objetivo

Deixar o PC de desenvolvimento e o projeto alinhados com a stack estavel mais atual possivel, sem usar beta/RC no servidor 24h e sem depender de tags flutuantes em servicos criticos.

## Versoes alvo

| Componente | Alvo | Observacao |
| --- | --- | --- |
| Python | 3.14.6 | Runtime principal do backend e worker. Fallback tecnico: 3.13.x se dependencia binaria bloquear. |
| Node.js | 24 LTS | Runtime suportado do frontend, alinhado ao arquivo `.node-version` e ao CI. |
| npm | Versão incluída no Node 24 LTS | Usar o npm atualizado pelo instalador oficial do Node. |
| PostgreSQL | 18.4 | Banco dev Docker. PostgreSQL continua fonte oficial da verdade. |
| Redis | 8.8.x | Cache/eventos locais via Docker. |
| n8n | 2.27.3 | Fixado para evitar mudanca silenciosa de workflows. |
| Python worker Docker | python:3.14-slim | Worker de compras. |
| Tauri | Rust crates 2.6.3, CLI 2.11.3 e API 2.11.x | Desktop depende de Rust stable, MSVC Build Tools e WebView2. |
| React | 19.2.7 | Patch mais novo conhecido no pacote atual. |
| Vite | 8.x | Mantido na linha 8. |
| TypeScript | 6.0.x | Exige validacao de types/lint. |
| Vitest | 4.1.9 | Test runner atual da linha estavel. |

## O que ja foi preparado no repo

- `.python-version` aponta para `3.14.6`.
- `.node-version` aponta para `24`.
- `infra/docker-compose.yml` usa imagens modernas via variaveis de ambiente.
- `.env.example` usa `POSTGRES_PORT=55432` para evitar conflito com PostgreSQL local em `5432`.
- Worker Docker passou para `python:3.14-slim`.
- Backend `ruff` passou a mirar `py314`.
- Tauri Rust usa crates `2.6.3`; Tauri CLI fica em `2.11.3`.
- Frontend declarou `engines` para Node 24 LTS e atualizou dependências de topo conhecidas.
- `backend/requirements-dev.txt` foi criado para testes/lint.
- `scripts/start_portal.ps1` agora valida Node moderno e Python 3.14, e oferece `-RecreateVenv`.

## Ordem segura para executar no PC

1. Rodar diagnostico:

```powershell
.\scripts\setup_windows_modern.ps1
```

2. Instalar ferramentas no PowerShell como Administrador:

```powershell
.\scripts\setup_windows_modern.ps1 -Install
```

3. Fechar e abrir um novo terminal.

4. Recriar backend venv explicitamente:

```powershell
.\scripts\start_portal.ps1 -RecreateVenv -NoBrowser
```

5. Atualizar lockfiles com rede liberada:

```powershell
cd apps\web
npm install
cd ..\..
```

6. Validar backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m compileall -q app
.\.venv\Scripts\pytest.exe -q
cd ..
```

7. Validar frontend:

```powershell
cd apps\web
npm run lint
npm run test:run
npm run build
cd ..\..
```

8. Validar Docker:

```powershell
docker compose -f infra\docker-compose.yml pull
docker compose -f infra\docker-compose.yml up -d db redis minio searxng n8n adminer
docker compose -f infra\docker-compose.yml ps
```

## Rollback local

- Se Python 3.14 falhar por dependencia binaria, instalar Python 3.13.x e ajustar `.python-version` temporariamente.
- Se uma atualização de Node quebrar o tooling, retornar ao Node 24 LTS definido em `.node-version`.
- Se PostgreSQL 18.4 quebrar migracoes, validar em banco dev vazio antes de qualquer dado real.
- Nunca rodar `down -v`, `--remove-all` ou reset de banco se houver dados locais que precisam ser preservados.

## Pendencias antes do servidor 24h

- Trocar segredos locais por segredos reais fortes fora do Git.
- Fixar MinIO/SearXNG/Adminer por tag ou digest validado, evitando `latest` em producao.
- Rodar E2E autenticado.
- Validar n8n 2.27.3 contra workflows reais antes de expor qualquer webhook.
- Fazer backup e plano de migracao antes de banco de producao.
