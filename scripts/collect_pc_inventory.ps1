# Script de Coleta Manual de Inventário do PC - Portal Vesper
# Execução: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\collect_pc_inventory.ps1

Write-Host "🌱 Iniciando a coleta de especificações deste computador..." -ForegroundColor Green

try {
    $Output = @{
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os = (Get-CimInstance Win32_OperatingSystem).Caption
        os_version = (Get-CimInstance Win32_OperatingSystem).Version
        manufacturer = (Get-CimInstance Win32_ComputerSystem).Manufacturer
        model = (Get-CimInstance Win32_ComputerSystem).Model
        serial_number = (Get-CimInstance Win32_BIOS).SerialNumber
        processor = (Get-CimInstance Win32_Processor).Name
        ram_total = "$([math]::round((Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB)) GB"
        motherboard = "$((Get-CimInstance Win32_BaseBoard).Manufacturer) - $((Get-CimInstance Win32_BaseBoard).Product)"
        gpu = (Get-CimInstance Win32_VideoController).Name -join ", "
        storage = (Get-CimInstance Win32_DiskDrive | ForEach-Object { "$($_.Model) ($([math]::round($_.Size / 1GB))) GB" }) -join ", "
        ip_address = (Get-NetIPAddress -InterfaceAddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } | Select-Object -First 1).IPAddress
        mac_address = (Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1).MacAddress
        domain = (Get-CimInstance Win32_ComputerSystem).Domain
        date = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }

    $Filename = "pc-inventory-$($Output.hostname).json"
    $Json = $Output | ConvertTo-Json

    # Salva o arquivo na pasta atual
    $Path = Join-Path $PSScriptRoot $Filename
    $Json | Out-File -FilePath $Path -Encoding utf8

    Write-Host "✅ Coleta concluída com sucesso!" -ForegroundColor Green
    Write-Host "💾 Arquivo salvo em: $Path" -ForegroundColor Cyan
    Write-Host "💡 Agora você pode importar este arquivo JSON na Central de TI > Ativos > Importar Especificações." -ForegroundColor Yellow
} catch {
    Write-Error "❌ Ocorreu um erro durante a coleta: $_"
}
