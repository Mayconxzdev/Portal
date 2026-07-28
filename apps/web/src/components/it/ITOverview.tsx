import React from 'react';
import { Activity, AlertTriangle, ClipboardList, Database, KeyRound, Laptop, ShieldCheck, Sparkles, Wrench } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { KodaMascot } from '../ui/KodaMascot';

export interface ITOverviewProps {
  summary: {
    open_tickets: number;
    in_progress_tickets: number;
    assets_in_maintenance: number;
    expiring_certificates: number;
  } | null;
  pcsInUseCount: number;
  changeLogs: any[];
  isTauri: boolean;
  collectLoading: boolean;
  onCollectLocal: () => void;
  onJsonImport: () => void;
  onCsvImport: () => void;
  onNewCredential: () => void;
  onNewNote: () => void;
  onCopyScript: () => void;
}

const metrics = [
  { key: 'open_tickets', label: 'Chamados abertos', icon: ClipboardList, tone: 'warning' },
  { key: 'in_progress_tickets', label: 'Em atendimento', icon: Activity, tone: 'info' },
  { key: 'pcs', label: 'PCs em uso', icon: Laptop, tone: 'success' },
  { key: 'assets_in_maintenance', label: 'Em manutenção', icon: Wrench, tone: 'amber' },
  { key: 'expiring_certificates', label: 'Expirações', icon: ShieldCheck, tone: 'danger' },
] as const;

export const ITOverview: React.FC<ITOverviewProps> = ({
  summary,
  pcsInUseCount,
  changeLogs,
  isTauri,
  collectLoading,
  onCollectLocal,
  onJsonImport,
  onCsvImport,
  onNewCredential,
  onNewNote,
  onCopyScript,
}) => {
  const valueFor = (key: string) => key === 'pcs' ? pcsInUseCount : Number((summary as any)?.[key] ?? 0);

  return (
    <div className="space-y-6">
      <div className="it-overview-grid">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <Card key={metric.key} variant="interactive" className={`it-metric-card it-metric-card--${metric.tone}`}>
              <div className="it-metric-icon"><Icon size={22} /></div>
              <div>
                <div className="it-metric-value">{valueFor(metric.key)}</div>
                <div className="it-metric-label">{metric.label}</div>
              </div>
            </Card>
          );
        })}
      </div>

      <div className="module-page-body module-page-body--with-aside">
        <main className="module-page-main">
          <Card className="p-5 space-y-4">
            <div className="flex justify-between items-start gap-4">
              <div>
                <span className="product-eyebrow">Operação diária</span>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Sparkles size={18} /> Ações rápidas
                </h3>
                <p className="text-xs text-slate-400">
                  Atalhos reais para atendimento, inventário e segurança de acessos.
                </p>
              </div>
            </div>

            <div className="quick-action-grid">
              {isTauri ? (
                <button className="quick-action-card" onClick={onCollectLocal} disabled={collectLoading}>
                  <Laptop size={22} />
                  <strong>{collectLoading ? 'Coletando...' : 'Coletar este PC'}</strong>
                  <span>Inventário local seguro pelo app desktop.</span>
                </button>
              ) : (
                <button className="quick-action-card quick-action-card--disabled" disabled>
                  <Laptop size={22} />
                  <strong>Coleta desktop</strong>
                  <span>Disponível no Portal Vesper Desktop/Tauri.</span>
                </button>
              )}
              <button className="quick-action-card" onClick={onCopyScript}>
                <ClipboardList size={22} />
                <strong>Copiar coletor</strong>
                <span>Script controlado para coleta manual.</span>
              </button>
              <button className="quick-action-card" onClick={onJsonImport}>
                <Database size={22} />
                <strong>Importar JSON</strong>
                <span>Pré-visualize antes de aplicar.</span>
              </button>
              <button className="quick-action-card" onClick={onCsvImport}>
                <Database size={22} />
                <strong>Importar CSV</strong>
                <span>Atualização em lote do inventário.</span>
              </button>
              <button className="quick-action-card" onClick={onNewCredential}>
                <KeyRound size={22} />
                <strong>Nova credencial</strong>
                <span>Cofre mascarado e auditado.</span>
              </button>
              <button className="quick-action-card" onClick={onNewNote}>
                <ClipboardList size={22} />
                <strong>Nova nota</strong>
                <span>Lembretes visuais para a equipe.</span>
              </button>
            </div>
          </Card>

          <Card className="p-5 space-y-4">
            <div>
              <span className="product-eyebrow">Auditoria recente</span>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Activity size={18} /> Histórico operacional
              </h3>
            </div>
            <div className="timeline-list">
              {changeLogs.slice(0, 10).map((log) => (
                <div key={log.id} className="timeline-item">
                  <div className="timeline-dot" />
                  <div>
                    <strong>{log.action || 'Atualização'}</strong>
                    <p>
                      {log.entity_type || 'Registro'} {log.entity_id ? `#${log.entity_id}` : ''} por{' '}
                      <span>{log.user?.username || 'Sistema'}</span>
                    </p>
                    {log.field_name && (
                      <small>
                        {log.field_name}: {log.old_value || 'vazio'} → {log.new_value || 'vazio'}
                      </small>
                    )}
                  </div>
                  <time>{log.created_at ? new Date(log.created_at).toLocaleString('pt-BR') : ''}</time>
                </div>
              ))}
              {changeLogs.length === 0 && (
                <div className="product-empty-inline">
                  <AlertTriangle size={18} />
                  <span>Nenhum evento registrado ainda.</span>
                </div>
              )}
            </div>
          </Card>
        </main>

        <aside className="module-page-aside">
          <Card className="help-card">
            <KodaMascot size="sm" mood="help" />
            <div>
              <h4>Dicas do Koda</h4>
              <p>
                Use a coleta desktop quando estiver no app Tauri. No navegador, importe JSON/CSV com prévia antes de salvar.
              </p>
              <Button variant="secondary" size="sm" onClick={onJsonImport}>Importar inventário</Button>
            </div>
          </Card>
          <Card className="module-side-card">
            <h4 className="dashboard-side-title">Segurança</h4>
            <div className="dashboard-empty-alert">
              <ShieldCheck size={16} />
              <span>Credenciais só aparecem mediante confirmação e auditoria.</span>
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
};

export default ITOverview;
