# Portal Vesper - Guia de Startup/Shutdown

## Quick Start

### Iniciar o Portal
```batch
INICIAR_PORTAL.bat
```

Isso vai:
1. ✅ Verificar pré-requisitos (Docker, Node.js, Python)
2. ✅ Validar permissões de admin automaticamente
3. ✅ Parar processos/containers antigos
4. ✅ Iniciar PostgreSQL, Redis, MinIO, Adminer (Docker)
5. ✅ Preparar ambiente Python (venv, dependências)
6. ✅ Aplicar migrações do banco de dados
7. ✅ Executar seed de desenvolvimento
8. ✅ Preparar frontend (Node modules, dependências)
9. ✅ Iniciar API Backend em `http://localhost:8000`
10. ✅ Iniciar Frontend em `http://localhost:5173`
11. ✅ Abrir navegador automaticamente

### Parar o Portal
```batch
PARAR_PORTAL.bat
```

Isso vai:
1. ✅ Encerrar processo do backend (Uvicorn)
2. ✅ Encerrar processo do frontend (Vite dev server)
3. ✅ Liberar portas 8000 e 5173
4. ℹ️ Manter containers Docker rodando (para preservar dados)

---

## Opções Avançadas

### Iniciar Rápido (Pula npm install)
```batch
INICIAR_PORTAL.bat --skip-install
```
**Uso:** Para reiniciar durante desenvolvimento sem refazer npm install  
**Tempo:** 30-45 segundos vs. 2-3 minutos normalmente  
**Aviso:** Use só se souber que node_modules está ok

### Recriar Backend Python 3.14
```batch
powershell -ExecutionPolicy Bypass ".\scripts\start_portal.ps1" -RecreateVenv
```
**Uso:** quando a pasta veio de outro PC ou a `backend\.venv` aponta para um Python antigo/quebrado.  
**Aviso:** remove e recria somente `backend\.venv`; nao apaga banco, uploads ou Docker volumes.
### Iniciar Sem Abrir Navegador
```batch
INICIAR_PORTAL.bat --no-browser
```
**Uso:** Quando você quer controlar qual navegador usar  
**Acesso Manual:** `http://localhost:5173`

### Iniciar Fresh (Limpa tudo)
```batch
INICIAR_PORTAL.bat --clean
```
**Uso:** Para reset completo (remove containers, volumes, etc.)  
**Tempo:** 3-5 minutos  
**Quando usar:**
- Após problemas de migração do banco
- Para descartar dados de teste
- Para começar do zero

### Combinar Opções
```batch
INICIAR_PORTAL.bat --skip-install --no-browser
```

---

## Parar com Opções

### Parar Apenas Frontend/Backend
```batch
PARAR_PORTAL.bat
```
**Efeito:**
- Encerra Uvicorn (backend)
- Encerra Vite (frontend)
- Libera portas 8000 e 5173
- **Docker continua rodando** (preserva dados)

### Parar Também Docker
```batch
PARAR_PORTAL.bat --stop-docker
```
**Efeito:**
- Para backend e frontend
- Para containers Docker (DB, Redis, MinIO)
- **Dados persistem** em volumes Docker

**Próxima execução:** `INICIAR_PORTAL.bat` reinicia tudo normalmente

### Limpar Tudo (Remove Dados)
```batch
PARAR_PORTAL.bat --remove-all
```
**⚠️ CUIDADO:** Remove containers E volumes  
**Efeito:**
- Para todos os processos
- Remove containers Docker
- **Apaga dados locais (banco de dados, uploads, cache)**

**Próxima execução:** Recria banco do zero com seed

---

## Endereços e URLs

Uma vez iniciado, acesse:

### Frontend (Portal Web)
- **Local:** `http://localhost:5173`
- **Rede (outro PC):** `http://<seu-ip>:5173`
- **Exemplo:** `http://192.168.1.100:5173`

### Backend API
- **Swagger (Documentação):** `http://localhost:8000/docs`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

### Utilidades de Desenvolvimento
- **Adminer (DB Manager):** `http://localhost:8080`
  - Servidor: `db` (interno do Docker)
  - Usuário: `postgres`
  - Senha: Configurada em `infra/docker-compose.yml`

### Logs
Todos os logs são salvos em `.\scratch\run\`:
```
scratch/run/
├── backend.out.log       # Stdout do backend
├── backend.err.log       # Stderr do backend
├── frontend.out.log      # Stdout do frontend
├── frontend.err.log      # Stderr do frontend
├── start-portal.log      # Log da inicialização
└── stop-portal.log       # Log da parada
```

**Dica:** Abra esses arquivos em tempo real em outro editor para debugar

---

## Troubleshooting

### Problema: "Docker nao encontrado"
**Solução:**
1. Instale Docker Desktop: https://www.docker.com/products/docker-desktop
2. Abra Docker Desktop antes de executar `INICIAR_PORTAL.bat`
3. Aguarde ele ficar "running" (pode levar 1-2 minutos)

### Problema: "npm nao encontrado"
**Solução:**
1. Instale Node.js 24 LTS: https://nodejs.org/
2. Confirme com: `node --version` e `npm --version` no terminal
3. Pode precisar reiniciar o terminal após instalação

### Problema: "Python nao encontrado"
**Solução:**
1. Instale Python 3.14.6 x64 com py launcher: https://www.python.org/
2. Certifique-se que selecionou "Add Python to PATH" durante instalação
3. Confirme com: `python --version` no terminal

### Problema: "Erro ao parar processos - Porta 8000/5173 ocupada"
**Solução:**
1. Execute como Admin (clique direito > "Executar como administrador")
2. Se continuar: `PARAR_PORTAL.bat` novamente
3. Se ainda ocupada: Reinicie o computador

### Problema: Backend retorna 401 (não autenticado)
**Solução:**
1. Verifique se seed rodou: Procure em `backend.out.log` por "seed"
2. Se seed falhou, tente: `INICIAR_PORTAL.bat --clean`
3. Verifique banco: http://localhost:8080 (Adminer)

### Problema: Frontend não carrega (erro de conexão)
**Solução:**
1. Verifique se backend iniciou: Abra `http://localhost:8000/health`
2. Se erro: Verifique `backend.out.log` e `backend.err.log`
3. Se backend ok mas frontend não funciona: Verifique `frontend.out.log`

### Problema: "Script nao pode ser carregado"
**Solução:**
1. Abra PowerShell como Admin
2. Execute: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
3. Digite `Y` e pressione Enter
4. Tente novamente: `INICIAR_PORTAL.bat`

### Problema: Porta 8000/5173 já está em uso
**Solução:**
1. Verifique se Portal já está rodando em outra janela
2. Se há processos antigos: `PARAR_PORTAL.bat`
3. Se problema persiste: Use commands customizadas:
   ```batch
   REM Usar portas diferentes
   powershell -ExecutionPolicy Bypass ".\scripts\start_portal.ps1" -BackendPort 8001 -FrontendPort 5174
   ```

---

## Desenvolvimento - Workflows Comuns

### Workflow 1: Desenvolvimento Frontend
```batch
INICIAR_PORTAL.bat
REM Aguarde até ver "Portal Web respondendo..."
REM Edite arquivos em apps/web/src/
REM Vite recarrega automaticamente (HMR)
REM Quando pronto, parar com:
PARAR_PORTAL.bat
```

### Workflow 2: Desenvolvimento Backend
```batch
INICIAR_PORTAL.bat
REM Aguarde até ver "Backend respondendo..."
REM Edite arquivos em backend/app/
REM Uvicorn com --reload recarrega automaticamente
REM Para depurar, use os logs em scratch/run/
PARAR_PORTAL.bat
```

### Workflow 3: Testes de Integração
```batch
REM Iniciar fresh
INICIAR_PORTAL.bat --clean

REM Aguarde completo (~3-5 min)
REM Banco será recriado com seed

REM Rodar testes
cd backend
.\\.venv\Scripts\python.exe -m pytest tests/
cd ..

REM Parar
PARAR_PORTAL.bat
```

### Workflow 4: Alterações no Docker Compose
```batch
REM Se alterou infra/docker-compose.yml
PARAR_PORTAL.bat --remove-all

REM Depois
INICIAR_PORTAL.bat
```

### Workflow 5: Limpar Cache/Reset de Dados
```batch
REM Opção 1: Só parar (dados preservados)
PARAR_PORTAL.bat

REM Opção 2: Parar docker (dados ainda em volumes)
PARAR_PORTAL.bat --stop-docker

REM Opção 3: Limpeza completa (DESTRÓI DADOS)
PARAR_PORTAL.bat --remove-all
INICIAR_PORTAL.bat --clean
```

---

## Monitoramento

### Ver se está rodando
```batch
REM Verificar backend
curl http://localhost:8000/health

REM Verificar frontend
curl http://localhost:5173

REM Verificar containers Docker
docker ps | find "postgres\|redis\|minio"
```

### Ver logs em tempo real
```powershell
REM Backend logs (continua mostrando)
Get-Content .\scratch\run\backend.out.log -Wait -Tail 50

REM Frontend logs (continua mostrando)
Get-Content .\scratch\run\frontend.out.log -Wait -Tail 50
```

### Ver o que está usando as portas
```powershell
netstat -ano | find "8000"
netstat -ano | find "5173"
```

---

## Estrutura de Diretórios

```
Portal-Vesper/
├── INICIAR_PORTAL.bat          ← Clique para iniciar tudo
├── PARAR_PORTAL.bat            ← Clique para parar tudo
├── scripts/
│   ├── start_portal.ps1        ← Script que faz a mágica da inicialização
│   ├── stop_portal.ps1         ← Script que para tudo
│   └── ports.ps1               ← Helper para gerenciar portas
├── backend/
│   ├── .venv/                  ← Ambiente Python (criado automaticamente)
│   ├── requirements.txt        ← Dependências Python
│   ├── alembic/                ← Migrações do banco
│   └── app/
├── apps/web/
│   ├── node_modules/           ← Dependências Node (criado automaticamente)
│   ├── package.json
│   └── src/
├── infra/
│   └── docker-compose.yml      ← Configuração Docker (DB, Redis, MinIO)
└── scratch/run/                ← Logs (criado automaticamente)
    ├── backend.out.log
    ├── backend.err.log
    ├── frontend.out.log
    └── frontend.err.log
```

---

## Requisitos do Sistema

- **Windows 10/11**
- **Docker Desktop** (latest)
- **Node.js 24 LTS**
- **Python 3.14.6 x64 com py launcher**
- **~2 GB RAM** para containers (recomendado 4+ GB)
- **~1 GB espaço em disco** para imagens Docker

---

## Configuração Recomendada da IDE (VS Code)

Para evitar alertas e erros falsos no Visual Studio Code (como imports marcados em vermelho no Python ou TypeScript), siga estas etapas de configuração:

### 1. Backend: Selecionar o Interpretador Python Correto
O VS Code precisa usar a máquina virtual (virtualenv) que o portal cria em `backend/.venv`.
1. Abra um arquivo Python do projeto, por exemplo, `backend/app/main.py`.
2. Abra a paleta de comandos (`Ctrl + Shift + P` ou `F1`).
3. Digite e selecione: `Python: Select Interpreter`.
4. Escolha o interpretador localizado no caminho `backend/.venv/Scripts/python.exe`.
5. Isso resolverá todos os erros falsos de importação ("Import could not be resolved" para FastAPI, SQLAlchemy, Pydantic, etc.).

### 2. Frontend: Execução Inicial do `npm install`
Se você vir avisos de imports marcados em vermelho nos arquivos de componente ou páginas React (`apps/web/src/...`):
1. Abra um terminal na pasta `apps/web`.
2. Execute o comando:
   ```bash
   npm install
   ```
3. O VS Code detectará os tipos de todas as dependências no diretório `node_modules` e os erros de digitação e import do TypeScript desaparecerão.

### 3. Extensões Recomendadas
Para garantir que a formatação e linter funcionem em tempo real no seu editor, instale as seguintes extensões oficiais no VS Code:
- **Python** (Microsoft) e **Pylance** (Microsoft): Para auto-complete, tipagem e análise estática do backend.
- **ESLint** (Microsoft): Para validar e exibir os alertas de código TypeScript em tempo real de acordo com as regras em `apps/web/.eslintrc.json`.
- **Prettier - Code formatter** (Prettier): Para formatar o código frontend automaticamente de acordo com as preferências estabelecidas no arquivo `.prettierrc`.

### 4. Configuração Automática ao Salvar
Para que o código frontend e backend seja formatado automaticamente toda vez que você salvar um arquivo, sugerimos adicionar a seguinte configuração nas preferências do VS Code (`.vscode/settings.json` na raiz do projeto):
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

---

## Notas Importantes

✅ **Admin Requerido:** Scripts pedem elevação automática  
✅ **Idempotente:** Pode rodar múltiplas vezes com segurança  
✅ **Logs Completos:** Todos os erros gravados em `scratch/run/`  
✅ **Cleanup Inteligente:** Para processos antigos automaticamente  
✅ **Saúde Verificada:** Testa endpoints de health antes de liberar  

⚠️ **Backup:**  Antes de usar `--remove-all`, considere backup se tem dados importantes  
⚠️ **Firewall:** Libere portas 5173 e 8000 se acessar de outra máquina  
⚠️ **Timeout:** Primeiro início pode levar 3-5 minutos (baixa imagens Docker)  

---

## Suporte

Se encontrar problemas:
1. Veja a seção **Troubleshooting** acima
2. Consulte os logs em `scratch/run/`
3. Verifique pré-requisitos (Docker aberto, Node.js, Python)
4. Tente: `PARAR_PORTAL.bat` + `INICIAR_PORTAL.bat --clean`
5. Se problema persistir, reinicie o computador

---

**Última atualização:** julho de 2026  
**Scripts:** start_portal.ps1, stop_portal.ps1, ports.ps1  
**Compatibilidade:** Windows 10+ com Docker Desktop
