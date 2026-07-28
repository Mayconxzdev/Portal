# Portal Vesper - utilitarios de portas locais

function Write-PortalLog {
    param(
        [string]$Message,
        [string]$LogPath
    )
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $Message
    if ($LogPath) {
        Add-Content -Path $LogPath -Value $line -Encoding UTF8
    }
}

function Get-PortalPortProcess {
    param([int[]]$Ports = @(8000, 5173))

    $items = @()
    foreach ($port in $Ports) {
        $connections = @()
        try {
            $connections = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction Stop)
        } catch {}

        $lines = netstat -ano | Select-String -Pattern "LISTENING"
        foreach ($line in $lines) {
            $text = ($line.ToString() -replace "\s+", " ").Trim()
            $parts = $text.Split(" ")
            if ($parts.Count -ge 5 -and $parts[1] -match ":$port$" -and $parts[-1] -match "^\d+$") {
                $connections += [pscustomobject]@{
                    LocalAddress = ($parts[1] -replace ":\d+$", "")
                    LocalPort = $port
                    OwningProcess = [int]$parts[-1]
                }
            }
        }

        foreach ($connection in $connections) {
            $pidValue = [int]$connection.OwningProcess
            $processName = "desconhecido"
            $path = ""
            $commandLine = ""
            try {
                $proc = Get-Process -Id $pidValue -ErrorAction Stop
                $processName = $proc.ProcessName
                $path = $proc.Path
            } catch {}
            try {
                $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction Stop
                $commandLine = $cim.CommandLine
            } catch {}
            if ($processName -eq "desconhecido" -and -not $commandLine) {
                # Netstat/Get-NetTCPConnection can briefly report a LISTENING PID that has already exited.
                # Treat it as stale so a just-stopped Portal does not block the next start.
                continue
            }
            $items += [pscustomobject]@{
                Port = $port
                Pid = $pidValue
                ProcessName = $processName
                Path = $path
                CommandLine = $commandLine
                LocalAddress = $connection.LocalAddress
            }
        }
    }

    return $items | Sort-Object Port, Pid | Group-Object Port, Pid | ForEach-Object { $_.Group[0] }
}

function Stop-PortalPortProcesses {
    param(
        [int[]]$Ports = @(8000, 5173),
        [string]$LogPath
    )

    $processes = @(Get-PortalPortProcess -Ports $Ports)
    if ($processes.Count -eq 0) {
        Write-PortalLog "Portas $($Ports -join ', ') livres." $LogPath
        return
    }

    foreach ($item in $processes) {
        Write-PortalLog "Encerrando processo na porta $($item.Port): PID $($item.Pid) $($item.ProcessName) $($item.CommandLine)" $LogPath
        try {
            $proc = Get-Process -Id $item.Pid -ErrorAction Stop
            if ($proc.MainWindowHandle -ne 0) {
                [void]$proc.CloseMainWindow()
                Start-Sleep -Seconds 2
            }
        } catch {}

        $isRunning = $true
        if (-not (Get-Process -Id $item.Pid -ErrorAction SilentlyContinue)) {
            $isRunning = $false
        }
        if ($isRunning) {
            try {
                Stop-Process -Id $item.Pid -Force -ErrorAction Stop
                Write-PortalLog "PID $($item.Pid) encerrado via PowerShell." $LogPath
            } catch {
                Write-PortalLog "PowerShell nao encerrou PID $($item.Pid): $($_.Exception.Message)" $LogPath
                try {
                    $taskkillOutput = taskkill /PID $item.Pid /T /F 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        Write-PortalLog "PID $($item.Pid) encerrado via taskkill." $LogPath
                    } else {
                        Write-PortalLog "taskkill nao encerrou PID $($item.Pid): $taskkillOutput" $LogPath
                    }
                } catch {
                    Write-PortalLog "taskkill nao encerrou PID $($item.Pid): $($_.Exception.Message)" $LogPath
                }
            }
        }
    }
}

function Assert-PortalPortsFree {
    param(
        [int[]]$Ports = @(8000, 5173),
        [string]$LogPath
    )
    Start-Sleep -Seconds 2
    $remaining = @(Get-PortalPortProcess -Ports $Ports)
    if ($remaining.Count -gt 0) {
        foreach ($item in $remaining) {
            Write-PortalLog "Porta ainda ocupada: $($item.Port) PID $($item.Pid) $($item.ProcessName) $($item.CommandLine)" $LogPath
        }
        throw "As portas $($Ports -join ', ') continuam ocupadas. Execute PARAR_PORTAL.bat como administrador ou reinicie o Windows antes de iniciar o Portal."
    }
    Write-PortalLog "Portas $($Ports -join ', ') confirmadas como livres." $LogPath
}

function Wait-PortalHttpOk {
    param(
        [string]$Url,
        [string]$Label,
        [int]$TimeoutSeconds = 60,
        [string]$LogPath
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Write-PortalLog "$Label respondeu em $Url" $LogPath
                return $response
            }
        } catch {}
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    throw "$Label nao respondeu em $Url dentro de $TimeoutSeconds segundos."
}
