# ==============================================================================
# PORTAL VESPER - INICIADOR LOCAL ROBUSTO (WINDOWS)
# ==============================================================================
# Uso:
#   .\start_portal.ps1                      # Inicia normalmente
#   .\start_portal.ps1 -SkipInstall         # Pula npm/pip install (mais rápido)
#   .\start_portal.ps1 -NoBrowser           # Não abre navegador
#   .\start_portal.ps1 -CleanStart          # Remove containers e inicia fresh
#   .\start_portal.ps1 -SkipInstall -NoBrowser
#

param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$SkipInstall,
    [switch]$NoBrowser,
    [switch]$CleanStart,
    [switch]$RecreateVenv
)

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptPath "..")
Set-Location $projectRoot

$logsDir = Join-Path $projectRoot "scratch\run"
New-Item -ItemType Directory -Force $logsDir | Out-Null
. (Join-Path $scriptPath "ports.ps1")

$backendOut = Join-Path $logsDir "backend.out.log"
$backendErr = Join-Path $logsDir "backend.err.log"
$frontendOut = Join-Path $logsDir "frontend.out.log"
$frontendErr = Join-Path $logsDir "frontend.err.log"
$startLog = Join-Path $logsDir "start-portal.log"
Set-Content -Path $startLog -Value "[INICIO] $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Encoding UTF8

function Write-Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Write-Ok($message) {
    Write-Host "    OK  $message" -ForegroundColor Green
}

function Write-Warn($message) {
    Write-Host "    AVISO  $message" -ForegroundColor Yellow
}

function Test-Command($command) {
    return [bool](Get-Command $command -ErrorAction SilentlyContinue)
}

$RequiredPythonMajor = 3
$RequiredPythonMinor = 14
$RecommendedNodeMajor = 24

function Get-VersionParts([string]$value) {
    $match = [regex]::Match($value, "(\d+)\.(\d+)\.(\d+)")
    if (-not $match.Success) { return $null }
    return [pscustomobject]@{
        Major = [int]$match.Groups[1].Value
        Minor = [int]$match.Groups[2].Value
        Patch = [int]$match.Groups[3].Value
    }
}

function Get-PortalPythonLauncher {
    if (Test-Command "py") {
        $py314 = & py -3.14 --version 2>&1
        if ($LASTEXITCODE -eq 0) { return @("py", "-3.14") }
    }

    if (Test-Command "python") {
        $pythonVersion = & python --version 2>&1
        $parts = Get-VersionParts ($pythonVersion -join " ")
        if ($parts -and $parts.Major -eq $RequiredPythonMajor -and $parts.Minor -ge $RequiredPythonMinor) {
            return @("python")
        }
    }

    throw "Python 3.14 nao encontrado. Instale Python 3.14.6 x64 com py launcher e recrie backend\.venv."
}

function Assert-ModernNode {
    $nodeVersion = & node --version 2>&1
    $parts = Get-VersionParts ($nodeVersion -join " ")
    if (-not $parts) { throw "Nao foi possivel identificar a versao do Node.js: $nodeVersion" }
    if ($parts.Major -lt $RecommendedNodeMajor) {
        Write-Warn "Node.js $nodeVersion detectado. O alvo suportado do Portal e Node.js 24 LTS. Atualize antes de consolidar o ambiente."
    } else {
        Write-Ok "Node.js $nodeVersion detectado."
    }
}

function Stop-ProjectProcesses {
    Write-Step "Liberando portas do Portal"
    Stop-PortalPortProcesses -Ports @($BackendPort, $FrontendPort) -LogPath $startLog
    Assert-PortalPortsFree -Ports @($BackendPort, $FrontendPort) -LogPath $startLog
    Write-Ok "Portas $BackendPort e $FrontendPort estao livres."
}

function Get-LanIp {
    $matches = ipconfig | Select-String -Pattern "IPv4"
    foreach ($match in $matches) {
        $line = $match.ToString()
        $ip = ($line -split ":")[-1].Trim()
        if ($ip -match "^\d+\.\d+\.\d+\.\d+$" -and $ip -notlike "169.254*" -and $ip -ne "127.0.0.1") {
            return $ip
        }
    }

    return "localhost"
}

function Test-PortalApiCurrent {
    param([int]$Port)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:$Port/openapi.json" -TimeoutSec 3
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500 -and $response.Content -match "/api/v1/it/tickets" -and $response.Content -match "/api/v1/purchases/requests")
    } catch {
        return $false
    }
}

function Test-PortalWebCurrent {
    param([int]$Port)
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:$Port" -TimeoutSec 3
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500)
    } catch {
        return $false
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "      PORTAL VESPER - INICIANDO AMBIENTE LOCAL" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

if (-not (Test-Command "docker")) {
    throw "Docker nao encontrado. Instale/abra o Docker Desktop antes de iniciar o Portal."
}

if (-not (Test-Command "npm")) {
    throw "npm nao encontrado. Instale Node.js 24 LTS antes de iniciar o Portal."
}

Assert-ModernNode

Stop-ProjectProcesses

if ($CleanStart) {
    Write-Step "Limpando containers e volumes Docker (CleanStart)"
    docker compose -f infra/docker-compose.yml down -v
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Containers e volumes removidos com sucesso."
    } else {
        Write-Warn "Erro ao remover containers (pode estar OK se ja nao existiam)."
    }
}

Write-Step "Subindo infraestrutura local"
docker compose -f infra/docker-compose.yml up -d db redis minio searxng adminer
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose falhou. Verifique se o Docker Desktop esta aberto."
}
Write-Ok "PostgreSQL, Redis, MinIO, SearXNG e Adminer solicitados ao Docker."

Write-Host "    Tentando iniciar n8n local opcional..."
docker compose -f infra/docker-compose.yml up -d n8n
if ($LASTEXITCODE -ne 0) {
    Write-Warn "n8n local nao iniciou, provavelmente por porta 5678 ocupada. O Portal continuara sem n8n."
} else {
    Write-Ok "n8n local solicitado ao Docker."
}

Write-Step "Preparando backend"
if ($RecreateVenv -and (Test-Path "backend\.venv")) {
    Write-Warn "Removendo backend\.venv por solicitacao explicita (-RecreateVenv)."
    Remove-Item -LiteralPath "backend\.venv" -Recurse -Force
}

if (Test-Path "backend\.venv\Scripts\python.exe") {
    $venvVersion = & backend\.venv\Scripts\python.exe --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "A venv atual esta quebrada. Execute novamente com -RecreateVenv depois de instalar Python 3.14.6. Detalhe: $venvVersion"
    }
    $venvParts = Get-VersionParts ($venvVersion -join " ")
    if (-not $venvParts -or $venvParts.Major -ne $RequiredPythonMajor -or $venvParts.Minor -lt $RequiredPythonMinor) {
        throw "A venv atual usa $venvVersion. O alvo do Portal e Python 3.14.x. Execute novamente com -RecreateVenv."
    }
} else {
    Write-Host "    Criando ambiente Python 3.14 em backend\.venv..."
    if (Test-Command "py") {
        & py -3.14 -m venv backend\.venv
    } else {
        & python -m venv backend\.venv
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Criacao da venv Python 3.14 falhou. Instale Python 3.14.6 x64 com py launcher."
    }
}

if (-not $SkipInstall) {
    Write-Host "    Conferindo dependencias Python..."
    & backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Instalacao de dependencias Python falhou."
    }
}

Write-Host "    Aplicando migracoes do banco..."
Push-Location backend
& .\.venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "Alembic upgrade falhou."
}
Pop-Location

Write-Host "    Rodando seed de desenvolvimento idempotente..."
& backend\.venv\Scripts\python.exe scripts\seed_dev.py
if ($LASTEXITCODE -ne 0) {
    throw "Seed de desenvolvimento falhou."
}
Write-Ok "Backend preparado."

Write-Step "Preparando frontend"
if (-not (Test-Path "apps\web\node_modules")) {
    Write-Host "    Instalando dependencias do frontend..."
    Push-Location apps\web
    npm install
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        throw "npm install falhou."
    }
    Pop-Location
} elseif (-not $SkipInstall) {
    Write-Host "    node_modules ja existe. Pulando npm install completo."
}
Write-Ok "Frontend preparado."

Write-Step "Iniciando API e Portal Web"
if (Test-PortalApiCurrent -Port $BackendPort) {
    Write-Warn "API atual do Portal ja responde na porta $BackendPort. Reutilizando processo existente."
} else {
    Start-Process -FilePath ".\backend\.venv\Scripts\python.exe" `
        -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port",$BackendPort,"--reload" `
        -WorkingDirectory ".\backend" `
        -RedirectStandardOutput $backendOut `
        -RedirectStandardError $backendErr `
        -WindowStyle Hidden

    Start-Sleep -Seconds 3
}

if (Test-PortalWebCurrent -Port $FrontendPort) {
    Write-Warn "Portal Web ja responde na porta $FrontendPort. Reutilizando processo existente."
} else {
    Start-Process -FilePath "npm.cmd" `
        -ArgumentList "run","dev","--","--host","0.0.0.0","--port",$FrontendPort `
        -WorkingDirectory ".\apps\web" `
        -RedirectStandardOutput $frontendOut `
        -RedirectStandardError $frontendErr `
        -WindowStyle Hidden
}

$apiUrl = "http://localhost:$BackendPort/health"
$webUrl = "http://localhost:$FrontendPort"
$swaggerUrl = "http://localhost:$BackendPort/docs"
$lanIp = Get-LanIp
$lanWebUrl = "http://$lanIp`:$FrontendPort"
$lanApiUrl = "http://$lanIp`:$BackendPort/docs"

Wait-PortalHttpOk -Url $apiUrl -Label "API" -TimeoutSeconds 60 -LogPath $startLog | Out-Null
$openApi = Wait-PortalHttpOk -Url "http://localhost:$BackendPort/openapi.json" -Label "OpenAPI" -TimeoutSeconds 20 -LogPath $startLog
if ($openApi.Content -notmatch "/api/v1/it/tickets" -or $openApi.Content -notmatch "/api/v1/purchases/requests") {
    throw "A API na porta $BackendPort respondeu, mas nao parece ser a versao atual do Portal: rotas de TI (/api/v1/it/tickets) ou Compras (/api/v1/purchases/requests) ausentes."
}
Write-Ok "OpenAPI confirmou as rotas atuais do TI e de Compras."
Wait-PortalHttpOk -Url $webUrl -Label "Portal Web" -TimeoutSeconds 60 -LogPath $startLog | Out-Null

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "      PORTAL VESPER INICIADO" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Neste computador:" -ForegroundColor White
Write-Host "  Portal:  $webUrl" -ForegroundColor Green
Write-Host "  API:     $swaggerUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Em outro computador da mesma rede:" -ForegroundColor White
Write-Host "  Portal:  $lanWebUrl" -ForegroundColor Green
Write-Host "  API:     $lanApiUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Logs:" -ForegroundColor White
Write-Host "  Backend:  $backendOut"
Write-Host "  Frontend: $frontendOut"
Write-Host ""
Write-Host "Para parar tudo que foi iniciado pelo Portal, execute: PARAR_PORTAL.bat" -ForegroundColor Yellow
Write-Host "Se outro PC nao abrir, libere as portas $FrontendPort e $BackendPort no Firewall do Windows." -ForegroundColor Yellow

if (-not $NoBrowser) {
    Start-Process $webUrl
}

