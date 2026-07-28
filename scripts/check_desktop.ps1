# ==============================================================================
# PORTAL VESPER - DIAGNÓSTICO DO AMBIENTE TAURI DESKTOP (RUST)
# ==============================================================================

Write-Host "[INFO] Iniciando diagnóstico do ambiente Desktop (Tauri/Rust)..." -ForegroundColor Cyan

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath\..

$cargoExists = $false
$rustcExists = $false
$tauriCliExists = $false

# 1. Verificar cargo
$cargoCheck = Get-Command cargo -ErrorAction SilentlyContinue
if ($cargoCheck) {
    $cargoExists = $true
    $cargoVersion = & cargo --version
    Write-Host "[OK] Cargo detectado: $cargoVersion" -ForegroundColor Green
} else {
    Write-Host "[WARN] Cargo (gerenciador do Rust) não encontrado no PATH." -ForegroundColor Yellow
}

# 2. Verificar rustc
$rustcCheck = Get-Command rustc -ErrorAction SilentlyContinue
if ($rustcCheck) {
    $rustcExists = $true
    $rustcVersion = & rustc --version
    Write-Host "[OK] Rustc (compilador) detectado: $rustcVersion" -ForegroundColor Green
} else {
    Write-Host "[WARN] Rustc (compilador Rust) não encontrado no PATH." -ForegroundColor Yellow
}

# 3. Verificar Tauri CLI (npx tauri ou cargo tauri)
$tauriCliCheck = $false
# Verificar tauri via cargo
if ($cargoExists) {
    $cargoTauri = & cargo tauri --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $cargoTauri) {
        $tauriCliExists = $true
        Write-Host "[OK] Tauri CLI (cargo) detectado: $cargoTauri" -ForegroundColor Green
    }
}
if (-not $tauriCliExists) {
    # Verificar tauri via npx tauri
    $npxTauri = & npx tauri --version 2>&1
    if ($LASTEXITCODE -eq 0 -and $npxTauri) {
        $tauriCliExists = $true
        Write-Host "[OK] Tauri CLI (npx) detectado: $npxTauri" -ForegroundColor Green
    }
}

if (-not $tauriCliExists) {
    Write-Host "[WARN] Tauri CLI não detectado via cargo ou npx." -ForegroundColor Yellow
}

# 4. Executar cargo check se o ambiente de compilador existir
if ($cargoExists -and $rustcExists) {
    Write-Host ""
    Write-Host "[TAURI] Executando cargo check para validação de compilabilidade..." -ForegroundColor Yellow
    Push-Location apps\desktop\src-tauri
    & cargo check
    $cargoExitCode = $LASTEXITCODE
    Pop-Location
    
    if ($cargoExitCode -eq 0) {
        Write-Host "[OK] Cargo check concluído com sucesso no código Rust!" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Cargo check falhou. Erros de compilação ou sintaxe no código Rust." -ForegroundColor Red
        # Como o compilador existe e o check falhou, consideramos isso um erro real de código
        Exit 1
    }
} else {
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Yellow
    Write-Host "PENDÊNCIA DE INFRAESTRUTURA LOCAL - AMBIENTE RUST/TAURI INCOMPLETO" -ForegroundColor Yellow
    Write-Host "Como instalar o compilador Rust e Tauri CLI no Windows:" -ForegroundColor Cyan
    Write-Host "1. Acesse https://rustup.rs e baixe o instalador 'rustup-init.exe' para Windows." -ForegroundColor White
    Write-Host "2. Execute o instalador e escolha a opção padrão (instalar ferramentas MSVC C++Build se solicitado)." -ForegroundColor White
    Write-Host "3. Abra um novo terminal do PowerShell para atualizar o PATH." -ForegroundColor White
    Write-Host "4. Instale o Tauri CLI executando: cargo install tauri-cli --version '^2.11.3' --locked" -ForegroundColor White
    Write-Host "5. Em seguida, valide com: cargo check" -ForegroundColor White
    Write-Host "==============================================================================" -ForegroundColor Yellow
    Write-Host "[INFO] Continuando pipeline web. A build do desktop Tauri está suspensa localmente." -ForegroundColor Cyan
}

Exit 0
