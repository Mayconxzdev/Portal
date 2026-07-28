# ==============================================================================
# PORTAL VESPER - PARADA LOCAL SEGURA (WINDOWS)
# ==============================================================================
# Uso:
#   .\stop_portal.ps1              # Para apenas Frontend e Backend
#   .\stop_portal.ps1 -StopDocker  # Para também containers Docker
#   .\stop_portal.ps1 -RemoveAll   # Remove containers e volumes (CUIDADO!)
#

param(
    [switch]$StopDocker,
    [switch]$RemoveAll
)

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptPath "..")
Set-Location $projectRoot
$logsDir = Join-Path $projectRoot "scratch\run"
New-Item -ItemType Directory -Force $logsDir | Out-Null
$stopLog = Join-Path $logsDir "stop-portal.log"
Set-Content -Path $stopLog -Value "[INICIO] $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Encoding UTF8
. (Join-Path $scriptPath "ports.ps1")

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "      PORTAL VESPER - PARANDO SERVIDORES LOCAIS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Stop-PortalPortProcesses -Ports @(8000, 5173) -LogPath $stopLog
try {
    Assert-PortalPortsFree -Ports @(8000, 5173) -LogPath $stopLog
    Write-Host "Portas locais do Portal liberadas." -ForegroundColor Green
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}

if ($RemoveAll) {
    Write-Host ""
    Write-Host "[AVISO] Removendo containers Docker e volumes..." -ForegroundColor Yellow
    docker compose -f infra/docker-compose.yml down -v
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Containers e volumes removidos com sucesso." -ForegroundColor Green
    } else {
        Write-Host "Erro ao remover containers (pode estar OK se ja nao existiam)." -ForegroundColor Yellow
    }
} elseif ($StopDocker) {
    Write-Host ""
    Write-Host "[INFO] Parando containers Docker (dados preservados)..." -ForegroundColor Cyan
    docker compose -f infra/docker-compose.yml stop
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Containers Docker parados com sucesso." -ForegroundColor Green
    } else {
        Write-Host "Erro ao parar containers (pode estar OK se ja nao existiam)." -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "Containers Docker continuam ativos para preservar banco/local services." -ForegroundColor Yellow
    Write-Host "Para parar tambem Docker, use:" -ForegroundColor Yellow
    Write-Host "  PARAR_PORTAL.bat --stop-docker" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Para remover containers e volumes (CUIDADO!), use:" -ForegroundColor Yellow
    Write-Host "  PARAR_PORTAL.bat --remove-all" -ForegroundColor Yellow
}
