/**
 * Helper para detecção e integração com o Tauri 2.0 Desktop.
 */

declare global {
  interface Window {
    __TAURI_INTERNALS__?: any;
    __TAURI__?: any;
  }
}

/**
 * Retorna se o Portal Vesper está rodando dentro do aplicativo Tauri Desktop.
 */
export function isTauriApp(): boolean {
  return typeof window !== "undefined" && (!!window.__TAURI_INTERNALS__ || !!window.__TAURI__);
}

/**
 * Invoca um comando Tauri nativo de forma dinâmica para evitar erros de importação no navegador.
 */
export async function invokeTauriCommand<T>(commandName: string, args?: Record<string, any>): Promise<T> {
  if (!isTauriApp()) {
    throw new Error("Recurso nativo indisponível no navegador web.");
  }
  // Importação dinâmica do core do Tauri 2.0 para evitar erros no bundle de produção web
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<T>(commandName, args);
}

export interface DesktopEnvironment {
  os: string;
  hostname: string;
  username: string;
  app_version: string;
  is_tauri: boolean;
}

/**
 * Retorna metadados básicos do ambiente desktop nativo.
 */
export async function getDesktopEnvironment(): Promise<DesktopEnvironment | null> {
  if (!isTauriApp()) return null;
  try {
    return await invokeTauriCommand<DesktopEnvironment>("get_desktop_environment");
  } catch (error) {
    console.error("Erro ao ler ambiente do desktop:", error);
    return null;
  }
}

export interface PcInventorySnapshot {
  hostname?: string;
  username?: string;
  os?: string;
  os_version?: string;
  manufacturer?: string;
  model?: string;
  serial_number?: string;
  processor?: string;
  ram_total?: string;
  motherboard?: string;
  gpu?: string;
  storage?: string;
  ip_address?: string;
  mac_address?: string;
  domain?: string;
  date?: string;
}

/**
 * Coleta as informações de hardware do PC local chamando o comando Rust seguro.
 */
export async function collectLocalPcInventory(): Promise<PcInventorySnapshot | null> {
  if (!isTauriApp()) return null;
  try {
    const resultString = await invokeTauriCommand<string>("collect_local_pc_inventory");
    return JSON.parse(resultString) as PcInventorySnapshot;
  } catch (error) {
    console.error("Erro ao coletar inventário local:", error);
    throw error;
  }
}
