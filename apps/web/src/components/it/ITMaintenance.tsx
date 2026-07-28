import React from 'react';
import { Wrench, Plus, Calendar, Clock, User, Link2, Laptop } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { EmptyState } from '../ui/EmptyState';
import { KodaMascot } from '../ui/KodaMascot';

export interface ITMaintenanceProps {
  maintenances: any[];
  assetsList: any[];
  onNew: () => void;
  onEdit: (maint: any) => void;
  onDelete: (maint: any) => void;
}

export const ITMaintenance: React.FC<ITMaintenanceProps> = ({
  maintenances,
  assetsList = [],
  onNew,
  onEdit,
  onDelete,
}) => {
  // Map asset_id to Asset Name/Hostname
  const getAssetDetails = (assetId: number | null) => {
    if (!assetId) return null;
    return assetsList.find((a) => a.id === assetId);
  };

  const humanizeStatus = (status: string) => {
    switch (status) {
      case 'AGENDADA':
        return 'Agendada';
      case 'EM_ANDAMENTO':
        return 'Em Andamento';
      case 'CONCLUIDA':
        return 'Concluída';
      default:
        return status;
    }
  };

  // Sort by date (newest/upcoming first)
  const sortedMaintenances = [...maintenances].sort((a, b) => {
    const dateA = new Date(a.scheduled_at || a.created_at).getTime();
    const dateB = new Date(b.scheduled_at || b.created_at).getTime();
    return dateB - dateA;
  });

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              🔧 Manutenções Preventivas e Corretivas
            </h2>
            <p className="text-xs text-slate-400 mt-1 font-medium">
              Controle de chamados de hardware, limpezas físicas, atualizações e reparação geral de ativos.
            </p>
          </div>
          <Button size="sm" variant="primary" onClick={onNew} leftIcon={<Plus size={14} />}>
            Agendar Manutenção
          </Button>
        </div>

        {/* Timeline Header Helper */}
        <div className="p-4 rounded-2xl bg-slate-950/20 border border-slate-800 flex items-center gap-4 mb-6">
          <KodaMascot variant="working" size="sm" withGlow />
          <div>
            <h4 className="text-sm font-bold text-sky-400">Cronograma de Manutenção de TI</h4>
            <p className="text-xs text-slate-350 leading-relaxed font-semibold">
              Garanta a vida útil dos equipamentos realizando limpezas físicas semestrais e auditorias de disco preventivas.
            </p>
          </div>
        </div>

        {/* Timeline Layout */}
        {sortedMaintenances.length > 0 ? (
          <div className="relative pl-6 border-l-2 border-slate-800 space-y-6 text-left">
            {sortedMaintenances.map((maint) => {
              const asset = getAssetDetails(maint.asset_id);
              const dateVal = maint.scheduled_at || maint.created_at;

              return (
                <div key={maint.id} className="relative">
                  {/* Timeline bullet dot */}
                  <span className={`absolute -left-[31px] top-1.5 w-4 h-4 rounded-full border-4 border-slate-900 ${
                    maint.status === 'CONCLUIDA' ? 'bg-emerald-500' :
                    maint.status === 'EM_ANDAMENTO' ? 'bg-sky-500' : 'bg-amber-500'
                  }`}></span>

                  <Card className="p-5 border border-slate-800/80 bg-slate-950/20 hover:border-slate-700 transition-colors space-y-4">
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <strong className="text-base text-white">{maint.title}</strong>
                          <Badge
                            variant={
                              maint.status === 'CONCLUIDA' ? 'success' :
                              maint.status === 'EM_ANDAMENTO' ? 'primary' : 'warning'
                            }
                            className="text-[10px]"
                          >
                            {humanizeStatus(maint.status)}
                          </Badge>
                        </div>
                        {dateVal && (
                          <span className="text-[10px] text-slate-500 font-bold block mt-1 flex items-center gap-1">
                            <Clock size={11} /> {new Date(dateVal).toLocaleDateString('pt-BR')}
                          </span>
                        )}
                      </div>

                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => onEdit(maint)}
                          className="text-[10px] py-1 bg-slate-900 border-slate-850 hover:bg-slate-800 text-slate-300"
                        >
                          Editar
                        </Button>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => onDelete(maint)}
                          className="text-[10px] py-1 font-bold"
                        >
                          Excluir
                        </Button>
                      </div>
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed font-semibold">
                      {maint.description || "Nenhuma descrição detalhada informada."}
                    </p>

                    {/* Meta information row */}
                    <div className="flex flex-wrap gap-3 pt-3 border-t border-slate-900/60 text-[10px] text-slate-450 font-bold">
                      {asset && (
                        <div className="flex items-center gap-1 text-sky-400 bg-sky-950/10 border border-sky-900/20 px-2 py-0.5 rounded-full">
                          <Laptop size={11} />
                          <span>Ativo: {asset.hostname || asset.name} ({asset.asset_tag})</span>
                        </div>
                      )}
                      {maint.ticket_id && (
                        <div className="flex items-center gap-1 text-indigo-400 bg-indigo-950/10 border border-indigo-900/20 px-2 py-0.5 rounded-full">
                          <Link2 size={11} />
                          <span>Chamado #{maint.ticket_id}</span>
                        </div>
                      )}
                      {maint.performed_by_user_id && (
                        <div className="flex items-center gap-1 text-slate-400 bg-slate-900 border border-slate-850 px-2 py-0.5 rounded-full">
                          <User size={11} />
                          <span>Técnico ID: {maint.performed_by_user_id}</span>
                        </div>
                      )}
                    </div>
                  </Card>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState
            icon={<Wrench size={40} className="text-slate-600" />}
            title="Nenhuma manutenção registrada"
            description="Agende manutenções preventivas ou corretivas nos computadores e servidores da empresa."
            actionText="Agendar Manutenção"
            onAction={onNew}
          />
        )}
      </Card>
    </div>
  );
};

export default ITMaintenance;
