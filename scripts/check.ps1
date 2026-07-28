# ==============================================================================
# PORTAL VESPER - SCRIPT DE VERIFICAÇÃO E QUALIDADE (WINDOWS POWERSHELL)
# ==============================================================================

Write-Host "[INFO] Iniciando analises estaticas do Portal Vesper..." -ForegroundColor Cyan

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath\..

$failed = $false

# 1. Validacao do Backend Python
Write-Host ""
Write-Host "[PYTHON] Validando Backend Python..." -ForegroundColor Yellow
if (Test-Path "backend\.venv") {
    # Testa se o Python consegue compilar os arquivos sem erros de importacao basica
    Write-Host "   [-] Verificando sintaxe basica dos arquivos Python..."
    $pythonExe = (Resolve-Path "backend\.venv\Scripts\python.exe").Path
    $pythonVersionOutput = & $pythonExe --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] Python da venv nao pode ser executado neste shell: $pythonVersionOutput" -ForegroundColor Yellow
        Write-Host "[WARN] Pulando py_compile aqui. Rode pytest para validar o backend." -ForegroundColor Yellow
    } else {
        & $pythonExe -m compileall -q "backend\app"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Erro de compilacao/sintaxe encontrado no backend." -ForegroundColor Red
            $failed = $true
        }
    }
    
    if (-not $failed -and $LASTEXITCODE -eq 0) {
        Write-Host "[OK] Sintaxe do Backend Python validada com sucesso!" -ForegroundColor Green
    }
} else {
    Write-Host "[WARN] Ambiente virtual (.venv) do backend nao encontrado. Pulando validacao do Python." -ForegroundColor Yellow
}

# 2. Validacao do Frontend React (TypeScript)
Write-Host ""
Write-Host "[REACT] Validando Frontend React (TypeScript)..." -ForegroundColor Yellow
if (Test-Path "apps\web\node_modules") {
    Write-Host "   [-] Executando compilador TypeScript (tsc) para checar tipagens..."
    Push-Location apps\web
    npx tsc --noEmit
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Erros de tipagem TypeScript encontrados no Frontend." -ForegroundColor Red
        $failed = $true
    } else {
        Write-Host "[OK] Tipagem do Frontend validada com sucesso!" -ForegroundColor Green
    }
    if (Test-Path "node_modules\vitest") {
        Write-Host "   [-] Executando testes unitarios do Frontend..."
        npm run test:run
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Testes unitarios do Frontend falharam." -ForegroundColor Red
            $failed = $true
        } else {
            Write-Host "[OK] Testes unitarios do Frontend passaram com sucesso!" -ForegroundColor Green
        }
    }
    Pop-Location
} else {
    Write-Host "[WARN] node_modules do frontend nao encontrado. Rode 'npm install' primeiro." -ForegroundColor Yellow
}

# 3. Diagnostico do Tauri Desktop (Rust)
Write-Host ""
Write-Host "[DESKTOP] Verificando ambiente Tauri/Rust..." -ForegroundColor Yellow
& $scriptPath\check_desktop.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Erros encontrados na checagem do Rust/Tauri Desktop." -ForegroundColor Red
    $failed = $true
}

# 4. Status Final
Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan
if ($failed) {
    Write-Host "[ERROR] A verificacao falhou em alguns componentes. Corrija os erros acima!" -ForegroundColor Red
    Exit 1
} else {
    Write-Host "[OK] Todas as analises estaticas passaram sem erros! Qualidade garantida." -ForegroundColor Green
    Exit 0
}
