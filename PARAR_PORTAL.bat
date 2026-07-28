@echo off
REM ==============================================================================
REM PORTAL VESPER - PARADOR SEGURO E COMPLETO
REM ==============================================================================
REM
REM Este script para completamente o Portal Vesper:
REM  - Encerra processo do backend (API FastAPI/Uvicorn)
REM  - Encerra processo do frontend (Vite dev server)
REM  - Libera as portas 8000 e 5173
REM  - Opcionalmente para também containers Docker
REM
REM Uso:
REM   PARAR_PORTAL.bat              # Para apenas Frontend e Backend
REM   PARAR_PORTAL.bat --stop-docker # Para também Docker containers (DB, Redis, MinIO)
REM   PARAR_PORTAL.bat --remove-all  # Remove containers e volumes (CUIDADO!)
REM
REM ==============================================================================

setlocal enabledelayedexpansion
color 0C
title Portal Vesper - Parar Servidores

echo.
echo  =====================================================
echo       PORTAL VESPER - Parar Servidores Locais
echo  =====================================================
echo.

REM Mudar para diretório do script
cd /d "%~dp0"

REM Verificar se está rodando como Admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [AVISO] Este script deveria rodar como Administrador para:
    echo    - Encerrar processos de forma segura
    echo    - Gerenciar Docker apropriadamente
    echo.
    echo  Reabrindo como Admin...
    timeout /t 2
    powershell -Command "Start-Process cmd -ArgumentList '/c','\"%~f0\" %*' -Verb RunAs"
    exit /b
)

REM Construir argumentos para passar ao PowerShell
set "PS_ARGS="
if "%1"=="--stop-docker" set "PS_ARGS=-StopDocker"
if "%1"=="--remove-all" set "PS_ARGS=%PS_ARGS% -RemoveAll"

REM Executar script PowerShell com argumentos
powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\stop_portal.ps1" %PS_ARGS%

if errorlevel 1 (
    echo.
    echo  ====================================================
    echo    [AVISO] Alguns processos podem ainda estar em execução
    echo  ====================================================
    echo.
    echo  Tente:
    echo    1. Fechar manualmente janelas abertas pelo Portal
    echo    2. Aguarde alguns segundos e execute este script novamente
    echo    3. Se problema persistir, reinicie o computador
    echo.
    pause
    exit /b 1
)

echo.
echo  ====================================================
echo    [SUCESSO] Portal Vesper parado com sucesso!
echo  ====================================================
echo.
echo  Portas 8000 (Backend) e 5173 (Frontend) liberadas.
echo.

if "%1"=="--stop-docker" (
    echo  Containers Docker foram parados.
    echo  Para reiniciar, execute: INICIAR_PORTAL.bat
    echo.
)

if "%1"=="--remove-all" (
    echo  [AVISO] Containers e volumes foram removidos!
    echo  Dados locais foram apagados. Banco será recriado no próximo INICIAR.
    echo.
)

echo  Para iniciar novamente, execute: INICIAR_PORTAL.bat
echo.
echo  ====================================================
echo    Pressione qualquer tecla para fechar esta janela.
echo  ====================================================
pause >nul
exit /b 0
