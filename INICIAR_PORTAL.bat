@echo off
REM ==============================================================================
REM PORTAL VESPER - INICIADOR COMPLETO E ROBUSTO
REM ==============================================================================
REM
REM Este script inicia completamente o Portal Vesper:
REM  - Verifica pré-requisitos (Docker, Node.js, Python)
REM  - Para processos/containers antigos
REM  - Inicia infraestrutura (PostgreSQL, Redis, MinIO)
REM  - Prepara backend (venv, dependências, migrations)
REM  - Prepara frontend (dependências, build se necessário)
REM  - Inicia API em http://localhost:8000
REM  - Inicia Frontend em http://localhost:5173
REM  - Abre o navegador automaticamente
REM
REM Uso:
REM   INICIAR_PORTAL.bat                 # Inicia normalmente
REM   INICIAR_PORTAL.bat --skip-install  # Pula npm/pip install (mais rápido)
REM   INICIAR_PORTAL.bat --no-browser    # Inicia sem abrir navegador
REM   INICIAR_PORTAL.bat --clean         # Limpa containers e inicia fresh
REM
REM ==============================================================================

setlocal enabledelayedexpansion
color 0B
title Portal Vesper - Iniciar Ambiente Local

echo.
echo  =====================================================
echo         PORTAL VESPER - Iniciar Ambiente Local
echo  =====================================================
echo.

REM Mudar para diretório do script
cd /d "%~dp0"

REM Verificar se está rodando como Admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [AVISO] Este script deveria rodar como Administrador para:
    echo    - Liberar portas do firewall se necessário
    echo    - Gerenciar Docker apropriadamente
    echo.
    echo  Reabrindo como Admin...
    timeout /t 2
    powershell -Command "Start-Process cmd -ArgumentList '/c','\"%~f0\" %*' -Verb RunAs"
    exit /b
)

REM Construir argumentos para passar ao PowerShell
set "PS_ARGS="
if "%1"=="--skip-install" set "PS_ARGS=-SkipInstall"
if "%1"=="--no-browser" set "PS_ARGS=%PS_ARGS% -NoBrowser"
if "%1"=="--clean" set "PS_ARGS=%PS_ARGS% -CleanStart"

REM Executar script PowerShell com argumentos
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start_portal.ps1" %PS_ARGS%

if errorlevel 1 (
    echo.
    echo  ====================================================
    echo    [ERRO] Falha ao iniciar Portal Vesper
    echo  ====================================================
    echo.
    echo  Verifique:
    echo    1. Docker Desktop está aberto e rodando?
    echo    2. Node.js (npm) está instalado? (node --version)
    echo    3. Python está instalado? (python --version)
    echo    4. As portas 8000 (backend) e 5173 (frontend) estão livres?
    echo.
    echo  Logs disponíveis em:
    echo    - .\scratch\run\backend.out.log
    echo    - .\scratch\run\frontend.out.log
    echo    - .\scratch\run\start-portal.log
    echo.
    pause
    exit /b 1
)

echo.
echo  ====================================================
echo    [SUCESSO] Portal Vesper iniciado com sucesso!
echo  ====================================================
echo.
echo  Acesse em: http://localhost:5173
echo.
echo  Para parar tudo, execute: PARAR_PORTAL.bat
echo.
echo  ====================================================
echo    O Portal continua rodando em segundo plano.
echo    Pressione qualquer tecla para fechar esta janela.
echo  ====================================================
pause >nul
exit /b 0
