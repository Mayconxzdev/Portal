# ==============================================================================
# PORTAL VESPER - SETUP MODERNO DO WINDOWS
# ==============================================================================
# Padrao: modo diagnostico/dry-run, nao instala nada.
# Para instalar: abrir PowerShell como Administrador e executar:
#   .\scripts\setup_windows_modern.ps1 -Install
#
# O script usa winget quando disponivel. Revise cada pacote antes de confirmar uso
# em servidor ou maquina com politicas corporativas.
# ==============================================================================

param(
    [switch]$Install
)

$ErrorActionPreference = "Stop"

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

function Show-Version($label, $command, $CommandArgs = @()) {
    if (Test-Command $command) {
        try {
            $value = & $command @CommandArgs 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "${label}: $value"
            } else {
                Write-Warn "${label} encontrado, mas nao respondeu corretamente: $value"
            }
        } catch {
            Write-Warn "${label} encontrado, mas falhou ao executar: $($_.Exception.Message)"
        }
    } else {
        Write-Warn "$label nao encontrado"
    }
}

function Invoke-Install($id, $label) {
    $cmd = "winget install --id $id --exact --source winget --accept-package-agreements --accept-source-agreements"
    if ($Install) {
        Write-Step "Instalando $label"
        winget install --id $id --exact --source winget --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "    $cmd" -ForegroundColor DarkGray
    }
}

Write-Host "Portal Vesper - Setup moderno do Windows" -ForegroundColor Cyan
if (-not $Install) {
    Write-Warn "Modo diagnostico: nenhum software sera instalado. Use -Install em PowerShell administrador para instalar."
}

Write-Step "Versoes detectadas"
Show-Version "Git" "git" @("--version")
Show-Version "Node" "node" @("--version")
Show-Version "npm" "npm" @("--version")
Show-Version "Python" "python" @("--version")
Show-Version "Python launcher 3.14" "py" @("-3.14", "--version")
Show-Version "Docker" "docker" @("--version")
Show-Version "Docker Compose" "docker" @("compose", "version")
Show-Version "Rust/Cargo" "cargo" @("--version")

Write-Step "Pacotes recomendados"
if (-not (Test-Command "winget")) {
    throw "winget nao encontrado. Atualize o App Installer pela Microsoft Store ou instale manualmente os prerequisitos."
}

Invoke-Install "Git.Git" "Git"
Invoke-Install "OpenJS.NodeJS.LTS" "Node.js 24 LTS"
Invoke-Install "Python.Python.3.14" "Python 3.14"
Invoke-Install "Docker.DockerDesktop" "Docker Desktop"
Invoke-Install "Rustlang.Rustup" "Rustup/Cargo"
Invoke-Install "Microsoft.VisualStudio.2022.BuildTools" "Visual Studio Build Tools 2022"

Write-Step "Acoes manuais ainda necessarias"
Write-Host "1. Abra Docker Desktop e aguarde ficar running." -ForegroundColor White
Write-Host "2. Reinicie o PowerShell para atualizar PATH." -ForegroundColor White
Write-Host "3. Valide Python 3.14: py -3.14 --version" -ForegroundColor White
Write-Host "4. Valide Node 24 LTS: node --version" -ForegroundColor White
Write-Host "5. Recrie a venv do backend: .\scripts\start_portal.ps1 -RecreateVenv -NoBrowser" -ForegroundColor White
Write-Host "6. Atualize lockfiles com rede liberada: cd apps\web; npm install" -ForegroundColor White

if ($Install) {
    Write-Warn "Se algum instalador pediu reboot ou novo terminal, faca isso antes de rodar o Portal."
}
