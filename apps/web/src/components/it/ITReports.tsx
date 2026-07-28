import React, { useMemo } from 'react';
import { BarChart3, FileText, Download, CheckCircle, ShieldAlert, Wrench, Laptop } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { statusLabel, categoryLabel } from './itApi';

export interface ITReportsProps {
  tickets: any[];
  assetsList: any[];
  certificates: any[];
  maintenances: any[];
  onExportCSV: (type: 'assets' | 'tickets' | 'certificates') => void;
}

const BarChartComponent: React.FC<{ data: { label: string; count: number }[]; color: string }> = ({ data, color }) => {
  const max = Math.max(...data.map(d => d.count), 1);
  return (
    <div className="space-y-3">
      {data.map(item => {
        const pct = (item.count / max) * 100;
        return (
          <div key={item.label} className="space-y-1">
            <div className="flex justify-between text-xs font-bold text-slate-350">
              <span>{item.label}</span>
              <span className="text-white font-extrabold">{item.count}</span>
            </div>
            <div className="w-full bg-slate-950/60 rounded-full h-3 border border-slate-800/80 overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${color}`} 
                style={{ width: `${pct}%` }}
              ></div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const ITReportsPanel: React.FC<{
  tickets: any[];
  assetsList: any[];
  certificates: any[];
  maintenances: any[];
}> = ({ tickets, assetsList, certificates, maintenances }) => {
  const ticketsByStatus = useMemo(() => {
    const counts: Record<string, number> = {};
    tickets.forEach(t => {
      const status = t.status || 'ABERTO';
      counts[status] = (counts[status] || 0) + 1;
    });
    return Object.entries(counts).map(([label, count]) => ({
      label: statusLabel(label),
      count
    }));
  }, [tickets]);

  const ticketsByCategory = useMemo(() => {
    const counts: Record<string, number> = {};
    tickets.forEach(t => {
      const category = t.category || 'OUTRO';
      counts[category] = (counts[category] || 0) + 1;
    });
    return Object.entries(counts).map(([label, count]) => ({
      label: categoryLabel(label),
      count
    }));
  }, [tickets]);

  const assetsByType = useMemo(() => {
    const counts: Record<string, number> = {};
    assetsList.forEach(a => {
      const type = a.asset_type || 'OUTRO';
      counts[type] = (counts[type] || 0) + 1;
    });
    const labels: Record<string, string> = {
      PC: 'Computador/Desktop',
      NOTEBOOK: 'Notebook',
      MONITOR: 'Monitor',
      IMPRESSORA: 'Impressora',
      SERVIDOR: 'Servidor',
      ROTEADOR: 'Roteador',
      SWITCH: 'Switch',
      OUTRO: 'Outro'
    };
    return Object.entries(counts).map(([label, count]) => ({
      label: labels[label] || label,
      count
    }));
  }, [assetsList]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8 pt-6 border-t border-slate-800">
      {/* Distribuição por Status */}
      <Card className="p-5">
        <h4 className="text-sm font-extrabold text-slate-350 uppercase tracking-wider mb-4 flex items-center gap-2">
          📊 Chamados por Status
        </h4>
        {ticketsByStatus.length > 0 ? (
          <BarChartComponent data={ticketsByStatus} color="bg-indigo-500" />
        ) : (
          <p className="text-xs text-slate-500 text-center py-8">Nenhum chamado registrado para métricas.</p>
        )}
      </Card>

      {/* Distribuição por Categoria */}
      <Card className="p-5">
        <h4 className="text-sm font-extrabold text-slate-350 uppercase tracking-wider mb-4 flex items-center gap-2">
          📊 Chamados por Categoria
        </h4>
        {ticketsByCategory.length > 0 ? (
          <BarChartComponent data={ticketsByCategory} color="bg-emerald-500" />
        ) : (
          <p className="text-xs text-slate-500 text-center py-8">Nenhuma categoria com chamados.</p>
        )}
      </Card>

      {/* Ativos por Tipo */}
      <Card className="p-5">
        <h4 className="text-sm font-extrabold text-slate-350 uppercase tracking-wider mb-4 flex items-center gap-2">
          📊 Ativos por Tipo
        </h4>
        {assetsByType.length > 0 ? (
          <BarChartComponent data={assetsByType} color="bg-violet-500" />
        ) : (
          <p className="text-xs text-slate-500 text-center py-8">Nenhum ativo cadastrado para métricas.</p>
        )}
      </Card>
    </div>
  );
};

export const ITReports: React.FC<ITReportsProps> = ({
  tickets,
  assetsList,
  certificates,
  maintenances,
  onExportCSV,
}) => {
  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
          📊 Central de Relatórios de TI
        </h2>
        <p className="text-xs text-slate-400 mb-6 font-medium">
          Exportação de dados auditáveis em conformidade ISO 9001 e visualização gráfica de volumetria.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card Ativos */}
          <Card className="bg-slate-950/20 border-slate-800 p-5 flex flex-col justify-between items-center text-center gap-4 hover:border-slate-700 transition-colors">
            <div className="w-12 h-12 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-full flex items-center justify-center text-2xl">
              💻
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Ativos (Hardware)</h3>
              <p className="text-xs text-slate-400 font-medium my-2">
                Planilha de ativos com número de série, patrimônio, CPU, RAM, hostname e IPs dos dispositivos.
              </p>
            </div>
            <Button size="sm" variant="primary" className="w-full justify-center bg-indigo-650 hover:bg-indigo-600" onClick={() => onExportCSV('assets')} leftIcon={<Download size={14} />}>
              Exportar CSV
            </Button>
          </Card>

          {/* Card Chamados */}
          <Card className="bg-slate-950/20 border-slate-800 p-5 flex flex-col justify-between items-center text-center gap-4 hover:border-slate-700 transition-colors">
            <div className="w-12 h-12 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full flex items-center justify-center text-2xl">
              🎫
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Histórico de Chamados</h3>
              <p className="text-xs text-slate-400 font-medium my-2">
                Histórico completo com datas, SLA, descrições, requisitantes e resoluções técnicas.
              </p>
            </div>
            <Button size="sm" variant="primary" className="w-full justify-center bg-emerald-650 hover:bg-emerald-600" onClick={() => onExportCSV('tickets')} leftIcon={<Download size={14} />}>
              Exportar CSV
            </Button>
          </Card>

          {/* Card Certificados */}
          <Card className="bg-slate-950/20 border-slate-800 p-5 flex flex-col justify-between items-center text-center gap-4 hover:border-slate-700 transition-colors">
            <div className="w-12 h-12 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-full flex items-center justify-center text-2xl">
              🛡️
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Certificados & Licenças</h3>
              <p className="text-xs text-slate-400 font-medium my-2">
                Auditoria de chaves e licenças SSL cadastradas, indicando prazos e vencimentos.
              </p>
            </div>
            <Button size="sm" variant="primary" className="w-full justify-center bg-rose-650 hover:bg-rose-600" onClick={() => onExportCSV('certificates')} leftIcon={<Download size={14} />}>
              Exportar CSV
            </Button>
          </Card>
        </div>

        <ITReportsPanel
          tickets={tickets}
          assetsList={assetsList}
          certificates={certificates}
          maintenances={maintenances}
        />
      </Card>
    </div>
  );
};

export default ITReports;
