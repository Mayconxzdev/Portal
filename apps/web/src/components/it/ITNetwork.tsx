import React, { useState } from 'react';
import { Network, Plus, Server, HardDrive, Shield, User, Clock, Info } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { EmptyState } from '../ui/EmptyState';
import { Drawer } from '../ui/Drawer';

export interface ITNetworkProps {
  networkItems: any[];
  nasFolders: any[];
  onNewNetwork: () => void;
  onEditNetwork: (net: any) => void;
  onDeleteNetwork: (net: any) => void;
  onNewNas: () => void;
  onEditNas: (nas: any) => void;
  onDeleteNas: (nas: any) => void;
}

export const ITNetwork: React.FC<ITNetworkProps> = ({
  networkItems,
  nasFolders,
  onNewNetwork,
  onEditNetwork,
  onDeleteNetwork,
  onNewNas,
  onEditNas,
  onDeleteNas,
}) => {
  const [selectedNetworkItem, setSelectedNetworkItem] = useState<any | null>(null);
  const [selectedNasFolder, setSelectedNasFolder] = useState<any | null>(null);

  // Humanize permission level
  const humanizePermission = (level: string) => {
    switch (level) {
      case 'LEITURA':
        return 'Leitura';
      case 'ESCRITA':
        return 'Leitura e escrita';
      case 'ADMIN':
        return 'Administrador da Pasta';
      default:
        return level || 'Sem acesso';
    }
  };

  const humanizeNetworkType = (type?: string) => ({
    SWITCH: 'Switch',
    ROUTER: 'Roteador',
    ACCESS_POINT: 'Access point',
    FIREWALL: 'Firewall',
    NAS: 'NAS / QNAP',
  }[String(type || '').toUpperCase()] || type || 'Equipamento de rede');

  const humanizeNetworkStatus = (status?: string) => ({
    ACTIVE: 'Ativo',
    ONLINE: 'Online',
    OFFLINE: 'Offline',
    MAINTENANCE: 'Em manutenção',
    INACTIVE: 'Inativo',
  }[String(status || '').toUpperCase()] || status || 'Não informado');

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              🌐 Equipamentos de Rede & Pastas NAS (QNAP)
            </h2>
            <p className="text-xs text-slate-400 mt-1 font-medium">
              Controle físico e lógico de ativos de rede e infraestrutura de armazenamento de arquivos.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Equipamentos de Rede */}
          <div className="space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                🔌 Itens de Rede
              </h3>
              <Button size="sm" variant="primary" onClick={onNewNetwork} leftIcon={<Plus size={12} />}>
                Equipamento
              </Button>
            </div>
            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1 scrollbar-thin">
              {networkItems.map((net) => (
                <div 
                  key={net.id} 
                  onClick={() => setSelectedNetworkItem(net)}
                  className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 hover:border-slate-700 transition-colors flex justify-between items-center cursor-pointer text-left"
                >
                  <div>
                    <strong className="text-sm text-white block">{net.name}</strong>
                    <span className="text-xs text-slate-400 font-medium">IP: {net.ip_address || "sem IP"} | Local: {net.location || "sem local"}</span>
                  </div>
                  <span className="text-[10px] text-sky-400 font-bold shrink-0">Ficha ➔</span>
                </div>
              ))}
              {networkItems.length === 0 && (
                <EmptyState
                  icon={<Network size={32} className="text-slate-600" />}
                  title="Sem equipamentos"
                  description="Nenhum roteador, switch ou access point cadastrado."
                />
              )}
            </div>
          </div>

          {/* Pastas NAS */}
          <div className="space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                💾 Mapeamento de Pastas NAS
              </h3>
              <Button size="sm" variant="primary" onClick={onNewNas} leftIcon={<Plus size={12} />}>
                Pasta
              </Button>
            </div>
            <p className="text-xs text-slate-400 font-semibold leading-relaxed">
              Mapeamento de compartilhamento de arquivos e QNAP da empresa, atendendo aos requisitos de conformidade ISO 9001.
            </p>
            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1 scrollbar-thin">
              {nasFolders.map((folder) => (
                <div 
                  key={folder.id} 
                  onClick={() => setSelectedNasFolder(folder)}
                  className="p-4 rounded-xl border border-slate-800 bg-slate-950/40 hover:border-slate-700 transition-colors flex justify-between items-center cursor-pointer text-left"
                >
                  <div>
                    <strong className="text-sm text-white block">{folder.name} [Letra: {folder.drive_letter || "s/ letra"}]</strong>
                    <span className="text-xs text-slate-400 font-medium truncate block max-w-[280px]">Caminho: {folder.network_path || "não informado"}</span>
                    <span className="inline-block text-[10px] text-indigo-400 bg-indigo-950/40 border border-indigo-900/50 px-1.5 py-0.5 rounded-full mt-1.5 font-bold">
                      Permissão: {humanizePermission(folder.permission_level)}
                    </span>
                  </div>
                  <span className="text-[10px] text-sky-400 font-bold shrink-0">Ficha ➔</span>
                </div>
              ))}
              {nasFolders.length === 0 && (
                <EmptyState
                  icon={<HardDrive size={32} className="text-slate-600" />}
                  title="Sem pastas mapeadas"
                  description="Nenhuma partição ou pasta compartilhada do QNAP NAS cadastrada."
                />
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Drawer: Detalhe do Equipamento de Rede */}
      {selectedNetworkItem && (
        <Drawer
          open={!!selectedNetworkItem}
          onClose={() => setSelectedNetworkItem(null)}
          title={`Ficha: ${selectedNetworkItem.name}`}
          description={`${humanizeNetworkType(selectedNetworkItem.item_type)} em ${selectedNetworkItem.location || 'local não informado'}`}
        >
          <div className="space-y-4">
            <div className="bg-slate-950/40 p-4 rounded-xl border border-white/5 space-y-3">
              <h4 className="text-xs font-black text-slate-500 uppercase tracking-wider">Especificações de Rede</h4>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 block font-bold">Nome do Ativo</span>
                  <span className="text-slate-200 font-black text-sm">{selectedNetworkItem.name}</span>
                </div>
                <div>
                  <span className="text-slate-500 block font-bold">Tipo de Item</span>
                  <span className="text-slate-200 font-black text-sm">{humanizeNetworkType(selectedNetworkItem.item_type)}</span>
                </div>
                <div>
                  <span className="text-slate-500 block font-bold">Endereço IP</span>
                  <span className="text-slate-200 font-black text-sm font-mono">{selectedNetworkItem.ip_address || "Não atribuído"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block font-bold">Localização</span>
                  <span className="text-slate-200 font-black text-sm">{selectedNetworkItem.location || "Não informado"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block font-bold">Status Operacional</span>
                  <span className="text-slate-200 font-black text-sm">{humanizeNetworkStatus(selectedNetworkItem.status)}</span>
                </div>
              </div>
            </div>

            {selectedNetworkItem.notes && (
              <div className="bg-slate-950/40 p-4 rounded-xl border border-white/5 space-y-1 text-xs">
                <span className="text-slate-500 block font-bold uppercase tracking-wider text-[10px]">Observações Técnicas</span>
                <p className="text-slate-300 leading-relaxed font-medium">{selectedNetworkItem.notes}</p>
              </div>
            )}

            <div className="bg-slate-950/40 p-4 rounded-xl border border-white/5 space-y-2 text-xs text-left">
              <span className="text-slate-500 block font-bold uppercase tracking-wider text-[10px]">Auditoria & Tempo</span>
              <div className="flex items-center gap-1.5 text-slate-400 font-medium">
                <Clock size={13} />
                <span>Última revisão: {selectedNetworkItem.updated_at ? new Date(selectedNetworkItem.updated_at).toLocaleDateString('pt-BR') : "Sem registro"}</span>
              </div>
            </div>
          </div>

          <div className="flex gap-2 pt-4 border-t border-slate-800 mt-4">
            <Button
              variant="secondary"
              size="sm"
              className="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-bold"
              onClick={() => {
                onEditNetwork(selectedNetworkItem);
                setSelectedNetworkItem(null);
              }}
            >
              Editar
            </Button>
            <Button
              variant="danger"
              size="sm"
              className="flex-1 font-bold"
              onClick={() => {
                onDeleteNetwork(selectedNetworkItem);
                setSelectedNetworkItem(null);
              }}
            >
              Excluir
            </Button>
            <Button
              variant="secondary"
              size="sm"
              className="flex-1 border-slate-800 text-slate-300 hover:bg-slate-800"
              onClick={() => setSelectedNetworkItem(null)}
            >
              Fechar
            </Button>
          </div>
        </Drawer>
      )}

      {/* Drawer: Detalhe de Pasta NAS */}
      {selectedNasFolder && (
        <Drawer
          open={!!selectedNasFolder}
          onClose={() => setSelectedNasFolder(null)}
          title={`Pasta Mapeada: ${selectedNasFolder.name}`}
          description={`Armazenamento NAS / QNAP — Drive ${selectedNasFolder.drive_letter || "N/A"}`}
        >
          <div className="space-y-4 text-xs font-bold text-slate-300">
            <div className="bg-slate-950/40 p-4 rounded-xl border border-white/5 space-y-3">
              <h4 className="text-xs font-black text-slate-500 uppercase tracking-wider">Diretório & Acesso</h4>
              <div className="space-y-2">
                <div>
                  <span className="text-slate-500 block text-[10px]">Caminho de Rede</span>
                  <span className="text-slate-200 block text-xs font-mono select-all bg-slate-950 p-2 rounded border border-white/5">{selectedNasFolder.network_path || "Não configurado"}</span>
                </div>
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <span className="text-slate-500 block text-[10px]">Letra Mapeada</span>
                    <span className="text-white text-sm font-black">{selectedNasFolder.drive_letter || "Nenhuma"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Nível de Permissão</span>
                    <span className="text-sky-400 text-sm font-black">{humanizePermission(selectedNasFolder.permission_level)}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-slate-950/40 p-4 rounded-xl border border-white/5 space-y-2">
              <h4 className="text-xs font-black text-slate-500 uppercase tracking-wider flex items-center gap-1.5"><User size={13} /> Usuários com acesso</h4>
              <p className="text-xs text-slate-300 leading-relaxed font-semibold">
                Responsável cadastrado: <span className="text-sky-400 font-black">{selectedNasFolder.user?.username || "Técnico de TI (Geral)"}</span>
              </p>
            </div>

            {selectedNasFolder.notes && (
              <div className="bg-slate-950/40 p-4 rounded-xl border border-white/5 space-y-1">
                <span className="text-slate-550 block text-[10px] uppercase">Finalidade / Observações</span>
                <p className="text-slate-300 font-medium leading-relaxed">{selectedNasFolder.notes}</p>
              </div>
            )}

            <div className="bg-slate-950/40 p-4 rounded-xl border border-white/5 space-y-1 text-left">
              <span className="text-slate-500 block text-[10px] uppercase">Auditoria de Segurança</span>
              <div className="flex items-center gap-1.5 text-slate-400 font-medium">
                <Clock size={13} />
                <span>Última revisão: {selectedNasFolder.updated_at ? new Date(selectedNasFolder.updated_at).toLocaleDateString('pt-BR') : "Sem registro"}</span>
              </div>
            </div>
          </div>

          <div className="flex gap-2 pt-4 border-t border-slate-800 mt-4">
            <Button
              variant="secondary"
              size="sm"
              className="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-bold"
              onClick={() => {
                onEditNas(selectedNasFolder);
                setSelectedNasFolder(null);
              }}
            >
              Editar
            </Button>
            <Button
              variant="danger"
              size="sm"
              className="flex-1 font-bold"
              onClick={() => {
                onDeleteNas(selectedNasFolder);
                setSelectedNasFolder(null);
              }}
            >
              Excluir
            </Button>
            <Button
              variant="secondary"
              size="sm"
              className="flex-1 border-slate-800 text-slate-300 hover:bg-slate-800"
              onClick={() => setSelectedNasFolder(null)}
            >
              Fechar
            </Button>
          </div>
        </Drawer>
      )}
    </div>
  );
};

export default ITNetwork;
