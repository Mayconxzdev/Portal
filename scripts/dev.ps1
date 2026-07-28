# Compatibilidade: o fluxo principal agora fica em start_portal.ps1.
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $scriptPath "start_portal.ps1") @args
