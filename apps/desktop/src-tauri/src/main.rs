// Prevents additional console window on Windows in release, do not remove.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct DesktopEnvironment {
    pub os: String,
    pub hostname: String,
    pub username: String,
    pub app_version: String,
    pub is_tauri: bool,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct PcInventorySnapshot {
    pub hostname: Option<String>,
    pub username: Option<String>,
    pub os: Option<String>,
    pub os_version: Option<String>,
    pub manufacturer: Option<String>,
    pub model: Option<String>,
    pub serial_number: Option<String>,
    pub processor: Option<String>,
    pub ram_total: Option<String>,
    pub motherboard: Option<String>,
    pub gpu: Option<String>,
    pub storage: Option<String>,
    pub ip_address: Option<String>,
    pub mac_address: Option<String>,
    pub domain: Option<String>,
    pub date: Option<String>,
}

#[tauri::command]
fn get_desktop_environment() -> Result<DesktopEnvironment, String> {
    let os_name = if cfg!(target_os = "windows") {
        "Windows".to_string()
    } else if cfg!(target_os = "macos") {
        "macOS".to_string()
    } else {
        "Linux".to_string()
    };

    let hostname = std::env::var("COMPUTERNAME")
        .or_else(|_| std::env::var("HOSTNAME"))
        .unwrap_or_else(|_| "Unknown".to_string());

    let username = std::env::var("USERNAME")
        .or_else(|_| std::env::var("USER"))
        .unwrap_or_else(|_| "Unknown".to_string());

    Ok(DesktopEnvironment {
        os: os_name,
        hostname,
        username,
        app_version: env!("CARGO_PKG_VERSION").to_string(),
        is_tauri: true,
    })
}

#[tauri::command]
fn collect_local_pc_inventory() -> Result<String, String> {
    if !cfg!(target_os = "windows") {
        return Err("Coleta automática disponível apenas em sistemas Windows.".to_string());
    }

    // Script PowerShell embutido, limpo e imutável (sem parâmetros externos)
    let ps_script = r#"
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
$Output | ConvertTo-Json -Compress
"#;

    let output = Command::new("powershell")
        .args(["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_script])
        .output()
        .map_err(|e| format!("Falha ao executar o PowerShell: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        return Err(format!("Erro na execução do script de inventário: {}", stderr));
    }

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    Ok(stdout.trim().to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_desktop_environment,
            collect_local_pc_inventory
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
