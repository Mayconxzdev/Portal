$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"

Set-Location $backendDir
python -m dramatiq app.modules.purchases.worker
