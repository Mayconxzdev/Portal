import React, { useMemo, useState } from 'react';
import { Cpu, Layers, Laptop, Plus, Search, Upload } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Select } from '../ui/Select';
import { EmptyState } from '../ui/EmptyState';

export interface ITAssetsProps {
  assetsList: any[];
  onOpenAssetDetail: (asset: any) => void;
  onCollectLocal: () => void;
  onCreateAsset: () => void;
  onCsvImport: () => void;
  isTauri: boolean;
  collectLoading: boolean;
  activeAssetTypes: { value: string; label: string }[];
}

const assetStatusLabel = (status?: string) => {
  const labels: Record<string, string> = {
    EM_USO: 'Em uso',
    DISPONIVEL: 'Disponível',
    MANUTENCAO: 'Manutenção',
    APOSENTADO: 'Aposentado',
    PERDIDO: 'Perdido',
  };
  return status ? labels[status] || status : 'Sem status';
};

const assetTypeLabel = (type?: string) => {
  const labels: Record<string, string> = {
    PC: 'Computador Desktop',
    NOTEBOOK: 'Notebook / Laptop',
    SERVIDOR: 'Servidor',
    SWITCH: 'Switch de Rede',
    ROUTER: 'Roteador',
    OUTRO: 'Outro Equipamento',
  };
  return type ? labels[type] || type : 'Tipo não informado';
};

export const ITAssets: React.FC<ITAssetsProps> = ({
  assetsList,
  onOpenAssetDetail,
  onCollectLocal,
  onCreateAsset,
  onCsvImport,
  isTauri,
  collectLoading,
  activeAssetTypes,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  const filteredAssets = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();
    return assetsList.filter((asset) => {
      const matchesSearch =
        !query ||
        asset.name?.toLowerCase().includes(query) ||
        asset.hostname?.toLowerCase().includes(query) ||
        asset.asset_tag?.toLowerCase().includes(query) ||
        asset.serial_number?.toLowerCase().includes(query) ||
        asset.model?.toLowerCase().includes(query) ||
        asset.assigned_user?.username?.toLowerCase().includes(query);

      return matchesSearch && (!selectedType || asset.asset_type === selectedType) && (!selectedStatus || asset.status === selectedStatus);
    });
  }, [assetsList, searchTerm, selectedType, selectedStatus]);

  const statusOptions = [
    { value: '', label: 'Todos os status' },
    { value: 'EM_USO', label: 'Em uso' },
    { value: 'DISPONIVEL', label: 'Disponível' },
    { value: 'MANUTENCAO', label: 'Em manutenção' },
    { value: 'APOSENTADO', label: 'Aposentado' },
  ];

  return (
    <div className="space-y-6">
      <div className="section-card it-product-header">
        <div>
          <span className="product-eyebrow">Inventário corporativo</span>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">Ativos de TI</h2>
          <p className="text-xs text-slate-400">
            Controle computadores, notebooks, periféricos e histórico de manutenção sem planilhas soltas.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant={isTauri ? 'primary' : 'secondary'}
            onClick={isTauri ? onCollectLocal : undefined}
            isLoading={collectLoading}
            disabled={!isTauri}
            leftIcon={<Cpu size={15} />}
            title={isTauri ? 'Coletar inventário deste computador' : 'Disponível apenas no app desktop/Tauri.'}
          >
            Coletar este PC
          </Button>
          <Button variant="secondary" onClick={onCsvImport} leftIcon={<Upload size={15} />}>
            Importar CSV
          </Button>
          <Button variant="primary" onClick={onCreateAsset} leftIcon={<Plus size={16} />}>
            Novo ativo
          </Button>
        </div>
      </div>

      <Card className="p-4 flex flex-col md:flex-row gap-3 product-filter-card">
        <div className="product-search-box flex-1">
          <Search size={16} className="text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por hostname, patrimônio, serial, modelo ou usuário..."
            className="w-full bg-transparent border-none outline-none text-xs text-white placeholder-slate-500 py-1.5"
          />
        </div>
        <Select
          label=""
          value={selectedType}
          options={[{ value: '', label: 'Todos os tipos' }, ...activeAssetTypes]}
          onChange={(e) => setSelectedType(e.target.value)}
          className="!min-h-[38px] text-xs md:w-48"
        />
        <Select
          label=""
          value={selectedStatus}
          options={statusOptions}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="!min-h-[38px] text-xs md:w-48"
        />
      </Card>

      <div className="data-card-grid">
        {filteredAssets.map((asset) => (
          <Card
            key={asset.id}
            variant="interactive"
            className="asset-product-card"
            onClick={() => onOpenAssetDetail(asset)}
            role="button"
            aria-label={`Ver detalhes do ativo ${asset.name || asset.hostname || ''}`}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onOpenAssetDetail(asset);
              }
            }}
          >
            <div className="flex justify-between items-start gap-3">
              <div className="asset-product-icon"><Laptop size={22} /></div>
              <span className={`status-mini status-mini--${String(asset.status || '').toLowerCase()}`}>
                {assetStatusLabel(asset.status)}
              </span>
            </div>
            <div>
              <span className="ticket-number-chip">{asset.asset_tag || 'Sem patrimônio'}</span>
              <h3 className="text-base font-bold text-white mt-2 line-clamp-1">{asset.name || asset.hostname || 'Ativo sem nome'}</h3>
              <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                {asset.model || asset.manufacturer || 'Equipamento aguardando ficha técnica completa.'}
              </p>
            </div>
            <div className="ticket-product-meta">
              <div className="ticket-meta-pill"><Layers size={13} /> {assetTypeLabel(asset.asset_type)}</div>
              <div className="ticket-meta-pill">Serial: {asset.serial_number || 'não informado'}</div>
              <div className="ticket-meta-pill">Usuário: {asset.assigned_user?.username || asset.assigned_to?.username || 'sem vínculo'}</div>
            </div>
            <div className="flex justify-between items-center pt-3 border-t border-white/5 text-[11px] font-bold text-slate-400">
              <span>{asset.hostname || 'Hostname não informado'}</span>
              <Button variant="secondary" size="sm" onClick={(event) => { event.stopPropagation(); onOpenAssetDetail(asset); }}>
                Ver ficha
              </Button>
            </div>
          </Card>
        ))}

        {filteredAssets.length === 0 && (
          <div className="col-span-2 py-12">
            <EmptyState
              icon={<Laptop size={48} />}
              title="Nenhum ativo encontrado"
              description="Nenhum equipamento corresponde aos filtros aplicados."
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default ITAssets;
